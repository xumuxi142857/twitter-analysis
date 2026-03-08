import json
import os
import sys
import requests
from datetime import datetime

# ================= 配置区域 =================
if len(sys.argv) > 1:
    TARGET_DATE = sys.argv[1]
else:
    # 🚨 修改点：默认获取当天的日期，不再是昨天
    TARGET_DATE = datetime.now().strftime("%Y-%m-%d")

API_KEY = "sk-mwphmyljrynungesqkaqnbimwghczzpniulmdgepgswhjrco" 
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL_NAME = "Pro/zai-org/GLM-4.7" 

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'database', 'raw')
OUTPUT_DIR = os.path.join(BASE_DIR, 'public', 'db', 'agents')

# 领域配置
AGENTS_CONFIG = {
    "agent_1": {
        "name": "NBA & 中美关系智能体",
        "domains": ["US", "NBA"], # 注意：为了左上显示US，左下显示NBA，我调换了顺序
        "tab_name": "US_NBA"
    },
    "agent_2": {
        "name": "好莱坞 & 两岸关系智能体",
        "domains": ["Taiwan", "Hollywood"],
        "tab_name": "Taiwan_Hollywood"
    },
    "agent_3": {
        "name": "马斯克 & 中日关系智能体",
        "domains": ["Japan", "ElonMusk"],
        "tab_name": "Japan_Musk"
    },
    "agent_4": {
        "name": "AI & 中菲关系智能体",
        "domains": ["Philippines", "Ai"],
        "tab_name": "PH_AI"
    }
}
# ===========================================

def load_top_tweets_for_domain(target_date_str, domain_keyword, limit=20):
    tweets = []
    if not os.path.exists(RAW_DIR): return tweets

    for root, dirs, files in os.walk(RAW_DIR):
        for filename in files:
            if not filename.endswith('.json'): continue
            if target_date_str not in filename: continue
            if domain_keyword.lower() not in filename.lower(): continue
            
            path = os.path.join(root, filename)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    items = data if isinstance(data, list) else [data]
                    tweets.extend(items)
            except: pass
            
    def get_impact(t): return t.get('retweet_count', 0)*2 + t.get('reply_count', 0) + t.get('favorite_count', 0)
    sorted_tweets = sorted(tweets, key=get_impact, reverse=True)
    return sorted_tweets[:limit]

def run_agent_synthesis(agent_id, agent_info, date_str):
    domain1, domain2 = agent_info["domains"]
    
    date_compact = date_str.replace("-", "")
    tweets_d1 = load_top_tweets_for_domain(date_compact, domain1, 15)
    tweets_d2 = load_top_tweets_for_domain(date_compact, domain2, 15)
    
    if not tweets_d1 and not tweets_d2:
        return None

    d1_texts = "\n".join([f"- {t.get('full_text', '')}" for t in tweets_d1])
    d2_texts = "\n".join([f"- {t.get('full_text', '')}" for t in tweets_d2])
    
    # 🚨 核心修改点：分别独立提取话题
    prompt = f"""
    你是一名隶属于中国顶尖智库的资深情报分析师。
    你正在监控两个特定的战略领域：【{domain1}】和【{domain2}】。
    
    领域 A ({domain1}) 的近期高热度言论：
    {d1_texts}
    
    领域 B ({domain2}) 的近期高热度言论：
    {d2_texts}
    
    【任务要求】
    请分别针对领域A和领域B，各自挖掘并提炼出 5-8 个最具战略价值的“核心焦点话题”。
    
    规则：
    1. 必须全部使用流畅的中文。
    2. 两个领域的话题必须各自独立提炼，绝对不要混为一谈！
    3. 标题风格：犀利、一针见血、具有新闻洞察力。
    
    请严格输出以下 JSON 格式：
    {{
        "domain1_topics": [
            {{"rank": 1, "topic": "领域A的话题标题", "summary": "具体背景及分析（约60字）"}}
        ],
        "domain2_topics": [
            {{"rank": 1, "topic": "领域B的话题标题", "summary": "具体背景及分析（约60字）"}}
        ]
    }}
    """

    print(f"   🤖 正在独立提炼双领域话题 [{agent_info['name']}] ...")
    try:
        response = requests.post(API_URL, json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=90)
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            content = content.replace('```json', '').replace('```', '').strip()
            result_json = json.loads(content)
            
            # 加入领域名称方便前端展示
            result_json['domain1_name'] = domain1
            result_json['domain2_name'] = domain2
            return result_json
    except Exception as e:
        print(f"⚠️ Agent 运行出错: {e}")
    
    return None

def main():
    print(f"🚀 开始执行智能体双轨话题提取 | 目标日期: {TARGET_DATE}")
    
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    out_path = os.path.join(OUTPUT_DIR, f"{TARGET_DATE}.json")
    daily_result = {}
    
    for agent_id, info in AGENTS_CONFIG.items():
        print(f"\n──────────────────────────────────────────")
        print(f"⚙️ 启动: {info['name']}")
        result = run_agent_synthesis(agent_id, info, TARGET_DATE)
        if result:
            daily_result[info["tab_name"]] = result
            print(f"   ✅ 分析完成")
            
    daily_result["_meta"] = {"updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(daily_result, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 全部智能体执行完毕，结果已保存至: {out_path}")

if __name__ == "__main__":
    main()