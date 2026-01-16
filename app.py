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
# OpenAI API Key（Secrets 固定）
# ======================================================
if "OPENAI_API_KEY" not in st.secrets:
    st.error("OpenAI API Key が設定されていません（Secrets）")
    st.stop()

API_KEY = st.secrets["OPENAI_API_KEY"]
MAX_CALLS = int(st.secrets.get("MAX_CALLS", 100))

client = OpenAI(api_key=API_KEY)

# ======================================================
# API使用回数カウンタ
# ======================================================
if "api_calls" not in st.session_state:
    st.session_state.api_calls = 0

def check_api_limit():
    if st.session_state.api_calls >= MAX_CALLS:
        st.error(
            f"⚠ API利用上限に達しました（{MAX_CALLS}回）。"
            " 管理者に連絡してください。"
        )
        st.stop()

# ======================================================
# 評価項目名（15項目）
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

# ======================================================
# ランク判定（300点）
# ======================================================
def judge_rank(total: int) -> str:
    if total >= 270:
        return "S（極めて完成度が高い）"
    if total >= 240:
        return "A（非常に質が高い）"
    if total >= 210:
        return "B（水準以上）"
    if total >= 180:
        return "C（最低限成立）"
    if total >= 150:
        return "D（再設計推奨）"
    return "E（不十分）"

# ======================================================
# レーダーチャート
# ======================================================
def show_axis_radar(scores, axis):
    labels = [ITEM_NAMES[str(i)] for i in range(1, 16)]
    values = [scores[str(i)][axis] for i in range(1, 16)]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=labels + [labels[0]],
        fill="toself"
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 5])),
        showlegend=False,
        title=f"{axis} 評価（15項目）"
    )
    st.plotly_chart(fig, use_container_width=True)

# ======================================================
# AI 採点プロンプト
# ======================================================
def build_prompt(text: str) -> str:
    return f"""
あなたは地方議会の一般質問を評価する専門家です。

【採点方式】
・15項目
・各項目 A〜D（各0〜5点）
・1項目20点、合計300点
・3点＝最低限、5点＝例外的
・迷った場合は必ず低い点を付ける
・評価不能は0点

【評価対象文章】
{text}

【出力形式（JSONのみ）】
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
""".strip()

# ======================================================
# UI
# ======================================================
st.title("📘 一般質問 採点AIシステム（300点モデル）")
st.caption(f"API利用状況：{st.session_state.api_calls} / {MAX_CALLS} 回")

question_text = st.text_area("▼ 一般質問の原稿", height=280)

if st.button("🚀 AIで自動採点"):
    check_api_limit()

    if not question_text.strip():
        st.error("文章が入力されていません。")
    else:
        with st.spinner("AIが採点中…"):
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": build_prompt(question_text)}]
            )

            st.session_state.api_calls += 1

            raw = response.choices[0].message.content
            data = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])

            scores = data["scores"]

            total = 0
            item_totals = {}
            for i in range(1, 16):
                s = scores[str(i)]
                subtotal = s["A"] + s["B"] + s["C"] + s["D"]
                item_totals[str(i)] = subtotal
                total += subtotal

        st.success("採点完了")

        for i in range(1, 16):
            with st.expander(
                f"{i}. {ITEM_NAMES[str(i)]}（{item_totals[str(i)]} / 20点）"
            ):
                for k in ["A", "B", "C", "D"]:
                    st.write(f"{k}：{scores[str(i)][k]}点")

        st.subheader(f"🔢 合計点：{total} / 300")
        st.subheader(f"🏆 ランク：{judge_rank(total)}")

        axis = st.radio(
            "📊 表示する評価軸",
            ["A", "B", "C", "D"]
        )
        show_axis_radar(scores, axis)
