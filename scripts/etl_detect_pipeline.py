import json
import os
import requests
import hashlib
from datetime import datetime
from dateutil import parser # pip install python-dateutil

# ================= 配置区域 =================
API_KEY = "sk-mwphmyljrynungesqkaqnbimwghczzpniulmdgepgswhjrco" 
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 原始数据目录 (profile文件夹)
PROFILE_DIR = os.path.join(BASE_DIR, 'database', 'raw', 'profile')
# 配置文件路径
CONFIG_FILE = os.path.join(PROFILE_DIR, 'targets.json')
# 输出文件 (目标监测通常是生成一个汇总文件供前端读取)
OUTPUT_FILE = os.path.join(BASE_DIR, 'public', 'db', 'detect', 'targets.json')

# ===========================================

def get_file_fingerprint(file_path):
    """计算单个文件的指纹 (MD5)"""
    if not os.path.exists(file_path): return None
    stat = os.stat(file_path)
    # 组合文件名、大小、修改时间作为指纹
    identifier = f"{os.path.basename(file_path)}_{stat.st_size}_{stat.st_mtime}"
    return hashlib.md5(identifier.encode('utf-8')).hexdigest()

def calculate_stats(tweets):
    """计算统计指标: 日均发稿量 & 活跃时段"""
    if not tweets: return 0, "N/A"
    
    dates = []
    hours = []
    for t in tweets:
        try:
            dt = parser.parse(t.get('created_at', ''))
            dates.append(dt)
            hours.append(dt.hour)
        except: continue
            
    if not dates: return 0, "N/A"
    
    # 日均
    delta_days = (max(dates) - min(dates)).days
    if delta_days < 1: delta_days = 1
    daily_count = round(len(tweets) / delta_days, 1)
    
    # 活跃时段 (众数)
    if hours:
        most_common_hour = max(set(hours), key=hours.count)
        active_time = f"{most_common_hour:02d}:00 - {most_common_hour+2:02d}:00"
    else:
        active_time = "N/A"
    
    return daily_count, active_time

def analyze_profile(name, tweets):
    """调用 LLM 分析人物画像"""
    content_str = "\n".join([t.get('full_text', '') for t in tweets[:30]]) 
    
    prompt = f"""
    你是一个情报分析师。目标人物是 "{name}"。根据以下推文内容进行分析。
    
    推文样本：
    {content_str}

    任务要求（返回 JSON）：
    1. bio: 生成一段简短的情报简介（50字内，包含其主要关注领域）。
    2. keywords: 提取 5 个核心关键词。
    3. stance_matrix: 生成对中立场矩阵 [[x(0-2), y(0-3), val(0-10)]...]。
       维度(Y): 0政1军2经3文; 立场(X): 0负1中2正。
    4. influence_type: 生成影响类型饼图数据 (name/value)。

    JSON 示例：
    {{
        "bio": "该目标近期频繁关注AI与太空技术...",
        "keywords": ["AI", "Space", "Policy"],
        "stance_matrix": [[0,0,5], [1,0,5]...],
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
    except Exception as e:
        print(f"API Error: {e}")
    return None

def main():
    print("🚀 开始执行目标监测分析 (Config配置版)...")
    
    # 1. 检查目录
    if not os.path.exists(PROFILE_DIR):
        print(f"❌ 错误: 找不到 Profile 目录 {PROFILE_DIR}")
        return
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ 错误: 找不到配置文件 {CONFIG_FILE}")
        print("请在 database/raw/profile/ 下创建 targets.json")
        return

    # 2. 读取配置文件
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            targets_config = json.load(f)
    except Exception as e:
        print(f"❌ 配置文件格式错误: {e}")
        return

    # 3. 读取旧的输出结果 (用于增量更新)
    old_data_map = {} # Key: filename, Value: target_object
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                old_json = json.load(f)
                # 将旧数据展平方便查找
                for region, r_data in old_json.items():
                    if region == "_meta": continue
                    for target in r_data.get('targets', []):
                        old_data_map[target['id']] = target
        except: pass

    # 4. 初始化结果容器
    # 前端需要按 region 分组的结构
    final_result = {
        "US": {"region": "US", "targets": []},
        "Japan": {"region": "Japan", "targets": []},
        "Philippines": {"region": "Philippines", "targets": []},
        "Taiwan": {"region": "Taiwan", "targets": []},
    }
    
    # 5. 遍历配置进行处理
    print(f"📋 读取到 {len(targets_config)} 个监测目标")
    
    for config in targets_config:
        filename = config.get('filename')
        display_name = config.get('name')
        region = config.get('region')
        category = config.get('category')
        
        if not filename or not region: continue
        
        file_path = os.path.join(PROFILE_DIR, filename)
        
        # A. 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"⚠️警告: 配置文件中引用的 {filename} 不存在，跳过。")
            continue
            
        # B. 检查是否需要更新 (指纹对比)
        current_fingerprint = get_file_fingerprint(file_path)
        cached_target = old_data_map.get(filename)
        
        # 如果有缓存且指纹一致，直接复用旧数据
        if cached_target and cached_target.get('_fingerprint') == current_fingerprint:
            print(f"⏩ [跳过] {display_name} 数据未变动")
            if region in final_result:
                final_result[region]['targets'].append(cached_target)
            continue
            
        # C. 需要更新: 读取并分析
        print(f"🔄 [分析] 正在处理: {display_name} ...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                tweets = raw_data if isinstance(raw_data, list) else [raw_data]
        except:
            print(f"❌ 读取 JSON 失败: {filename}")
            continue
            
        # 计算统计
        daily_count, active_time = calculate_stats(tweets)
        # LLM 分析
        llm_res = analyze_profile(display_name, tweets)
        
        if llm_res:
            target_obj = {
                "id": filename,
                "_fingerprint": current_fingerprint, # 存入指纹
                "name": display_name,
                "username": tweets[0].get('username', 'unknown') if tweets else 'unknown',
                "category": category,
                "metrics": {
                    "bio": llm_res.get('bio', '暂无简介'),
                    "daily_count": daily_count,
                    "active_hours": active_time,
                    "keywords": llm_res.get('keywords', [])
                },
                "stance_matrix": llm_res.get('stance_matrix', []),
                "influence_type": llm_res.get('influence_type', [])
            }
            
            # 存入结果
            if region not in final_result:
                final_result[region] = {"region": region, "targets": []}
            final_result[region]['targets'].append(target_obj)

    # 6. 保存结果
    out_dir = os.path.dirname(OUTPUT_FILE)
    if not os.path.exists(out_dir): os.makedirs(out_dir)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 目标监测数据已更新: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()