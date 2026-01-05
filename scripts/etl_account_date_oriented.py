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
RAW_DIR = os.path.join(BASE_DIR, 'database', 'raw')
# 输出目录: public/db/account
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
    """
    计算某一日期下所有源文件的“指纹”。
    只要文件列表变了、文件大小变了、或者修改时间变了，指纹就会变。
    """
    target_date_str = date_key.replace("-", "") # 2025-12-25 -> 20251225
    related_files = []
    
    if os.path.exists(RAW_DIR):
        for f in os.listdir(RAW_DIR):
            # 只要文件名包含该日期字符串，就认为是该日期的源文件
            if target_date_str in f and f.endswith('.json'):
                path = os.path.join(RAW_DIR, f)
                # 记录文件名、大小、修改时间
                stat = os.stat(path)
                related_files.append(f"{f}_{stat.st_size}_{stat.st_mtime}")
    
    if not related_files:
        return None

    # 排序并拼接 (保证顺序一致性)
    related_files.sort()
    combined_str = "|".join(related_files)
    
    # 生成 MD5 哈希
    return hashlib.md5(combined_str.encode('utf-8')).hexdigest()

def check_needs_update(output_file, current_fingerprint):
    """
    对比指纹来决定是否更新
    """
    # 1. 如果输出文件不存在，必须更新
    if not os.path.exists(output_file):
        return True
    
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 获取上次保存的指纹 (在 _meta 字段里)
            saved_fingerprint = data.get('_meta', {}).get('fingerprint', '')
            
            # 2. 如果指纹不一样，说明源文件有变动，需要更新
            if saved_fingerprint != current_fingerprint:
                return True
            
            # 3. 指纹一样，无需更新
            return False
    except:
        # 读取出错则强制更新
        return True

def load_and_group_by_date_user():
    """
    加载数据，返回结构:
    {
        "2025-12-25": {
            "Philippines": { "user1": [tweets...], "user2": [tweets...] },
            "US": ...
        }
    }
    """
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

        # 初始化层级
        if date_key not in grouped_data: grouped_data[date_key] = {}
        if target_region not in grouped_data[date_key]: grouped_data[date_key][target_region] = {}

        path = os.path.join(RAW_DIR, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                items = data if isinstance(data, list) else [data]
                
                for item in items:
                    uname = item.get('username', 'Unknown')
                    text = item.get('full_text', '')
                    if uname not in grouped_data[date_key][target_region]:
                        grouped_data[date_key][target_region][uname] = []
                    grouped_data[date_key][target_region][uname].append(text)
        except: pass

    return grouped_data

def analyze_user_profile(username, tweets):
    """调用 LLM 分析单个用户画像"""
    content_str = "\n---\n".join(tweets[:15]) # 限制上下文长度
    
    prompt = f"""
    你是一个社会心理学专家。请根据用户 "{username}" 的推文生成画像。
    
    推文记录：
    {content_str}

    请返回严格 JSON：
    1. info: 一句话概括人设(50字内)。
    2. stance_matrix: 对中立场矩阵 [[x(立场0-2), y(维度0-3), value(0-10)]...]。维度:0政1军2经3文; 立场:0负1中2正。
    3. influence_type: 亲情/同伴/权威 三类占比。

    JSON 示例：
    {{
        "info": "激进的军事评论员...",
        "stance_matrix": [[0,0,8], [1,0,2]...], 
        "influence_type": [{{"name": "权威 (Authority)", "value": 80}}, {{"name": "同伴 (Peer)", "value": 20}}]
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
            return json.loads(response.json()['choices'][0]['message']['content'])
    except: pass
    return None

def main():
    print("🚀 开始按日期处理账号推荐数据 (智能增量更新版 - Account)...")
    date_groups = load_and_group_by_date_user()
    
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

    for date_key, regions_data in date_groups.items():
        # 定义输出文件路径
        out_path = os.path.join(OUTPUT_DIR, f"{date_key}.json")
        
        # --- 智能更新判断核心 ---
        current_fingerprint = get_files_fingerprint(date_key)
        
        if not check_needs_update(out_path, current_fingerprint):
            print(f"⏩ 日期 {date_key} 源文件集未变动，跳过 (已节省 Token)")
            continue
        # ----------------------

        print(f"\n──────────────────────────────────────────")
        print(f"🔄 检测到数据变动，正在处理账号画像: {date_key}")
        
        daily_result = {} 
        
        for region, users_map in regions_data.items():
            print(f"   -> 板块 [{region}] 共有 {len(users_map)} 个活跃用户")
            
            # 1. 简单排序：取发帖量最多的 Top 5 (节省 Token)
            sorted_users = sorted(users_map.items(), key=lambda x: len(x[1]), reverse=True)[:5]
            
            analyzed_list = []
            for uname, tweets in sorted_users:
                print(f"      分析用户: {uname}...")
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
        
        # 写入文件，同时写入 _meta 指纹信息
        daily_result["_meta"] = {
            "fingerprint": current_fingerprint,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
            
        try:
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(daily_result, f, ensure_ascii=False, indent=2)
            print(f"✅ 更新成功: {out_path}")
        except Exception as e:
            print(f"❌ 保存文件失败: {e}")

    print("\n🎉 全部处理完成！")

if __name__ == "__main__":
    main()