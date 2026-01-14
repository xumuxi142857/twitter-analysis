import json
import os
import re
import requests
import hashlib
import traceback
from datetime import datetime

# ================= 配置区域 =================
# 📅 指定日期
TARGET_DATE = "2025-12-25" 

API_KEY = "sk-mwphmyljrynungesqkaqnbimwghczzpniulmdgepgswhjrco"
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'database', 'raw')
OUTPUT_DIR = os.path.join(BASE_DIR, 'public', 'db', 'topic')

FILENAME_MAPPING = {
    "Taiwan": "Taiwan",
    "China_US": "US", 
    "Philippines": "Philippines",
    "Japan": "Japan",
    "JP": "Japan",
    "ph": "Philippines",
    "us": "US",
    "jp": "Japan",
    "tw": "Taiwan"
}
# ===========================================

def parse_date_from_filename(filename):
    # 兼容带时间后缀和不带后缀的文件名
    match = re.search(r'(20[2-3]\d{5})', filename)
    if match:
        date_str = match.group(1)
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return None

def get_files_fingerprint(date_key):
    target_date_str = date_key.replace("-", "") 
    related_files = []
    
    if os.path.exists(RAW_DIR):
        for root, dirs, files in os.walk(RAW_DIR):
            for f in files:
                if target_date_str in f and f.endswith('.json'):
                    path = os.path.join(root, f)
                    stat = os.stat(path)
                    related_files.append(f"{f}_{stat.st_size}_{stat.st_mtime}")
    
    if not related_files: return None
    related_files.sort()
    combined_str = "|".join(related_files)
    return hashlib.md5(combined_str.encode('utf-8')).hexdigest()

def load_data_for_target_date(target_date):
    region_data = {}
    target_date_str = target_date.replace("-", "")
    
    if not os.path.exists(RAW_DIR):
        print(f"❌ 错误: 找不到目录 {RAW_DIR}")
        return region_data

    print(f"📂 正在扫描 {RAW_DIR} 中包含 '{target_date_str}' 的文件...")
    file_count = 0
    
    for root, dirs, files in os.walk(RAW_DIR):
        for filename in files:
            if not filename.endswith('.json'): continue
            if target_date_str not in filename: continue
            
            target_region = None
            for key, region in FILENAME_MAPPING.items():
                if key.lower() in filename.lower(): 
                    target_region = region
                    break
            if not target_region: continue

            if target_region not in region_data: region_data[target_region] = []

            path = os.path.join(root, filename)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get('full_text'):
                            region_data[target_region].append(item)
                    file_count += 1
            except: pass
            
    print(f"✅ 扫描完成，共找到 {file_count} 个相关文件")
    return region_data

