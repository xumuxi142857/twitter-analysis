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
OUTPUT_DIR = os.path.join(BASE_DIR, 'public', 'db', 'guide')

FILENAME_MAPPING = {
    "Taiwan": "Taiwan",
    "China_Relations": "US",
    "Philippines": "Philippines",
    "JP": "Japan",
    "Japan": "Japan",
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

def load_and_group_by_date():
    """
    返回结构:
    {
        "2025-12-25": { "Philippines": [texts...], "US": [texts...] },
        ...
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

        if date_key not in grouped_data: grouped_data[date_key] = {}
        if target_region not in grouped_data[date_key]: grouped_data[date_key][target_region] = []

        try:
            with open(os.path.join(RAW_DIR, filename), 'r', encoding='utf-8') as f:
                data = json.load(f)
                items = data if isinstance(data, list) else [data]
                texts = [i.get('full_text', '') for i in items]
                grouped_data[date_key][target_region].extend(texts)
        except: pass

    return grouped_data

def generate_guides(region, texts):
    """调用 LLM 生成引导策略"""
    if not texts: return None
    
    # 截取前 40 条上下文
    context_str = "\n".join(texts[:40])
    
    prompt = f"""
    你是一名资深舆情应对专家。请分析以下关于“{region}”的推特舆情数据。
    
    原始数据：
    {context_str}
    
    任务：
    1. 提炼 Top 5 关键话题 (topic) 及其对中立场 (stance: positive/neutral/negative)。
    2. 针对每个话题，编写 3 条不同风格的推文回复草稿 (drafts)：
       - authority (权威): 语气严肃、官方、引用法规或历史事实。
       - peer (同伴): 语气轻松、平视、使用网络流行语或反讽。
       - kinship (亲情): 语气感性、温暖、以“家人/同胞/和平”为切入点。
    
    要求：
    - 草稿长度控制在 40-60 字。
    - 输出严格 JSON。

    输出 JSON 示例：
    {{
        "topics": [
            {{
                "topic": "话题摘要...",
                "stance": "negative",
                "drafts": {{
                    "authority": "...",
                    "peer": "...",
                    "kinship": "..."
                }}
            }}
        ]
    }}
    """

    try:
        response = requests.post(API_URL, json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7, # 稍微高一点，让文案更有创意
            "response_format": {"type": "json_object"}
        }, headers={"Authorization": f"Bearer {API_KEY}"})
        
        if response.status_code == 200:
            return json.loads(response.json()['choices'][0]['message']['content'])
    except Exception as e:
        print(f"API Error: {e}")
    return None

def main():
    print("🚀 开始执行按日期生成推文引导数据 (智能增量更新版 - Guide)...")
    date_groups = load_and_group_by_date()
    
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
        print(f"🔄 检测到数据变动，正在生成引导策略: {date_key}")
        
        daily_result = {}
        
        for region, texts in regions_data.items():
            print(f"   -> 生成 [{region}] 引导策略 ({len(texts)} 条上下文)...")
            result = generate_guides(region, texts)
            
            if result:
                daily_result[region] = {
                    "region": region,
                    "time_range": [date_key, date_key],
                    "topics": result.get('topics', [])
                }
            else:
                daily_result[region] = {"topics": []}

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