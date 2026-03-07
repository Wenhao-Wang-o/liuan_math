import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI
from supabase import create_client
import time
import random

# --- 1. 核心配置 ---
SUPABASE_URL = "https://jjewahmunvpxvcdijkut.supabase.co"
SUPABASE_KEY = "sb_publishable_KsergHPW4s6njlkY3P2vag_xRRfoJ14"


@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = init_supabase()

# --- 2. 稳健版 UI 样式 ---
st.set_page_config(page_title="皋陶数苑-AI自适应系统", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .metric-card { 
        background: white; padding: 15px; border-radius: 10px; text-align: center; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-bottom: 4px solid #1E88E5;
    }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3.2em; }
    </style>
    """, unsafe_allow_html=True)


# --- 3. 核心功能函数 ---
def fetch_student_data():
    res = supabase.table("student_scores").select("*").order("student_name").execute()
    return pd.DataFrame(res.data)


def update_ability_auto(name, kp, impact):
    res = supabase.table("student_scores").select(kp).eq("student_name", name).single().execute()
    old_val = float(res.data[kp])
    new_val = max(0, min(100, old_val + int(impact)))
    supabase.table("student_scores").update({kp: new_val}).eq("student_name", name).execute()
    return new_val


def gao_tao_ai_engine(sys_msg, user_msg, api_key, is_review=False):
    if not api_key: return "⚠️ 请在侧边栏输入 API Key"
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    entropy = str(time.time_ns())[-6:]

    # 彻底隔离指令：区分命题与批改
    if is_review:
        base_instruction = f"识别码:{entropy}。你现在是名师李鹏燕。任务：批改。要求：第一行必须写‘【判定】：正确/错误’。严禁使用LaTeX。"
    else:
        base_instruction = f"识别码:{entropy}。你现在是名师李鹏燕。任务：命题。要求：只给题干和选项。严禁出现‘判定’、‘正确’字眼。严禁使用LaTeX。不准提图。"

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": base_instruction + sys_msg},
                      {"role": "user", "content": user_msg}],
            temperature=0.3, max_tokens=600
        )
        return response.choices[0].message.content
    except:
        return "连接中..."


# --- 4. 侧边栏 ---
try:
    df = fetch_student_data()
    student_list = df["student_name"].tolist()
    with st.sidebar:
        st.header("🏫 皋陶学校管理中心")
        curr_student = st.selectbox("🎯 选择辅导学生：", student_list)
        s_data = df[df["student_name"] == curr_student].iloc[0]
        kps = ["二次函数", "圆的性质", "相似三角形", "锐角三角函数", "反比例函数", "综合几何"]
        scores = [s_data[k] for k in kps]

        radar_df = pd.DataFrame({"维度": kps, "得分": scores})
        fig = px.line_polar(radar_df, r='得分', theta='维度', line_close=True, range_r=[0, 100])
        fig.update_traces(fill='toself', fillcolor='rgba(30, 136, 229, 0.2)', line_color='#1E88E5')
        st.plotly_chart(fig, use_container_width=True)
        recommended_kp = kps[scores.index(min(scores))]
    deepseek_key = st.sidebar.text_input("🔑 DeepSeek Key", type="password")
except:
    st.error("数据连接异常")

# --- 5. 主界面看板 ---
st.title("🛡️ 智汇皋陶：九年级数学自适应演化系统")
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="metric-card">👤 学生：{curr_student}</div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="metric-card">🎯 攻坚：{recommended_kp}</div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="metric-card">📈 能力值：{sum(scores) / 6:.1f}</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🎯 演化练习", "📊 成长轨迹", "📜 诊断报告"])

with tab1:
    l_col, r_col = st.columns([3, 2])
    with l_col:
        st.subheader("🛠️ 选题中心")
        topic_map = {
            "相似三角形": ["相似三角形的判定", "相似三角形的性质"],
            "二次函数": ["二次函数图像性质", "二次函数与几何综合"],
            "圆的性质": ["垂径定理", "切线的判定与性质"],
            "锐角三角函数": ["特殊角的三角函数", "解直角三角形"],
            "反比例函数": ["反比例函数几何意义"],
            "综合几何": ["辅助线构造策略"]
        }
        m_cat = st.selectbox("大类：", list(topic_map.keys()))
        s_cat = st.selectbox("子主题：", topic_map[m_cat])

        if st.button("✨ 生成练习题目"):
            # 清理状态防止残留
            for key in ["last_review", "last_impact"]:
                if key in st.session_state: del st.session_state[key]
            q_prompt = f"针对【{s_cat}】出一道单选题。不准提图。只给题干和选项。"
            st.session_state.q_text = gao_tao_ai_engine("命题专家", q_prompt, deepseek_key, is_review=False)
            st.session_state.active_m, st.session_state.active_s = m_cat, s_cat
            st.rerun()

        if "q_text" in st.session_state:
            st.info(f"当前主题：{st.session_state.active_s}")
            st.success(st.session_state.q_text)  # 用原生绿色框显示题目，稳妥无错
            u_ans = st.text_area("✍️ 输入你的回答：", height=100)
            if st.button("🚀 提交并自动演化"):
                p_prompt = f"题目：{st.session_state.q_text}\n回答：{u_ans}\n判定对错并点拨。"
                review = gao_tao_ai_engine("导师", p_prompt, deepseek_key, is_review=True)
                impact = 2 if "【判定】：正确" in review else -2
                update_ability_auto(curr_student, st.session_state.active_m, impact)
                supabase.table("study_logs").insert({
                    "student_name": curr_student, "knowledge_point": st.session_state.active_s,
                    "question": st.session_state.q_text, "answer_logic": u_ans, "ai_review": review,
                    "score_impact": impact
                }).execute()
                st.session_state.last_review, st.session_state.last_impact = review, impact
                st.rerun()

    with r_col:
        st.subheader("💡 演化反馈")
        if "last_review" in st.session_state:
            st.metric("能力值变动", f"{'+' if st.session_state.last_impact > 0 else ''}{st.session_state.last_impact}")
            st.write(st.session_state.last_review)

with tab2:
    st.subheader("📜 历史演化轴")
    try:
        logs = supabase.table("study_logs").select("*").eq("student_name", curr_student).order("created_at",
                                                                                               desc=True).execute().data
        for log in logs:
            with st.expander(f"📅 {log['created_at'][:16]} | {log['knowledge_point']}"):
                st.write(f"题：{log['question']}")
                st.info(f"批：{log['ai_review']}")
    except:
        st.write("档案载入中...")

with tab3:
    st.subheader("📋 学情诊断简报")
    if st.button("📈 一键生成名师诊断报告"):
        # 放弃 HTML 渲染，使用 Markdown 高级语法排版
        best_kp = radar_df.loc[radar_df['得分'].idxmax(), '维度']
        avg_score = sum(scores) / 6

        st.divider()
        st.header(f"皋陶数苑：{curr_student} 同学学情诊断书")

        st.subheader("一、 整体画像分析")
        st.write(
            f"孩子，这一阶段你的综合能力值已达到 **{avg_score:.1f}** 分。目前你在 **{best_kp}** 领域展现出了极强的几何直观，这非常难得！")

        st.subheader("二、 知识盲区动态诊断")
        st.write(f"通过系统的 **{len(logs)}** 次交互，我发现你在 **{recommended_kp}** 这一板块存在明显的“能力震荡”。")

        st.subheader("三、 名师导学建议")
        st.markdown(f"""
        * **【策略性学习】**：每天针对“{recommended_kp}”进行 15 分钟思维建模，重点攻克辅助线逻辑。
        * **【数字化反馈】**：多利用系统的“点拨”功能，答错后不要急着看答案，根据提示重试。
        * **【心理锚定】**：目前的每一次“-2分”都是为了中考时的“+20分”，保持心态平稳。
        """)

        st.write(f"\n\n**—— 您的专属导学老师：李鹏燕**")
        st.write(f"*生成日期：2026-03-07*")
        st.balloons()