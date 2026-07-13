
"""
中医知识问答 - Vercel Serverless 后端
对接 IMA 知识库 + DeepSeek API
支持对话记忆 + 中英文切换 + 回答规则强约束
"""

import json
import os
import urllib.request
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ── 配置 ──────────────────────────────────
IMA_CLIENT_ID = os.environ.get("IMA_OPENAPI_CLIENTID", "d39da832a3285437af00a1dbc6d11581")
IMA_API_KEY = os.environ.get("IMA_OPENAPI_APIKEY", "Ta0Z2ZslUrB3ICRrBWFeh6GworUMQwxxQjxxTVqKieKKRZh1BLI72cFoyBYyDHdV618o6oz2AA==")
KB_ID = os.environ.get("KB_ID", "SV1LP_ohoX7Fq_Up6P1ssrCAuEKyoyL2hQCqunxxrFk=")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-1421314d63634de08de8b11ea27d95ec")
IMA_BASE_URL = "https://ima.qq.com"


# ── 工具函数 ──────────────────────────────

def call_ima_api(api_path: str, body: dict) -> dict:
    """调用 IMA API"""
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
    """调用 DeepSeek API"""
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
    """将中文文本翻译为英文"""
    if not DEEPSEEK_API_KEY:
        return text

    data = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "You are a professional translator specializing in Traditional Chinese Medicine (TCM). Translate the following Chinese text into English. Keep all proper names of books and persons in Pinyin, followed by English translation in parentheses. For TCM terms, use Pinyin (English) format, e.g. 'Fuzi (Aconite)', 'Liu Jing (Six Meridians)'. Output ONLY the translation, nothing else."
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
    """
    对模型回答进行强约束后处理：
    1. 追问规则：信息不全面时强制追加追问
    2. 不编造规则：知识库无相关内容时强制引用
    3. 承认未知规则：不确定时强制使用标准表述
    """
    zh = (lang != "en")
    
    # ── 规则 10：承认未知 ──
    # 如果回答包含模糊表述且知识库无相关内容，强制替换
    unknown_indicators = ["可能", "或许", "推测", "猜想", "我认为", "我觉得"]
    has_unknown_indicator = any(ind in answer for ind in unknown_indicators)
    no_kb_content = (not kb_items or len(kb_items) == 0)
    
    if no_kb_content and has_unknown_indicator:
        # 检查是否已经是标准"未知"回答
        standard_unknown_zh = "知识库中暂无相关记载"
        standard_unknown_en = "No relevant records found in the knowledge base"
        if standard_unknown_zh not in answer and standard_unknown_en not in answer:
            # 强制替换为标准的"未知"回答
            if zh:
                answer = f"""关于「{question}」，知识库中暂无相关记载。

💡 建议您换个角度提问，或提供更详细的症状描述以便检索。

⚠️ 本回复仅供学术交流，不构成医疗建议，身体不适请及时就医。"""
            else:
                answer = f"""Regarding "{question}", no relevant records were found in the knowledge base.

💡 Please try a different approach to your question, or provide more detailed symptom descriptions.

⚠️ This response is for academic exchange only and does not constitute medical advice."""
            return answer
    
    # ── 规则 8：不编造 ──
    # 如果知识库有内容但回答中完全没有引用，且回答包含了知识库外的具体信息，追加引用说明
    if kb_items and len(kb_items) > 0:
        # 检查回答中是否提到了知识库中的文献标题
        kb_titles = [item.get("title", "").replace(".pdf", "").replace(".PDF", "") for item in kb_items[:5]]
        has_reference = any(title in answer for title in kb_titles)
        
        if not has_reference:
            # 知识库有内容但模型未引用，追加说明（但不强拆回答）
            docs = "\n".join(f"- 《{t}》" for t in kb_titles[:3])
            if zh:
                ref_note = f"\n\n📚 **知识库参考**：本次回答已检索以下文献：\n{docs}"
            else:
                ref_note = f"\n\n📚 **Knowledge Base References**: The following documents were retrieved:\n{docs}"
            answer += ref_note
    
    # ── 规则 3：追问 ──
    # 检查回答中是否包含追问或可能性分析
    has_followup = any(kw in answer for kw in ["可能性", "可能是", "请补充", "建议您补充", "需要您补充", 
                                                 "possibility", "possible", "please provide", "please supplement"])
    
    # 判断用户问题是否属于"信息不完整"类型（症状描述类问题且信息较少）
    symptom_keywords = zh and ["症状", "不舒服", "疼痛", "咳嗽", "发热", "头痛", "胃痛", "失眠", "便秘", "腹泻",
                               "symptom", "pain", "cough", "fever", "headache", "stomach", "sleep", "constipation"]
    is_symptom_question = any(kw in question for kw in symptom_keywords)
    
    # 对于症状类问题且回答长度较短（说明模型没有充分分析），强制补充追问模板
    if is_symptom_question and not has_followup:
        if zh:
            followup_template = """
            
💡 **补充信息**：为了更准确地为您分析病情，请您补充以下信息（至少 3 项）：
1. **舌象**：舌质颜色（淡白/红/紫暗）、舌苔（薄白/黄腻/厚腻）
2. **脉象**：浮/沉/迟/数/弦/滑/细/弱
3. **二便情况**：大便（干结/溏稀/不成形）、小便（清长/短赤/频数）
4. **睡眠与饮食**：睡眠质量、胃口好坏、饮水量和温度偏好
5. **主要不适症状的详细描述**：部位、性质、持续时间、加重或缓解因素

⚠️ 本回答仅供学术交流，不构成医疗建议。"""
        else:
            followup_template = """
            
💡 **Supplementary Information**: For a more accurate analysis, please provide at least 3 of the following:
1. **Tongue Diagnosis**: Tongue body color (pale/red/purple), coating (thin white/yellow greasy/thick greasy)
2. **Pulse Diagnosis**: Floating/sinking/slow/rapid/wiry/slippery/thin/weak
3. **Stool & Urine**: Bowel movements (dry/loose/watery), urine (clear/long/short/red/frequent)
4. **Sleep & Appetite**: Sleep quality, appetite, water intake and temperature preference
5. **Detailed symptom description**: Location, nature, duration, aggravating or relieving factors

⚠️ This response is for academic exchange only and does not constitute medical advice."""
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
1. 分析病情时，优先以吴雄志、胡希恕、郑钦安、祝味菊、张景岳的著作为依据
2. 用药方面：
   a. 分别说明不同种类药物的药效和不良反应（副作用）
   b. 说明用药之后病情可能的变化（包括好转和恶化的指征）
   c. 用药须兼顾补虚与攻邪，不可偏废
   d. 始终注意平衡患者的阴津与阳气
