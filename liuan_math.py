import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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

# --- 2. 炫酷 UI 样式注入 ---
st.set_page_config(page_title="皋陶数苑-AI自适应系统", layout="wide")
st.markdown("""
    <style>
    /* 渐变背景 */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    /* 玻璃拟态主卡片 */
    .main-card {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(10px);
        padding: 25px;
        border-radius: 20px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.18);
        margin-bottom: 20px;
    }
    /* 统计卡片动画 */
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border-top: 6px solid #1E88E5;
        transition: transform 0.3s;
    }
    .metric-card:hover {
        transform: translateY(-5px);
    }
    /* 按钮美化 */
    .stButton>button {
        background: linear-gradient(to right, #1E88E5, #1565C0);
        color: white;
        border: none;
        border-radius: 12px;
        font-weight: bold;
        height: 3.5em;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        box-shadow: 0 5px 15px rgba(21, 101, 192, 0.4);
        transform: scale(1.02);
    }
    /* 针对问题的题目框 */
    .question-display {
        background: #e3f2fd;
        border-left: 10px solid #1E88E5;
        padding: 20px;
        border-radius: 10px;
        font-size: 1.1em;
        color: #0d47a1;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心功能函数 (逻辑保持不变) ---
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
        base_instruction = f"识别码:{entropy}。你现在是名师李鹏燕。任务：批改。要求：第一行必须写‘【判定】：正确/错误’。严禁使用LaTeX。"
    else:
        base_instruction = f"识别码:{entropy}。你现在是名师李鹏燕。任务：命题。要求：只给题干和选项。严禁出现‘判定’字眼。严禁使用LaTeX。不准提图。"

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": base_instruction + sys_msg},{"role": "user", "content": user_msg}],
            temperature=0.3, max_tokens=600
        )
        return response.choices[0].message.content
    except: return "连接中..."

# --- 4. 侧边栏 ---
try:
    df = fetch_student_data()
    student_list = df["student_name"].tolist()
    with st.sidebar:
        st.markdown("## 🏫 皋陶学校管理中心")
        curr_student = st.selectbox("👤 选择辅导学生：", student_list)
        s_data = df[df["student_name"] == curr_student].iloc[0]
        kps = ["二次函数", "圆的性质", "相似三角形", "锐角三角函数", "反比例函数", "综合几何"]
        scores = [s_data[k] for k in kps]

        radar_df = pd.DataFrame({"维度": kps, "得分": scores})
        fig = px.line_polar(radar_df, r='得分', theta='维度', line_close=True, range_r=[0, 100], title="能力雷达图")
        fig.update_traces(fill='toself', fillcolor='rgba(30, 136, 229, 0.4)', line_color='#1E88E5')
        st.plotly_chart(fig, use_container_width=True)
        recommended_kp = kps[scores.index(min(scores))]
        deepseek_key = st.text_input("🔑 API Key", type="password")
except: st.error("数据连接异常")

# --- 5. 主界面看板 ---
st.markdown(f"# 🛡️ 智汇皋陶：九年级数学自适应系统")

# 炫酷看板：3个指标卡 + 1个综合得分仪
c1, c2, c3, c4 = st.columns([2, 2, 2, 3])
with c1:
    st.markdown(f'<div class="metric-card"><h3>👤 学生</h3><h2>{curr_student}</h2></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><h3>🎯 攻坚项</h3><h2 style="color:#D32F2F;">{recommended_kp}</h2></div>', unsafe_allow_html=True)
with c3:
    avg_score = sum(scores) / 6
    st.markdown(f'<div class="metric-card"><h3>📈 能力值</h3><h2 style="color:#2E7D32;">{avg_score:.1f}</h2></div>', unsafe_allow_html=True)
with c4:
    # 综合得分仪表盘
    gauge_fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = avg_score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "教学质量指数", 'font': {'size': 20}},
        gauge = {'axis': {'range': [None, 100]},
                 'bar': {'color': "#1E88E5"},
                 'steps': [
                     {'range': [0, 60], 'color': "#ffcdd2"},
                     {'range': [60, 85], 'color': "#fff9c4"},
                     {'range': [85, 100], 'color': "#c8e6c9"}]}))
    gauge_fig.update_layout(height=180, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(gauge_fig, use_container_width=True)

# --- 6. 标签页内容 ---
tab1, tab2, tab3 = st.tabs(["🎯 智能演化空间", "📊 成长轨迹轴", "📜 深度报告生成"])

with tab1:
    l_col, r_col = st.columns([3, 2])
    with l_col:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.subheader("🛠️ 智能选题中心")
        topic_map = {"相似三角形": ["判定", "性质"], "二次函数": ["图像", "综合"], "圆的性质": ["垂径定理", "切线"], "锐角三角函数": ["计算", "应用"], "反比例函数": ["意义"], "综合几何": ["辅助线"]}
        m_cat = st.selectbox("选择知识大类", list(topic_map.keys()))
        
        if st.button("✨ 立即开启自适应进化题目"):
            for key in ["last_review", "last_impact"]:
                if key in st.session_state: del st.session_state[key]
            st.session_state.q_text = gao_tao_ai_engine("命题专家", f"针对【{m_cat}】出一道单选题", deepseek_key)
            st.session_state.active_m = m_cat
            st.rerun()

        if "q_text" in st.session_state:
            st.markdown(f'<div class="question-display"><b>【题目展示】</b><br>{st.session_state.q_text}</div>', unsafe_allow_html=True)
            u_ans = st.text_area("✍️ 录入你的思考逻辑...", height=100)
            if st.button("🚀 提交并更新能力图谱"):
                with st.spinner("AI正在重构能力模型..."):
                    review = gao_tao_ai_engine("导师", f"题目：{st.session_state.q_text}\n答案：{u_ans}", deepseek_key, is_review=True)
                    impact = 2 if "【判定】：正确" in review else -2
                    update_ability_auto(curr_student, st.session_state.active_m, impact)
                    supabase.table("study_logs").insert({"student_name": curr_student, "knowledge_point": st.session_state.active_m, "question": st.session_state.q_text, "answer_logic": u_ans, "ai_review": review, "score_impact": impact}).execute()
                    st.session_state.last_review, st.session_state.last_impact = review, impact
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with r_col:
        st.subheader("💡 动态演化结果")
        if "last_review" in st.session_state:
            st.metric("本次演化增量", f"{st.session_state.last_impact}", delta=st.session_state.last_impact)
            st.info(st.session_state.last_review)
        else:
            st.write("等待演化触发...")

with tab2:
    st.markdown("### 📜 数字化成长档案")
    try:
        logs = supabase.table("study_logs").select("*").eq("student_name", curr_student).order("created_at", desc=True).execute().data
        for log in logs:
            with st.expander(f"📅 {log['created_at'][:16]} | {log['knowledge_point']} | 演化：{log['score_impact']}"):
                st.write(log['question'])
                st.info(log['ai_review'])
    except: st.write("档案载入中...")

with tab3:
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.subheader("📋 数字化诊断报告")
    if st.button("📈 汇总全量数据生成报告"):
        st.balloons()
        best_kp = radar_df.loc[radar_df['得分'].idxmax(), '维度']
        st.markdown(f"""
        # 🏫 皋陶学校：{curr_student} 同学学情简报
        ---
        ### 👑 卓越项：{best_kp}
        孩子，你在 **{best_kp}** 展现出的直觉非常棒！
        
        ### 🌋 攻坚项：{recommended_kp}
        我们在 **{recommended_kp}** 上还存在“能力震荡”，建议加强辅助线思维建模。
        
        **—— 您的专属导师：李鹏燕**
        """)
    st.markdown('</div>', unsafe_allow_html=True)
