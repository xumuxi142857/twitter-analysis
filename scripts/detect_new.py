import json
import os
import requests
import hashlib
from datetime import datetime
from dateutil import parser

# ================= 配置区域 =================
API_KEY = "sk-7ba052d40efe48ae990141e577d952d1"  # 
API_URL = "https://api.deepseek.com/chat/completions"
MODEL_NAME = "deepseek-chat"  # 

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE_DIR = os.path.join(BASE_DIR, 'database1', 'raw', 'profile')
CONFIG_FILE = os.path.join(PROFILE_DIR, 'targets.json')

# 输出目录配置
DETECT_DB_DIR = os.path.join(BASE_DIR, 'public', 'db', 'detect')
LIST_FILE = os.path.join(DETECT_DB_DIR, 'list.json')
DETAILS_DIR = os.path.join(DETECT_DB_DIR, 'details')
# ===========================================

def get_file_fingerprint(file_path):
    if not os.path.exists(file_path): return None
    stat = os.stat(file_path)
    identifier = f"{os.path.basename(file_path)}_{stat.st_size}_{stat.st_mtime}"
    return hashlib.md5(identifier.encode('utf-8')).hexdigest()

def calculate_stats(tweets):
    if not tweets: return 0
    dates = []
    for t in tweets:
        try:
            dt = parser.parse(t.get('created_at', ''))
            dates.append(dt)
        except: continue
    if not dates: return 0
    delta_days = (max(dates) - min(dates)).days
    if delta_days < 1: delta_days = 1
    return round(len(tweets) / delta_days, 1)

