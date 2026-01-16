import streamlit as st
from openai import OpenAI
import json
import plotly.graph_objects as go

# ======================================================
# Streamlit 基本設定
# ======================================================
st.set_page_config(
    page_title="一般質問 採点AIシステム（300点・Before/After完全版）",
    layout="wide"
)

# ======================================================
# OpenAI API Key（Secrets固定）
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

def check_api_limit():
    if st.session_state.api_calls >= MAX_CALLS:
        st.error(f"⚠ API利用上限に達しました（{MAX_CALLS}回）")
        st.stop()

# ======================================================
# 評価項目・評価軸
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
    4: "実務上ほぼ問題なし。",
    3: "最低限達成（抽象的）。",
    2: "不足が明確。",
    1: "形式的・断片的。",
    0: "未達・評価不能。"
}

# ======================================================
# ランク判定（210点＝合格）
# ======================================================
def judge_rank(total: int) -> str:
    if total >= 270:
        return "S（模範水準）"
    if total >= 240:
        return "A（非常に優秀）"
    if total >= 210:
        return "B（合格：実務水準）"
    if total >= 180:
        return "C（未達）"
    if total >= 150:
        return "D（要再設計）"
    return "E（不十分）"

# ======================================================
# レーダーチャート（Before / After）
# ======================================================
def show_radar_chart_before_after(before_totals, after_totals):
    labels = [ITEM_NAMES[str(i)] for i in range(1, 16)]
    before_values = [before_totals[str(i)] for i in range(1, 16)]
    after_values = [after_totals[str(i)] for i in range(1, 16)]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=before_values + [before_values[0]],
        theta=labels + [labels[0]],
        fill="toself",
        name="Before（元原稿）",
        line=dict(color="rgba(0,123,255,0.9)", width=2),
        fillcolor="rgba(0,123,255,0.25)"
    ))

    fig.add_trace(go.Scatterpolar(
        r=after_values + [after_values[0]],
        theta=labels + [labels[0]],
        fill="toself",
        name="After（修正版）",
        line=dict(color="rgba(255,193,7,0.9)", width=2),
        fillcolor="rgba(255,193,7,0.35)"
    ))

    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 20])),
        showlegend=True,
        title="Before / After レーダーチャート比較（20点満点）"
    )

    st.plotly_chart(fig, use_container_width=True)

# ======================================================
# AI採点プロンプト
# ======================================================
def build_prompt(text: str) -> str:
    return f"""
あなたは地方議会一般質問の評価者です。

【採点方式】
15項目 × A〜D（各0〜5点）＝300点満点
3点は最低限、5点は例外的
迷ったら必ず低い点
評価不能は0点

【評価対象】
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
"""

# ======================================================
# 共通採点関数
# ======================================================
def run_scoring(text: str):
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": build_prompt(text)}]
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

    return scores, item_totals, total

# ======================================================
# UI
# ======================================================
st.title("📘 一般質問 採点AIシステム（300点・Before/After完全版）")
st.caption(f"API利用状況：{st.session_state.api_calls} / {MAX_CALLS}")

question_text = st.text_area(
    "▼ 一般質問の原稿を貼り付けてください（Before）",
    height=260
)

if st.button("🚀 採点 → 改善 → 再採点まで実行"):
    check_api_limit()

    if not question_text.strip():
        st.error("文章が入力されていません。")
        st.stop()

    # ===== Before =====
    before_scores, before_item_totals, before_total = run_scoring(question_text)
    st.subheader("① Before（元原稿）")
    st.write(f"合計点：{before_total} / 300　ランク：{judge_rank(before_total)}")

    # ===== 改善提案 =====
    improve_prompt = f"""
以下の一般質問をSランクに近づけるための改善提案を5つ出してください。
制度名・数値・期限・修正例を必ず含めてください。

【原稿】
{question_text}
"""
    improve_response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": improve_prompt}]
    )
    st.session_state.api_calls += 1
    st.subheader("② 改善提案")
    st.write(improve_response.choices[0].message.content)

    # ===== 修正版 =====
    revise_prompt = f"""
以下の元原稿と改善提案を踏まえ、
趣旨を変えず、一般質問としてそのまま読める修正版を作成してください。

【元原稿】
{question_text}

【改善提案】
{improve_response.choices[0].message.content}
"""
    revise_response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": revise_prompt}]
    )
    st.session_state.api_calls += 1

    revised_text = revise_response.choices[0].message.content
    st.subheader("③ 修正版・一般質問文（After）")
    st.write(revised_text)

    # ===== After =====
    after_scores, after_item_totals, after_total = run_scoring(revised_text)
    st.subheader("④ After（修正版）")
    st.write(f"合計点：{after_total} / 300　ランク：{judge_rank(after_total)}")

    # ===== 成果判定（3色）=====
    st.subheader("⑤ 成果判定")
    if after_total >= 210:
        st.success("🟢 合格水準に到達しました")
    elif after_total > before_total:
        st.warning(
            f"🟡 改善は見られますが、まだ合格水準には達していません\n\n"
            f"（Before：{before_total} 点 → After：{after_total} 点）"
        )
    else:
        st.error(
            f"🔴 十分な改善が見られず、不合格水準です\n\n"
            f"（Before：{before_total} 点 → After：{after_total} 点）"
        )

    # ===== レーダー比較 =====
    st.subheader("📊 Before / After レーダーチャート比較")
    show_radar_chart_before_after(before_item_totals, after_item_totals)
