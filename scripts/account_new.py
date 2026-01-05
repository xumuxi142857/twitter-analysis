import json
import os
import re
import requests
import hashlib
from datetime import datetime

# ================= 配置区域 =================
API_KEY = "sk-7ba052d40efe48ae990141e577d952d1"  # 
API_URL = "https://api.deepseek.com/chat/completions"
MODEL_NAME = "deepseek-chat"  # 

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'database', 'raw')
OUTPUT_DIR = os.path.join(BASE_DIR, 'public', 'db', 'account')

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

def check_needs_update(output_file, current_fingerprint):
    if not os.path.exists(output_file): return True
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            saved_fingerprint = data.get('_meta', {}).get('fingerprint', '')
            return saved_fingerprint != current_fingerprint
    except: return True

def load_and_group_by_date_user():
    grouped_data = {}
    if not os.path.exists(RAW_DIR): return grouped_data

    print(f"📂 正在扫描 {RAW_DIR} ...")
    for root, dirs, files in os.walk(RAW_DIR):
        for filename in files:
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
            if target_region not in grouped_data[date_key]: grouped_data[date_key][target_region] = {}

            path = os.path.join(root, filename)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    items = data if isinstance(data, list) else [data]
                    
                    for item in items:
                        uname = item.get('username', 'Unknown')
                        # 存储完整对象以便后续使用
                        if item.get('full_text'):
                            if uname not in grouped_data[date_key][target_region]:
                                grouped_data[date_key][target_region][uname] = []
                            grouped_data[date_key][target_region][uname].append(item)
            except: pass

    return grouped_data

def analyze_user_profile(username, raw_tweets):
    """
    调用 LLM 分析用户画像 + 推文立场
    """
    if not raw_tweets: return None

    # 1. 智能采样：按互动量排序，取 Top 15
    def calculate_impact(item):
        return (item.get('retweet_count', 0)*2) + item.get('reply_count', 0) + (item.get('favorite_count', 0)*0.5)
    
    # 复制一份并排序，以免影响原列表
    sorted_tweets = sorted(raw_tweets, key=calculate_impact, reverse=True)
    # 限制分析 Top 15 条，防止 Token 爆炸
    top_tweets = sorted_tweets[:15]
    
    # 2. 构建带 ID 的输入
    input_list = []
    for idx, t in enumerate(top_tweets):
        text = t.get('full_text', '').replace('\n', ' ').strip()
        if len(text) > 10:
            input_list.append(f"ID[{idx}]: {text}")
    
    input_text_str = "\n".join(input_list)
    
    prompt = f"""
    你是一个社会心理学专家。请根据用户 "{username}" 的推文记录进行分析。
    
    推文列表 (带ID):
    {input_text_str}

    任务：
    1. 【画像生成】
       - info: 一句话概括人设(50字内)。
       - stance_matrix: 对中立场矩阵 [[x(立场0-2), y(维度0-3), value(0-10)]...]。维度:0政1军2经3文; 立场:0负1中2正。
       - influence_type: 亲情/同伴/权威 三类占比。
    
    2. 【推文研判】
       - 针对提供的每一条推文ID，判断其具体的立场 (positive/neutral/negative)。
    
    输出 JSON 格式：
    {{
        "info": "...",
        "stance_matrix": [[0,0,8]...], 
        "influence_type": [{{"name": "权威 (Authority)", "value": 80}}...],
        "tweet_analysis": [
            {{"id": 0, "stance": "negative"}},
            {{"id": 1, "stance": "neutral"}}
        ]
    }}
    """

    try:
        response = requests.post(API_URL, json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }, headers={"Authorization": f"Bearer {API_KEY}"})
        
        if response.status_code == 200:
            res_json = json.loads(response.json()['choices'][0]['message']['content'])
            
            # 3. 数据回填：把 LLM 的立场判断与原始推文拼合
            enriched_tweets = []
            analysis_map = {item['id']: item['stance'] for item in res_json.get('tweet_analysis', [])}
            
            for idx, tweet in enumerate(top_tweets):
                stance = analysis_map.get(idx, 'neutral') # 默认中性
                enriched_tweets.append({
                    "text": tweet.get('full_text', ''),
                    "stance": stance,
                    "username": tweet.get('username', username),
                    "created_at": tweet.get('created_at', ''),
                    "metrics": {
                        "reply": tweet.get('reply_count', 0),
                        "retweet": tweet.get('retweet_count', 0),
                        "like": tweet.get('favorite_count', 0)
                    }
                })
            
            # 返回组合好的数据
            return {
                "info": res_json.get("info"),
                "stance_matrix": res_json.get("stance_matrix"),
                "influence_type": res_json.get("influence_type"),
                "tweets": enriched_tweets
            }

    except Exception as e:
        print(f"Error analyzing {username}: {e}")
    return None

def main():
    print("🚀 开始按日期处理账号推荐数据 (推文溯源版)...")
    date_groups = load_and_group_by_date_user()
    
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

    for date_key, regions_data in date_groups.items():
        out_path = os.path.join(OUTPUT_DIR, f"{date_key}.json")
        current_fingerprint = get_files_fingerprint(date_key)
        
        if not check_needs_update(out_path, current_fingerprint):
            print(f"⏩ 日期 {date_key} 未变动，跳过")
            continue

        print(f"\n──────────────────────────────────────────")
        print(f"🔄 正在分析日期: {date_key}")
        
        daily_result = {} 
        
        for region, users_map in regions_data.items():
            print(f"   -> 板块 [{region}] 共有 {len(users_map)} 个活跃用户")
            
            # 简单排序：取发帖量最多的 Top 5
            sorted_users = sorted(users_map.items(), key=lambda x: len(x[1]), reverse=True)[:5]
            
            analyzed_list = []
            for uname, tweets in sorted_users:
                print(f"      正在画像: {uname} (基于 {min(len(tweets), 15)} 条高热度推文)...")
                
                profile = analyze_user_profile(uname, tweets)
                
                if profile:
                    profile['username'] = uname
                    profile['tweet_count'] = len(tweets)
                    analyzed_list.append(profile)
            
            daily_result[region] = {
                "region": region,
                "time_range": [date_key, date_key],
                "top_users": analyzed_list
            }
        
        daily_result["_meta"] = {
            "fingerprint": current_fingerprint,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
            
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(daily_result, f, ensure_ascii=False, indent=2)
        print(f"✅ 更新成功: {out_path}")

    print("\n🎉 全部处理完成！")

if __name__ == "__main__":
    main()