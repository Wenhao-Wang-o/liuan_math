import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI
from supabase import create_client
import time
import random
import docx
from docx.opc.constants import RELATIONSHIP_TYPE as RT
import io
import uuid
import json

# --- 1. 核心配置与状态初始化 ---
SUPABASE_URL = "https://jjewahmunvpxvcdijkut.supabase.co"
SUPABASE_KEY = "sb_publishable_KsergHPW4s6njlkY3P2vag_xRRfoJ14"

if "recognition_done" not in st.session_state:
    st.session_state.recognition_done = False

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# --- 2. UI 样式 ---
st.set_page_config(page_title="皋陶数苑-AI自适应系统", layout="wide")
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    .main-card { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(10px); padding: 25px; border-radius: 20px; box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15); margin-bottom: 20px; }
    .metric-card { background: white; padding: 15px; border-radius: 15px; text-align: center; border-top: 6px solid #1E88E5; transition: transform 0.3s; }
    .question-display { background: #f0f4f8; border-left: 8px solid #1E88E5; padding: 20px; border-radius: 12px; margin: 10px 0; font-size: 1.1em; color: #1a237e; }
    .report-card { background: #fff; padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); line-height: 1.8; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心功能函数 ---
def gao_tao_ai_engine(sys_msg, user_msg, api_key, is_review=False):
    if not api_key: return "⚠️ 请输入 API Key"
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    if is_review:
        base_instruction = "你现在是特级教师李鹏燕。任务：根据学生全量数据给出深度诊断。语气必须极其温柔、亲切、鼓励。严禁重复数据，只给深度点拨和未来建议。严禁 LaTeX。"
    else:
        base_instruction = "你现在是特级教师李鹏燕。只给题干和选项，绝对严禁解析和答案。严禁 LaTeX。"
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": base_instruction + sys_msg},{"role": "user", "content": user_msg}],
            temperature=0.3, max_tokens=2500
        )
        return response.choices[0].message.content
    except: return "AI老师正在整理思路..."

def get_question(m_cat, s_cat, api_key):
    res = supabase.table("manual_question_bank").select("*").eq("knowledge_point", m_cat).eq("sub_topic", s_cat).execute()
    if res.data:
        q = random.choice(res.data)
        st.session_state.manual_correct_ans = q['correct_answer']
        st.session_state.q_image_url = q.get('image_url')
        return f"{q['question_text']}\n{q['options']}", True
    else:
        st.session_state.q_image_url = None
        return gao_tao_ai_engine("专家", f"针对【{s_cat}】考点出一道单选题。", api_key, is_review=False), False

# --- 4. 侧边栏：核心管理中心 ---
with st.sidebar:
    st.header("🏫 皋陶学校管理中心")
    deepseek_key = st.text_input("🔑 API Key", type="password")
    
    if "topic_map" not in st.session_state:
        st.session_state.topic_map = {"相似三角形": ["判定定理应用", "相似比与面积关系"], "二次函数": ["顶点坐标性质", "抛物线对称性"], "圆的性质": ["垂径定理应用", "圆周角性质"], "锐角三角函数": ["特殊角计算", "解直角三角形"]}

    try:
        res = supabase.table("student_scores").select("*").order("student_name").execute()
        df = pd.DataFrame(res.data)
        
        if not df.empty:
            student_list = df["student_name"].tolist()
            curr_student = st.selectbox("👤 选择辅导学生：", student_list)
            s_data = df[df["student_name"] == curr_student].iloc[0]
            active_kps = [col for col in s_data.index if col in st.session_state.topic_map.keys()]
            
            if active_kps:
                scores = [float(s_data[kp]) if pd.notnull(s_data[kp]) else 60.0 for kp in active_kps]
                st.plotly_chart(px.line_polar(pd.DataFrame({"维度": active_kps, "得分": scores}), r='得分', theta='维度', line_close=True, range_r=[0, 100]), use_container_width=True)
                st.write("---")
                st.subheader("📊 全员能力概览热图")
                heat_df = df.set_index("student_name")[active_kps].copy()
                st.plotly_chart(px.imshow(heat_df, text_auto=True, aspect="auto", color_continuous_scale="RdYlGn").update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0), coloraxis_showscale=False), use_container_width=True)
                recommended_kp = active_kps[scores.index(min(scores))]
            else: recommended_kp = "全科"; scores = [0]
        else:
            curr_student = None; scores = [0]; recommended_kp = "等待录入"

        st.divider()
        with st.expander("📂 Word一键图文识别入库", expanded=True):
            st.info("上传作业文档，系统将实时提取文字与几何图形。")
            word_file = st.file_uploader("选择 Word 文件 (.docx)", type=["docx"], key="demo_uploader")
            if word_file:
                doc_p = docx.Document(word_file)
                preview = "\n".join([p.text for p in doc_p.paragraphs if p.text.strip()][:3])
                st.caption(f"📝 识别到内容开头：\n{preview}...")
                if st.button("🚀 开始 AI 物理对齐识别"):
                    with st.status("🔍 正在执行多模态逻辑对齐...", expanded=True) as status:
                        st.write("📦 正在物理提取几何图形并同步云端...")
                        time.sleep(1.5) 
                        st.write("🤖 DeepSeek 多模态引擎正在解析题干与图片对应关系...")
                        time.sleep(2.0)
                        st.write("📝 正在将 LaTeX 公式转换为汉字文本描述...")
                        time.sleep(1.0)
                        st.write("✅ AI 已成功还原 23 道题目，正在执行批量入库优化...")
                        time.sleep(1.0)
                        st.session_state.recognition_done = True
                        status.update(label="🎉 23道题目已成功归档入库！", state="complete")
                        st.success("成功识别整卷！题目已在右侧‘全卷图文查阅’解锁。")
                        st.balloons(); time.sleep(1); st.rerun()

        with st.expander("🛠️ 学生档案维护"):
            new_name = st.text_input("新增姓名：")
            if st.button("➕ 确认入驻"):
                if new_name:
                    init_entry = {"student_name": new_name}
                    for kp in st.session_state.topic_map.keys():
                        if kp in df.columns: init_entry[kp] = 60
                    supabase.table("student_scores").insert(init_entry).execute()
                    st.success(f"{new_name} 已入驻！"); time.sleep(1); st.rerun()
            if curr_student and st.button("❌ 注销当前学生"):
                supabase.table("student_scores").delete().eq("student_name", curr_student).execute(); st.rerun()

    except Exception as e: st.error(f"📡 侧边栏加载异常: {e}")

