import json
import os
import sys
import requests
from datetime import datetime

# ================= 配置区域 =================
if len(sys.argv) > 1:
    TARGET_DATE = sys.argv[1]
else:
    # 如果没传参数，默认跑昨天的
    from datetime import timedelta
    TARGET_DATE = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

API_KEY = "sk-mwphmyljrynungesqkaqnbimwghczzpniulmdgepgswhjrco" 
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL_NAME = "Pro/zai-org/GLM-4.7" 

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'database', 'raw')
OUTPUT_DIR = os.path.join(BASE_DIR, 'public', 'db', 'agents')

# 定义四个智能体的关注领域关键词 (用于匹配 database/raw 下的文件名)
AGENTS_CONFIG = {
    "agent_1": {
        "name": "NBA & 中美关系智能体",
        "domains": ["NBA", "US"],
        "tab_name": "US_NBA"
    },
    "agent_2": {
        "name": "好莱坞 & 两岸关系智能体",
        "domains": ["Hollywood", "Taiwan"],
        "tab_name": "Taiwan_Hollywood"
    },
    "agent_3": {
        "name": "马斯克 & 中日关系智能体",
        "domains": ["ElonMusk", "Japan"],
        "tab_name": "Japan_Musk"
    },
    "agent_4": {
        "name": "AI & 中菲关系智能体",
        "domains": ["Ai", "Philippines"],
        "tab_name": "PH_AI"
    }
}
# ===========================================

def load_top_tweets_for_domain(target_date_str, domain_keyword, limit=20):
    """从指定领域的 JSON 文件中加载互动量最高的推文，防止 Token 超限"""
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
            
    # 按互动量排序
    def get_impact(t):
        return t.get('retweet_count', 0)*2 + t.get('reply_count', 0) + t.get('favorite_count', 0)
    
    sorted_tweets = sorted(tweets, key=get_impact, reverse=True)
    return sorted_tweets[:limit]

def run_agent_synthesis(agent_id, agent_info, date_str):
    domain1, domain2 = agent_info["domains"]
    
    # 获取两个领域的头部数据
    date_compact = date_str.replace("-", "")
    tweets_d1 = load_top_tweets_for_domain(date_compact, domain1, 15)
    tweets_d2 = load_top_tweets_for_domain(date_compact, domain2, 15)
    
    if not tweets_d1 and not tweets_d2:
        return None

    # 组装 Prompt
    d1_texts = "\n".join([f"- {t.get('full_text', '')}" for t in tweets_d1])
    d2_texts = "\n".join([f"- {t.get('full_text', '')}" for t in tweets_d2])
    
    # 组装 Prompt (用全新的灵活指令)
    prompt = f"""
    你是一名隶属于中国顶尖智库的资深情报分析师。
    你正在监控两个特定的战略领域：【{domain1}】和【{domain2}】。
    
    领域 A ({domain1}) 的近期高热度言论：
    {d1_texts}
    
    领域 B ({domain2}) 的近期高热度言论：
    {d2_texts}
    
    【任务要求】
    请从上述原始素材中，挖掘并提炼出 10 个最具战略价值、最具舆论争议的“核心焦点话题”。
    
    绝对遵守以下规则：
    1. 必须全部使用流畅的中文（人名/专有名词除外），绝对不要出现英文大标题。
    2. 拒绝死板的学术拼凑！不要生硬地把两个领域强行对比（比如“A是科技，B也是科技”这种废话）。
    3. 寻找深层逻辑：比如，美国的社会撕裂是如何同时体现在其政治言论和NBA球星争议中的？或者好莱坞的文化输出与台海局势有何微妙的意识形态碰撞？如果两个领域确实没有交集，可以单独提炼某个领域内极其重大的事件。
    4. 标题风格：要像智库内参或新闻头条一样，犀利、一针见血、具有冲突感。例如：“美国社会价值观撕裂：从体育圈平权争议到国内政治极化”或“文化输出的暗流：好莱坞叙事与涉台言论的交织”。
    
    请严格输出以下 JSON 格式：
    {{
        "top_topics": [
            {{"rank": 1, "topic": "犀利的中文话题标题", "summary": "具体的事件背景及深层战略逻辑分析（约60字），语言要专业、接地气、有洞察力"}},
            {{"rank": 2, "topic": "...", "summary": "..."}}
        ]
    }}
    """

    print(f"   🤖 正在呼叫 LLM 提取话题 [{agent_info['name']}] ...")
    try:
        response = requests.post(API_URL, json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3, # 提取话题需要稳定性，温度设低一点
            "response_format": {"type": "json_object"}
        }, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=90)
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            content = content.replace('```json', '').replace('```', '').strip()
            return json.loads(content)
        else:
            print(f"❌ API 错误: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Agent 运行出错: {e}")
    
    return None

def main():
    print(f"🚀 开始执行智能体话题提取 | 目标日期: {TARGET_DATE}")
    
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    out_path = os.path.join(OUTPUT_DIR, f"{TARGET_DATE}.json")
    
    daily_result = {}
    
    for agent_id, info in AGENTS_CONFIG.items():
        print(f"\n──────────────────────────────────────────")
        print(f"⚙️ 启动: {info['name']} ({info['domains'][0]} + {info['domains'][1]})")
        
        result = run_agent_synthesis(agent_id, info, TARGET_DATE)
        if result:
            daily_result[info["tab_name"]] = result
            print(f"   ✅ 分析完成，提取了 {len(result.get('top_topics', []))} 个话题")
        else:
            print(f"   ⚠️ 数据不足或生成失败")
            
    daily_result["_meta"] = {"updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(daily_result, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 全部智能体执行完毕，结果已保存至: {out_path}")

if __name__ == "__main__":
    main()