def analyze_profile_and_tweets(name, raw_tweets):
    if not raw_tweets: return None

    # 智能采样：Top 60
    def calculate_impact(item):
        return (item.get('retweet_count', 0)*2) + item.get('reply_count', 0) + (item.get('favorite_count', 0)*0.5)
    
    sorted_tweets = sorted(raw_tweets, key=calculate_impact, reverse=True)
    top_tweets = sorted_tweets[:60]
    
    input_list = []
    for idx, t in enumerate(top_tweets):
        text = t.get('full_text', '').replace('\n', ' ').strip()
        if len(text) > 10:
            input_list.append(f"ID[{idx}]: {text}")
    
    input_text_str = "\n".join(input_list)
    
    prompt = f"""
    你是一个情报分析师。目标人物是 "{name}"。
    推文样本 (带ID):
    {input_text_str}

    任务：
    1. 【画像分析】bio(50字内简介), keywords(5个), stance_matrix([[x,y,val]]), influence_type(name/value).
    2. 【言论研判】判断每条推文立场(positive/neutral/negative).
       
    输出 JSON 格式：
    {{
        "bio": "...",
        "keywords": ["..."],
        "stance_matrix": [[0,0,5]...],
        "influence_type": [{{"name": "权威", "value": 80}}...],
        "tweet_analysis": [
            {{"id": 0, "stance": "negative"}}
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
            
            # 数据回填
            enriched_tweets = []
            analysis_map = {item['id']: item['stance'] for item in res_json.get('tweet_analysis', [])}
            
            for idx, tweet in enumerate(top_tweets):
                stance = analysis_map.get(idx, 'neutral')
                enriched_tweets.append({
                    "text": tweet.get('full_text', ''),
                    "stance": stance,
                    "username": tweet.get('username', name),
                    "created_at": tweet.get('created_at', ''),
                    "metrics": {
                        "reply": tweet.get('reply_count', 0),
                        "retweet": tweet.get('retweet_count', 0),
                        "like": tweet.get('favorite_count', 0)
                    }
                })
            
            return {
                "bio": res_json.get("bio"),
                "keywords": res_json.get("keywords"),
                "stance_matrix": res_json.get("stance_matrix"),
                "influence_type": res_json.get("influence_type"),
                "tweets": enriched_tweets
            }

    except Exception as e:
        print(f"API Error: {e}")
    return None

def main():
    print("🚀 开始执行目标监测分析 (分离存储版)...")
    
    if not os.path.exists(DETECT_DB_DIR): os.makedirs(DETECT_DB_DIR)
    if not os.path.exists(DETAILS_DIR): os.makedirs(DETAILS_DIR)

    if not os.path.exists(CONFIG_FILE):
        print(f"❌ 找不到配置文件: {CONFIG_FILE}")
        return

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            targets_config = json.load(f)
    except Exception as e:
        print(f"❌ 配置文件错误: {e}")
        return

    # 初始化 list.json 的结构
    list_result = {
        "US": {"region": "US", "targets": []},
        "Japan": {"region": "Japan", "targets": []},
        "Philippines": {"region": "Philippines", "targets": []},
        "Taiwan": {"region": "Taiwan", "targets": []},
        "China": {"region": "China", "targets": []}
    }
    
    for config in targets_config:
        filename = config.get('filename')
        display_name = config.get('name')
        region = config.get('region')
        category = config.get('category')
        
        file_path = os.path.join(PROFILE_DIR, filename)
        if not os.path.exists(file_path): continue
            
        current_fingerprint = get_file_fingerprint(file_path)
        detail_out_path = os.path.join(DETAILS_DIR, filename) # 详情文件路径
        
        # 1. 检查详情文件是否需要更新
        need_update = True
        if os.path.exists(detail_out_path):
            try:
                with open(detail_out_path, 'r', encoding='utf-8') as f:
                    old_detail = json.load(f)
                    if old_detail.get('_fingerprint') == current_fingerprint:
                        need_update = False
            except: pass
        
        # 2. 准备 Summary 数据 (这部分总是要重新收集到 list.json 中)
        # 如果不需要更新，我们直接读取旧的详情文件来获取 summary 信息
        
        final_detail_data = None

        if not need_update:
            print(f"⏩ [跳过] {display_name} 详情未变动，读取缓存...")
            with open(detail_out_path, 'r', encoding='utf-8') as f:
                final_detail_data = json.load(f)
        else:
            print(f"🔄 [分析] 正在更新详情: {display_name} ...")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tweets = json.load(f)
                    if not isinstance(tweets, list): tweets = [tweets]
            except: continue
                
            daily_count = calculate_stats(tweets)
            llm_res = analyze_profile_and_tweets(display_name, tweets)
            
            if llm_res:
                final_detail_data = {
                    "id": filename, # 用文件名做ID，方便前端拼接URL
                    "_fingerprint": current_fingerprint,
                    "name": display_name,
                    "username": tweets[0].get('username', 'unknown') if tweets else 'unknown',
                    "category": category,
                    "metrics": {
                        "bio": llm_res.get('bio', '暂无简介'),
                        "daily_count": daily_count,
                        "keywords": llm_res.get('keywords', [])
                    },
                    "stance_matrix": llm_res.get('stance_matrix', []),
                    "influence_type": llm_res.get('influence_type', []),
                    "tweets": llm_res.get('tweets', [])
                }
                # 保存详情文件 (Heavy)
                with open(detail_out_path, 'w', encoding='utf-8') as f:
                    json.dump(final_detail_data, f, ensure_ascii=False, indent=2)

        # 3. 提取轻量级 Summary 并加入 list_result
        if final_detail_data:
            summary_obj = {
                "id": filename, # 前端通过这个 ID 去 fetch details/filename
                "name": display_name,
                "username": final_detail_data['username'],
                "category": category,
                "metrics": final_detail_data['metrics'] # 只保留 Bio 等基础信息
                # 注意：这里不包含 tweets, stance_matrix, influence_type
            }
            
            if region in list_result:
                list_result[region]['targets'].append(summary_obj)

    # 4. 保存轻量级索引文件 (Light)
    with open(LIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(list_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 索引已更新: {LIST_FILE}")
    print(f"✅ 详情已分片存储于: {DETAILS_DIR}")

if __name__ == "__main__":
    main()