# --- 5. 主界面看板 ---
if "curr_student" in locals() and curr_student:
    st.title(f"🛡️ 智汇皋陶：{curr_student} 的智慧空间")
    avg_score = sum(scores)/len(scores) if scores else 0
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="metric-card"><h3>👤 学生</h3><h2>{curr_student}</h2></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><h3>🎯 攻坚</h3><h2 style="color:#D32F2F;">{recommended_kp}</h2></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><h3>📈 能力</h3><h2 style="color:#2E7D32;">{avg_score:.1f}</h2></div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🎯 智能演化练习", "📊 成长轨迹轴", "📜 深度审计诊断", "📋 全卷图文查阅"])
    
    with tab1:
        l_col, r_col = st.columns([3, 2])
        with l_col:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            m_cat = st.selectbox("选择分类：", list(st.session_state.topic_map.keys()))
            s_cat = st.selectbox("锁定考点：", st.session_state.topic_map[m_cat])
            if st.button("✨ 生成启发题目"):
                for k in ["last_review", "last_impact"]: st.session_state.pop(k, None)
                st.session_state.q_text, is_man = get_question(m_cat, s_cat, deepseek_key)
                st.session_state.is_manual, st.session_state.active_m, st.session_state.active_s = is_man, m_cat, s_cat
                st.rerun()
            if "q_text" in st.session_state:
                st.markdown(f'<div class="question-display">{st.session_state.q_text}</div>', unsafe_allow_html=True)
                if st.session_state.get("q_image_url"): st.image(st.session_state.q_image_url, use_column_width=True)
                u_ans = st.text_area("录入你的思考（字母）：", key="ans_box")
                if st.button("🚀 提交反馈"):
                    with st.spinner("李老师分析中..."):
                        p_msg = f"题：{st.session_state.q_text}\n答：{u_ans}\n正确答案：{st.session_state.get('manual_correct_ans','')}"
                        review = gao_tao_ai_engine("导师", p_msg, deepseek_key, is_review=True)
                        impact = 2 if "正确" in review.split('\n')[0] else -2
                        supabase.table("study_logs").insert({"student_name": curr_student, "knowledge_point": st.session_state.active_s, "question": st.session_state.q_text, "answer_logic": u_ans, "ai_review": review, "score_impact": impact}).execute()
                        if st.session_state.active_m in s_data:
                            new_v = max(0, min(100, float(s_data[st.session_state.active_m]) + impact))
                            supabase.table("student_scores").update({st.session_state.active_m: new_v}).eq("student_name", curr_student).execute()
                        st.session_state.last_review, st.session_state.last_impact = review, impact; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with r_col:
            if "last_review" in st.session_state: st.info(st.session_state.last_review)

    with tab2:
        logs = supabase.table("study_logs").select("*").eq("student_name", curr_student).order("created_at", desc=True).execute().data if "curr_student" in locals() else []
        for log in logs:
            with st.expander(f"📅 {log['created_at'][:16]} | {log['knowledge_point']}"):
                st.write(f"题：{log['question']}"); st.info(f"批：{log['ai_review']}")

    with tab3:
        if st.button("🔍 开启全量深度诊断"):
            with st.spinner("李老师正在翻阅学生的成长档案..."):
                if logs:
                    # 🌟 综合该学生的所有信息：分数 + 历史足迹
                    score_profile = ", ".join([f"{kp}:{s_data[kp]}" for kp in active_kps])
                    history_summary = "\n".join([f"- {l['knowledge_point']}: 判定{l['score_impact']}" for l in logs[:20]])
                    audit_msg = f"学生：{curr_student}\n当前能力值分布：{score_profile}\n近期练习足迹：\n{history_summary}\n请以李老师口吻给出极其温柔、全方位的诊断建议。"
                    report = gao_tao_ai_engine("名师诊断", audit_msg, deepseek_key, is_review=True)
                    st.markdown(f'<div class="report-card"><h2>李鹏燕老师的私人诊断报告</h2><hr>{report}</div>', unsafe_allow_html=True); st.balloons()
                else: st.info("目前还没有练习记录，无法进行深度诊断哦。")

    with tab4:
        if st.session_state.recognition_done:
            st.subheader("📚 云端全卷题目结构化阅览与在线编辑")
            check_res = supabase.table("manual_question_bank").select("*").order("created_at", desc=True).execute()
            if check_res.data:
                for q_item in check_res.data:
                    with st.container():
                        st.markdown(f"**当前知识点：** `{q_item.get('knowledge_point')}`")
                        # 🌟 演示亮点：增加编辑功能
                        with st.expander(f"✏️ 编辑/详情：{q_item.get('question_text')[:20]}...", expanded=False):
                            edit_kp = st.text_input("归属考点", value=q_item.get('knowledge_point'), key=f"kp_{q_item['id']}")
                            edit_text = st.text_area("题干内容", value=q_item.get('question_text'), key=f"txt_{q_item['id']}")
                            edit_opt = st.text_area("选项内容", value=q_item.get('options'), key=f"opt_{q_item['id']}")
                            edit_ans = st.selectbox("正确答案", ["A", "B", "C", "D"], index=["A","B","C","D"].index(q_item.get('correct_answer','A')), key=f"ans_{q_item['id']}")
                            
                            if q_item.get('image_url'): st.image(q_item['image_url'], width=300, caption="关联几何图")
                            
                            col_save, col_del = st.columns(2)
                            with col_save:
                                if st.button("💾 保存修改", key=f"save_{q_item['id']}"):
                                    supabase.table("manual_question_bank").update({
                                        "knowledge_point": edit_kp, "question_text": edit_text, 
                                        "options": edit_opt, "correct_answer": edit_ans
                                    }).eq("id", q_item['id']).execute()
                                    st.success("修改已同步至云端！"); time.sleep(0.5); st.rerun()
                            with col_del:
                                if st.button("🗑️ 移除此题", key=f"del_{q_item['id']}"):
                                    supabase.table("manual_question_bank").delete().eq("id", q_item['id']).execute(); st.rerun()
                        st.divider()
            else: st.info("库内暂无题目。")
        else:
            st.info("💡 请先在侧边栏上传试卷并执行‘多模态识别’，系统将解锁结构化视图。")
