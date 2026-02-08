import json
import os
import re
import requests
import hashlib
import sys  # <--- 必须导入这个
from datetime import datetime

# ================= 配置区域 =================
# 📅 动态获取日期
# 逻辑：如果有命令行参数 (python account.py 2026-02-03)，就用参数；否则用默认值。
if len(sys.argv) > 1:
    TARGET_DATE = sys.argv[1]
else:
    TARGET_DATE = "2025-12-28" # 默认备份日期

# API 配置 (保持不变)
API_KEY = "sk-mwphmyljrynungesqkaqnbimwghczzpniulmdgepgswhjrco" 
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL_NAME = "Pro/zai-org/GLM-4.7" 

# ... 下面的代码保持完全一致 ...

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

def get_files_fingerprint(date_key):
    """计算目标日期下相关文件的指纹"""
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

def load_data_for_target_date(target_date):
    """只加载指定日期的数据，按用户分组"""
    grouped_data = {}
    target_date_str = target_date.replace("-", "")
    
    if not os.path.exists(RAW_DIR): return grouped_data

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

            if target_region not in grouped_data: grouped_data[target_region] = {}

            path = os.path.join(root, filename)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    items = data if isinstance(data, list) else [data]
                    
                    for item in items:
                        uname = item.get('username', 'Unknown')
                        if item.get('full_text'):
                            if uname not in grouped_data[target_region]:
                                grouped_data[target_region][uname] = []
                            grouped_data[target_region][uname].append(item)
                    file_count += 1
            except: pass

    print(f"✅ 扫描完成，共找到 {file_count} 个相关文件")
    return grouped_data

def analyze_user_profile(username, raw_tweets):
    """
    LLM 分析：用户画像 + 推文翻译与立场
    """
    if not raw_tweets: return None

    # 1. 智能采样：Top 15
    def calculate_impact(item):
        return (item.get('retweet_count', 0)*2) + item.get('reply_count', 0) + (item.get('favorite_count', 0)*0.5)
    
    sorted_tweets = sorted(raw_tweets, key=calculate_impact, reverse=True)
    top_tweets = sorted_tweets[:10]
    
    # 2. 构建输入
    input_list = []
    for idx, t in enumerate(top_tweets):
        text = t.get('full_text', '').replace('\n', ' ').strip()
        if len(text) > 5:
            input_list.append(f"ID[{idx}]: {text}")
    
    input_text_str = "\n".join(input_list)
    
    prompt = f"""
    你是一个情报分析专家。请根据用户 "{username}" 的推文记录进行画像。
    
    推文列表:
    {input_text_str}

    任务：
    1. 【画像生成】
       - info: 极其精简的情报简述，控制在20字以内，不要换行。
       - stance_matrix: 立场热力图数据，格式为 [[x, y, value], ...] 的二维数组。
         **坐标定义严格遵守以下标准，不要搞错：**
         * x轴 (立场): 0=反华(Negative), 1=中立(Neutral), 2=亲华(Positive)
         * y轴 (领域): 0=政治(Political), 1=军事(Military), 2=经济(Economic), 3=文化(Cultural)
         * value (强度): 0-10 的整数
       - influence_type: 亲情/同伴/权威 三类占比。
    
    2. 【推文研判】
       - 对每一条推文进行针对中国大陆的立场判断（如果是反华则为negative） (positive/neutral/negative)。
       - **必须**提供该推文的中文翻译 (translation)。
       - 安全审查：如果用户发布色情内容，或者数据无法分析，请务必将 info 字段设置为字符串 "INVALID_USER"，不要输出其他解释。
    
    输出 JSON 格式（严禁Markdown）：
    {{
        "info": "反华激进派，主要关注南海军事议题。",
        "stance_matrix": [[0,1,9]...], 
        "influence_type": [{{"name": "权威", "value": 80}}...],
        "tweet_analysis": [
            {{"id": 0, "stance": "negative", "translation": "这里是推文0的中文翻译..."}},
            {{"id": 1, "stance": "neutral", "translation": "这里是推文1的中文翻译..."}}
        ]
    }}
    """

    try:
        response = requests.post(API_URL, json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=60)
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            content = content.replace('```json', '').replace('```', '').strip()
            res_json = json.loads(content)
            
            info_text = res_json.get("info", "")
            
            # 1. 检查 Prompt 约定的特定标识
            if "INVALID_USER" in info_text:
                print(f"🛑 拦截无效用户 [{username}]: LLM 判定为无效/违规")
                return None
            
            # 2. 关键词兜底（防止 LLM 不听话，没输出 INVALID_USER 而是输出了人话）
            block_keywords = ["色情", "无法生成", "移除", "adult", "porn","数据异常","异常"]
            if any(k in info_text for k in block_keywords):
                 print(f"🛑 拦截敏感用户 [{username}]: 触发关键词过滤")
                 return None
                 
            # 3. 检查矩阵数据是否为空
            if not res_json.get("stance_matrix"):
                print(f"⚠️ 拦截空数据用户 [{username}]: 矩阵数据缺失")
                return None
            # =======================================================
            
            # 3. 数据回填 (包含翻译)
            enriched_tweets = []
            analysis_map = {item['id']: item for item in res_json.get('tweet_analysis', [])}
            
            for idx, tweet in enumerate(top_tweets):
                analysis = analysis_map.get(idx, {})
                stance = analysis.get('stance', 'neutral')
                trans = analysis.get('translation', '暂无翻译') 
                
                enriched_tweets.append({
                    "text": tweet.get('full_text', ''),
                    "translation": trans,
                    "stance": stance,
                    "username": tweet.get('username', username),
                    "created_at": tweet.get('created_at', ''),
                    "metrics": {
                        "reply": tweet.get('reply_count', 0),
                        "retweet": tweet.get('retweet_count', 0),
                        "like": tweet.get('favorite_count', 0)
                    }
                })
            
            return {
                "info": info_text,
                "stance_matrix": res_json.get("stance_matrix"),
                "influence_type": res_json.get("influence_type"),
                "tweets": enriched_tweets
            }

    except Exception as e:
        print(f"⚠️ Error analyzing {username}: {e}")
    return None

