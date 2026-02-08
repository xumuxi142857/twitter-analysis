import json
import os
import re
import requests
import hashlib
import sys
import time
import math
from datetime import datetime

# ================= 配置区域 =================
if len(sys.argv) > 1:
    TARGET_DATE = sys.argv[1]
else:
    TARGET_DATE = "2025-12-23"

# ⚠️ 1. 批处理大小：保持 15-20
BATCH_SIZE = 20
# ⚠️ 2. 最大限制：想要更多数据，请把这里设大 (例如 800) 或者设为 0 (不限制，跑完为止)
MAX_PROCESS_LIMIT = 20

# API 配置 (你现在的 SiliconFlow 配置)
API_KEY = "sk-mwphmyljrynungesqkaqnbimwghczzpniulmdgepgswhjrco" 
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL_NAME = "Pro/zai-org/GLM-4.7"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'database', 'raw')
OUTPUT_DIR = os.path.join(BASE_DIR, 'public', 'db', 'topic')

FILENAME_MAPPING = {
    "Taiwan": "Taiwan", "China_US": "US", "Philippines": "Philippines",
    "Japan": "Japan", "JP": "Japan", "ph": "Philippines", "us": "US", "jp": "Japan", "tw": "Taiwan"
}
# ===========================================

def get_files_fingerprint(date_key):
    target_date_str = date_key.replace("-", "") 
    related_files = []
    if os.path.exists(RAW_DIR):
        for root, dirs, files in os.walk(RAW_DIR):
            for f in files:
                if target_date_str in f and f.endswith('.json'):
                    try:
                        stat = os.stat(os.path.join(root, f))
                        related_files.append(f"{f}_{stat.st_size}")
                    except: pass
    return hashlib.md5("|".join(sorted(related_files)).encode('utf-8')).hexdigest()

