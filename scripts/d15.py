import json
import os
import requests
import hashlib
from datetime import datetime
from dateutil import parser
import traceback

# ================= 配置区域 =================
# 🎯 在这里填写你要处理的目标名称
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

def generate_deep_report(name, raw_tweets):
    """
    生成：9维报告 + 立场矩阵 + 影响力饼图
    """
    if not raw_tweets: return None

    # --- 1. 数据采样 ---
    def safe_parse_time(t):
        try: return parser.parse(t.get('created_at', ''))
        except: return datetime.min

    sorted_by_date = sorted(raw_tweets, key=safe_parse_time, reverse=True)
    recent_tweets = sorted_by_date[:20]
    
    def get_impact(t): return (t.get('retweet_count',0)*2 + t.get('reply_count',0))
    sorted_by_impact = sorted(raw_tweets, key=get_impact, reverse=True)
    top_tweets = sorted_by_impact[:30]
    
    # 合并去重
    sample_pool = {}
    for t in recent_tweets + top_tweets:
        key = t.get('tweet_id', t.get('full_text')[:50])
        sample_pool[key] = t
    
    final_samples = list(sample_pool.values())
    print(f"      [采样] 精选 {len(final_samples)} 条推文进行深度画像...")

    input_text = ""
    for idx, t in enumerate(final_samples):
        clean_text = t.get('full_text', '').replace('\n', ' ').strip()
        if len(clean_text) > 5:
            input_text += f"[{idx+1}] {clean_text}\n"

    # --- 2. 复合 Prompt ---
    prompt = f"""
    你是一名高级情报分析专家。目标对象是："{name}"。
    以下是该目标在社交媒体上的言论样本：
    {input_text}
    
    任务：请基于上述数据，完成以下三项分析任务，并以严格的 JSON 格式输出。

    【任务一：深度研判报告 (Report)】
    请严格按照以下 9 个维度进行分析。每项包含 title, summary(30字内), detail(150字左右)。
    1. 大五人格 (Big Five): 分析开放性、尽责性、外向性、宜人性、神经质的特征。
    2. 人格缺陷 (Personality Defects): 识别如自恋、马基雅维利主义、冷漠等暗黑特征。
    3. 认知倾向 (Cognitive Bias): 分析阴谋思维、归因偏差、刻板印象等。
    4. 行为层面认知脆弱点 (Behavioral Vulnerabilities): 识别冲动、回避责任、操控等行为弱点。
    5. 立场层面认知脆弱点 (Stance Vulnerabilities): 识别立场摇摆、迎合、模糊等问题。
    6. 能力层面认知脆弱点 (Competence Vulnerabilities): 评估外交、经济、管理等方面的短板。
    7. 心智层面认知脆弱点 (Mental Vulnerabilities): 分析情绪稳定性、偏执、风险偏好等。
    8. 隐藏意图 (Hidden Intentions): 推测其对不同利益方（如本国、盟友、对手）的真实意图。
    9. 领域话题 (Domain Topics): 总结其关注的核心领域（政治、经济、军事等）及具体子话题。
    *要求：禁止引用样本编号，遇到外语名词需附中文翻译。*

    【任务二：对华立场矩阵 (Stance Matrix)】
    评估其对中国的态度。
    维度(Y轴): 0=政治, 1=军事, 2=经济, 3=文化
    立场(X轴): 0=负面(反华/强硬), 1=中立/务实, 2=正面(友好/合作)
    数值(Value): 0-10 (强度)
    格式：[[x, y, value], [x, y, value]...] (需覆盖所有4个维度)

    【任务三：影响力类型 (Influence Type)】
    评估其影响受众的方式，总和 100。
    类型：权威 (Authority), 同伴 (Peer), 亲情 (Kinship)
    格式：[{{ "name": "权威", "value": 60 }}, ...]

    ⭐⭐ 输出 JSON 结构要求 ⭐⭐：
    {{
        "report": [ {{ "dimension": "1. 大五人格", "summary": "...", "detail": "..." }}, ... ],
        "stance_matrix": [[0,0,8], [1,0,5], [1,2,4], ...],
        "influence_type": [{{ "name": "权威", "value": 70 }}, {{ "name": "同伴", "value": 20 }}, {{ "name": "亲情", "value": 10 }}]
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
            
            try:
                return json.loads(content)
            except:
                print(f"❌ JSON 解析失败。")
                return None
    except Exception as e:
        print(f"API Error: {e}")
    
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
    print(f"✅ 索引 list.json 已更新: {summary_obj['name']}")

def main():
    print(f"🚀 开始执行单目标全维度分析 | 目标: {TARGET_NAME}")
    
    if not os.path.exists(DETECT_DB_DIR): os.makedirs(DETECT_DB_DIR)
    if not os.path.exists(DETAILS_DIR): os.makedirs(DETAILS_DIR)

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        targets_config = json.load(f)
    
    target_config = next((item for item in targets_config if item["name"] == TARGET_NAME), None)
    
    if not target_config:
        print(f"❌ 未找到 '{TARGET_NAME}' 配置。")
        return

    filename = target_config.get('filename')
    region = target_config.get('region')
    category = target_config.get('category')
    file_path = os.path.join(PROFILE_DIR, filename)

    if not os.path.exists(file_path):
        print(f"❌ 找不到源文件: {file_path}")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tweets = json.load(f)
            if not isinstance(tweets, list): tweets = [tweets]
    except Exception as e:
        print(f"❌ 读取源 JSON 失败: {e}")
        return

    print(f"🔄 [深度分析] 正在研判: {TARGET_NAME} ...")
    
    # 获取综合分析结果
    analysis_result = generate_deep_report(TARGET_NAME, tweets)
    
    if analysis_result:
        daily_cnt = calculate_stats(tweets)

        # 整理推文 (Top 100)
        clean_tweets = []
        sorted_all_tweets = sorted(tweets, key=lambda x: x.get('created_at', ''), reverse=True)
        for t in sorted_all_tweets[:100]:
            clean_tweets.append({
                "created_at": t.get('created_at'),
                "text": t.get('full_text'),
                "metrics": {
                    "reply": t.get('reply_count', 0),
                    "retweet": t.get('retweet_count', 0),
                    "like": t.get('favorite_count', 0)
                }
            })

        final_detail_data = {
            "id": filename,
            "_fingerprint": get_file_fingerprint(file_path),
            "name": TARGET_NAME,
            "username": tweets[0].get('username', 'unknown'),
            "category": category,
            "daily_count": daily_cnt,
            "analysis_report": analysis_result.get("report", []), # 9点报告
            "stance_matrix": analysis_result.get("stance_matrix", []), # 立场矩阵
            "influence_type": analysis_result.get("influence_type", []), # 影响力饼图
            "all_tweets": clean_tweets
        }
        
        detail_out_path = os.path.join(DETAILS_DIR, filename)
        with open(detail_out_path, 'w', encoding='utf-8') as f:
            json.dump(final_detail_data, f, ensure_ascii=False, indent=2)
        print(f"   ✅ 详情文件生成完毕 (包含图表数据)")

        summary_obj = {
            "id": filename,
            "name": TARGET_NAME,
            "username": final_detail_data['username'],
            "category": category,
            "daily_count": daily_cnt,
            # 取第一条摘要作为预览
            "preview": analysis_result.get("report", [{}])[0].get("summary", "暂无摘要")
        }
        update_list_json(region, summary_obj)
        
    else:
        print("❌ LLM 分析失败。")

if __name__ == "__main__":
    main()