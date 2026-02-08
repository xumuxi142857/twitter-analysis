from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import os
import sys
import threading
import time
import uuid

app = Flask(__name__)
CORS(app)

# === 配置区域 ===
# 脚本所在目录 (假设在 backend 上一级目录的 scripts 文件夹)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')
PYTHON_EXEC = sys.executable  # 使用当前环境的 python

# === 任务状态存储 (内存中) ===
# 结构: { "task_id": { "status": "running/success/error", "logs": "...", "script": "..." } }
# 注意：重启服务后任务记录会丢失，生产环境通常存数据库，这里存内存够用了
TASKS = {}

def run_script_background(task_id, script_name, target_date):
    """后台线程：执行脚本并实时捕获日志"""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    TASKS[task_id]['status'] = 'running'
    TASKS[task_id]['logs'] = f"🚀 [System] 开始执行 {script_name}，目标日期: {target_date}...\n"

    try:
        # 使用 Popen 实时捕获输出
        process = subprocess.Popen(
            [PYTHON_EXEC, script_path, target_date],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # 把错误也重定向到标准输出
            text=True,
            encoding='utf-8',
            bufsize=1 # 行缓冲
        )

        # 实时读取日志
        for line in process.stdout:
            TASKS[task_id]['logs'] += line

        process.wait() # 等待结束

        if process.returncode == 0:
            TASKS[task_id]['status'] = 'success'
            TASKS[task_id]['logs'] += f"\n✅ [System] 执行完成！"
        else:
            TASKS[task_id]['status'] = 'error'
            TASKS[task_id]['logs'] += f"\n❌ [System] 脚本异常退出，返回码: {process.returncode}"

    except Exception as e:
        TASKS[task_id]['status'] = 'error'
        TASKS[task_id]['logs'] += f"\n❌ [System] 线程执行出错: {str(e)}"

# === 接口 1: 提交任务 ===
@app.route('/api/run_script', methods=['POST'])
def submit_task():
    data = request.json
    script_type = data.get('type')
    target_date = data.get('date')

    if not target_date:
        return jsonify({"error": "日期不能为空"}), 400

    # 脚本映射表 (请根据你实际的文件名修改这里)
    script_map = {
        'topic': 'topic.py',        # 话题分析
        'target': 'detect.py',   # 目标监测
        'account': 'account.py',    # 账号推荐
    }

    script_name = script_map.get(script_type)
    if not script_name:
        return jsonify({"error": "未知的任务类型"}), 400
    
    if not os.path.exists(os.path.join(SCRIPTS_DIR, script_name)):
        return jsonify({"error": f"脚本文件不存在: {script_name}"}), 404

    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 初始化状态
    TASKS[task_id] = {
        "status": "pending",
        "logs": "",
        "start_time": time.time()
    }

    # 启动后台线程
    thread = threading.Thread(target=run_script_background, args=(task_id, script_name, target_date))
    thread.daemon = True # 设置为守护线程，主程序退出时它也会退出
    thread.start()

    # 立刻返回，不等待脚本结束
    return jsonify({
        "status": "submitted",
        "task_id": task_id,
        "message": "任务已提交后台运行"
    })

# === 接口 2: 查询任务进度 (轮询用) ===
@app.route('/api/task_status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task = TASKS.get(task_id)
    if not task:
        return jsonify({"error": "任务ID不存在"}), 404
    
    return jsonify(task)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)