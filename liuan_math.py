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
    .report-card { background: #fff; padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); line-height: 1.8; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心 AI 引擎 ---
def gao_tao_ai_engine(sys_msg, user_msg, api_key, is_review=False):
    if not api_key: return "⚠️ 请在侧边栏输入 API Key"
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    if is_review:
        base_instruction = (
            "你现在是皋陶学校数学特级教师李鹏燕。任务：批改。要求：\n"
            "1. 第一行必须写‘【判定】：正确/错误。正确答案是：[字母]’。\n"
            "2. 严禁使用任何 LaTeX 语法（如 $、^、sqrt、/）。\n"
            "3. 严禁使用枯燥代数式。所有几何关系必须用汉字描述（如：‘边长的平方’、‘根号2’、‘30度角’）。\n"
            "4. 一定要用老师的语气，温柔一点的老师，悉心指导。\n"
            "5. 启发式点拨，不要给步骤，只给‘题眼’引导学生思考。"
        )
    else:
        base_instruction = "你现在是特级教师李鹏燕。任务：命题。要求：只给题干和选项。严禁 LaTeX，纯文字描述，允许阿拉伯数字。"
        
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": base_instruction + sys_msg},{"role": "user", "content": user_msg}],
            temperature=0.7, max_tokens=800
        )
        return response.choices[0].message.content
    except: return "AI老师正在整理思路..."

# --- 4. 侧边栏：管理中心 ---
with st.sidebar:
    st.header("🏫 皋陶学校管理中心")
    deepseek_key = st.text_input("🔑 API Key", type="password")
    
    if "topic_map" not in st.session_state:
        st.session_state.topic_map = {
            "相似三角形": ["判定定理应用", "相似比与面积关系"],
            "二次函数": ["顶点坐标性质", "抛物线对称性"],
            "圆的性质": ["垂径定理应用", "圆周角性质"],
            "锐角三角函数": ["特殊角计算", "解直角三角形"]
        }

    try:
        res = supabase.table("student_scores").select("*").order("student_name").execute()
        df = pd.DataFrame(res.data)
        student_list = df["student_name"].tolist()
        curr_student = st.selectbox("👤 选择辅导学生：", student_list)
        
        s_data = df[df["student_name"] == curr_student].iloc[0]
        active_kps = [col for col in s_data.index if col in st.session_state.topic_map.keys()]
        
        if active_kps:
            scores = [float(s_data[kp]) if pd.notnull(s_data[kp]) else 60.0 for kp in active_kps]
            radar_df = pd.DataFrame({"维度": active_kps, "得分": scores})
            fig = px.line_polar(radar_df, r='得分', theta='维度', line_close=True, range_r=[0, 100])
            fig.update_traces(fill='toself', fillcolor='rgba(30, 136, 229, 0.4)', line_color='#1E88E5')
            st.plotly_chart(fig, use_container_width=True)
            recommended_kp = active_kps[scores.index(min(scores))]
        else:
            recommended_kp = "全科"; scores = [0]; st.warning("⚠️ 数据库列不匹配")
        
        st.divider()
        with st.expander("🛠️ 系统档案与维护"):
            new_name = st.text_input("新增姓名：")
            if st.button("➕ 确认入驻"):
                if new_name:
                    init_entry = {"student_name": new_name}
                    for kp in st.session_state.topic_map.keys(): init_entry[kp] = 60
                    supabase.table("student_scores").insert(init_entry).execute()
                    st.success(f"{new_name} 入驻成功"); time.sleep(0.5); st.rerun()
            if st.button("❌ 注销当前学生"):
                supabase.table("student_scores").delete().eq("student_name", curr_student).execute()
                st.rerun()
            st.divider()
            new_cat = st.text_input("新增大类：")
            if st.button("➕ 添加大类"):
                if new_cat: st.session_state.topic_map[new_cat] = ["基础考点"]; st.rerun()
    except: st.error("⚠️ 状态同步中...")

# --- 5. 主界面内容 ---
# 增加安全检查防止 NameError
if "curr_student" in locals() and curr_student:
    st.title(f"🛡️ 智汇皋陶：{curr_student} 的演化空间")
    avg_score = sum(scores)/len(scores) if scores else 0

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="metric-card"><h3>👤 学生</h3><h2>{curr_student}</h2></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><h3>🎯 攻坚项</h3><h2 style="color:#D32F2F;">{recommended_kp}</h2></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><h3>📈 能力值</h3><h2 style="color:#2E7D32;">{avg_score:.1f}</h2></div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🎯 智能演化练习", "📊 成长轨迹轴", "📜 深度审计诊断"])

    with tab1:
        l_col, r_col = st.columns([3, 2])
        with l_col:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            m_cat = st.selectbox("选择知识大类：", list(st.session_state.topic_map.keys()))
            s_cat = st.selectbox("锁定精细主题：", st.session_state.topic_map[m_cat])

            if st.button("✨ 生成启发式题目"):
                for key in ["last_review", "last_impact"]:
                    if key in st.session_state: del st.session_state[key]
                if "user_ans_widget" in st.session_state: st.session_state["user_ans_widget"] = ""
                st.session_state.q_text = gao_tao_ai_engine("命题专家", f"针对【{s_cat}】考点出一道单选题", deepseek_key)
                st.session_state.active_m, st.session_state.active_s = m_cat, s_cat
                st.rerun()

            if "q_text" in st.session_state:
                st.markdown(f'<div class="question-display">{st.session_state.q_text}</div>', unsafe_allow_html=True)
                u_ans = st.text_area("✍️ 录入你的思考（请输入选项字母）：", height=100, key="user_ans_widget")
                if st.button("🚀 提交并更新图谱"):
                    with st.spinner("名师正在分析中..."):
                        review = gao_tao_ai_engine("导师", f"题：{st.session_state.q_text}\n答：{u_ans}", deepseek_key, is_review=True)
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
else:
    st.info("👋 欢迎来到皋陶数苑！请先在侧边栏输入 API Key 并选择一位学生开始导学。")

with tab2:
    logs = supabase.table("study_logs").select("*").eq("student_name", curr_student).order("created_at", desc=True).execute().data if "curr_student" in locals() else []
    if logs:
        for log in logs:
            with st.expander(f"📅 {log['created_at'][:16]} | {log['knowledge_point']}"):
                st.write(f"题：{log['question']}"); st.info(f"批：{log['ai_review']}")
    else: st.info("暂无成长足迹")

with tab3:
    if st.button("🔍 开启全量数据审计与深度诊断"):
        with st.spinner("名师正在审计中..."):
            if "logs" in locals() and logs:
                history = "\n".join([f"考点:{l['knowledge_point']} | 判定:{'对' if l['score_impact']>0 else '错'}" for l in logs])
                report = gao_tao_ai_engine("诊断专家", f"记录：\n{history}\n请写全汉字的启发式学情分析。严禁LaTeX。", deepseek_key)
                st.markdown(f'<div class="report-card"><h2 style="text-align:center; color:#1E88E5;">皋陶数苑：{curr_student} 深度诊断报告</h2><hr>{report}<br><br><p style="text-align:right;"><b>主诊教师：李鹏燕</b></p></div>', unsafe_allow_html=True)
                st.balloons()
