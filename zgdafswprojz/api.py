from flask import Flask, request, jsonify
from flask_cors import CORS  # 处理跨域请求
import json
import os
from datetime import datetime
import hashlib

app = Flask(__name__)
CORS(app)  # 允许前端跨域访问

# 简单的内存存储（生产环境可换为数据库）
messages = []
message_limit = 50

# 安全配置
API_TOKENS = set()  # 有效的API令牌


def init_tokens():
    """初始化API令牌"""
    tokens = os.environ.get('API_TOKENS', '').split(',')
    for token in tokens:
        if token.strip():
            API_TOKENS.add(token.strip())


def verify_token(token):
    """验证API令牌"""
    if not API_TOKENS:  # 如果没有设置令牌，允许所有请求
        return True
    return token in API_TOKENS


def extract_verification_code(text):
    """提取验证码"""
    import re
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
    """健康检查端点"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message_count": len(messages)
    })


@app.route('/api/messages', methods=['GET'])
def get_messages():
    """获取消息列表"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not verify_token(token):
        return jsonify({"error": "未授权的访问"}), 401

    # 返回最近的消息
    recent_messages = messages[-20:]  # 只返回最近20条
    return jsonify({
        "messages": recent_messages,
        "total": len(messages)
    })


@app.route('/api/messages/latest', methods=['GET'])
def get_latest_message():
    """获取最新一条消息"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not verify_token(token):
        return jsonify({"error": "未授权的访问"}), 401

    if messages:
        return jsonify(messages[-1])
    else:
        return jsonify({"error": "没有消息"}), 404


@app.route('/api/webhook/sms', methods=['POST'])
def receive_sms():
    """接收短信的webhook端点"""
    # 验证请求来源（简单的令牌验证）
    token = request.headers.get('X-API-Token', '')

    if not verify_token(token):
        return jsonify({"error": "无效的令牌"}), 401

    try:
        # 解析请求数据
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        # 提取必要字段
        message_content = data.get('message') or data.get('body') or data.get('text', '')
        sender = data.get('from') or data.get('sender') or data.get('phone', '未知号码')

        if not message_content:
            return jsonify({"error": "消息内容为空"}), 400

        # 创建消息对象
        message = {
            "id": len(messages) + 1,
            "sender": sender,
            "content": message_content,
            "verification_code": extract_verification_code(message_content),
            "timestamp": datetime.now().isoformat(),
            "received_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 添加到消息列表
        messages.append(message)

        # 限制消息数量
        if len(messages) > message_limit:
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
    """删除指定消息"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not verify_token(token):
        return jsonify({"error": "未授权的访问"}), 401

    global messages
    messages = [msg for msg in messages if msg['id'] != message_id]

    return jsonify({"status": "success", "message": "消息已删除"})


@app.route('/api/messages/clear', methods=['DELETE'])
def clear_messages():
    """清空所有消息"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not verify_token(token):
        return jsonify({"error": "未授权的访问"}), 401

    messages.clear()
    return jsonify({"status": "success", "message": "所有消息已清空"})


if __name__ == '__main__':
    # 初始化API令牌
    init_tokens()

    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'

    print("=" * 50)
    print("短信API服务器启动中...")
    print(f"API端点: http://localhost:{port}/api/")
    print(f"Webhook地址: http://localhost:{port}/api/webhook/sms")
    print("=" * 50)

    app.run(host='0.0.0.0', port=port, debug=debug)