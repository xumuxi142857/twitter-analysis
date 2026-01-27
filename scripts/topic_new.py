import json
import os
import re
import requests
import hashlib
import sys
import time
import math
from datetime import datetime  # <--- 补上了这个关键的 import

# ================= 配置区域 =================
if len(sys.argv) > 1:
    TARGET_DATE = sys.argv[1]
else:
    TARGET_DATE = "2026-01-26"

# ⚠️ 批处理大小：每批处理 15 条
BATCH_SIZE = 15
# ⚠️ 最大处理数量：上限，设为 0 则不限制
MAX_PROCESS_LIMIT = 300

#API_KEY = "sk-7ba052d40efe48ae990141e577d952d1" 
#API_URL = "https://api.deepseek.com/chat/completions"
#MODEL_NAME = "deepseek-chat" 

API_KEY = "sk-mwphmyljrynungesqkaqnbimwghczzpniulmdgepgswhjrco" 
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL_NAME = "Pro/zai-org/GLM-4.7" 

#API_KEY = "sk-jtDFyIPxnt2jqyHQPVsxiZwEcWOY2592WvEqN2F6tYP1juu6" 
#API_URL = "https://api.302.ai/v1/chat/completions"
#MODEL_NAME = "gpt-5-nano-2025-08-07" 

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
    """尝试修复截断的 JSON"""
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
    第一阶段：分批处理。翻译、判立、提取关键词、过滤垃圾。
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

        prompt = f"""
        你是一个情报分析助手。请处理以下推文列表。
        
        {input_txt}

        任务：
        1. 判断推文是否有情报价值 (is_valid)。跳过纯广告、乱码或无关内容。
        2. 翻译成中文 (translation) 出现的推特用户名（例如@Creed_is_T1，可以忽略，不出现在正文中）。
        3. 判断对华立场 (stance): positive(亲华)/neutral(中立)/negative(反华)。
        4. 提取 2-3 个核心关键词或短语 (keywords)，必须是原文中出现的高频词汇翻译成的中文。

        输出 JSON 列表:
        {{
            "results": [
                {{ "id": 0, "is_valid": true, "translation": "...", "stance": "negative", "keywords": ["贸易战", "关税"] }},
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
        
        time.sleep(1) 

    return processed_results

def global_cluster_topics(processed_tweets, region):
    """
    第二阶段：基于所有提取出的关键词进行聚类。
    """
    if not processed_tweets: return [], []

    print(f"   [Step 2] 正在对 {len(processed_tweets)} 条有效推文进行全局聚类...")

    # 准备聚类输入：只发送 ID 和 关键词
    cluster_input = ""
    for idx, item in enumerate(processed_tweets):
        kws = ", ".join(item['keywords'])
        cluster_input += f"GID[{idx}]: {kws}\n"

    prompt = f"""
    以下是多条推文的关键词列表。请根据这些关键词将推文归类为 五到十 个核心话题。

    {cluster_input}

    核心要求：
    1. **话题名称(topic)** 必须是具体的、在推文中出现过的**高频短语** (如"半导体制裁", "海警船碰撞")，尽量少出现国家名(如“中国，美国”)，用更加具体的词语来替代，并且扩展成一个类似热搜的话题，例如“冬季风暴造成至少30人死亡”。
    2. 每个推文 (GID) 只能归入一个最匹配的话题。
    3. 同时提取整个数据集的 Top 15 热门词云 (hot_words)。

    输出 JSON:
    {{
        "topics": [
            {{ "topic": "具体短语", "gids": [0, 5, 12...] }},
            ...
        ],
        "hot_words": [ {{ "name": "词", "value": 10 }} ]
    }}
    """

    res = call_llm(prompt)
    if not res: return [], []

    final_topics = []
    used_gids = set()

    for topic_obj in res.get('topics', []):
        topic_name = topic_obj.get('topic', '未命名话题')
        tweets_in_topic = []
        
        for gid in topic_obj.get('gids', []):
            if isinstance(gid, int) and 0 <= gid < len(processed_tweets):
                pt = processed_tweets[gid]
                orig = pt['original_obj']
                tweets_in_topic.append({
                    "text": orig.get('full_text', ''),
                    "translation": pt['translation'], 
                    "stance": pt['stance'],           
                    "username": orig.get('username', 'Unknown'),
                    "created_at": orig.get('created_at', ''),
                    "metrics": {
                        "reply": orig.get('reply_count', 0),
                        "retweet": orig.get('retweet_count', 0),
                        "like": orig.get('favorite_count', 0)
                    }
                })
                used_gids.add(gid)
        
        if tweets_in_topic:
            final_topics.append({
                "topic": topic_name,
                "tweets": tweets_in_topic
            })
    
    return final_topics, res.get('hot_words', [])

def calculate_stance_stats(topics):
    """统计全板块的立场分布"""
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
    print(f"🚀 [全量分析模式] 开始执行 | 日期: {TARGET_DATE}")
    
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
        print(f"🔄 处理板块: [{region}] (共 {len(items)} 条)...")
        
        # 1. 预过滤 (去重 & 限制数量)
        unique_items = { (i.get('tweet_id') or i.get('full_text')): i for i in items }.values()
        clean_items = list(unique_items)
        if MAX_PROCESS_LIMIT > 0:
            clean_items = clean_items[:MAX_PROCESS_LIMIT]

        # 2. 第一步：分批次全量分析
        processed = batch_process_tweets(clean_items, region)
        
        if not processed:
            print(f"   ❌ [{region}] 无有效推文，跳过")
            continue

        # 3. 第二步：全局聚类
        topics, hot_words = global_cluster_topics(processed, region)
        
        # 4. 计算统计数据
        stance_chart_data = calculate_stance_stats(topics)

        # 5. 保存 (每做一个板块就存一次)
        current_data[region] = {
            "region": region,
            "time_range": [TARGET_DATE, TARGET_DATE],
            "top_topics": topics,
            "hot_words": hot_words,
            "stance_stats": stance_chart_data, 
            "total_analyzed": len(processed)
        }
        
        # 安全保存：这里使用了 try-except 防止保存时崩溃导致数据丢失
        try:
            current_data["_meta"] = {
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, ensure_ascii=False, indent=2)
            print(f"   ✅ [{region}] 完成: {len(topics)} 个话题, 分析了 {len(processed)} 条推文")
        except Exception as e:
            print(f"   ❌ [{region}] 保存文件失败: {e}")
            # 尝试备份保存
            with open(f"{out_path}.bak", 'w', encoding='utf-8') as f:
                json.dump(current_data, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 任务结束: {out_path}")

if __name__ == "__main__":
    main()