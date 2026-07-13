"""
中医知识问答 - 后端服务（纯Python版，可部署到任意云平台）
对接 IMA 知识库 + DeepSeek API
支持对话记忆 + 中英文切换 + 回答规则强约束
"""

import json
import os
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.request

# ── 配置 ──────────────────────────────
IMA_CLIENT_ID = os.environ.get("IMA_OPENAPI_CLIENTID", "")
IMA_API_KEY = os.environ.get("IMA_OPENAPI_APIKEY", "")
KB_ID = os.environ.get("KB_ID", "SV1LP_ohoX7Fq_Up6P1ssrCAuEKyoyL2hQCqunxxrFk=")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
PORT = int(os.environ.get("PORT", "8088"))
IMA_BASE_URL = "https://ima.qq.com"


# ── 工具函数 ──────────────────────────────

def call_ima_api(api_path: str, body: dict) -> dict:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{IMA_BASE_URL}/{api_path}",
        data=data,
        headers={
            "Content-Type": "application/json",
            "ima-openapi-clientid": IMA_CLIENT_ID,
            "ima-openapi-apikey": IMA_API_KEY,
            "ima-openapi-ctx": "skill_version=1.1.7",
        }
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read())
    except Exception as e:
        return {"code": -1, "msg": str(e)}


def call_deepseek(messages: list) -> str:
    if not DEEPSEEK_API_KEY:
        return None
    data = json.dumps({
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
    )
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read())
        return result["choices"]["message"]["content"]
    except Exception as e:
        return f"【调用 DeepSeek 出错】{str(e)}"


def translate_to_english(text):
    if not DEEPSEEK_API_KEY:
        return text
    data = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "You are a professional translator specializing in TCM. Translate the following Chinese text into English. Keep all proper names of books and persons in Pinyin, followed by English translation in parentheses. For TCM terms, use Pinyin (English) format. Output ONLY the translation."
            },
            {
                "role": "user",
                "content": f"Translate the following into English:\n\n{text}"
            }
        ],
        "temperature": 0.3,
        "max_tokens": 2500
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
    )
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read())
        return result["choices"]["message"]["content"]
    except Exception as e:
        return f"【翻译出错】{str(e)}"


# ═══════════════════════════════════════════════
# 强约束规则：追问、不编造、承认未知
# ═══════════════════════════════════════════════

def enforce_question_rules(answer, question, kb_items, lang):
    """对模型回答进行强约束后处理"""
    zh = (lang != "en")
    
    # 规则 10：承认未知
    unknown_indicators = ["可能", "或许", "推测", "猜想", "我认为", "我觉得"]
    has_unknown_indicator = any(ind in answer for ind in unknown_indicators)
    no_kb_content = (not kb_items or len(kb_items) == 0)
    
    if no_kb_content and has_unknown_indicator:
        standard_unknown_zh = "知识库中暂无相关记载"
        standard_unknown_en = "No relevant records found in the knowledge base"
        if standard_unknown_zh not in answer and standard_unknown_en not in answer:
            if zh:
                answer = f"""关于「{question}」，知识库中暂无相关记载。

💡 建议您换个角度提问，或提供更详细的症状描述以便检索。

⚠️ 本回复仅供学术交流，不构成医疗建议，身体不适请及时就医。"""
            else:
                answer = f"""Regarding "{question}", no relevant records were found in the knowledge base.

💡 Please try a different approach to your question, or provide more detailed symptom descriptions.

⚠️ This response is for academic exchange only and does not constitute medical advice."""
            return answer
    
    # 规则 8：不编造（追加引用）
    if kb_items and len(kb_items) > 0:
        kb_titles = [item.get("title", "").replace(".pdf", "").replace(".PDF", "") for item in kb_items[:5]]
        has_reference = any(title in answer for title in kb_titles)
        if not has_reference:
            docs = "\n".join(f"- 《{t}》" for t in kb_titles[:3])
            if zh:
                ref_note = f"\n\n📚 **知识库参考**：本次回答已检索以下文献：\n{docs}"
            else:
                ref_note = f"\n\n📚 **Knowledge Base References**: The following documents were retrieved:\n{docs}"
            answer += ref_note
    
    # 规则 3：追问
    has_followup = any(kw in answer for kw in ["可能性", "可能是", "请补充", "建议您补充", "需要您补充",
                                                 "possibility", "possible", "please provide", "please supplement"])
    symptom_keywords = ["症状", "不舒服", "疼痛", "咳嗽", "发热", "头痛", "胃痛", "失眠", "便秘", "腹泻",
                        "symptom", "pain", "cough", "fever", "headache", "stomach", "sleep", "constipation"]
    is_symptom_question = any(kw in question for kw in symptom_keywords)
    
    if is_symptom_question and not has_followup:
        if zh:
            followup_template = """
            
💡 **补充信息**：为了更准确地为您分析病情，请您补充以下信息（至少 3 项）：
1. **舌象**：舌质颜色、舌苔情况
2. **脉象**：浮/沉/迟/数/弦/滑/细/弱
3. **二便情况**：大便性状、小便颜色和频率
4. **睡眠与饮食**：睡眠质量、胃口、饮水偏好
5. **主要不适症状的详细描述**

⚠️ 本回答仅供学术交流，不构成医疗建议。"""
        else:
            followup_template = """
            
💡 **Supplementary Information**: For accurate analysis, please provide at least 3 items:
1. **Tongue Diagnosis**: Body color and coating
2. **Pulse Diagnosis**: Floating/sinking/slow/rapid/wiry/slippery/thin/weak
3. **Stool & Urine**: Characteristics
4. **Sleep & Appetite**: Quality and preferences
5. **Detailed symptom description**

⚠️ This response is for academic exchange only."""
        answer += followup_template
    
    return answer


