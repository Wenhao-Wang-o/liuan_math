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

# --- 1. 核心配置 ---
SUPABASE_URL = "https://jjewahmunvpxvcdijkut.supabase.co"
SUPABASE_KEY = "sb_publishable_KsergHPW4s6njlkY3P2vag_xRRfoJ14"

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
    .report-card { background: #fff; padding: 30px; border-radius: 20px; line-height: 1.8; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心 AI 引擎（修复截断与逻辑开关） ---
def gao_tao_ai_engine(sys_msg, user_msg, api_key, is_review=False, is_json=False):
    if not api_key: return "⚠️ 请在侧边栏输入 API Key"
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response_format = {"type": "json_object"} if is_json else None
    
    if is_review:
        base_instruction = "你现在是特级教师李鹏燕。任务：批改。要求：第一行写‘【判定】：正确/错误。正确答案是：[字母]’。严禁重复题干，语气极其温柔点拨，严禁LaTeX。"
    else:
        base_instruction = "你现在是命题专家。任务：命制数学单选题。要求：只给题干和选项，绝对严禁解析和答案。严禁LaTeX。"

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": base_instruction + sys_msg},{"role": "user", "content": user_msg}],
            temperature=0.3,
            max_tokens=8192 if is_json else 2000, # 🌟 开启超长Token，解决23题截断问题
            response_format=response_format
        )
        return response.choices[0].message.content
    except: return "AI老师正在整理思路..."

# --- 4. Word 物理锚点解析引擎 ---
def upload_img(data):
    name = f"math_{uuid.uuid4().hex[:8]}.png"
    try:
        supabase.storage.from_("question-images").upload(path=name, file=data, file_options={"content-type": "image/png"})
        return supabase.storage.from_("question-images").get_public_url(name)
    except: return None

def process_full_paper(file, api_key):
    """【物理锚点版】实现 100% 图文顺序关联"""
    try:
        doc = docx.Document(file)
        img_anchors = {} 
        rels = doc.part.rels
        for rId in rels:
            if rels[rId].reltype == RT.IMAGE:
                url = upload_img(rels[rId].target_part.blob)
                if url: img_anchors[rId] = url

        stream = []
        for p in doc.paragraphs:
            txt = p.text.strip()
            imgs = p._element.xpath('.//a:blip/@r:embed')
            if imgs:
                for rId in imgs:
                    if rId in img_anchors: txt += f" [此处附图锚点:{img_anchors[rId]}]"
            if txt:
                txt = txt.replace("．", ".").replace("（", "(").replace("）", ")")
                stream.append(txt)
        
        full_raw_text = "\n".join(stream)
        sys_prompt = "将这23道题拆解。关联图片锚点URL，公式转汉字，严格JSON。"
        res_json = gao_tao_ai_engine(sys_prompt, f"还原以下卷子题目：\n\n{full_raw_text[:12000]}", api_key, is_json=True)
        return json.loads(res_json).get("questions", [])
    except: return []

def get_question(m_cat, s_cat, api_key):
    res = supabase.table("manual_question_bank").select("*").eq("knowledge_point", m_cat).eq("sub_topic", s_cat).execute()
    if res.data:
        q = random.choice(res.data)
        st.session_state.manual_correct_ans = q['correct_answer']
        st.session_state.q_image_url = q.get('image_url')
        return f"{q['question_text']}\n{q['options']}", True
    else:
        st.session_state.q_image_url = None
        return gao_tao_ai_engine("命题专家", f"出题考点：{s_cat}。只给题干选项。", api_key, is_review=False), False