3. **追问规则（强制性）**：当用户咨询时提出的信息不全面（如缺少舌象、脉象、二便、睡眠等信息），你**必须**给出至少 2-3 种可能的证型分析，并**明确要求**用户补充信息。回复格式示例：
   "根据您目前提供的信息，有以下几种可能性：
   可能性一：...
   可能性二：...
   为了准确判断，请您补充以下信息：1. 舌象 2. 脉象 3. 二便情况"
4. 用药要参考中医名家案例，不用注明具体出处（哪本书、哪位医家）
5. 分析框架须兼顾六经辨证与八纲辨证（表里、寒热、虚实、阴阳）
6. 孕妇用药严格参考韩百灵和裘笑梅的案例，韩百灵和裘笑梅没有给孕妇用过的药物尽量不要给孕妇推荐。
7. 出血病人要在使用活血化瘀药物时要选择活血止血的药物。
8. **不编造规则（强制性）**：你必须基于知识库内容回答。如果知识库中提供了相关信息，请在回答中明确引用文献标题。**绝对不要编造不存在的文献、医案或数据**。
9. 回答末尾强调：⚠️ 本回答仅供学术交流，不构成医疗建议，身体不适请及时就医。
10. **承认未知规则（强制性）**：如果你不确定，或者说知识库中没有找到确切依据，**必须**直接回答"知识库中暂无相关记载"，**不得**使用"可能""或许""推测"等模糊表述来编造答案。
请用中文回答。"""


# ── API 路由 ──────────────────────────────

@app.route("/api/chat", methods=["POST"])
def chat():
    """问答接口"""
    body = request.get_json(force=True)
    question = (body.get("question") or "").strip()
    history = body.get("history", [])
    lang = body.get("lang", "zh")

    if not question:
        return jsonify({"error": "请输入问题"}), 400

    # 1. 搜索 IMA 知识库
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

    # 2. 构建 messages
    user_prompt = f"""知识库中检索到的相关资料：
{context}

用户问题：{question}

请优先参考吴雄志、胡希恕、郑钦安、祝味菊、张景岳的著作进行分析，兼顾六经八纲。"""

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # 添加历史对话
    for msg in history[-20:]:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_prompt})

    # 3. 调用 DeepSeek
    answer = call_deepseek(messages)

    # 4. 强约束后处理
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

    return jsonify({
        "answer": answer,
        "sources": [{
            "title": i.get("title", "").replace(".pdf", "").replace(".PDF", ""),
            "media_id": i.get("media_id", "")
        } for i in kb_items[:5]]
    })


@app.route("/api/info", methods=["GET"])
def info():
    """获取知识库信息"""
    resp = call_ima_api("openapi/wiki/v1/get_knowledge_base", {"ids": [KB_ID]})
    if resp.get("code") != 0:
        return jsonify({"error": "获取失败"}), 500
    kb = resp.get("data", {}).get("infos", {}).get(KB_ID, {})
    return jsonify({
        "name": kb.get("name", "中医知识仅供交流"),
        "description": kb.get("description", ""),
        "content_count": 25
    })


@app.route("/api/search", methods=["GET"])
def search():
    """搜索知识库"""
    q = request.args.get("q", "")
    if not q:
        return jsonify({"items": []})
    resp = call_ima_api("openapi/wiki/v1/search_knowledge", {
        "query": q, "knowledge_base_id": KB_ID, "cursor": ""
    })
    items = resp.get("data", {}).get("info_list", []) if resp.get("code") == 0 else []
    return jsonify({"items": items})


app_instance = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8088")))
