
""" 中医知识问答系统 - Vercel Serverless 适配版（最终修正版） """
import os
import sys
import json
from typing import Optional
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# ---------- 环境变量（无默认值，部署时必须在 Vercel 后台设置） ----------
IMA_CLIENT_ID = os.environ.get("IMA_OPENAPI_CLIENTID")
IMA_API_KEY = os.environ.get("IMA_OPENAPI_APIKEY")
KB_ID = os.environ.get("KB_ID")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

# 可选的环境变量（有默认值，但建议按实际修改）
IMA_BASE_URL = os.environ.get("IMA_BASE_URL", "https://openapi.ima.com/v1")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# 在应用实例化前检查必填环境变量，避免冷启动后无密钥
if not all([IMA_CLIENT_ID, IMA_API_KEY, KB_ID, DEEPSEEK_API_KEY]):
    raise RuntimeError(
        "Missing required environment variables: IMA_OPENAPI_CLIENTID, "
        "IMA_OPENAPI_APIKEY, KB_ID, DEEPSEEK_API_KEY"
    )

# ---------- Flask 应用 ----------
app = Flask(__name__)

# CORS 配置：允许指定域名，默认放行所有来源（开发/测试）
ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
if ALLOWED_ORIGINS == ["*"]:
    CORS(app)
else:
    CORS(app, origins=ALLOWED_ORIGINS)

# ---------- 辅助函数 ----------

def call_ima_api(query: str) -> dict:
    """调用 IMA 知识库搜索 API"""
    try:
        resp = requests.post(
            f"{IMA_BASE_URL}/kb/search",
            json={"kb_id": KB_ID, "query": query, "top_k": 5},
            headers={
                "Content-Type": "application/json",
                "X-Client-Id": IMA_CLIENT_ID,
                "X-Api-Key": IMA_API_KEY,
            },
            timeout=15,
        )
        # 检查 HTTP 状态码
        if resp.status_code != 200:
            return {"code": -1, "msg": f"IMA API returned {resp.status_code}: {resp.text}"}
        return resp.json()
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def call_deepseek(messages: list) -> Optional[str]:
    """调用 DeepSeek 对话 API，失败返回 None"""
    try:
        resp = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1500,
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            },
            timeout=30,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        # 最终修正：choices 是列表，必须用 [0] 取第一条
        return data["choices"]["message"]["content"]
    except Exception:
        return None

def enforce_question_rules(answer: str, question: str, kb_items: list, history: list, lang: str) -> str:
    """规则增强：追问症状、承认未知、来源引用"""
    zh = (lang == "zh")
    q_lower = question.lower()

    # ---------- 1. 症状追问 ----------
    if zh:
        symptom_keywords = ["症状", "不舒服", "疼痛", "咳嗽", "发热", "头痛", "胃痛", "失眠", "便秘", "腹泻"]
        time_check = ["多久", "时间"]
    else:
        symptom_keywords = ["symptom", "pain", "cough", "fever", "headache", "stomach", "sleep", "constipation"]
        time_check = ["how long", "when"]

    is_symptom = any(kw in q_lower for kw in symptom_keywords)

    if is_symptom:
        recent_contents = []
        for msg in history[-3:]:
            if isinstance(msg, dict):
                recent_contents.append(msg.get("content", ""))
            else:
                recent_contents.append(str(msg))
        asked_time_in_question = any(kw in q_lower for kw in time_check)
        asked_time_in_history = any(
            kw in content.lower() for content in recent_contents for kw in time_check
        )
        if not asked_time_in_question and not asked_time_in_history:
            follow = (
                "\n\n💡 请问这个症状持续多久了？还有其他伴随症状吗？"
                if zh
                else "\n\n💡 How long have you had this symptom? Any other accompanying symptoms?"
            )
            if follow not in answer:
                answer += follow

    # ---------- 2. 知识库为空时的不确定处理 ----------
    no_kb = not kb_items
    uncertain = ["可能", "也许", "不一定", "不确定"] if zh else ["maybe", "perhaps", "might", "uncertain"]
    if no_kb and any(w in answer for w in uncertain):
        answer = (
            "【知识库中暂无相关记载】目前没有找到关于此问题的权威资料，建议咨询专业医师。"
            if zh
            else "[No relevant records in the knowledge base] No authoritative information found. Please consult a professional."
        )

    # ---------- 3. 来源引用 ----------
    if kb_items and "【来源】" not in answer and "📚" not in answer:
        answer += "\n\n" + ("📚 参考资料：\n" if zh else "📚 References:\n")
        for item in kb_items[:3]:
            answer += f"- {item.get('title', '未命名')}\n"

    return answer

# ---------- 路由 ----------

@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True)
    question = body.get("question", "").strip()[:500]  # 限制输入长度
    history = body.get("history", [])
    lang = body.get("lang", "zh")

    if not question:
        return jsonify({"error": "问题不能为空"}), 400

    # 知识库搜索
    ima_resp = call_ima_api(question)
    # 兼容不同返回结构
    data = ima_resp.get("data", {}) if isinstance(ima_resp, dict) else {}
    kb_items = data.get("info_list") or data.get("items") or []

    # 如果开发环境下可打印返回结构进行调试（生产环境可删除）
    # print("IMA response:", json.dumps(ima_resp, ensure_ascii=False))

    # 消息组装
    system_prompt = (
        "你是一位中医专家助手。请基于提供的知识库内容回答。"
        if lang == "zh"
        else "You are a TCM assistant. Answer based on the provided knowledge base."
    )
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-20:]:
        messages.append(msg)
    messages.append({"role": "user", "content": question})

    # 调用 DeepSeek
    ai_answer = call_deepseek(messages)

    if ai_answer is None:
        if kb_items:
            ai_answer = (
                "【知识库匹配结果】\n" if lang == "zh" else "[Knowledge Base Results]\n"
            )
            for item in kb_items[:3]:
                ai_answer += f"- {item.get('title', '')}\n"
        else:
            ai_answer = (
                "抱歉，暂时无法回答该问题。"
                if lang == "zh"
                else "Sorry, unable to answer at this time."
            )

    ai_answer = enforce_question_rules(ai_answer, question, kb_items, history, lang)

    return jsonify({"answer": ai_answer, "sources": kb_items[:3]})

@app.route("/api/search", methods=["GET"])
def search():
    q = request.args.get("q", "").strip()[:200]
    if not q:
        return jsonify({"error": "查询内容无效"}), 400
    result = call_ima_api(q)
    return jsonify(result)

@app.route("/")
def serve_index():
    """提供 index.html 首页"""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}
    except FileNotFoundError:
        return jsonify({"error": "index.html not found"}), 404

# 其他所有未匹配路径返回 404，避免误匹配
@app.route("/<path:path>")
def catch_all(path):
    return jsonify({"error": "Not found"}), 404