def load_data_for_target_date(target_date):
    region_data = {}
    target_date_str = target_date.replace("-", "")
    if not os.path.exists(RAW_DIR): return region_data
    
    print(f"📂 扫描原始数据: {target_date} ...")
    for root, dirs, files in os.walk(RAW_DIR):
        for filename in files:
            if not filename.endswith('.json') or target_date_str not in filename: continue
            
            target_region = None
            for key, region in FILENAME_MAPPING.items():
                if key.lower() in filename.lower(): 
                    target_region = region
                    break
            if not target_region: continue

            if target_region not in region_data: region_data[target_region] = []
            try:
                with open(os.path.join(root, filename), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get('full_text'):
                            region_data[target_region].append(item)
            except: pass
    return region_data

def repair_json(json_str):
    json_str = json_str.strip()
    if not json_str.endswith(']') and not json_str.endswith('}'):
        if json_str.endswith(','): json_str = json_str[:-1]
        try: return json.loads(json_str + ']')
        except: 
            try: return json.loads(json_str + '}')
            except: pass
    try: return json.loads(json_str)
    except: return None

def call_llm(prompt, max_tokens=4096):
    try:
        response = requests.post(API_URL, json={
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": "You are a JSON generator. Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"}
        }, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=120)
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            match = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', content)
            if match:
                return repair_json(match.group(0))
    except Exception as e:
        print(f"⚠️ LLM 调用异常: {e}")
    return None

def batch_process_tweets(tweets, region):
    """
    Step 1: 分批全量处理。
    """
    processed_results = []
    total_batches = math.ceil(len(tweets) / BATCH_SIZE)
    
    print(f"   [Step 1] 正在处理 {len(tweets)} 条推文，分 {total_batches} 批执行...")

    for i in range(0, len(tweets), BATCH_SIZE):
        batch = tweets[i : i + BATCH_SIZE]
        print(f"      -> 处理批次 {i//BATCH_SIZE + 1}/{total_batches} ...")
        
        input_txt = ""
        for idx, t in enumerate(batch):
            text = t.get('full_text', '').replace('\n', ' ').replace('"', "'")[:200]
            input_txt += f"ID[{idx}]: {text}\n"

        # 提示词微调：要求尽量保留数据，只剔除明显无意义的
        prompt = f"""
        你是一个情报分析助手。请处理以下推文。
        
        {input_txt}

        任务：
        1. 判断推文是否有内容 (is_valid)。**保留所有包含观点、新闻、事实的推文**，仅剔除纯乱码或纯广告。
        2. 翻译成中文 (translation)。出现的推特用户名（例如@Creed_is_T1)可以忽略，不出现在正文中.
        3. 判断这篇推文对中国的立场 (stance): positive(亲华)/neutral(中立)/negative(反华)。
        4. 提取 2-3 个核心中文关键词 (keywords)，用于后续聚类。

        输出 JSON:
        {{
            "results": [
                {{ "id": 0, "is_valid": true, "translation": "...", "stance": "negative", "keywords": ["半导体", "制裁"] }},
                ...
            ]
        }}
        """
        
        res = call_llm(prompt)
        if res and 'results' in res:
            for item in res['results']:
                local_id = item.get('id')
                if local_id is not None and 0 <= local_id < len(batch):
                    if item.get('is_valid', True): 
                        original_tweet = batch[local_id]
                        processed_results.append({
                            "original_obj": original_tweet,
                            "translation": item.get('translation'),
                            "stance": item.get('stance'),
                            "keywords": item.get('keywords', [])
                        })
        
        # 简单防限流
        time.sleep(0.5)

    return processed_results

def generate_topic_definitions(processed_tweets):
    """
    Step 2: 让 LLM 只生成话题定义（不归类 ID，节省 Token）。
    """
    if not processed_tweets: return [], []

    print(f"   [Step 2] 正在分析 {len(processed_tweets)} 条推文的关键词以制定话题...")

    # 只提取关键词给 LLM
    all_keywords = []
    for item in processed_tweets:
        all_keywords.extend(item['keywords'])
    
    # 为了防止关键词太多，截取前 800 个词（通常足够代表整体趋势）
    keywords_text = ", ".join(all_keywords[:800])

    prompt = f"""
    以下是当前社交媒体上关于某地区的热门关键词集合：
    {keywords_text}

    任务：
    1. 根据这些关键词，总结出 5-10 个核心舆情话题。
    2. **话题名称 (topic)** 必须是具体的短语 (如"南海冲突", "芯片法案")。尽量少出现国家名(如“中国，美国”)，用更加具体的词语来替代，并且扩展成一个类似热搜的话题，例如“冬季风暴造成至少30人死亡”。
    3. 为每个话题提供 3-5 个**代表性关键词 (tags)**，**关键词不要出现国家名(如中国，美国)**。
    4. 提取 Top 15 全局热词 (hot_words)。

    输出 JSON:
    {{
        "topics": [
            {{ "topic": "话题名称", "tags": ["关键词1", "关键词2"] }},
            ...
        ],
        "hot_words": [ {{ "name": "词", "value": 10 }} ]
    }}
    """

    res = call_llm(prompt)
    if not res: return [], []
    
    return res.get('topics', []), res.get('hot_words', [])

def classify_tweets_locally(processed_tweets, topic_definitions):
    """
    Step 3: 本地 Python 归类算法。
    强制将 Step 1 的推文分配给 Step 2 的话题，保证数据量。
    """
    print(f"   [Step 3] 正在本地归类 {len(processed_tweets)} 条推文...")
    
    # 初始化结果结构
    final_clusters = {t['topic']: {'topic': t['topic'], 'tweets': [], 'tags': t.get('tags', [])} for t in topic_definitions}
    # 增加一个“其他话题”兜底
    final_clusters["其他热点"] = {'topic': "其他热点", 'tweets': [], 'tags': []}

    for tweet in processed_tweets:
        best_topic = "其他热点"
        max_score = 0
        
        # 推文的特征：它的关键词 + 翻译文本
        tweet_text = (tweet['translation'] + " " + " ".join(tweet['keywords'])).lower()
        
        for topic in topic_definitions:
            score = 0
            # 1. 匹配话题名称
            if topic['topic'].lower() in tweet_text:
                score += 5
            # 2. 匹配话题标签
            for tag in topic.get('tags', []):
                if tag.lower() in tweet_text:
                    score += 2
            
            if score > max_score:
                max_score = score
                best_topic = topic['topic']
        
        # 只有匹配度大于0才进特定话题，否则进“其他”
        if max_score > 0:
            target_key = best_topic
        else:
            target_key = "其他热点"

        # 构造前端需要的数据格式
        orig = tweet['original_obj']
        tweet_data = {
            "text": orig.get('full_text', ''),
            "translation": tweet['translation'], 
            "stance": tweet['stance'],           
            "username": orig.get('username', 'Unknown'),
            "created_at": orig.get('created_at', ''),
            "metrics": {
                "reply": orig.get('reply_count', 0),
                "retweet": orig.get('retweet_count', 0),
                "like": orig.get('favorite_count', 0)
            }
        }
        final_clusters[target_key]['tweets'].append(tweet_data)

    # 转换为列表并过滤空话题
    sorted_topics = []
    # 先把非“其他”的按数量排序
    regular_topics = [v for k, v in final_clusters.items() if k != "其他热点" and len(v['tweets']) > 0]
    regular_topics.sort(key=lambda x: len(x['tweets']), reverse=True)
    sorted_topics.extend(regular_topics)
    
    # 最后放“其他”
    if len(final_clusters["其他热点"]['tweets']) > 0:
        sorted_topics.append(final_clusters["其他热点"])
        
    return sorted_topics

def calculate_stance_stats(topics):
    stats = {"positive": 0, "neutral": 0, "negative": 0}
    for t in topics:
        for tw in t['tweets']:
            s = str(tw.get('stance', 'neutral')).lower()
            if 'positive' in s or '亲华' in s: stats['positive'] += 1
            elif 'negative' in s or '反华' in s: stats['negative'] += 1
            else: stats['neutral'] += 1
    return [
        {"name": "亲华 (Positive)", "value": stats['positive']},
        {"name": "中立 (Neutral)", "value": stats['neutral']},
        {"name": "反华 (Negative)", "value": stats['negative']}
    ]

def main():
    print(f"🚀 [海量数据模式] 开始执行 | 日期: {TARGET_DATE}")
    print(f"⚙️  配置: 批大小={BATCH_SIZE}, 最大处理限制={MAX_PROCESS_LIMIT} (0为不限)")
    
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    out_path = os.path.join(OUTPUT_DIR, f"{TARGET_DATE}.json")

    current_data = {}
    if os.path.exists(out_path):
        try:
            with open(out_path, 'r', encoding='utf-8') as f:
                current_data = json.load(f)
        except: pass

    regions_map = load_data_for_target_date(TARGET_DATE)
    if not regions_map:
        print("⚠️ 未找到源数据")
        return

    print(f"\n──────────────────────────────────────────")
    
    for region, items in regions_map.items():
        print(f"🔄 处理板块: [{region}] (源数据共 {len(items)} 条)...")
        
        # 1. 预过滤
        unique_items = { (i.get('tweet_id') or i.get('full_text')): i for i in items }.values()
        clean_items = list(unique_items)
        if MAX_PROCESS_LIMIT > 0:
            clean_items = clean_items[:MAX_PROCESS_LIMIT]

        # 2. Step 1: LLM 逐条翻译判立
        processed = batch_process_tweets(clean_items, region)
        if not processed:
            print(f"   ❌ [{region}] 无有效推文")
            continue

        # 3. Step 2: LLM 定义话题
        topic_defs, hot_words = generate_topic_definitions(processed)

        # 4. Step 3: Python 本地归类 (保证数量)
        final_topics = classify_tweets_locally(processed, topic_defs)
        
        # 5. 统计
        stance_stats = calculate_stance_stats(final_topics)

        # 6. 保存
        current_data[region] = {
            "region": region,
            "time_range": [TARGET_DATE, TARGET_DATE],
            "top_topics": final_topics,
            "hot_words": hot_words,
            "stance_stats": stance_stats,
            "total_analyzed": len(processed)
        }
        
        try:
            current_data["_meta"] = {
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, ensure_ascii=False, indent=2)
            
            total_tweets = sum(len(t['tweets']) for t in final_topics)
            print(f"   ✅ [{region}] 完成: 生成 {len(final_topics)} 个话题, 包含 {total_tweets} 条推文")
        except Exception as e:
            print(f"   ❌ [{region}] 保存失败: {e}")

    print(f"\n🎉 任务结束: {out_path}")

if __name__ == "__main__":
    main()