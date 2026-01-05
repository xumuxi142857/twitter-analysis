import json
import os
import re
import requests
import hashlib
from datetime import datetime
import time

# ================= 配置区域 =================
# DeepSeek API
API_KEY = "sk-7ba052d40efe48ae990141e577d952d1"  # 
API_URL = "https://api.deepseek.com/chat/completions"
MODEL_NAME = "deepseek-chat"  # 

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
    match = re.search(r'(\d{8})_(\d{6})', filename)
    if match:
        date_str = match.group(1)
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return None

def get_files_fingerprint(date_key):
    target_date_str = date_key.replace("-", "") 
    related_files = []
    if os.path.exists(RAW_DIR):
        for f in os.listdir(RAW_DIR):
            if target_date_str in f and f.endswith('.json'):
                path = os.path.join(RAW_DIR, f)
                stat = os.stat(path)
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
            if saved_fingerprint != current_fingerprint: return True
            return False
    except: return True

def load_and_group_by_date():
    grouped_data = {}
    if not os.path.exists(RAW_DIR): return grouped_data

    for filename in os.listdir(RAW_DIR):
        if not filename.endswith('.json'): continue
        date_key = parse_date_from_filename(filename)
        if not date_key: continue
        target_region = None
        for key, region in FILENAME_MAPPING.items():
            if key.lower() in filename.lower(): 
                target_region = region
                break
        if not target_region: continue

        if date_key not in grouped_data: grouped_data[date_key] = {}
        if target_region not in grouped_data[date_key]: grouped_data[date_key][target_region] = []

        path = os.path.join(RAW_DIR, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                items = data if isinstance(data, list) else [data]
                
                for item in items:
                    if item.get('full_text'):
                        grouped_data[date_key][target_region].append(item)
        except: pass

    return grouped_data

def call_llm_analysis(region, raw_items):
    """
    raw_items: 原始推文对象列表
    """
    if not raw_items: return None

    # 显示进度：开始处理
    print(f"      🤖 开始分析 {region} 板块 ({len(raw_items)} 条推文)...")
    
    # 1. 构建带索引的输入，方便 LLM 引用
    # 限制前 60 条，防止 Token 溢出
    process_items = raw_items[:60]
    input_list = []
    for idx, item in enumerate(process_items):
        text = item.get('full_text', '').replace('\n', ' ').strip()
        if len(text) > 10:
            input_list.append(f"ID[{idx}]: {text}")
    
    input_text_str = "\n".join(input_list)
    
    # 2. 修改 Prompt
    prompt = f"""
    你是一个情报分析员。请分析以下"{region}"板块的推特文本。
    
    文本列表 (带ID):
    {input_text_str}

    任务：
    1. 【话题聚类】将推文聚类为 Top 10 核心话题。
    2. 【立场研判】列出每个话题下的推文ID，并判断该推文的立场(positive/neutral/negative)。
    3. 【词云提取】提取 Top 20 热门关键词，必须严格按照要求来进行提取。
       词云要求：
       - 必须是具体的实体、事件、名词（如"关税"、"华为"、"南海冲突"）。
       - 禁止输出"中国"、"美国"、"China"、"US"等过于宽泛的国家名称。
    
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
        # 显示进度：正在调用 API
        print(f"      📡 正在调用 DeepSeek API...", end="", flush=True)
        start_time = time.time()
        
        response = requests.post(
            API_URL, 
            json=payload, 
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=60  # 添加超时设置
        )
        
        # 显示进度：API 调用完成
        api_time = time.time() - start_time
        print(f" 完成 (耗时: {api_time:.1f}秒)")
        
        if response.status_code == 200:
            # 显示进度：解析响应
            print(f"      🔍 解析 API 响应...", end="", flush=True)
            
            llm_json = json.loads(response.json()['choices'][0]['message']['content'])
            
            # 3. 【数据回填】根据 ID 把原始元数据拼回去
            final_topics = []
            for topic_obj in llm_json.get('top_topics', []):
                enriched_tweets = []
                for t_ref in topic_obj.get('tweet_ids', []):
                    tid = t_ref.get('id')
                    stance = t_ref.get('stance', 'neutral')
                    
                    # 确保 ID 有效
                    if isinstance(tid, int) and 0 <= tid < len(process_items):
                        original = process_items[tid]
                        enriched_tweets.append({
                            "text": original.get('full_text', ''),
                            "stance": stance,
                            # 回填元数据
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
            
            # 显示进度：处理完成
            print(f" 完成")
            print(f"      ✅ {region} 分析完成: {len(final_topics)} 个话题, {len(llm_json.get('hot_words', []))} 个热词")
            
            return {
                "top_topics": final_topics,
                "hot_words": llm_json.get('hot_words', [])
            }

        else:
            print(f"      ❌ API 错误: {response.status_code} - {response.text}")
    except requests.exceptions.Timeout:
        print(f"      ⏰ API 请求超时")
    except Exception as e:
        print(f"      ⚠️ 异常: {e}")
    
    return None

def main():
    print("🚀 开始执行话题溯源分析 (Topic Drill-down & Metadata)...")
    
    # 显示进度：检查目录
    print("📁 检查目录结构...")
    if not os.path.exists(RAW_DIR):
        print(f"❌ 原始数据目录不存在: {RAW_DIR}")
        return
    
    if not os.path.exists(OUTPUT_DIR):
        print(f"📂 创建输出目录: {OUTPUT_DIR}")
        os.makedirs(OUTPUT_DIR)
    
    date_groups = load_and_group_by_date()
    
    if not date_groups:
        print("❌ 未找到任何可处理的数据文件")
        return
    
    print(f"📊 找到 {len(date_groups)} 天的数据")
    
    total_dates = len(date_groups)
    processed_dates = 0
    
    for date_key, regions_data in date_groups.items():
        processed_dates += 1
        out_path = os.path.join(OUTPUT_DIR, f"{date_key}.json")
        current_fingerprint = get_files_fingerprint(date_key)
        
        print(f"\n{'='*50}")
        print(f"📅 处理进度: {processed_dates}/{total_dates} | 日期: {date_key}")
        print(f"{'='*50}")
        
        if not check_needs_update(out_path, current_fingerprint):
            print(f"⏩ 数据未变动，跳过")
            continue
        
        print(f"🔄 开始聚类分析...")
        print(f"📊 数据统计:")
        for region, items in regions_data.items():
            print(f"   • {region}: {len(items)} 条推文")
        
        daily_result = {}
        
        total_regions = len(regions_data)
        processed_regions = 0
        
        for region, items in regions_data.items():
            processed_regions += 1
            print(f"\n   ┌── [{processed_regions}/{total_regions}] 处理 {region} 板块")
            analysis = call_llm_analysis(region, items)
            
            if analysis:
                daily_result[region] = {
                    "region": region,
                    "time_range": [date_key, date_key],
                    "top_topics": analysis.get('top_topics', []),
                    "hot_words": analysis.get('hot_words', [])
                }
            else:
                daily_result[region] = {"top_topics": [], "hot_words": []}
            
            print(f"   └── 完成")
        
        daily_result["_meta"] = {
            "fingerprint": current_fingerprint,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_regions_processed": total_regions
        }

        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(daily_result, f, ensure_ascii=False, indent=2)
        print(f"\n✅ {date_key} 更新成功: {out_path}")

    print(f"\n{'🎉'*3} 全部处理完成！ {'🎉'*3}")
    print(f"📁 输出目录: {OUTPUT_DIR}")
    print(f"📅 总共处理了 {total_dates} 天的数据")

if __name__ == "__main__":
    main()