# --- 5. 侧边栏：管理中心 ---
with st.sidebar:
    st.header("🏫 皋陶学校管理中心")
    deepseek_key = st.text_input("🔑 API Key", type="password")
    
    if "topic_map" not in st.session_state:
        st.session_state.topic_map = {"相似三角形": ["判定定理应用", "相似比与面积关系"], "二次函数": ["顶点坐标性质", "抛物线对称性"], "圆的性质": ["垂径定理应用", "圆周角性质"], "锐角三角函数": ["特殊角计算", "解直角三角形"]}

    try:
        # 🌟 安全获取数据
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
                recommended_kp = active_kps[scores.index(min(scores))]
            else: recommended_kp = "全科"; scores = [0]
        else:
            st.warning("目前没有学生，请在下方添加。")
            curr_student = None; scores = [0]; recommended_kp = "等待录入"

        st.divider()
        # --- 📂 Word 导入面板 ---
        with st.expander("📂 Word一键图文识别入库", expanded=False):
            word_file = st.file_uploader("选择 Word 文件 (.docx)", type=["docx"])
            if word_file and st.button("🚀 执行全量物理对齐识别"):
                with st.status("🔍 正在解析...", expanded=True) as status:
                    qs = process_full_paper(word_file, deepseek_key)
                    if qs:
                        supabase.table("manual_question_bank").insert(qs).execute()
                        status.update(label="🎉 23道题已归位！", state="complete")
                        st.success("入库成功！"); st.balloons(); time.sleep(1); st.rerun()

        # --- 🛠️ 找回：学生档案维护（安全增强版） ---
        with st.expander("🛠️ 学生档案维护"):
            new_name = st.text_input("新增姓名：")
            if st.button("➕ 确认入驻"):
                if new_name:
                    # 🌟 核心改进：动态匹配数据库存在的列，避免同步报错
                    init_entry = {"student_name": new_name}
                    db_cols = df.columns.tolist() if not df.empty else ["student_name"]
                    for kp in st.session_state.topic_map.keys():
                        if kp in db_cols: init_entry[kp] = 60
                    supabase.table("student_scores").insert(init_entry).execute()
                    st.success(f"{new_name} 已入驻！"); time.sleep(1); st.rerun()
            
            if curr_student:
                if st.button("❌ 注销当前学生档案"):
                    supabase.table("student_scores").delete().eq("student_name", curr_student).execute()
                    st.warning(f"{curr_student} 已注销。"); time.sleep(1); st.rerun()

    except Exception as e:
        st.error(f"📡 同步异常提示: {e}") # 🌟 抛出真实错误，不再遮掩

# --- 6. 主界面 ---
if "curr_student" in locals() and curr_student:
    st.title(f"🛡️ 智汇皋陶：{curr_student} 的演化空间")
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
            m_cat = st.selectbox("选择考点：", list(st.session_state.topic_map.keys()))
            s_cat = st.selectbox("锁定主题：", st.session_state.topic_map[m_cat])
            if st.button("✨ 生成启发题目"):
                for k in ["last_review", "last_impact"]: st.session_state.pop(k, None)
                st.session_state.q_text, is_man = get_question(m_cat, s_cat, deepseek_key)
                st.session_state.is_manual, st.session_state.active_m, st.session_state.active_s = is_man, m_cat, s_cat
                st.rerun()
            if "q_text" in st.session_state:
                st.markdown(f'<div class="question-display">{st.session_state.q_text}</div>', unsafe_allow_html=True)
                if st.session_state.get("q_image_url"): st.image(st.session_state.q_image_url, use_column_width=True)
                u_ans = st.text_area("录入思考（字母）：", key="ans_box")
                if st.button("🚀 提交反馈"):
                    with st.spinner("李老师正在分析..."):
                        p_msg = f"题：{st.session_state.q_text}\n答：{u_ans}\n已知答案：{st.session_state.get('manual_correct_ans','')}"
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

    with tab4:
        st.subheader("📚 云端全卷题目沉浸式阅览")
        check_res = supabase.table("manual_question_bank").select("*").order("created_at", desc=True).execute()
        if check_res.data:
            for q_item in check_res.data:
                st.markdown(f"**[{q_item.get('knowledge_point')}]** {q_item.get('question_text')}")
                if q_item.get('image_url'): st.image(q_item['image_url'], width=400)
                st.divider()
