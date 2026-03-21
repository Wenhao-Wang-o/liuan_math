import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI
from supabase import create_client
import time
import random
import docx  # 处理Word文档
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

# --- 2. 炫酷 UI 样式 ---
st.set_page_config(page_title="皋陶数苑-AI自适应系统", layout="wide")
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    .main-card { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(10px); padding: 25px; border-radius: 20px; box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15); margin-bottom: 20px; }
    .metric-card { background: white; padding: 15px; border-radius: 15px; text-align: center; border-top: 6px solid #1E88E5; transition: transform 0.3s; }
    .metric-card:hover { transform: translateY(-5px); }
    .question-display { background: #e3f2fd; border-left: 10px solid #1E88E5; padding: 20px; border-radius: 10px; font-size: 1.1em; color: #0d47a1; }
    .report-card { background: #fff; padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); line-height: 1.8; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心功能函数 ---
def gao_tao_ai_engine(sys_msg, user_msg, api_key, is_review=False, is_json=False):
    if not api_key: return "⚠️ 请在侧边栏输入 API Key"
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    response_format = {"type": "json_object"} if is_json else None
    
    if is_review:
        base_instruction = "你现在是皋陶学校数学特级教师李鹏燕。批改任务：第一行写‘【判定】：正确/错误。正确答案是：[字母]’。严禁LaTeX，全汉字描述逻辑，语气温柔启发。"
    else:
        base_instruction = "你现在是特级教师李鹏燕。任务：识别Word题目或生成题目。严禁 LaTeX，纯文字描述。"
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": base_instruction + sys_msg},{"role": "user", "content": user_msg}],
            temperature=0.3 if is_json else 0.7, 
            max_tokens=2000,
            response_format=response_format
        )
        return response.choices[0].message.content
    except: return "{}" if is_json else "AI老师正在整理思路..."

# --- 🌟 优化：图文自动导入逻辑 ---
def upload_img_to_storage(img_data):
    """物理上传图片到存储桶"""
    file_name = f"math_{uuid.uuid4().hex[:8]}.png"
    try:
        supabase.storage.from_("question-images").upload(path=file_name, file=img_data, file_options={"content-type": "image/png"})
        return supabase.storage.from_("question-images").get_public_url(file_name)
    except: return None

def process_word_auto_import(file, api_key):
    """提取Word内容并与AI进行图文对齐"""
    try:
        doc = docx.Document(file)
        text_content = []
        found_image_urls = []

        # 1. 物理提取图片
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                url = upload_img_to_storage(rel.target_part.blob)
                if url: found_image_urls.append(url)

        # 2. 文本清洗
        for p in doc.paragraphs:
            t = p.text.strip()
            if t and "装订线" not in t:
                # 处理全角点，方便识别
                t = t.replace("．", ".").replace("（", "(").replace("）", ")")
                text_content.append(t)
        
        # 3. AI 结构化指令
        sys_prompt = """你是一个数学题库自动化专家。任务：将文本拆解为题目。
        要求：
        1. 识别：知识大类(相似三角形/二次函数/圆的性质/锐角三角函数)、题干、选项、答案。
        2. 图片关联：若题干包含“如图”，按顺序从图片列表中分配URL给 image_url 字段。
        3. 转换：所有数学公式转为汉字描述，严禁LaTeX。
        4. 返回严格 JSON：{"questions": [{"knowledge_point":"", "question_text":"", "options":"", "correct_answer":"", "image_url":""}]}"""
        
        user_msg = f"文本内容：\n{chr(10).join(text_content)[:3000]}\n\n可用图片列表：\n{found_image_urls}"
        res_json = gao_tao_ai_engine(sys_prompt, user_msg, api_key, is_json=True)
        return json.loads(res_json).get("questions", [])
    except Exception as e:
        st.error(f"解析细节偏差：{str(e)}")
        return []

def get_question(m_cat, s_cat, api_key):
    res = supabase.table("manual_question_bank").select("*").eq("knowledge_point", m_cat).eq("sub_topic", s_cat).execute()
    if res.data:
        q = random.choice(res.data)
        st.session_state.manual_correct_ans = q['correct_answer']
        st.session_state.q_image_url = q.get('image_url')
        return f"{q['question_text']}\n{q['options']}", True
    else:
        st.session_state.q_image_url = None
        return gao_tao_ai_engine("专家", f"针对【{s_cat}】考点出一道单选题。只给题干和选项。", api_key), False

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
            st.plotly_chart(px.line_polar(radar_df, r='得分', theta='维度', line_close=True, range_r=[0, 100]), use_container_width=True)
            st.write("---")
            st.subheader("📊 全员能力概览")
            st.plotly_chart(px.imshow(df.set_index("student_name")[active_kps], text_auto=True, color_continuous_scale="RdYlGn").update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0), coloraxis_showscale=False), use_container_width=True)
            recommended_kp = active_kps[scores.index(min(scores))]
        else: recommended_kp = "全科"; scores = [0]
        
        st.divider()
        # --- 🌟 增强交互：Word 自动化全流程导入面板 ---
        with st.expander("📂 Word一键智能识别入库", expanded=True):
            st.info("上传作业后，系统将展示文字预览与AI解析清单。")
            word_file = st.file_uploader("选择 Word 文件 (.docx)", type=["docx"])
            
            if word_file:
                # 即时回显
                doc_p = docx.Document(word_file)
                preview = "\n".join([p.text for p in doc_p.paragraphs if p.text.strip()][:5])
                st.caption(f"📝 识别到内容开头：\n{preview}...")
                
                if st.button("🚀 开始 AI 逻辑拆解入库"):
                    if not deepseek_key: st.error("请先填入 Key")
                    else:
                        with st.status("🔍 正在图文逻辑对齐...", expanded=True) as status:
                            st.write("📦 正在物理抓取几何图形并上传云端...")
                            qs = process_word_auto_import(word_file, deepseek_key)
                            
                            if qs:
                                st.write(f"✅ 成功提取 {len(qs)} 道题目，正在写入数据库...")
                                for q in qs:
                                    # 题目去重或长度校验
                                    if len(q.get("question_text","")) > 5:
                                        supabase.table("manual_question_bank").insert(q).execute()
                                
                                status.update(label="🎉 导入全流程已完成！", state="complete")
                                st.success(f"成功导入 {len(qs)} 道精品题！")
                                # 展示表格回显
                                st.table(pd.DataFrame(qs)[['knowledge_point','correct_answer']])
                                st.balloons()
                                time.sleep(3); st.rerun()
                            else:
                                status.update(label="❌ 解析未识别到题目", state="error")
    except: st.error("📡 数据连接中...")

