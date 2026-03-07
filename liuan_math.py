# --- 1. 核心配置与初始化 ---
import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI
from supabase import create_client
import time

SUPABASE_URL = "https://jjewahmunvpxvcdijkut.supabase.co"
SUPABASE_KEY = "sb_publishable_KsergHPW4s6njlkY3P2vag_xRRfoJ14"

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# --- 2. 增强版 UI 样式 ---
st.set_page_config(page_title="皋陶数苑-全功能管理系统", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .main-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    .question-box { background: #ffffff; padding: 25px; border-radius: 12px; border-left: 10px solid #1E88E5; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 25px; }
    .report-card { background: #fff; padding: 35px; border: 1px solid #e2e8f0; border-radius: 20px; box-shadow: 0 10px 30px rgba(30,136,229,0.1); line-height: 2; }
    .metric-card { background: white; padding: 15px; border-radius: 10px; text-align: center; border-bottom: 4px solid #1E88E5; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心功能函数 ---
def fetch_student_data():
    res = supabase.table("student_scores").select("*").order("student_name").execute()
    return pd.DataFrame(res.data)

def gao_tao_ai_engine(sys_msg, user_msg, api_key, is_review=False):
    if not api_key: return "⚠️ 请在侧边栏输入 API Key"
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    entropy = str(time.time_ns())[-6:]
    if is_review:
        base_instruction = f"识别码:{entropy}。你现在是李鹏燕老师。任务：批改。第一行给‘正确答案是：[选项]’，随后大白话启发，准许数字，严禁LaTeX。"
    else:
        base_instruction = f"识别码:{entropy}。你现在是名师李鹏燕。任务：命题。只给题干和选项。纯文字描述，不准提图，严禁LaTeX。"

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": base_instruction + sys_msg},
                      {"role": "user", "content": user_msg}],
            temperature=0.4, max_tokens=1000
        )
        return response.choices[0].message.content
    except: return "AI 老师思考中..."

# --- 4. 侧边栏：管理中心 ---
with st.sidebar:
    st.header("🏫 皋陶学校管理中心")
    deepseek_key = st.text_input("🔑 DeepSeek Key", type="password")
    
    # 核心：初始化选题体系（如果还没有的话）
    if "topic_map" not in st.session_state:
        st.session_state.topic_map = {
            "相似三角形": ["判定定理应用", "相似比与面积关系"],
            "二次函数": ["顶点坐标性质", "抛物线对称性"],
            "圆的性质": ["垂径定理应用", "圆周角性质"],
            "锐角三角函数": ["特殊角计算", "解直角三角形"],
            "反比例函数": ["几何意义", "图像交点"],
            "综合几何": ["辅助线构造", "最值问题"]
        }

    try:
        df = fetch_student_data()
        student_list = df["student_name"].tolist()
        curr_student = st.selectbox("🎯 当前辅导学生：", student_list)
        
        # --- 修复后的雷达图逻辑 ---
        s_data = df[df["student_name"] == curr_student].iloc[0]
        # 找出数据库中实际存在的数学大类列
        valid_columns = [col for col in s_data.index if col in st.session_state.topic_map.keys()]
        
        if valid_columns:
            radar_scores = [s_data[col] for col in valid_columns]
            radar_df = pd.DataFrame({"维度": valid_columns, "得分": radar_scores})
            fig = px.line_polar(radar_df, r='得分', theta='维度', line_close=True, range_r=[0, 100])
            fig.update_traces(fill='toself', fillcolor='rgba(30, 136, 229, 0.2)', line_color='#1E88E5')
            st.plotly_chart(fig, use_container_width=True)
            recommended_kp = valid_columns[radar_scores.index(min(radar_scores))]
        else:
            st.warning("暂无对应维度的能力评分")
            recommended_kp = "全科"
            radar_scores = [0]

        # 后台管理入口
        st.divider()
        with st.expander("🛠️ 数据库与体系维护"):
            st.subheader("👤 学生档案")
            add_name = st.text_input("新增姓名：")
            if st.button("➕ 确认入驻"):
                if add_name:
                    supabase.table("student_scores").insert({"student_name": add_name, "相似三角形": 60, "二次函数": 60, "圆的性质": 60, "锐角三角函数": 60, "反比例函数": 60, "综合几何": 60}).execute()
                    st.success("已加入"); st.rerun()
            if st.button("❌ 注销当前学生"):
                supabase.table("student_scores").delete().eq("student_name", curr_student).execute()
                st.rerun()

            st.divider()
            st.subheader("📚 课题维护")
            new_cat = st.text_input("新增大类：")
            if st.button("➕ 添加"):
                if new_cat:
                    st.session_state.topic_map[new_cat] = ["基础考点"]
                    st.rerun()
    except Exception as e:
        st.error(f"连接异常: {str(e)}")

# --- 5. 主界面内容 ---
if "curr_student" in locals():
    st.title(f"🛡️ 智汇皋陶：{curr_student} 的演化空间")
    avg_score = sum(radar_scores)/len(radar_scores) if radar_scores else 0
    
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="metric-card">👤 学生：{curr_student}</div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card">📈 综合均分：{avg_score:.1f}</div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card">🎯 建议攻坚：{recommended_kp}</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🎯 智能演化练习", "📊 成长轨迹", "📜 深度诊断报告"])

    with tab1:
        l_col, r_col = st.columns([3, 2])
        with l_col:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            m_cat = st.selectbox("选择知识大类：", list(st.session_state.topic_map.keys()))
            s_cat = st.selectbox("锁定精细主题：", st.session_state.topic_map[m_cat])

            if st.button("✨ 生成启发式题目"):
                q_prompt = f"针对【{s_cat}】出一道单选题。纯文字描述，只给题干和选项。"
                st.session_state.q_text = gao_tao_ai_engine("专家", q_prompt, deepseek_key)
                st.session_state.active_m, st.session_state.active_s = m_cat, s_cat
                st.rerun()

            if "q_text" in st.session_state:
                st.markdown(f'<div class="question-box">{st.session_state.q_text}</div>', unsafe_allow_html=True)
                u_ans = st.text_area("✍️ 你的思考（请输入选项）：", height=100)
                if st.button("🚀 提交并更新图谱"):
                    p_prompt = f"题目：{st.session_state.q_text}\n回答：{u_ans}\n判定对错并点拨。第一行给正确答案。"
                    review = gao_tao_ai_engine("导师", p_prompt, deepseek_key, is_review=True)
                    impact = 2 if "正确" in review or u_ans.upper() in review[:25] else -2
                    
                    supabase.table("study_logs").insert({"student_name": curr_student, "knowledge_point": st.session_state.active_s, "question": st.session_state.q_text, "answer_logic": u_ans, "ai_review": review, "score_impact": impact}).execute()
                    st.session_state.last_review = review
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with r_col:
            if "last_review" in st.session_state:
                st.subheader("💡 名师点评")
                st.write(st.session_state.last_review)

    with tab3:
        st.subheader("📋 深度学情诊断简报（名师定制版）")
        if st.button("🔍 开启数据审计"):
            with st.spinner("分析中..."):
                logs = supabase.table("study_logs").select("*").eq("student_name", curr_student).order("created_at", desc=True).limit(10).execute().data
                if logs:
                    history = "\n".join([f"考点:{l['knowledge_point']} | 判定:{'对' if l['score_impact']>0 else '错'} | 点拨:{l['ai_review'][:50]}" for l in logs])
                    diag_msg = f"该生最近记录：\n{history}\n请作为李鹏燕老师写详细诊断。包含：1.易错点。2.思维原因。3.建议。"
                    report = gao_tao_ai_engine("诊断专家", diag_msg, deepseek_key)
                    st.markdown(f'<div class="report-card"><h2 style="text-align:center; color:#1E88E5;">皋陶数苑：{curr_student} 深度诊断报告</h2><hr>{report}<br><br><p style="text-align:right;"><b>主诊教师：李鹏燕</b></p></div>', unsafe_allow_html=True)
                    st.balloons()
