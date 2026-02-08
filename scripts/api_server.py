# api_server.py (全功能合并版)
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import subprocess
import os
import sys
import threading
import time
import uuid

app = Flask(__name__)
CORS(app)  # 允许跨域

# ================= 配置区域 =================
# 1. LLM API 配置 (保留你原有的)
API_KEY = "sk-mwphmyljrynungesqkaqnbimwghczzpniulmdgepgswhjrco" 
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL_NAME = "Pro/zai-org/GLM-4.7" 

# 2. 脚本路径配置
# 假设目录结构: /var/www/demo/server/api_server.py
# 脚本在: /var/www/demo/scripts/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')
PYTHON_EXEC = sys.executable  # 使用当前环境的 python

# 3. 内存任务状态存储 (用于异步任务)
TASKS = {}

# ================= 核心逻辑区域 =================

# --- 功能 A: 推文引导 (你原有的逻辑) ---
@app.route('/api/generate_guide', methods=['POST'])
def generate_guide():
    data = request.json
    tweet_text = data.get('text', '')
    topic_name = data.get('topic', '')
    region = data.get('region', '')

    prompt = f"""
    你是一名中国资深舆情应对专家。请站在中国的立场上，以维护中国的利益为根本，针对以下关于“{region}”的推文，请生成应对策略。
    话题背景：{topic_name}
    具体推文内容：{tweet_text}

    任务：请严格编写 3 条不同风格的回复草稿 (drafts)：
    1. authority (权威): 语气严肃、官方、引用法规或历史事实。
    2. peer (同伴): 语气轻松、平视、使用网络流行语或反讽。
    3. kinship (亲情): 语气感性、温暖、以“家人/同胞/和平”为切入点。

    要求：每条草稿 60 字左右。必须返回纯 JSON 格式。
    输出示例：
    {{
        "authority": "...",
        "peer": "...",
        "kinship": "..."
    }}
    """

    try:
        response = requests.post(API_URL, json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8,
            "response_format": {"type": "json_object"}
        }, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=60)

        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            # 简单清洗 markdown 标记
            content = content.replace('```json', '').replace('```', '').strip()
            return jsonify(json.loads(content))
        else:
            return jsonify({"error": "LLM API Error"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- 功能 B: 异步脚本执行 (新加的逻辑) ---

def run_script_background(task_id, script_name, target_date):
    """后台线程：执行脚本并捕获日志"""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    TASKS[task_id]['status'] = 'running'
    TASKS[task_id]['logs'] = f"🚀 [System] 任务启动: {script_name} | 日期: {target_date}\n"

    try:
        # 实时捕获输出
        process = subprocess.Popen(
            [PYTHON_EXEC, script_path, target_date],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            bufsize=1
        )

        for line in process.stdout:
            TASKS[task_id]['logs'] += line

        process.wait()

        if process.returncode == 0:
            TASKS[task_id]['status'] = 'success'
            TASKS[task_id]['logs'] += f"\n✅ [System] 执行完成 (Success)"
        else:
            TASKS[task_id]['status'] = 'error'
            TASKS[task_id]['logs'] += f"\n❌ [System] 异常退出 Code: {process.returncode}"

    except Exception as e:
        TASKS[task_id]['status'] = 'error'
        TASKS[task_id]['logs'] += f"\n❌ [System] 线程错误: {str(e)}"


@app.route('/api/run_script', methods=['POST'])
def submit_task():
    data = request.json
    script_type = data.get('type')
    target_date = data.get('date')

    if not target_date:
        return jsonify({"error": "日期不能为空"}), 400

    # 映射表：前端 type -> 后端文件名
    script_map = {
        'topic': 'topic.py',
        'account': 'account.py',
        'target': 'detect.py' # 假设你的目标监测脚本叫这个，如果是其他名字请修改这里
    }

    script_name = script_map.get(script_type)
    if not script_name:
        return jsonify({"error": "未知任务类型"}), 400
    
    # 检查文件是否存在
    if not os.path.exists(os.path.join(SCRIPTS_DIR, script_name)):
        return jsonify({"error": f"服务器上找不到脚本: {script_name}"}), 404

    task_id = str(uuid.uuid4())
    TASKS[task_id] = {
        "status": "pending",
        "logs": "正在初始化...",
        "start_time": time.time()
    }

    thread = threading.Thread(target=run_script_background, args=(task_id, script_name, target_date))
    thread.daemon = True
    thread.start()

    return jsonify({"status": "submitted", "task_id": task_id})


@app.route('/api/task_status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task = TASKS.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)


if __name__ == "__main__":
    # 监听所有IP的 5000 端口
    app.run(host='0.0.0.0', port=5000, debug=True)