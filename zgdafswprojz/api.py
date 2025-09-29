from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import re

app = Flask(__name__)
CORS(app)

# 存储短信
messages = []
MESSAGE_LIMIT = 50

# 配置
API_TOKENS = set()


def init_tokens():
    tokens = os.environ.get('API_TOKENS', '').split(',')
    for token in tokens:
        if token.strip():
            API_TOKENS.add(token.strip())


def verify_token(token):
    if not API_TOKENS:
        return True
    return token in API_TOKENS


def extract_verification_code(text):
    if not text:
        return None
    patterns = [
        r'\b\d{4,6}\b',
        r'验证码[：:]\s*(\d{4,6})',
        r'验证码是\s*(\d{4,6})',
        r'code[：:]\s*(\d{4,6})'
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            code = match.group(1) if match.groups() else match.group(0)
            if code.isdigit():
                return code
    return None


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message_count": len(messages)
    })


@app.route('/api/messages', methods=['GET'])
def get_messages():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not verify_token(token):
        return jsonify({"error": "未授权的访问"}), 401

    recent_messages = messages[-20:]
    return jsonify({
        "messages": recent_messages,
        "total": len(messages)
    })


@app.route('/api/messages/latest', methods=['GET'])
def get_latest_message():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not verify_token(token):
        return jsonify({"error": "未授权的访问"}), 401

    if messages:
        return jsonify(messages[-1])
    else:
        return jsonify({"error": "没有消息"}), 404


@app.route('/api/webhook/sms', methods=['POST'])
def receive_sms():
    token = request.headers.get('X-API-Token', '')

    if not verify_token(token):
        return jsonify({"error": "无效的令牌"}), 401

    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        message_content = data.get('message') or data.get('body') or data.get('text', '')
        sender = data.get('from') or data.get('sender') or data.get('phone', '未知号码')

        if not message_content:
            return jsonify({"error": "消息内容为空"}), 400

        message = {
            "id": len(messages) + 1,
            "sender": sender,
            "content": message_content,
            "verification_code": extract_verification_code(message_content),
            "timestamp": datetime.now().isoformat(),
            "received_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        messages.append(message)

        if len(messages) > MESSAGE_LIMIT:
            messages.pop(0)

        print(f"收到新消息: {sender} - {message_content[:50]}...")

        return jsonify({
            "status": "success",
            "message": "消息接收成功",
            "id": message["id"],
            "verification_code": message["verification_code"]
        })

    except Exception as e:
        print(f"处理消息时出错: {e}")
        return jsonify({"error": "处理消息时出错"}), 500


@app.route('/api/messages/<int:message_id>', methods=['DELETE'])
def delete_message(message_id):
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not verify_token(token):
        return jsonify({"error": "未授权的访问"}), 401

    global messages
    messages = [msg for msg in messages if msg['id'] != message_id]

    return jsonify({"status": "success", "message": "消息已删除"})


@app.route('/api/messages/clear', methods=['DELETE'])
def clear_messages():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not verify_token(token):
        return jsonify({"error": "未授权的访问"}), 401

    messages.clear()
    return jsonify({"status": "success", "message": "所有消息已清空"})


if __name__ == '__main__':
    init_tokens()

    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'

    print("=" * 50)
    print("短信API服务器启动中...")
    print(f"API端点: http://localhost:{port}/api/")
    print(f"Webhook地址: http://localhost:{port}/api/webhook/sms")
    print("=" * 50)

    app.run(host='0.0.0.0', port=port, debug=debug)