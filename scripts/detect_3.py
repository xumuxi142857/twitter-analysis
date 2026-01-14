import json
import os
import requests
import hashlib
from datetime import datetime
from dateutil import parser
import traceback

# ================= 配置区域 =================
# 🎯 目标名称 (必须与 targets.json 一致)
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
    生成 9 维深度研判报告 (结构化 JSON)
    """
    if not raw_tweets: return None

    # --- 1. 数据采样 (为了上下文窗口，精选高价值推文) ---
    def safe_parse_time(t):
        try: return parser.parse(t.get('created_at', ''))
        except: return datetime.min

    # 取最新的 30 条 (看近况)
    sorted_by_date = sorted(raw_tweets, key=safe_parse_time, reverse=True)
    recent_tweets = sorted_by_date[:30]
    
    # 取互动最高的 40 条 (看典型特征)
    def get_impact(t): return (t.get('retweet_count',0)*2 + t.get('reply_count',0))
    sorted_by_impact = sorted(raw_tweets, key=get_impact, reverse=True)
    top_tweets = sorted_by_impact[:40]
    
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

    # --- 2. 9维度深度 Prompt ---
    prompt = f"""
    你是一名政治心理学与情报分析专家。目标对象是："{name}"。
    基于提供的推特言论样本，请生成一份《人物深度侧写与脆弱点研判报告》。
    
    推文样本：
    {input_text}
    
    任务：请严格按照以下 9 个维度进行分析。内容需专业、简练（类似简报风格），避免冗长。
    
    分析维度要求：
    1. 大五人格 (Big Five): 分析开放性、尽责性、外向性、宜人性、神经质的特征。
    2. 人格缺陷 (Personality Defects): 识别如自恋、马基雅维利主义、冷漠等暗黑特征。
    3. 认知倾向 (Cognitive Bias): 分析阴谋思维、归因偏差、刻板印象等。
    4. 行为层面认知脆弱点 (Behavioral Vulnerabilities): 识别冲动、回避责任、操控等行为弱点。
    5. 立场层面认知脆弱点 (Stance Vulnerabilities): 识别立场摇摆、迎合、模糊等问题。
    6. 能力层面认知脆弱点 (Competence Vulnerabilities): 评估外交、经济、管理等方面的短板。
    7. 心智层面认知脆弱点 (Mental Vulnerabilities): 分析情绪稳定性、偏执、风险偏好等。
    8. 隐藏意图 (Hidden Intentions): 推测其对不同利益方（如本国、盟友、对手）的真实意图。
    9. 领域话题 (Domain Topics): 总结其关注的核心领域（政治、经济、军事等）及具体子话题。

    输出格式 (Strict JSON Array):
    返回一个包含 9 个对象的数组。每个对象包含：
    - "dimension": 维度名称 (例如 "1. 大五人格")
    - "summary": 该维度的整体一句话综述 (50字内)
    - "sub_items": 一个数组，包含具体分析点。每个点包含 "term"(关键词/子维度) 和 "analysis"(具体表现与推论，100字左右),另外注意analysis中不要出现 #1，#2这种引用样本的说法，不需要写从什么地方得出结论。

    JSON 结构示例 (请严格遵守):
    [
      {{
        "dimension": "1. 大五人格",
        "summary": "整体表现为高开放性、低宜人性，情绪稳定性较差。",
        "sub_items": [
          {{ "term": "开放性", "analysis": "表现特征：较高。推文涉足多元议题... 推理依据：多次引用..." }},
          {{ "term": "神经质", "analysis": "表现特征：中高。面对批评反应激烈..." }}
        ]
      }},
      {{
        "dimension": "2. 人格缺陷",
        "summary": "存在明显的自恋倾向与缺乏共情特征。",
        "sub_items": [
          {{ "term": "自恋倾向", "analysis": "频繁强调个人成就，忽视团队贡献..." }}
        ]
      }}
      ... (依次类推直到第9点)
    ]
    """

    try:
        response = requests.post(API_URL, json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3, # 降低温度以保证格式准确
            "response_format": {"type": "json_object"}
        }, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=180) # 增加超时时间，因为生成内容较多
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            content = content.replace('```json', '').replace('```', '').strip()
            
            try:
                raw_json = json.loads(content)
                # 兼容性处理
                if isinstance(raw_json, list): return raw_json
                if isinstance(raw_json, dict):
                    for k, v in raw_json.items():
                        if isinstance(v, list): return v
                return []
            except:
                print(f"❌ JSON 解析失败。")
                return None
        else:
            print(f"❌ API Error: {response.status_code}")
    except Exception as e:
        print(f"API Exception: {e}")
    
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
    print(f"🚀 开始执行单目标深度分析 (9维报告版) | 目标: {TARGET_NAME}")
    
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
    
    report_data = generate_deep_report(TARGET_NAME, tweets)
    
    if report_data:
        daily_cnt = calculate_stats(tweets)

        # 整理推文 (最新的100条)
        clean_tweets = []
        sorted_all_tweets = sorted(tweets, key=lambda x: x.get('created_at', ''), reverse=True)
        top_100_tweets = sorted_all_tweets[:100]
        
        for t in top_100_tweets:
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
            "analysis_report": report_data, # 9点分析数据
            "all_tweets": clean_tweets
        }
        
        detail_out_path = os.path.join(DETAILS_DIR, filename)
        with open(detail_out_path, 'w', encoding='utf-8') as f:
            json.dump(final_detail_data, f, ensure_ascii=False, indent=2)
        print(f"   ✅ 详情文件生成完毕")

        # 更新索引 (preview 取第一个维度的 summary)
        preview_text = "暂无摘要"
        if len(report_data) > 0 and 'summary' in report_data[0]:
            preview_text = report_data[0]['summary']

        summary_obj = {
            "id": filename,
            "name": TARGET_NAME,
            "username": final_detail_data['username'],
            "category": category,
            "daily_count": daily_cnt,
            "preview": preview_text
        }
        update_list_json(region, summary_obj)
        
    else:
        print("❌ LLM 分析失败。")

if __name__ == "__main__":
    main()