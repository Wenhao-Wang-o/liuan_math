import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI
from supabase import create_client
import time

# --- 1. 核心配置与初始化 ---
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
    
    # 核心指令：先给答案，启发点拨，汉字描述逻辑，允许数字
    if is_review:
        base_instruction = (
            f"识别码:{entropy}。你现在是皋陶学校数学特级教师李鹏燕。任务：批改与启发。"
            "【输出规范】：1. 第一行必须直接给出正确选项，格式为：‘正确答案是：[选项字母]’。"
            "2. 从第二行开始进行名师启发。3. 严禁使用 LaTeX 符号（如 $、^、sqrt、/）。"
            "4. 允许使用阿拉伯数字（如 30度、2倍）。5. 语气要温和，只给‘题眼’不给步骤。"
        )
    else:
        base_instruction = (
            f"识别码:{entropy}。你现在是名师李鹏燕。任务：命题。"
            "【要求】：只给题干和选项。纯文字描述，严禁出现符号和‘图’字，120字内。"
        )

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": base_instruction + sys_msg},
                      {"role": "user", "content": user_msg}],
            temperature=0.4, max_tokens=1000
        )
        return response.choices[0].message.content
    except: return "AI 老师正在思考中..."

# --- 4. 侧边栏：全功能管理中心 ---
with st.sidebar:
    st.header("🏫 皋陶学校管理中心")
    deepseek_key = st.text_input("🔑 DeepSeek Key", type="password")
    
    try:
        df = fetch_student_data()
        student_list = df["student_name"].tolist()
        curr_student = st.selectbox("🎯 当前辅导学生：", student_list)
        
        st.divider()
        with st.expander("🛠️ 后台管理系统"):
            # A. 学生增删
            st.subheader("👤 学生档案管理")
            add_name = st.text_input("新增学生姓名：")
            if st.button("➕ 确认入驻"):
                if add_name:
                    init_scores = {"student_name": add_name, "相似三角形": 60, "二次函数": 60, "圆的性质": 60, "锐角三角函数": 60, "反比例函数": 60, "综合几何": 60}
                    supabase.table("student_scores").insert(init_scores).execute()
                    st.success(f"{add_name} 已加入系统"); st.rerun()
            
            if st.button("❌ 注销当前学生"):
                supabase.table("student_scores").delete().eq("student_name", curr_student).execute()
                st.warning(f"{curr_student} 档案已清理"); st.rerun()

            st.divider()
            # B. 课题体系自定义
            st.subheader("📚 课题体系维护")
            if "topic_map" not in st.session_state:
                st.session_state.topic_map = {
                    "相似三角形": ["判定定理应用", "相似比与面积关系"],
                    "二次函数": ["顶点坐标性质", "抛物线对称性"],
                    "圆的性质": ["垂径定理应用", "圆周角性质"]
                }
            
            new_cat = st.text_input("新增大类名称：")
            if st.button("➕ 添加大类"):
                if new_cat:
                    st.session_state.topic_map[new_cat] = ["基础考点"]
                    st.rerun()
            
            target_cat = st.selectbox("选择要修改的大类：", list(st.session_state.topic_map.keys()))
            new_sub = st.text_input(f"为 {target_cat} 增加子主题：")
            if st.button("➕ 增加子主题"):
                if new_sub:
                    st.session_state.topic_map[target_cat].append(new_sub)
                    st.rerun()
    except: st.error("连接异常")