# ── 系统提示词（增强版） ──────────────────

SYSTEM_PROMPT = """你是一位精通中医经典文献的学术顾问。你的核心参考著作如下：

【核心医家】
- 吴雄志：《吴述重订伤寒杂病论》
- 胡希恕：《胡希恕温病条辨讲义》《经方医案（黄煌）》
- 郑钦安：《郑钦安医书阐释》（医理真传、医法圆通、伤寒恒论）
- 祝味菊：相关医案与学术著作
- 张景岳：《张景岳医学全书》（明清名医全书大成）

【补充参考】
- 火神派资料汇编、李可老中医经验专辑、危症难病倚附子、吴佩衡医案
- 医宗金鉴、蒲辅周/周仲瑛/朱良春/邓铁涛等临床家经验集
- 章真如临床经验集、孔伯华医案、傅青主女科、中华肿瘤治疗大成

回答规则（**必须严格遵守**）：
1. 分析病情时，优先以五位医家的著作为依据
2. 用药方面需说明药效、副作用、病情变化指征、兼顾补虚攻邪和阴阳平衡
3. **追问规则（强制性）**：信息不全面时，必须给出至少 2-3 种可能的证型，并明确要求用户补充舌象、脉象、二便等信息
4. 用药参考名家案例，不注明出处
5. 兼顾六经辨证与八纲辨证
6. 孕妇用药参考韩百灵和裘笑梅
7. 出血病人选择活血止血药物
8. **不编造规则（强制性）**：基于知识库回答，引用文献标题，绝对不编造
9. 回答末尾加免责声明
10. **承认未知规则（强制性）**：不确定时直接回答"知识库中暂无相关记载"，不得使用模糊表述
请用中文回答。"""


# ── HTTP 处理器 ──────────────────────────────

class Handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        if path == "/api/info":
            self._handle_info()
        elif path == "/api/search":
            params = parse_qs(parsed.query)
            self._handle_search(params.get("q", [""])[0](@ref)
        else:
            self._serve_static()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.rstrip("/") == "/api/chat":
            content_len = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_len))
            self._handle_chat(body)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _send_html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _handle_info(self):
        resp = call_ima_api("openapi/wiki/v1/get_knowledge_base", {"ids": [KB_ID]})
        if resp.get("code") != 0:
            return self._send_json({"error": "获取失败"}, 500)
        kb = resp.get("data", {}).get("infos", {}).get(KB_ID, {})
        self._send_json({
            "name": kb.get("name", "中医知识仅供交流"),
            "description": kb.get("description", ""),
            "content_count": 25
        })

    def _handle_search(self, q):
        if not q:
            return self._send_json({"items": []})
        resp = call_ima_api("openapi/wiki/v1/search_knowledge", {
            "query": q, "knowledge_base_id": KB_ID, "cursor": ""
        })
        items = resp.get("data", {}).get("info_list", []) if resp.get("code") == 0 else []
        self._send_json({"items": items})

    def _handle_chat(self, body):
        question = body.get("question", "").strip()
        history = body.get("history", [])
        lang = body.get("lang", "zh")

        if not question:
            return self._send_json({"error": "请输入问题"}, 400)

        # 搜索知识库
        ima_resp = call_ima_api("openapi/wiki/v1/search_knowledge", {
            "query": question, "knowledge_base_id": KB_ID, "cursor": ""
        })
        kb_items = ima_resp.get("data", {}).get("info_list", []) if ima_resp.get("code") == 0 else []

        context_lines = []
        titles = []
        for item in kb_items[:5]:
            t = item.get("title", "").replace(".pdf", "").replace(".PDF", "")
            titles.append(f"- 《{t}》")
            highlight = item.get("highlight_content", "")
            if highlight:
                context_lines.append(f"【{t}】{highlight}")

        context = "\n\n".join(context_lines) if context_lines else "知识库中找到相关文件：" + "\n".join(titles[:3])

        # 构建 messages
        user_prompt = f"""知识库中检索到的相关资料：
{context}

用户问题：{question}

请优先参考吴雄志、胡希恕、郑钦安、祝味菊、张景岳的著作进行分析，兼顾六经八纲。"""

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history[-20:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_prompt})

        # 调用 DeepSeek
        answer = call_deepseek(messages)

        # 强约束后处理
        answer = enforce_question_rules(answer, question, kb_items, lang)

        # 英文翻译
        if lang == "en" and DEEPSEEK_API_KEY:
            answer = translate_to_english(answer)

        if answer is None:
            if kb_items:
                docs = "\n".join(f"- 《{i.get('title','').replace('.pdf','')}》" for i in kb_items[:3])
                answer = f"""📚 **关于「{question}」**

根据知识库检索，以下典籍可能包含相关内容：

{docs}

⚠️ 本回复仅供学术交流，不构成医疗建议，身体不适请及时到医院就医。"""
            else:
                answer = f"""关于「{question}」，知识库中暂未检索到相关内容。

⚠️ 本回复仅供学术交流，不构成医疗建议。"""

        self._send_json({
            "answer": answer,
            "sources": [{
                "title": i.get("title", "").replace(".pdf", "").replace(".PDF", ""),
                "media_id": i.get("media_id", "")
            } for i in kb_items[:5]]
        })

    def _serve_static(self):
        html_path = os.path.join(os.path.dirname(__file__), "index.html")
        if os.path.exists(html_path):
            self._send_html(Path(html_path).read_text(encoding="utf-8"))
        else:
            self._send_html("<h1>页面未找到</h1>")


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"🚀 服务启动: http://0.0.0.0:{PORT}")
    server.serve_forever()
