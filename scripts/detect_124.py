import json
import os
import requests
import hashlib
from datetime import datetime
from dateutil import parser
import traceback

# ================= 配置区域 =================
# 🎯 目标名称
TARGET_NAME = "asahi" 

API_KEY = "sk-7ba052d40efe48ae990141e577d952d1"  # 
API_URL = "https://api.deepseek.com/chat/completions"
MODEL_NAME = "deepseek-chat"  # 

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE_DIR = os.path.join(BASE_DIR, 'database', 'raw', 'profile')
CONFIG_FILE = os.path.join(PROFILE_DIR, 'targets.json')

# 输出目录
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

def batch_analyze_tweets(tweets):
    """
    【新功能】批量分析最新的 20 条推文：翻译 + 判立
    """
    if not tweets: return []
    
    # 构建输入列表
    input_text = ""
    for idx, t in enumerate(tweets):
        clean_text = t.get('full_text', '').replace('\n', ' ').strip()
        input_text += f"ID[{idx}]: {clean_text}\n"
    
    prompt = f"""
    你是一个情报翻译官。请分析以下社交媒体推文列表。
    
    输入内容：
    {input_text}
    
    任务：
    1. 【中文翻译】：将推文翻译成流畅的中文。
    2. 【对中立场】：判断该条推文体现的对华立场（若推文与中国无关，标记为“无关”）。
       立场选项：正面 (Positive)、中立 (Neutral)、负面 (Negative)、无关 (Irrelevant)。
    
    输出要求：
    返回一个 JSON 数组，顺序与输入 ID 严格对应。格式如下：
    [
        {{ "id": 0, "trans": "中文翻译内容...", "stance": "负面" }},
        {{ "id": 1, "trans": "中文翻译...", "stance": "无关" }}
    ]
    """
    
    try:
        response = requests.post(API_URL, json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=120)
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            content = content.replace('```json', '').replace('```', '').strip()
            
            try:
                raw_json = json.loads(content)
                result_list = []
                if isinstance(raw_json, dict):
                    # 兼容不同返回格式
                    for k, v in raw_json.items():
                        if isinstance(v, list): result_list = v
                elif isinstance(raw_json, list):
                    result_list = raw_json
                
                # 将分析结果合并回原始推文
                enriched_tweets = []
                analysis_map = {item['id']: item for item in result_list}
                
                for idx, t in enumerate(tweets):
                    analysis = analysis_map.get(idx, {"trans": "翻译失败", "stance": "中立"})
                    enriched_tweets.append({
                        "created_at": t.get('created_at'),
                        "text": t.get('full_text'),
                        "translation": analysis.get('trans'),
                        "stance": analysis.get('stance'),
                        "metrics": {
                            "reply": t.get('reply_count', 0),
                            "retweet": t.get('retweet_count', 0),
                            "like": t.get('favorite_count', 0)
                        }
                    })
                return enriched_tweets
            except:
                print("❌ 推文批量分析 JSON 解析失败")
    except Exception as e:
        print(f"API Error (Batch Analysis): {e}")
    
    return [] # 失败则返回空，或者返回未翻译的原始数据

def generate_deep_report(name, raw_tweets):
    """
    生成 9 维报告 + 矩阵 + 饼图
    """
    # ... (保持原有的采样逻辑不变，为了节省篇幅，这里复用之前的采样代码)
    def safe_parse_time(t):
        try: return parser.parse(t.get('created_at', ''))
        except: return datetime.min

    sorted_by_date = sorted(raw_tweets, key=safe_parse_time, reverse=True)
    recent_tweets = sorted_by_date[:20]
    
    def get_impact(t): return (t.get('retweet_count',0)*2 + t.get('reply_count',0))
    sorted_by_impact = sorted(raw_tweets, key=get_impact, reverse=True)
    top_tweets = sorted_by_impact[:30]
    
    sample_pool = {}
    for t in recent_tweets + top_tweets:
        key = t.get('tweet_id', t.get('full_text')[:50])
        sample_pool[key] = t
    
    final_samples = list(sample_pool.values())
    print(f"      [深度报告采样] 精选 {len(final_samples)} 条推文...")

    input_text = ""
    for idx, t in enumerate(final_samples):
        clean_text = t.get('full_text', '').replace('\n', ' ').strip()
        if len(clean_text) > 5:
            input_text += f"[{idx+1}] {clean_text}\n"

    prompt = f"""
    你是一名高级情报分析专家。目标对象是："{name}"。
    言论样本：{input_text}
    
    任务：请生成《人物深度侧写与脆弱点研判报告》及配套图表数据。

    【任务一：9维报告】
    1. 大五人格 2. 人格缺陷 3. 认知倾向 4. 行为层面认知脆弱点 5. 立场层面认知脆弱点 
    6. 能力层面认知脆弱点 7. 心智层面认知脆弱点 8. 隐藏意图 9. 领域话题
    *要求：禁止引用编号，外语附中文翻译。*

    【任务二：对华立场矩阵】
    X轴: 0=负面, 1=中立, 2=正面; Y轴: 0=政治, 1=军事, 2=经济, 3=文化; Value: 0-10
    
    【任务三：影响力类型】
    权威, 同伴, 亲情 (总和100)

    输出 JSON：
    {{
        "report": [ {{ "dimension": "1. 大五人格", "summary": "...", "detail": "..." }}, ... ],
        "stance_matrix": [[0,0,8]...],
        "influence_type": [{{ "name": "权威", "value": 70 }}...]
    }}
    """

    try:
        response = requests.post(API_URL, json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=120)
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            content = content.replace('```json', '').replace('```', '').strip()
            try: return json.loads(content)
            except: return None
    except: pass
    return None