# --- 5. 主界面逻辑 ---
if "curr_student" in locals():
    s_data = df[df["student_name"] == curr_student].iloc[0]
    # 获取有效大类（数据库中存在的列）
    valid_kps = [k for k in st.session_state.topic_map.keys() if k in s_data]
    scores = [s_data[k] for k in valid_kps]
    avg_score = sum(scores)/len(scores) if scores else 0

    st.title(f"🛡️ 智汇皋陶：{curr_student} 的智慧导学空间")
    
    # 顶层看板
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="metric-card">👤 学生：{curr_student}</div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card">📈 综合能力：{avg_score:.1f}</div>', unsafe_allow_html=True)
    with c3:
        recommended = valid_kps[scores.index(min(scores))] if scores else "全科平衡"
        st.markdown(f'<div class="metric-card">🎯 建议攻坚：{recommended}</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🎯 自适应练习", "📊 成长记录", "📜 深度诊断报告"])

    with tab1:
        l_col, r_col = st.columns([3, 2])
        with l_col:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            m_cat = st.selectbox("选择知识大类：", list(st.session_state.topic_map.keys()))
            s_cat = st.selectbox("锁定精细主题：", st.session_state.topic_map[m_cat])

            if st.button("✨ 生成启发式题目"):
                q_prompt = f"针对【{s_cat}】出一道单选题。纯文字描述，只给题干和选项。"
                st.session_state.q_text = gao_tao_ai_engine("命题专家", q_prompt, deepseek_key)
                st.session_state.active_m, st.session_state.active_s = m_cat, s_cat
                st.rerun()

            if "q_text" in st.session_state:
                st.markdown(f'<div class="question-box">{st.session_state.q_text}</div>', unsafe_allow_html=True)
                u_ans = st.text_area("✍️ 你的思考与选项：", height=100)
                if st.button("🚀 提交并更新图谱"):
                    with st.spinner("李老师正在批改..."):
                        p_prompt = f"题目：{st.session_state.q_text}\n回答：{u_ans}\n判定对错并点拨。第一行给正确答案。"
                        review = gao_tao_ai_engine("导师", p_prompt, deepseek_key, is_review=True)
                        impact = 2 if "正确" in review or u_ans.upper() in review[:25] else -2
                        
                        # 写入日志
                        supabase.table("study_logs").insert({
                            "student_name": curr_student, "knowledge_point": st.session_state.active_s,
                            "question": st.session_state.q_text, "answer_logic": u_ans, "ai_review": review, "score_impact": impact
                        }).execute()
                        st.session_state.last_review = review
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with r_col:
            if "last_review" in st.session_state:
                st.subheader("💡 名师点评反馈")
                st.write(st.session_state.last_review)

    with tab2:
        st.subheader("📜 历史演化轴")
        logs = supabase.table("study_logs").select("*").eq("student_name", curr_student).order("created_at", desc=True).execute().data
        for log in logs:
            with st.expander(f"📅 {log['created_at'][:16]} | {log['knowledge_point']}"):
                st.write(f"题：{log['question']}")
                st.info(f"批：{log['ai_review']}")

    with tab3:
        st.subheader("📜 数字化教育质量评估报告")
        if st.button("🔍 开启全量数据审计与诊断"):
            with st.spinner("正在扫描历史档案库..."):
                recent_logs = supabase.table("study_logs").select("*").eq("student_name", curr_student).order("created_at", desc=True).limit(15).execute().data
                
                if recent_logs:
                    # 构造真实数据上下文
                    history = "\n".join([f"考点:{l['knowledge_point']} | 判定:{'对' if l['score_impact']>0 else '错'} | 点拨:{l['ai_review'][:50]}" for l in recent_logs])
                    diag_msg = f"该生最近练习记录：\n{history}\n请作为李鹏燕老师，写一份详细诊断。要求：1.总结该生最频繁出错的知识细项。2.从思维方式上分析原因。3.给出未来一周的补救建议。"
                    
                    detailed_report = gao_tao_ai_engine("诊断专家", diag_msg, deepseek_key)
                    
                    st.markdown(f"""
                    <div class="report-card">
                        <h2 style='text-align:center; color:#1E88E5;'>皋陶数苑：{curr_student} 同学深度学情报告</h2>
                        <p>孩子，我是你的导学老师李鹏燕。通过对你最近 <b>{len(recent_logs)}</b> 次自适应练习的监测，我为你提炼了以下诊断：</p>
                        <hr>
                        {detailed_report}
                        <br>
                        <p style='text-align:right;'><b>主诊教师：李鹏燕</b><br>生成于：2026年3月7日</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.balloons()
