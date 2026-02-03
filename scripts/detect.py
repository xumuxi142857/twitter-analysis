import json
import os
import requests
import hashlib
import time
import random
from datetime import datetime
from dateutil import parser
import traceback
from tqdm import tqdm  # 引入进度条库

# ================= 配置区域 =================
API_KEY = "sk-7ba052d40efe48ae990141e577d952d1"
API_URL = "https://api.deepseek.com/chat/completions"
MODEL_NAME = "deepseek-chat"
#API_KEY = "sk-mwphmyljrynungesqkaqnbimwghczzpniulmdgepgswhjrco" 
#API_URL = "https://api.siliconflow.cn/v1/chat/completions"
#MODEL_NAME = "Pro/zai-org/GLM-4.7" 
MAX_RETRIES = 3  # 最大重试次数

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE_DIR = os.path.join(BASE_DIR, 'database', 'raw2', 'profile')
CONFIG_FILE = os.path.join(PROFILE_DIR, 'targets.json')

DETECT_DB_DIR = os.path.join(BASE_DIR, 'public', 'db', 'detect2')
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

def call_deepseek_with_retry(prompt, task_name="Task", validate_func=None):
    """
    封装了重试机制、JSON解析和结果校验的通用请求函数
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(API_URL, json={
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2, # 低温减少幻觉
                "response_format": {"type": "json_object"}
            }, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=120)

            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                # 清洗 Markdown 标记
                content = content.replace('```json', '').replace('```', '').strip()
                
                # 1. 尝试解析 JSON
                data = json.loads(content)
                
                # 2. (可选) 执行业务逻辑校验
                if validate_func:
                    is_valid, err_msg = validate_func(data)
                    if not is_valid:
                        tqdm.write(f"   ⚠️ [Attempt {attempt+1}] 数据校验失败: {err_msg}，准备重试...")
                        raise ValueError(f"Validation failed: {err_msg}")
                
                return data
            else:
                tqdm.write(f"   ⚠️ [Attempt {attempt+1}] API 状态码错误: {response.status_code}")
        
        except json.JSONDecodeError:
            tqdm.write(f"   ⚠️ [Attempt {attempt+1}] JSON 解析失败，格式错误")
        except Exception as e:
            tqdm.write(f"   ⚠️ [Attempt {attempt+1}] 请求异常: {str(e)}")
        
        # 指数退避：第一次停2秒，第二次停4秒，第三次停8秒
        if attempt < MAX_RETRIES - 1:
            time.sleep(2 * (attempt + 1))
    
    tqdm.write(f"   ❌ {task_name} 最终失败，已达最大重试次数")
    return None

def batch_analyze_tweets(tweets):
    """【微观分析】批量分析最新的 20 条推文"""
    if not tweets: return []
    
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
    
    # 定义校验函数：确保返回的是列表
    def validate_tweets(data):
        if isinstance(data, dict): # 兼容 { "tweets": [...] }
            for k, v in data.items():
                if isinstance(v, list): return True, ""
            return False, "返回了字典但没找到列表"
        if isinstance(data, list): return True, ""
        return False, "返回格式既不是列表也不是包含列表的字典"

    result_raw = call_deepseek_with_retry(prompt, "微观推文分析", validate_tweets)
    
    if not result_raw: return []

    # 标准化数据
    result_list = []
    if isinstance(result_raw, dict):
        for k, v in result_raw.items():
            if isinstance(v, list): result_list = v
    elif isinstance(result_raw, list):
        result_list = result_raw

    # 合并数据
    enriched_tweets = []
    analysis_map = {item.get('id'): item for item in result_list}
    
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

def generate_deep_report(name, raw_tweets):
    """【宏观分析】生成 9 维报告 + 矩阵 + 饼图"""
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
    
    input_text = ""
    for idx, t in enumerate(final_samples):
        clean_text = t.get('full_text', '').replace('\n', ' ').strip()
        if len(clean_text) > 5:
            input_text += f"[{idx+1}] {clean_text}\n"

    prompt = f"""
    你是一名高级情报分析专家。目标对象是："{name}"。
    言论样本：
    {input_text}
    
    请基于样本生成《人物深度侧写与脆弱点研判报告》。

    【任务一：9维深度报告】
    分析维度：
    1. 大五人格 (Big Five)
    2. 人格缺陷 (Personality Flaws)
    3. 认知倾向 (Cognitive Bias)
    4. 行为层面脆弱点 (Behavioral Vulnerabilities)
    5. 立场层面脆弱点 (Stance Vulnerabilities)
    6. 能力层面脆弱点 (Competence Vulnerabilities)
    7. 心智层面脆弱点 (Mental Vulnerabilities)
    8. 隐藏意图 (Hidden Intentions)
    9. 领域话题 (Key Topics)

    **格式要求**：
    每个维度必须包含 `summary` (一句话概述) 和 `sub_items` (子项列表)。
    在 `sub_items` 中，将该维度拆解为 3-5 个具体的关键点。
    - `term`: 关键点名称（例如：“开放性极高”、“救世主情结”、“技术乐观主义”）。
    - `analysis`: 针对该点的详细分析和证据。**不要出现（样本X）**这样的字眼，直接给出分析内容。

    【任务二：对华立场矩阵 (Stance Matrix)】
    **强制约束：必须且只能生成 4 个坐标点，分别对应 Y 轴的 4 个领域。**
    坐标格式：[X, Y, Value]
    - Y轴 (领域): 0=政治, 1=军事, 2=经济, 3=文化. **(每个 Y 值必须出现一次且仅一次)**
    - X轴 (立场): 0=反华/负面, 1=中立/无感, 2=亲华/正面. (根据该人物在该领域的实际表现判断)
    - Value (强度): 1-10 (该领域言论的密度和情绪强烈程度)

    【任务三：影响力类型 (Influence Type)】
    分析其影响力构成，总和必须为 100。
    类型：权威 (Authority), 同伴 (Peer), 亲情/感性 (Affection).

    【输出 JSON 结构示例】
    {{
        "report": [
            {{
                "dimension": "1. 大五人格",
                "summary": "高开放性、高尽责性...",
                "sub_items": [
                    {{ "term": "开放性极高", "analysis": "频繁分享前沿科技与哲学思考..." }},
                    {{ "term": "宜人性低", "analysis": "常转发争议性内容，不避讳冲突..." }}
                ]
            }},
            ...
        ],
        "stance_matrix": [
            [0, 0, 8], // 政治领域：负面，强度8
            [1, 1, 5], // 军事领域：中立，强度5
            [2, 2, 9], // 经济领域：正面，强度9
            [0, 3, 6]  // 文化领域：负面，强度6
        ],
        "influence_type": [
            {{ "name": "权威", "value": 60 }},
            {{ "name": "同伴", "value": 30 }},
            {{ "name": "亲情", "value": 10 }}
        ]
    }}
    """

    # 定义强校验逻辑：防止 LLM 偷懒或格式错误
    def validate_report(data):
        if "report" not in data or "stance_matrix" not in data:
            return False, "缺少 report 或 stance_matrix 字段"
        
        # 校验矩阵是否偷懒（必须是4行）
        matrix = data.get("stance_matrix", [])
        if len(matrix) != 4:
            return False, f"立场矩阵行数错误: 期望 4 行，实际 {len(matrix)} 行"
        
        # 校验报告是否偷懒（至少要有8个维度）
        report = data.get("report", [])
        if len(report) < 8:
            return False, f"报告维度缺失: 期望 9 个，实际 {len(report)} 个"
            
        return True, ""

    return call_deepseek_with_retry(prompt, "宏观深度报告", validate_report)

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

def process_single_target(target_config):
    """处理单个目标，返回状态码"""
    target_name = target_config.get('name')
    filename = target_config.get('filename')
    region = target_config.get('region')
    category = target_config.get('category')
    
    detail_out_path = os.path.join(DETAILS_DIR, filename)
    if os.path.exists(detail_out_path):
        return "SKIPPED"

    file_path = os.path.join(PROFILE_DIR, filename)
    if not os.path.exists(file_path):
        return "MISSING_SOURCE"

    # 使用 tqdm.write 代替 print，防止打断进度条
    tqdm.write(f"👉 正在研判: {target_name} ...")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tweets = json.load(f)
            if not isinstance(tweets, list): tweets = [tweets]
    except Exception as e:
        tqdm.write(f"   ❌ 文件格式错误: {filename}")
        return "ERROR"

    # 1. 生成宏观报告
    analysis_result = generate_deep_report(target_name, tweets)
    
    if analysis_result:
        daily_cnt = calculate_stats(tweets)

        # 2. 批量分析最新 20 条
        sorted_all_tweets = sorted(tweets, key=lambda x: x.get('created_at', ''), reverse=True)
        top_20_tweets = sorted_all_tweets[:20]
        enriched_tweets = batch_analyze_tweets(top_20_tweets)

        final_detail_data = {
            "id": filename,
            "_fingerprint": get_file_fingerprint(file_path),
            "name": target_name,
            "username": tweets[0].get('username', 'unknown'),
            "category": category,
            "daily_count": daily_cnt,
            "analysis_report": analysis_result.get("report", []),
            "stance_matrix": analysis_result.get("stance_matrix", []),
            "influence_type": analysis_result.get("influence_type", []),
            "all_tweets": enriched_tweets
        }
        
        with open(detail_out_path, 'w', encoding='utf-8') as f:
            json.dump(final_detail_data, f, ensure_ascii=False, indent=2)
        
        summary_obj = {
            "id": filename,
            "name": target_name,
            "username": final_detail_data['username'],
            "category": category,
            "daily_count": daily_cnt,
            "preview": analysis_result.get("report", [{}])[0].get("summary", "暂无摘要")
        }
        update_list_json(region, summary_obj)
        return "SUCCESS"
    else:
        return "LLM_FAIL"

def main():
    print(f"🔥 启动智能增量研判程序 | {datetime.now().strftime('%H:%M:%S')}")
    
    if not os.path.exists(DETECT_DB_DIR): os.makedirs(DETECT_DB_DIR)
    if not os.path.exists(DETAILS_DIR): os.makedirs(DETAILS_DIR)

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            targets_config = json.load(f)
    except Exception as e:
        print(f"❌ 无法读取 targets.json: {e}")
        return

    # 过滤出真正需要处理的任务（排除已存在的）
    # 这样可以让进度条更真实地反映"待处理"的工作量
    pending_tasks = []
    skipped_count = 0
    
    print("🔍 正在扫描任务队列...")
    for t in targets_config:
        detail_path = os.path.join(DETAILS_DIR, t.get('filename'))
        if os.path.exists(detail_path):
            skipped_count += 1
        else:
            pending_tasks.append(t)

    print(f"📄 总任务: {len(targets_config)} | ✅ 已完成: {skipped_count} | ⏳ 待处理: {len(pending_tasks)}\n")

    if not pending_tasks:
        print("🎉 所有任务已完成，无需处理！")
        return

    # 使用 tqdm 创建进度条
    # unit="人" 表示单位
    # ncols=100 设置进度条宽度
    pbar = tqdm(pending_tasks, desc="正在研判", unit="人", ncols=100)
    
    success_count = 0
    fail_count = 0

    for target_config in pbar:
        status = process_single_target(target_config)
        
        if status == "SUCCESS":
            success_count += 1
            # 动态更新进度条后缀信息
            pbar.set_postfix({"状态": "成功", "冷却": "3s"})
            time.sleep(3) # 冷却防止限流
        elif status == "LLM_FAIL" or status == "ERROR":
            fail_count += 1
            pbar.set_postfix({"状态": "失败", "跳过": "Yes"})
        elif status == "MISSING_SOURCE":
            fail_count += 1
            tqdm.write(f"⚠️ 源文件缺失: {target_config.get('name')}")

    print(f"\n──────────────────────────────────────────")
    print(f"🎉 任务结束！")
    print(f"   - 成功: {success_count}")
    print(f"   - 失败: {fail_count}")
    print(f"   - 跳过: {skipped_count}")

if __name__ == "__main__":
    main()