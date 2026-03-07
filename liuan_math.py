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
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 4px solid #1E88E5;
    }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3.2em; }
    .question-box {
        background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 8px solid #1E88E5;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02); margin-bottom: 20px;
    }
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

    if is_review:
        # 【启发式核心】：禁止公式，强迫汉字点拨
        base_instruction = (
            f"识别码:{entropy}。你现在是名师李鹏燕。任务：批改与启发。"
            "【强制要求】：1. 严禁使用任何代数符号（如 ^, /, *, =, sqrt）。"
            "2. 数学关系必须用汉字描述（如：‘比值’、‘平方’、‘根号’、‘相等’）。"
            "3. 不要给步骤，要给‘题眼’启发。第一行必须写：【判定】：正确 或 【判定】：错误。"
        )
    else:
        base_instruction = (
            f"识别码:{entropy}。你现在是名师李鹏燕。任务：命题。"
            "【要求】：只给题干和选项。纯文字描述，严禁出现符号和‘图’字。"
        )

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": base_instruction + sys_msg},
                      {"role": "user", "content": user_msg}],
            temperature=0.7, # 提高语感丰富度
            max_tokens=600
        )
        return response.choices[0].message.content
    except: return "连接中..."

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
except: st.error("数据连接异常")

# --- 5. 主界面看板 ---
st.title("🛡️ 智汇皋陶：九年级数学自适应演化系统")
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="metric-card">👤 学生：{curr_student}</div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="metric-card">🎯 攻坚：{recommended_kp}</div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="metric-card">📈 能力值：{sum(scores)/6:.1f}</div>', unsafe_allow_html=True)

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
        m_cat = st.selectbox("大类：", list(topic_map.keys()), index=list(topic_map.keys()).index(recommended_kp) if recommended_kp in topic_map else 0)
        s_cat = st.selectbox("子主题：", topic_map[m_cat])

        if st.button("✨ 生成练习题目"):
            for key in ["last_review", "last_impact"]:
                if key in st.session_state: del st.session_state[key]
            q_prompt = f"针对【{s_cat}】出一道单选题。不准提图。只给题干和选项。"
            st.session_state.q_text = gao_tao_ai_engine("命题专家", q_prompt, deepseek_key, is_review=False)
            st.session_state.active_m, st.session_state.active_s = m_cat, s_cat
            st.rerun() 
        
        if "q_text" in st.session_state:
            st.markdown(f'<div class="question-box"><b>📝 练习：{st.session_state.active_s}</b><br><br>{st.session_state.q_text}</div>', unsafe_allow_html=True)
            u_ans = st.text_area("✍️ 输入你的答案或思路：", height=100)
            if st.button("🚀 提交并自动演化"):
                p_prompt = f"题目：{st.session_state.q_text}\n回答：{u_ans}\n判定对错并点拨。"
                review = gao_tao_ai_engine("导师", p_prompt, deepseek_key, is_review=True)
                
                # 【逻辑优化】：不区分大小写判定
                impact = 2 if "【判定】：正确" in review or "【判定】：正确".lower() in review.lower() else -2
                
                update_ability_auto(curr_student, st.session_state.active_m, impact)
                supabase.table("study_logs").insert({
                    "student_name": curr_student, "knowledge_point": st.session_state.active_s,
                    "question": st.session_state.q_text, "answer_logic": u_ans, "ai_review": review, "score_impact": impact
                }).execute()
                st.session_state.last_review, st.session_state.last_impact = review, impact
                st.rerun() 

    with r_col:
        st.subheader("💡 演化反馈")
        if "last_review" in st.session_state:
            color = "#10b981" if st.session_state.last_impact > 0 else "#ef4444"
            st.markdown(f'<h2 style="color:{color}; text-align:center;">{"+" if st.session_state.last_impact > 0 else ""}{st.session_state.last_impact}</h2>', unsafe_allow_html=True)
            st.write(st.session_state.last_review)

with tab2:
    st.subheader("📜 历史演化轴")
    try:
        logs = supabase.table("study_logs").select("*").eq("student_name", curr_student).order("created_at", desc=True).execute().data
        for log in logs:
            with st.expander(f"📅 {log['created_at'][:16]} | {log['knowledge_point']}"):
                st.write(f"题：{log['question']}")
                st.info(f"启发：{log['ai_review']}")
    except: st.write("档案载入中...")

with tab3:
    st.subheader("📋 学情诊断简报")
    if st.button("📈 生成名师诊断报告"):
        best_kp = radar_df.loc[radar_df['得分'].idxmax(), '维度']
        st.divider()
        st.header(f"皋陶数苑：{curr_student} 同学学情诊断书")
        st.subheader("一、 整体画像分析")
        st.write(f"孩子，这一阶段你的综合能力值已达到 **{sum(scores)/6:.1f}** 分。目前你在 **{best_kp}** 领域展现出了极强的几何直白感，非常棒！")
        
        st.subheader("二、 知识盲区诊断")
        st.write(f"通过系统的 **{len(logs)}** 次交互，我发现你在 **{recommended_kp}** 这一板块仍有挑战，要加油。")
        
        st.subheader("三、 导学建议")
        st.markdown(f"""
        * **【策略】**：每天针对“{recommended_kp}”进行汉字化逻辑推导，不急着动笔算。
        * **【反馈】**：多利用系统的“名师点拨”，从文字描述中寻找几何本质。
        """)
        
        st.write(f"\n\n**—— 您的导学老师：李鹏燕**")
        st.balloons()
