"""
中医知识问答 - 后端服务（纯Python版，可部署到任意云平台）
对接 IMA 知识库 + DeepSeek API
"""
import json
import os
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.request

# ── 配置（从环境变量读取，部署时在云平台设置）──────────────
IMA_CLIENT_ID = os.environ.get("IMA_OPENAPI_CLIENTID", "")
IMA_API_KEY = os.environ.get("IMA_OPENAPI_APIKEY", "")
KB_ID = os.environ.get("KB_ID", "SV1LP_ohoX7Fq_Up6P1ssrCAuEKyoyL2hQCqunxxrFk=")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-1421314d63634de08de8b11ea27d95ec")
PORT = int(os.environ.get("PORT", "8088"))

IMA_BASE_URL = "https://ima.qq.com"


def call_ima_api(api_path: str, body: dict) -> dict:
    """直接用 Python 调用 IMA API（不依赖 Node）"""
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
    """调用 DeepSeek API 生成回答"""
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
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"【调用 DeepSeek 出错】{str(e)}"


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
            self._handle_search(params.get("q", [""])[0])
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
        if not question:
            return self._send_json({"error": "请输入问题"}, 400)


            {"role": "system", "content": "You are a professional translator specializing in Traditional Chinese Medicine (TCM). Translate the following Chinese text into English. Keep all proper names of books and persons in Pinyin, followed by English translation in parentheses. For TCM terms, use Pinyin (English) format, e.g. 'Fuzi (Aconite)', 'Liu Jing (Six Meridians)'. Output ONLY the translation, nothing else."},
            {"role": "user", "content": f"Translate the following into English:\n\n{text}"}
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
        return result["choices"][0]["message"]["content"]
    except:
        return text


        
        # 1. 搜索知识库
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

        # 2. 调用 DeepSeek
        system_prompt = """你是一位精通中医经典文献的学术顾问。你的核心参考著作如下：

 # 3. 构建 messages（含历史对话记忆）
    user_prompt = f"""知识库中检索到的相关资料：
{context}


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

回答规则：
1. 分析病情时，优先以吴雄志、胡希恕、郑钦安、祝味菊、张景岳的著作为依据
2. 用药方面：
   a. 分别说明不同种类药物的药效和不良反应（副作用）
   b. 说明用药之后病情可能的变化（包括好转和恶化的指征）
   c. 用药须兼顾补虚与攻邪，不可偏废
   d. 始终注意平衡患者的阴津与阳气
3. 用户咨询时提出的信息如果不全面，不能下结论，可以给出病情有几种可能性，同时要求用户补充信息以完善分析
4. 用药要参考中医名家案例，不用注明具体出处（哪本书、哪位医家）
5. 分析框架须兼顾六经辨证与八纲辨证（表里、寒热、虚实、阴阳）
6. 孕妇用药严格参考韩百灵和裘笑梅的案例，韩百灵和裘笑梅没有给孕妇用过的药物尽量不要给孕妇推荐。
7. 出血病人要在使用活血化瘀药物时要选择活血止血的药物。
8. 基于知识库内容回答，不编造
9. 回答末尾强调：⚠️ 本回答仅供学术交流，不构成医疗建议，身体不适请及时就医。
10. 不确定时说"知识库中暂无相关记载"
请用中文回答。"""

        user_prompt = f"""知识库中检索到的相关资料：
{context}

用户问题：{question}

请优先参考吴雄志、胡希恕、郑钦安、祝味菊、张景岳的著作进行分析，兼顾六经八纲，不用注明出处。"""


  # 构建 messages: system + 历史对话 + 当前问题
    messages = [{"role": "system", "content": SYSTEM_PROMPT_ZH}]

    # 添加历史对话（最多保留最近 20 条消息 ≈ 10 轮）
    for msg in history[-20:]:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_prompt})

    answer = call_deepseek(messages)

    # 英文模式：将中文回答翻译成英文
    if answer and lang == "en" and DEEPSEEK_API_KEY:
        answer = translate_to_english(answer)

    if answer is None:
        if kb_items:
            docs = "\n".join(f"- 《{i.get('title','').replace('.pdf','')}》" for i in kb_items[:3])
            if lang == "en":
                answer = f"""📚 **About: "{question}"**       
        answer = call_deepseek([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])

        if answer is None:
            if kb_items:
                docs = "\n".join(f"- 《{i.get('title','').replace('.pdf','')}》" for i in kb_items[:3])
                answer = f"""📚 **关于「{question}」**

根据知识库检索，以下典籍可能包含相关内容：

{docs}

💡 **说明**：当前 DeepSeek API Key 未配置，已展示知识库中相关文献。

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