def main():
    print(f"🚀 开始执行单日账号画像分析 | 目标日期: {TARGET_DATE}")
    
    out_path = os.path.join(OUTPUT_DIR, f"{TARGET_DATE}.json")
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    
    regions_data = load_data_for_target_date(TARGET_DATE)
    
    if not regions_data:
        print(f"⚠️ 未找到日期 {TARGET_DATE} 的数据。")
        return

    print(f"\n──────────────────────────────────────────")
    print(f"🔄 正在分析: {TARGET_DATE}")
    
    daily_result = {}
    current_fingerprint = get_files_fingerprint(TARGET_DATE)
    
    # 指纹检查 (可注释掉强制运行)
    if not check_needs_update(out_path, current_fingerprint):
         print(f"⏩ 日期 {TARGET_DATE} 数据未变动，跳过处理")
         return

    for region, users_map in regions_data.items():
        print(f"   -> 板块 [{region}] 共有 {len(users_map)} 个活跃用户")
        
        # 【修改】取 Top 10
        sorted_users = sorted(users_map.items(), key=lambda x: len(x[1]), reverse=True)[:10]
        
        analyzed_list = []
        for uname, tweets in sorted_users:
            print(f"      正在画像: {uname}...")
            profile = analyze_user_profile(uname, tweets)
            
            if profile:
                profile['username'] = uname
                profile['tweet_count'] = len(tweets)
                analyzed_list.append(profile)
        
        daily_result[region] = {
            "region": region,
            "time_range": [TARGET_DATE, TARGET_DATE],
            "top_users": analyzed_list
        }
    
    daily_result["_meta"] = {
        "fingerprint": current_fingerprint,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
        
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(daily_result, f, ensure_ascii=False, indent=2)
    print(f"✅ 生成成功: {out_path}")

if __name__ == "__main__":
    main()