# --- 5. 主界面内容 ---
if "curr_student" in locals() and curr_student:
    st.title(f"🛡️ 智汇皋陶：{curr_student} 的演化空间")
    avg_score = sum(scores)/len(scores) if scores else 0
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="metric-card"><h3>👤 学生</h3><h2>{curr_student}</h2></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><h3>🎯 攻坚</h3><h2 style="color:#D32F2F;">{recommended_kp}</h2></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><h3>📈 能力</h3><h2 style="color:#2E7D32;">{avg_score:.1f}</h2></div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🎯 智能演化练习", "📊 成长轨迹轴", "📜 深度审计诊断"])

    with tab1:
        l_col, r_col = st.columns([3, 2])
        with l_col:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            m_cat = st.selectbox("选择知识大类：", list(st.session_state.topic_map.keys()))
            s_cat = st.selectbox("锁定精细主题：", st.session_state.topic_map[m_cat])

            if st.button("✨ 生成启发式题目"):
                for k in ["last_review", "last_impact"]: st.session_state.pop(k, None)
                if "user_ans_widget" in st.session_state: st.session_state["user_ans_widget"] = ""
                st.session_state.q_text, is_manual = get_question(m_cat, s_cat, deepseek_key)
                st.session_state.is_manual, st.session_state.active_m, st.session_state.active_s = is_manual, m_cat, s_cat
                st.rerun()

            if "q_text" in st.session_state:
                st.markdown(f'<div class="question-display">{st.session_state.q_text}</div>', unsafe_allow_html=True)
                if st.session_state.get("q_image_url"):
                    st.image(st.session_state.q_image_url, caption="几何参考图", use_column_width=True)
                
                u_ans = st.text_area("✍️ 录入你的思考：", key="user_ans_widget")
                if st.button("🚀 提交反馈"):
                    with st.spinner("名师分析中..."):
                        p_msg = f"题目：{st.session_state.q_text}\n"
                        if st.session_state.is_manual: p_msg += f"正确答案：{st.session_state.get('manual_correct_ans','')}\n"
                        review = gao_tao_ai_engine("导师", p_msg + f"答：{u_ans}", deepseek_key, is_review=True)
                        impact = 2 if "正确" in review.split('\n')[0] else -2
                        supabase.table("study_logs").insert({"student_name": curr_student, "knowledge_point": st.session_state.active_s, "question": st.session_state.q_text, "answer_logic": u_ans, "ai_review": review, "score_impact": impact}).execute()
                        if st.session_state.active_m in s_data:
                            new_val = max(0, min(100, float(s_data[st.session_state.active_m]) + impact))
                            supabase.table("student_scores").update({st.session_state.active_m: new_val}).eq("student_name", curr_student).execute()
                        st.session_state.last_review, st.session_state.last_impact = review, impact
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with r_col:
            if "last_review" in st.session_state:
                st.info(st.session_state.last_review)

with tab2:
    logs = supabase.table("study_logs").select("*").eq("student_name", curr_student).order("created_at", desc=True).execute().data if "curr_student" in locals() else []
    for log in logs:
        with st.expander(f"📅 {log['created_at'][:16]} | {log['knowledge_point']}"):
            st.write(f"题：{log['question']}"); st.info(f"批：{log['ai_review']}")

with tab3:
    if st.button("🔍 开启深度诊断"):
        with st.spinner("扫描档案中..."):
            if logs:
                history = "\n".join([f"考点:{l['knowledge_point']} | 判定:{'对' if l['score_impact']>0 else '错'}" for l in logs[:10]])
                report = gao_tao_ai_engine("诊断专家", f"记录：\n{history}\n请写全汉字启发分析。严禁LaTeX。", deepseek_key)
                st.markdown(f'<div class="report-card"><h2 style="text-align:center;">诊断报告</h2><hr>{report}</div>', unsafe_allow_html=True)
                st.balloons()
