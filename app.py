import streamlit as st
from openai import OpenAI
import json
import plotly.graph_objects as go

# ======================================================
# Streamlit 基本設定
# ======================================================
st.set_page_config(
    page_title="一般質問 採点AIシステム（300点モデル）",
    layout="wide"
)

# ======================================================
# OpenAI API Key
# ======================================================
if "OPENAI_API_KEY" not in st.secrets:
    st.error("OpenAI API Key が設定されていません（Secrets）")
    st.stop()

API_KEY = st.secrets["OPENAI_API_KEY"]
MAX_CALLS = int(st.secrets.get("MAX_CALLS", 100))
client = OpenAI(api_key=API_KEY)

# ======================================================
# API使用回数管理
# ======================================================
if "api_calls" not in st.session_state:
    st.session_state.api_calls = 0

def check_api_limit(calls=1):
    if st.session_state.api_calls + calls > MAX_CALLS:
        st.error(f"⚠ API利用上限に達します（上限 {MAX_CALLS} 回）")
        st.stop()

# ======================================================
# 評価項目
# ======================================================
ITEM_NAMES = {
    "1": "テーマ設定の妥当性",
    "2": "目的の明確性",
    "3": "論理構成の明確性",
    "4": "根拠・エビデンスの妥当性",
    "5": "質問の具体性",
    "6": "政策提案の実現可能性",
    "7": "行政答弁を引き出す質問力",
    "8": "議会の役割・法的理解",
    "9": "住民視点・説明責任の明瞭性",
    "10": "答弁後のフォロー可能性",
    "11": "文章表現・スピーチ技術",
    "12": "行政との協働姿勢・倫理性",
    "13": "将来志向・イノベーション性",
    "14": "政策横断性・全体視点",
    "15": "議員としての成長・継続性"
}

AXIS_LABELS = {
    "A": "核心適合・本質性",
    "B": "明確性・具体性",
    "C": "根拠・裏付け",
    "D": "議会・行政適合性"
}

SCORE_EXPLANATION = {
    5: "完全充足。具体・一義的で実務で修正不要。",
    4: "実務上ほぼ問題なし。軽微な補足不足あり。",
    3: "最低限達成。抽象的で追加説明が必要。",
    2: "不足が明確。実務に結びつかない。",
    1: "形式的・断片的。",
    0: "未達・評価不能。"
}

# ======================================================
# 判定
# ======================================================
def judge_rank(total: int) -> str:
    if total >= 270:
        return "S（模範水準）"
    if total >= 240:
        return "A（非常に優秀）"
    if total >= 210:
        return "B（合格：実務水準）"
    if total >= 180:
        return "C（ボーダー）"
    return "D（不十分）"

# ======================================================
# レーダーチャート
# ======================================================
def show_radar_chart(item_totals):
    labels = [ITEM_NAMES[str(i)] for i in range(1, 16)]
    values = [item_totals[str(i)] for i in range(1, 16)]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=labels + [labels[0]],
        fill="toself"
    ))

    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 20])),
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

# ======================================================
# プロンプト
# ======================================================
def build_prompt(text: str) -> str:
    return f"""
あなたは地方議会の一般質問を評価する専門家です。
JSON以外は絶対に出力しないでください。

{text}

出力形式：
{{
 "scores": {{
   "1": {{"A":0,"B":0,"C":0,"D":0}},
   "2": {{"A":0,"B":0,"C":0,"D":0}},
   "3": {{"A":0,"B":0,"C":0,"D":0}},
   "4": {{"A":0,"B":0,"C":0,"D":0}},
   "5": {{"A":0,"B":0,"C":0,"D":0}},
   "6": {{"A":0,"B":0,"C":0,"D":0}},
   "7": {{"A":0,"B":0,"C":0,"D":0}},
   "8": {{"A":0,"B":0,"C":0,"D":0}},
   "9": {{"A":0,"B":0,"C":0,"D":0}},
   "10": {{"A":0,"B":0,"C":0,"D":0}},
   "11": {{"A":0,"B":0,"C":0,"D":0}},
   "12": {{"A":0,"B":0,"C":0,"D":0}},
   "13": {{"A":0,"B":0,"C":0,"D":0}},
   "14": {{"A":0,"B":0,"C":0,"D":0}},
   "15": {{"A":0,"B":0,"C":0,"D":0}}
 }}
}}
"""

# ======================================================
# UI
# ======================================================
st.title("📘 一般質問 採点AIシステム（300点モデル）")
st.caption(f"API利用状況：{st.session_state.api_calls} / {MAX_CALLS}")

question_text = st.text_area("一般質問原稿", height=280)

if st.button("AIで採点"):
    check_api_limit(calls=3)

    with st.spinner("採点中…"):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": build_prompt(question_text)}]
        )
        st.session_state.api_calls += 1

    try:
        raw = response.choices[0].message.content
        data = json.loads(raw)
    except Exception as e:
        st.error("JSON解析に失敗しました。")
        st.code(raw)
        st.stop()

    scores = data["scores"]
    total = 0
    item_totals = {}

    for i in range(1, 16):
        s = scores[str(i)]
        subtotal = sum(s.values())
        item_totals[str(i)] = subtotal
        total += subtotal

    # 判定表示
    if total >= 210:
        st.success(f"🟢 合格：{total} / 300")
    elif total >= 180:
        st.warning(f"🟡 ボーダー：{total} / 300")
    else:
        st.error(f"🔴 不合格：{total} / 300")

    show_radar_chart(item_totals)
