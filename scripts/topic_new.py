import json
import os
import re
import requests
import hashlib
from datetime import datetime

# ================= 配置区域 =================
API_KEY = "sk-mwphmyljrynungesqkaqnbimwghczzpniulmdgepgswhjrco" 
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'database1', 'raw')
OUTPUT_DIR = os.path.join(BASE_DIR, 'public', 'db', 'topic')

FILENAME_MAPPING = {
    "Taiwan": "Taiwan",
    "US": "US", 
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
    match = re.search(r'(\d{8})_(\d{6})', filename)
    if match:
        date_str = match.group(1)
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return None

def get_files_fingerprint(date_key):
    """
    计算该日期下所有相关文件的指纹。
    """
    target_date_str = date_key.replace("-", "") 
    related_files = []
    
    if os.path.exists(RAW_DIR):
        for root, dirs, files in os.walk(RAW_DIR):
            for f in files:
                if target_date_str in f and f.endswith('.json'):
                    path = os.path.join(root, f)
                    stat = os.stat(path)
                    # 包含文件路径、大小、修改时间，确保唯一性
                    related_files.append(f"{f}_{stat.st_size}_{stat.st_mtime}")
    
    if not related_files: return None
    related_files.sort()
    combined_str = "|".join(related_files)
    return hashlib.md5(combined_str.encode('utf-8')).hexdigest()

def check_needs_update(output_file, current_fingerprint):
    if not os.path.exists(output_file): return True
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            saved_fingerprint = data.get('_meta', {}).get('fingerprint', '')
            return saved_fingerprint != current_fingerprint
    except: return True

def load_and_group_by_date():
    """
    【关键逻辑】
    遍历文件夹，将数据整理为:
    grouped_data[日期][地区] = [推文列表]
    """
    grouped_data = {}
    if not os.path.exists(RAW_DIR): return grouped_data

    print(f"📂 正在扫描 {RAW_DIR} 及其子目录...")
    
    file_count = 0
    # 使用 os.walk 递归扫描所有子文件夹
    for root, dirs, files in os.walk(RAW_DIR):
        for filename in files:
            if not filename.endswith('.json'): continue
            
            # 1. 识别日期
            date_key = parse_date_from_filename(filename)
            if not date_key: continue
            
            # 2. 识别地区
            target_region = None
            for key, region in FILENAME_MAPPING.items():
                if key.lower() in filename.lower(): 
                    target_region = region
                    break
            if not target_region: continue

            # 3. 初始化字典结构
            if date_key not in grouped_data: grouped_data[date_key] = {}
            if target_region not in grouped_data[date_key]: grouped_data[date_key][target_region] = []

            # 4. 读取数据并归类
            path = os.path.join(root, filename)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    items = data if isinstance(data, list) else [data]
                    
                    for item in items:
                        if item.get('full_text'):
                            # 将推文放入 [特定日期][特定地区] 的列表中
                            grouped_data[date_key][target_region].append(item)
                    file_count += 1
            except: pass
            
    print(f"✅ 扫描完成，共识别 {file_count} 个有效数据文件")
    return grouped_data

def call_llm_analysis(region, date, raw_items):
    """
    【智能采样】
    输入: 仅包含某一天、某一个地区的 raw_items
    输出: 分析结果
    """
    if not raw_items: return None

    # 1. 去重 (按推文ID 或 文本)
    unique_items = {}
    for item in raw_items:
        key = item.get('tweet_id') or item.get('full_text')
        unique_items[key] = item
    clean_items = list(unique_items.values())

    # 2. 按影响力排序 (Top-N 策略)
    # 影响力 = 转发*2 + 回复 + 点赞*0.5
    def calculate_impact(item):
        retweet = item.get('retweet_count', 0) or 0
        reply = item.get('reply_count', 0) or 0
        like = item.get('favorite_count', 0) or 0
        return (retweet * 2) + (reply * 1) + (like * 0.5)

    clean_items.sort(key=calculate_impact, reverse=True)

    # 3. 截取 Top 100
    # 这确保了我们只分析这一天这个地区最火的 100 条推文
    top_items = clean_items[:100]
    
    # 打印日志证明逻辑是正确的
    print(f"      [采样日志] {date} | {region}: 原始 {len(raw_items)} 条 -> 精选 Top {len(top_items)} 条")

    # 4. 构建 Prompt 输入
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
    1. 【话题聚类】将推文聚类为 Top 10 核心话题。
    2. 【立场研判】列出每个话题下的推文ID，并判断该推文的立场(positive/neutral/negative)。
    3. 【词云提取】提取 Top 20 热门关键词 (排除通用国家名，只保留具体事件/实体)。
    
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
            {"role": "system", "content": "You are a data analyst. Output raw JSON only."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(API_URL, json=payload, headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        })
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            llm_json = json.loads(content)
            
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
            print(f"⚠️ API Error ({region}): {response.status_code}")
    except Exception as e:
        print(f"⚠️ Exception ({region}): {e}")
    
    return None

def main():
    print("🚀 开始执行话题溯源分析 (Topic Drill-down & Metadata)...")
    
    # 1. 先按日期和地区分组
    date_groups = load_and_group_by_date()
    
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

    # 2. 遍历每一个日期 (例如 2025-12-25)
    for date_key, regions_data in date_groups.items():
        out_path = os.path.join(OUTPUT_DIR, f"{date_key}.json")
        current_fingerprint = get_files_fingerprint(date_key)
        
        # 智能跳过逻辑
        if not check_needs_update(out_path, current_fingerprint):
            print(f"⏩ 日期 {date_key} 未变动，跳过")
            continue

        print(f"\n──────────────────────────────────────────")
        print(f"🔄 正在处理日期: {date_key}")
        
        daily_result = {}
        
        # 3. 遍历该日期下的每一个地区 (例如 US, Philippines)
        for region, items in regions_data.items():
            print(f"   -> 正在分析 [{region}] 板块...")
            
            # 这里的 items 只是当天的、该地区的数据
            analysis = call_llm_analysis(region, date_key, items)
            
            if analysis:
                daily_result[region] = {
                    "region": region,
                    "time_range": [date_key, date_key],
                    "top_topics": analysis.get('top_topics', []),
                    "hot_words": analysis.get('hot_words', [])
                }
            else:
                daily_result[region] = {"top_topics": [], "hot_words": []}
        
        daily_result["_meta"] = {
            "fingerprint": current_fingerprint,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(daily_result, f, ensure_ascii=False, indent=2)
        print(f"✅ 日期 {date_key} 更新成功")

    print("\n🎉 全部处理完成！")

if __name__ == "__main__":
    main()