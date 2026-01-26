# api_server.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json

app = Flask(__name__)
CORS(app)  # 允许跨域，否则 Vue 无法访问 5000 端口


API_KEY = "sk-mwphmyljrynungesqkaqnbimwghczzpniulmdgepgswhjrco" 
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL_NAME = "Pro/zai-org/GLM-4.7" 


@app.route('/api/generate_guide', methods=['POST'])
def generate_guide():
    data = request.json
    tweet_text = data.get('text', '')  # 前端传过来的推文正文
    topic_name = data.get('topic', '')  # 前端传过来的话题名称
    region = data.get('region', '')  # 所属地区

    # 针对“单条推文”精心设计的 Prompt
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
        }, headers={"Authorization": f"Bearer {API_KEY}"})

        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            return jsonify(json.loads(content))
        else:
            return jsonify({"error": "LLM API Error"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # 运行在 5000 端口
    app.run(host='0.0.0.0', port=5000, debug=True)