def call_llm_analysis(region, date, raw_items):
    """
    【增强版】智能采样 + LLM 分析 + 错误调试
    """
    if not raw_items: return None

    # 1. 去重
    unique_items = {}
    for item in raw_items:
        key = item.get('tweet_id') or item.get('full_text')
        unique_items[key] = item
    clean_items = list(unique_items.values())

    # 2. 按影响力排序
    def calculate_impact(item):
        retweet = item.get('retweet_count', 0) or 0
        reply = item.get('reply_count', 0) or 0
        like = item.get('favorite_count', 0) or 0
        return (retweet * 2) + (reply * 1) + (like * 0.5)

    clean_items.sort(key=calculate_impact, reverse=True)

    # 3. 截取 Top 50
    top_items = clean_items[:50]
    print(f"      [采样] {region}: 原始 {len(raw_items)} 条 -> 精选 Top {len(top_items)} 条")

    # 4. 构建 Prompt
    input_list = []
    for idx, item in enumerate(top_items):
        text = item.get('full_text', '').replace('\n', ' ').strip()
        if len(text) > 15:
            input_list.append(f"ID[{idx}]: {text}")
    
    input_text_str = "\n".join(input_list)
    
    prompt = f"""
    你是一个情报分析员。请分析以下“{region}”板块的推特文本。
    
    文本列表 (带ID):
    {input_text_str}

    任务：
    1. 【话题聚类】将推文聚类为 Top 10 核心话题。一定不要有重复的话题。
    2. 【立场研判】列出每个话题下的推文ID，并判断该推文的立场(positive/neutral/negative)。
    3. 【词云提取】提取 Top 15 热门关键词 ,要翻译为中文(排除通用国家名，只保留具体事件/实体)。
    
    输出 JSON 格式：
    {{
        "top_topics": [
            {{
                "topic": "话题摘要",
                "tweet_ids": [
                    {{"id": 0, "stance": "negative"}},
                    {{"id": 3, "stance": "neutral"}}
                ]
            }}
        ],
        "hot_words": [
            {{"name": "具体名词", "value": 88}}
        ]
    }}
    """

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a data analyst. Output raw JSON only. Do not use Markdown blocks."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(API_URL, json=payload, headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }, timeout=60) # 增加超时设置
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            
            # 【关键修改】清洗 Markdown 标记，防止 JSON 解析挂掉
            content = content.replace('```json', '').replace('```', '').strip()
            
            try:
                llm_json = json.loads(content)
            except json.JSONDecodeError:
                print(f"❌ JSON 解析失败 [{region}]！LLM 返回了非 JSON 内容。")
                print(f"🔍 返回内容片段: {content[:100]}...")
                return None
            
            # 数据回填
            final_topics = []
            for topic_obj in llm_json.get('top_topics', []):
                enriched_tweets = []
                for t_ref in topic_obj.get('tweet_ids', []):
                    tid = t_ref.get('id')
                    stance = t_ref.get('stance', 'neutral')
                    
                    if isinstance(tid, int) and 0 <= tid < len(top_items):
                        original = top_items[tid]
                        enriched_tweets.append({
                            "text": original.get('full_text', ''),
                            "stance": stance,
                            "username": original.get('username', 'Unknown'),
                            "created_at": original.get('created_at', ''),
                            "metrics": {
                                "reply": original.get('reply_count', 0),
                                "retweet": original.get('retweet_count', 0),
                                "like": original.get('favorite_count', 0)
                            }
                        })
                
                if enriched_tweets:
                    final_topics.append({
                        "topic": topic_obj.get('topic'),
                        "tweets": enriched_tweets
                    })
            
            return {
                "top_topics": final_topics,
                "hot_words": llm_json.get('hot_words', [])
            }
        else:
            print(f"❌ API 请求失败 [{region}]: {response.status_code}")
            print(f"🔍 错误详情: {response.text}")
            
    except Exception as e:
        print(f"❌ 处理异常 [{region}]: {e}")
        traceback.print_exc() # 打印完整报错堆栈
    
    return None

def main():
    print(f"🚀 开始执行单日话题分析模式 | 目标日期: {TARGET_DATE}")
    
    out_path = os.path.join(OUTPUT_DIR, f"{TARGET_DATE}.json")
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    
    regions_data = load_data_for_target_date(TARGET_DATE)
    
    if not regions_data:
        print(f"⚠️ 未找到日期 {TARGET_DATE} 的任何数据。")
        return

    print(f"\n──────────────────────────────────────────")
    print(f"🔄 正在分析: {TARGET_DATE}")
    
    # 强制重新分析，为了调试，暂时注释掉指纹跳过逻辑
    # 如果想恢复跳过，请取消下面两行的注释
    # if not check_needs_update(out_path, get_files_fingerprint(TARGET_DATE)):
    #     print(f"⏩ 数据未变动，跳过")
    #     return
    
    daily_result = {}
    current_fingerprint = get_files_fingerprint(TARGET_DATE)
    
    for region, items in regions_data.items():
        print(f"   -> 正在处理 [{region}] 板块...")
        
        analysis = call_llm_analysis(region, TARGET_DATE, items)
        
        if analysis:
            print(f"      ✅ [{region}] 分析成功")
            daily_result[region] = {
                "region": region,
                "time_range": [TARGET_DATE, TARGET_DATE],
                "top_topics": analysis.get('top_topics', []),
                "hot_words": analysis.get('hot_words', [])
            }
        else:
            print(f"      ⚠️ [{region}] 分析返回为空，结果将为空白")
            daily_result[region] = {"top_topics": [], "hot_words": []}
    
    daily_result["_meta"] = {
        "fingerprint": current_fingerprint,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(daily_result, f, ensure_ascii=False, indent=2)
    print(f"✅ 生成成功: {out_path}")

if __name__ == "__main__":
    main()