def update_list_json(region, summary_obj):
    if os.path.exists(LIST_FILE):
        with open(LIST_FILE, 'r', encoding='utf-8') as f:
            list_data = json.load(f)
    else:
        list_data = {}
    
    if region not in list_data:
        list_data[region] = {"region": region, "targets": []}
    
    targets = list_data[region]['targets']
    found = False
    for i, t in enumerate(targets):
        if t['id'] == summary_obj['id']:
            targets[i] = summary_obj
            found = True
            break
    if not found: targets.append(summary_obj)
        
    with open(LIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(list_data, f, ensure_ascii=False, indent=2)
    print(f"✅ 索引 list.json 已更新")

def main():
    print(f"🚀 开始执行单目标全维度分析 | 目标: {TARGET_NAME}")
    
    if not os.path.exists(DETECT_DB_DIR): os.makedirs(DETECT_DB_DIR)
    if not os.path.exists(DETAILS_DIR): os.makedirs(DETAILS_DIR)

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        targets_config = json.load(f)
    target_config = next((item for item in targets_config if item["name"] == TARGET_NAME), None)
    if not target_config: return

    filename = target_config.get('filename')
    region = target_config.get('region')
    category = target_config.get('category')
    file_path = os.path.join(PROFILE_DIR, filename)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tweets = json.load(f)
            if not isinstance(tweets, list): tweets = [tweets]
    except: return

    print(f"🔄 [深度分析] 正在研判: {TARGET_NAME} ...")
    
    # 1. 生成宏观报告
    analysis_result = generate_deep_report(TARGET_NAME, tweets)
    
    if analysis_result:
        daily_cnt = calculate_stats(tweets)

        # 2. 【核心修改】提取最新的 20 条推文并进行翻译和立场判定
        sorted_all_tweets = sorted(tweets, key=lambda x: x.get('created_at', ''), reverse=True)
        top_20_tweets = sorted_all_tweets[:20] # 只取20条
        
        print(f"🔄 [微观分析] 正在逐条研判最新 20 条推文 (翻译+立场)...")
        enriched_tweets = batch_analyze_tweets(top_20_tweets)

        final_detail_data = {
            "id": filename,
            "_fingerprint": get_file_fingerprint(file_path),
            "name": TARGET_NAME,
            "username": tweets[0].get('username', 'unknown'),
            "category": category,
            "daily_count": daily_cnt,
            "analysis_report": analysis_result.get("report", []),
            "stance_matrix": analysis_result.get("stance_matrix", []),
            "influence_type": analysis_result.get("influence_type", []),
            "all_tweets": enriched_tweets # 这里现在是包含 translation 和 stance 的富数据
        }
        
        detail_out_path = os.path.join(DETAILS_DIR, filename)
        with open(detail_out_path, 'w', encoding='utf-8') as f:
            json.dump(final_detail_data, f, ensure_ascii=False, indent=2)
        print(f"   ✅ 详情文件生成完毕")

        summary_obj = {
            "id": filename,
            "name": TARGET_NAME,
            "username": final_detail_data['username'],
            "category": category,
            "daily_count": daily_cnt,
            "preview": analysis_result.get("report", [{}])[0].get("summary", "暂无摘要")
        }
        update_list_json(region, summary_obj)
        
    else:
        print("❌ LLM 分析失败。")

if __name__ == "__main__":
    main()