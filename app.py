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
# 評価項目（15項目）
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
# レーダーチャート
# ======================================================
def show_radar_chart(item_totals):
    labels = [ITEM_NAMES[str(i)] for i in range(1, 16)]
    values = [item_totals[str(i)] for i in range(1, 16)]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=labels + [labels[0]],
        fill="toself",
        line=dict(width=3)
    ))

    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 20])),
        showlegend=False,
        title="項目別評価分布（20点満点）"
    )

    st.plotly_chart(fig, use_container_width=True)

# ======================================================
# AI採点プロンプト
# ======================================================
def build_prompt(text: str) -> str:
    return f"""
あなたは地方議会の一般質問を評価する専門家です。

【採点方式】
・15項目
・各項目 A〜D の4観点
・各観点 0〜5点
・1項目20点、合計300点
・3点は最低限
・5点は例外的
・迷ったら必ず低く
・評価不能は0点

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
# UI
# ======================================================
st.title("📘 一般質問 採点AIシステム（300点モデル）")
st.caption(f"API利用状況：{st.session_state.api_calls} / {MAX_CALLS}")

question_text = st.text_area(
    "▼ 一般質問の原稿を貼り付けてください",
    height=280
)

if st.button("🚀 AIで自動採点する"):
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

        # ==================================================
        # 評価軸の凡例（1回だけ）
        # ==================================================
        st.info(
            "【評価軸の凡例】\n\n"
            "■ 核心適合・本質性\n"
            "なぜこの課題が重要なのか、地域課題の核心を突いているか\n\n"
            "■ 明確性・具体性\n"
            "誰が・いつ・何をするのかが具体的に示されているか\n\n"
            "■ 根拠・裏付け\n"
            "統計・計画・制度・会議録など客観的根拠が示されているか\n\n"
            "■ 議会・行政適合性\n"
            "議会質問として適切で、行政が答弁可能な設計か"
        )

        for i in range(1, 16):
            with st.expander(f"{i}. {ITEM_NAMES[str(i)]}（{item_totals[str(i)]} / 20点）"):
                for k in ["A", "B", "C", "D"]:
                    p = scores[str(i)][k]
                    st.markdown(f"**{AXIS_LABELS[k]}：{p}点**｜{SCORE_EXPLANATION[p]}")

        st.subheader(f"🔢 合計点：**{total} / 300 点**")
        st.subheader(f"🏆 ランク：**{judge_rank(total)}**")

        # ==================================================
        # 合格／不合格 色分け
        # ==================================================
        if total >= 210:
            st.success("🟢 判定：合格（実務水準）")
        else:
            st.error("🔴 判定：不合格（要改善）")

        # ==================================================
        # 合格に足りない項目 TOP3（不合格時）
        # ==================================================
        if total < 210:
            st.subheader("📉 合格に足りない項目 TOP3")
            shortage_list = []
            for i in range(1, 16):
                current = item_totals[str(i)]
                shortage_list.append({
                    "item": ITEM_NAMES[str(i)],
                    "current": current,
                    "shortage": 20 - current
                })

            top3 = sorted(shortage_list, key=lambda x: x["shortage"], reverse=True)[:3]
            for idx, t in enumerate(top3, start=1):
                st.markdown(
                    f"**{idx}. {t['item']}**  \n"
                    f"現在：{t['current']} / 20 点 ｜ 不足：**{t['shortage']} 点**"
                )

        st.subheader("📈 レーダーチャート")
        show_radar_chart(item_totals)

        # ==================================================
        # 総合講評
        # ==================================================
        summary_prompt = f"""
あなたは地方議会一般質問の評価者です。
合格基準は210点以上です。
以下の採点結果を踏まえて、200〜300字で総合講評を書いてください。

【原稿】
{question_text}

【結果】
合計点：{total} / 300
ランク：{judge_rank(total)}
項目別得点：
{json.dumps(item_totals, ensure_ascii=False)}
"""
        with st.spinner("総合講評を作成中…"):
            summary_response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": summary_prompt}]
            )
        st.subheader("📝 総合講評")
        st.write(summary_response.choices[0].message.content)

        # ==================================================
        # 改善提案
        # ==================================================
        improve_prompt = f"""
あなたは地方議会一般質問の専門添削者です。
Sランク（270点以上）を目指すための改善点を5つ挙げてください。
制度名・数値・期限・修正例を必ず含めてください。

【原稿】
{question_text}
"""
        with st.spinner("改善提案を作成中…"):
            improve_response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": improve_prompt}]
            )
        st.subheader("🛠 改善提案")
        st.write(improve_response.choices[0].message.content)
