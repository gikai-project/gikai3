import streamlit as st
from openai import OpenAI
import json
import plotly.graph_objects as go

# ======================================================
# Streamlit 基本設定
# ======================================================
st.set_page_config(
    page_title="地方議会一般質問 採点AIシステム（300点モデルver1）",
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
# API使用回数管理
# ======================================================
if "api_calls" not in st.session_state:
    st.session_state.api_calls = 0

def check_api_limit():
    if st.session_state.api_calls >= MAX_CALLS:
        st.error(
            f"⚠ API利用上限に達しました（{MAX_CALLS}回）。管理者に連絡してください。"
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
# 評価軸ラベル（A〜D）
# ======================================================
AXIS_LABELS = {
    "A": "核心適合・本質性",
    "B": "明確性・具体性",
    "C": "根拠・裏付け",
    "D": "議会・行政適合性"
}

# ======================================================
# 点数 → 説明文
# ======================================================
SCORE_EXPLANATION = {
    5: "完全充足。具体・一義的で、実務で修正不要。模範例として再利用可能。",
    4: "実務上ほぼ問題なし。一部に軽微な抽象や補足不足がある。",
    3: "最低限達成。触れてはいるが抽象的で、追加説明が必要。",
    2: "不足が明確。観点の一部にしか触れておらず、実務に結びつかない。",
    1: "形式的・断片的。キーワードが表面的に出るのみ。",
    0: "未達・評価不能。当該観点に触れていない、または不明確。"
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
# レーダーチャート（15項目×20点）
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
# AI 採点プロンプト（0〜5点定義を完全埋め込み）
# ======================================================
def build_prompt(text: str) -> str:
    return f"""
あなたは地方議会の一般質問を評価する専門家です。

【採点方式】
・15項目
・各項目 A〜D の4観点
・各観点 0〜5点（整数）
・1項目最大20点、合計300点
・3点は最低限（合格ではない）
・5点は例外的水準（頻出させない）
・迷った場合は必ず低い点を付ける
・評価不能な場合は必ず0点

【A〜D共通｜0〜5点 定義】
5点：完全充足。具体・一義的で第三者が同一理解に到達。
4点：実務上ほぼ問題なし。一部に軽微な抽象や補足不足あり。
3点：最低限達成。触れてはいるが抽象的で追加説明が必要。
2点：不足が明確。一部のみ触れており実務に結びつかない。
1点：形式的・断片的。キーワードのみ。
0点：未達・評価不能。推測や補完が必要な場合。

【評価観点】
A：核心適合・本質性  
B：明確性・具体性  
C：根拠・裏付け  
D：議会・行政適合性  

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
        # 評価軸の凡例（1回だけ表示）
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
            with st.expander(
                f"{i}. {ITEM_NAMES[str(i)]}（{item_totals[str(i)]} / 20点）"
            ):
                for k in ["A", "B", "C", "D"]:
                    p = scores[str(i)][k]
                    st.markdown(
                        f"**{AXIS_LABELS[k]}：{p}点**｜{SCORE_EXPLANATION[p]}"
                    )

        st.subheader(f"🔢 合計点：**{total} / 300 点**")
        st.subheader(f"🏆 ランク：**{judge_rank(total)}**")

        st.subheader("📈 レーダーチャート（AI採点）")
        show_radar_chart(item_totals)

        # ==================================================
        # 改善提案
        # ==================================================
        improve_prompt = f"""
あなたは地方議会一般質問の専門添削者です。
以下の一般質問を「Sランク（270点以上）」に近づけるため、
改善すべき点を **5つだけ** 箇条書きで提案してください。

【改善提案の厳格ルール】
- 抽象的表現は禁止
- 「何を／どの部分を／どの制度を使って／どう修正するか」まで明記
- 制度名・条例名・国ガイドライン・財源・担当部署のいずれかを含める
- 数値目標と期間を必ず含める
- 修正例（文章サンプル）を必ず付ける
- 他自治体事例を1つ以上含める

【一般質問原稿】
{question_text}

【AI採点結果】
{json.dumps(scores, ensure_ascii=False, indent=2)}
"""

        with st.spinner("改善提案を作成中…"):
            improve_response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": improve_prompt}]
            )

        st.subheader("🛠 改善提案（Sランクにするには？）")
        st.write(improve_response.choices[0].message.content)
