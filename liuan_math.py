import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI
from supabase import create_client
import time

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
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    .main-card { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(10px); padding: 25px; border-radius: 20px; box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15); margin-bottom: 20px; }
    .metric-card { background: white; padding: 15px; border-radius: 15px; text-align: center; border-top: 6px solid #1E88E5; transition: transform 0.3s; }
    .metric-card:hover { transform: translateY(-5px); }
    .stButton>button { background: linear-gradient(to right, #1E88E5, #1565C0); color: white; border-radius: 12px; font-weight: bold; height: 3.5em; transition: all 0.3s; }
    .question-display { background: #e3f2fd; border-left: 10px solid #1E88E5; padding: 20px; border-radius: 10px; font-size: 1.1em; color: #0d47a1; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心 AI 引擎 ---
def gao_tao_ai_engine(sys_msg, user_msg, api_key, is_review=False):
    if not api_key: return "⚠️ 请在侧边栏输入 API Key"
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    if is_review:
        base_instruction = "你现在是李鹏燕老师。任务：批改。要求：第一行必须写‘【判定】：正确/错误。正确答案是：[字母]’。随后启发点拨，准许数字，严禁LaTeX。"
    else:
        base_instruction = "你现在是李鹏燕老师。任务：命题。要求：只给题干和选项。纯汉字描述，严禁LaTeX，不准提图。"
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": base_instruction + sys_msg},{"role": "user", "content": user_msg}],
            temperature=0.4, max_tokens=1000
        )
        return response.choices[0].message.content
    except: return "AI老师思考中..."

# --- 4. 侧边栏：管理中心 (全功能回归) ---
with st.sidebar:
    st.header("🏫 皋陶学校管理中心")
    deepseek_key = st.text_input("🔑 API Key", type="password")
    
    # 初始化课题体系
    if "topic_map" not in st.session_state:
        st.session_state.topic_map = {
            "相似三角形": ["判定定理应用", "相似比与面积关系"],
            "二次函数": ["顶点坐标性质", "抛物线对称性"],
            "圆的性质": ["垂径定理应用", "圆周角性质"],
            "锐角三角函数": ["特殊角计算", "解直角三角形"],
            "综合几何": ["辅助线构造", "最值问题"]
        }

    try:
        res = supabase.table("student_scores").select("*").order("student_name").execute()
        df = pd.DataFrame(res.data)
        student_list = df["student_name"].tolist()
        curr_student = st.selectbox("👤 选择辅导学生：", student_list)
        
        # 实时雷达图
        s_data = df[df["student_name"] == curr_student].iloc[0]
        active_kps = [col for col in s_data.index if col in st.session_state.topic_map.keys()]
        if active_kps:
            scores = [s_data[kp] for kp in active_kps]
            radar_df = pd.DataFrame({"维度": active_kps, "得分": scores})
            fig = px.line_polar(radar_df, r='得分', theta='维度', line_close=True, range_r=[0, 100])
            fig.update_traces(fill='toself', fillcolor='rgba(30, 136, 229, 0.4)', line_color='#1E88E5')
            st.plotly_chart(fig, use_container_width=True)
            recommended_kp = active_kps[scores.index(min(scores))]
        
        # 管理后台
        st.divider()
        with st.expander("🛠️ 系统档案与体系维护"):
            st.subheader("学生管理")
            new_name = st.text_input("新增姓名：")
            if st.button("➕ 确认入驻"):
                if new_name:
                    supabase.table("student_scores").insert({"student_name": new_name, "相似三角形": 60, "二次函数": 60, "圆的性质": 60, "综合几何": 60, "锐角三角函数": 60}).execute()
                    st.rerun()
            if st.button("❌ 注销当前学生"):
                supabase.table("student_scores").delete().eq("student_name", curr_student).execute()
                st.rerun()
            st.divider()
            st.subheader("选题维护")
            new_cat = st.text_input("新增大类：")
            if st.button("➕ 添加大类"):
                if new_cat: st.session_state.topic_map[new_cat] = ["基础考点"]; st.rerun()
            target_cat = st.selectbox("为大类添加子项：", list(st.session_state.topic_map.keys()))
            new_sub = st.text_input(f"新子项名称：")
            if st.button("➕ 确认添加子项"):
                if new_sub: st.session_state.topic_map[target_cat].append(new_sub); st.rerun()
    except: st.error("连接异常")

# --- 5. 主界面看板 ---
st.title(f"🛡️ 智汇皋陶：{curr_student} 的智慧导学驾驶舱")
avg_score = sum(scores)/len(scores) if scores else 0

c1, c2, c3, c4 = st.columns([2, 2, 2, 3])
with c1: st.markdown(f'<div class="metric-card"><h3>👤 学生</h3><h2>{curr_student}</h2></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="metric-card"><h3>🎯 攻坚项</h3><h2 style="color:#D32F2F;">{recommended_kp}</h2></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="metric-card"><h3>📈 能力值</h3><h2 style="color:#2E7D32;">{avg_score:.1f}</h2></div>', unsafe_allow_html=True)
with c4:
    gauge_fig = go.Figure(go.Indicator(mode="gauge+number", value=avg_score, title={'text': "教学质量指数", 'font': {'size': 18}}, gauge={'axis': {'range': [None, 100]}, 'bar': {'color': "#1E88E5"}}))
    gauge_fig.update_layout(height=160, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(gauge_fig, use_container_width=True)

tab1, tab2, tab3 = st.tabs(["🎯 智能演化练习", "📊 成长轨迹记录", "📜 深度审计诊断"])

with tab1:
    l_col, r_col = st.columns([3, 2])
    with l_col:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.subheader("🛠️ 智能选题中心")
        m_cat = st.selectbox("选择知识大类：", list(st.session_state.topic_map.keys()))
        s_cat = st.selectbox("锁定精细主题：", st.session_state.topic_map[m_cat])

        if st.button("✨ 生成启发式题目"):
            for key in ["last_review", "last_impact"]:
                if key in st.session_state: del st.session_state[key]
            if "user_ans_widget" in st.session_state: st.session_state["user_ans_widget"] = ""
            st.session_state.q_text = gao_tao_ai_engine("命题专家", f"针对【{s_cat}】出一道单选题", deepseek_key)
            st.session_state.active_m, st.session_state.active_s = m_cat, s_cat
            st.rerun()

        if "q_text" in st.session_state:
            st.markdown(f'<div class="question-display">{st.session_state.q_text}</div>', unsafe_allow_html=True)
            u_ans = st.text_area("✍️ 录入你的思考（请输入选项）：", height=100, key="user_ans_widget")
            if st.button("🚀 提交并更新图谱"):
                with st.spinner("名师正在分析中..."):
                    review = gao_tao_ai_engine("导师", f"题目：{st.session_state.q_text}\n回答：{u_ans}", deepseek_key, is_review=True)
                    first_line = review.split('\n')[0]
                    impact = 2 if "正确" in first_line and "错误" not in first_line else -2
                    supabase.table("study_logs").insert({"student_name": curr_student, "knowledge_point": st.session_state.active_s, "question": st.session_state.q_text, "answer_logic": u_ans, "ai_review": review, "score_impact": impact}).execute()
                    if st.session_state.active_m in s_data:
                        new_val = max(0, min(100, float(s_data[st.session_state.active_m]) + impact))
                        supabase.table("student_scores").update({st.session_state.active_m: new_val}).eq("student_name", curr_student).execute()
                    st.session_state.last_review, st.session_state.last_impact = review, impact
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with r_col:
        if "last_review" in st.session_state:
            st.subheader("💡 名师点评反馈")
            color = "#10b981" if st.session_state.last_impact > 0 else "#ef4444"
            st.markdown(f'<h2 style="color:{color};">变动：{"+" if st.session_state.last_impact > 0 else ""}{st.session_state.last_impact}</h2>', unsafe_allow_html=True)
            st.info(st.session_state.last_review)

with tab2:
    logs = supabase.table("study_logs").select("*").eq("student_name", curr_student).order("created_at", desc=True).execute().data
    for log in logs:
        with st.expander(f"📅 {log['created_at'][:16]} | {log['knowledge_point']}"):
            st.write(f"题：{log['question']}"); st.info(f"批：{log['ai_review']}")

with tab3:
    if st.button("🔍 开启全量数据审计与深度诊断"):
        with st.spinner("正在扫描档案库..."):
            if logs:
                history = "\n".join([f"考点:{l['knowledge_point']} | 判定:{'对' if l['score_impact']>0 else '错'}" for l in logs[:12]])
                report = gao_tao_ai_engine("诊断专家", f"该生记录：\n{history}\n请写详细分析及补救建议。", deepseek_key)
                st.markdown(f'<div class="report-card"><h2 style="text-align:center; color:#1E88E5;">皋陶数苑：{curr_student} 深度诊断报告</h2><hr>{report}<br><br><p style="text-align:right;"><b>主诊教师：李鹏燕</b></p></div>', unsafe_allow_html=True)
                st.balloons()
