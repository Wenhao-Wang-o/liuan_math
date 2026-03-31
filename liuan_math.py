import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI
from supabase import create_client
import time
import random
import docx  # 处理Word文档
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

# --- 2. 炫酷 UI 样式 ---
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

# --- 3. 核心 AI 引擎 ---
def gao_tao_ai_engine(sys_msg, user_msg, api_key, is_review=False, is_json=False):
    if not api_key: return "⚠️ 请在侧边栏输入 API Key"
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response_format = {"type": "json_object"} if is_json else None
    
    if is_review:
        # 🌟 批改模式：强化启发式、温柔语气、去公式化
        base_instruction = (
            "你现在是皋陶学校数学特级教师李鹏燕。任务：批改学生回答。\n"
            "要求：\n"
            "1. 第一行格式：‘【判定】：正确/错误。正确答案是：[字母]’。\n"
            "2. 严禁使用 LaTeX（如 $、^、sqrt、/），所有数学关系用汉字描述（如：边长的平方、根号2）。\n"
            "3. 语气要极其温柔、亲切（如：‘孩子，别灰心’、‘李老师发现你已经观察到了...’）。\n"
            "4. 执行启发式点拨：不给具体解题步骤，只给出‘题眼’引导学生思考。"
        )
    else:
        # 🌟 命题模式：死命令不准给解析
        base_instruction = "你现在是特级教师李鹏燕。任务：出一道初中数学单选题。要求：只提供题干和选项，严禁提供答案和任何解析。严禁 LaTeX。"
        
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": base_instruction + sys_msg},{"role": "user", "content": user_msg}],
            temperature=0.3 if is_review else 0.7, 
            max_tokens=2000,
            response_format=response_format
        )
        return response.choices[0].message.content
    except: return "AI老师正在整理思路..."

# --- 🌟 核心：Word 图文“物理原位”对齐逻辑 ---
def upload_img(data):
    name = f"math_{uuid.uuid4().hex[:8]}.png"
    try:
        supabase.storage.from_("question-images").upload(path=name, file=data, file_options={"content-type": "image/png"})
        return supabase.storage.from_("question-images").get_public_url(name)
    except: return None

def process_full_paper(file, api_key):
    """【物理锚点版】穿透 Word 底层，将图片与文字在解析阶段就锁定位置"""
    try:
        doc = docx.Document(file)
        img_anchors = {} 
        rels = doc.part.rels
        # 1. 提取所有图片
        for rId in rels:
            if rels[rId].reltype == RT.IMAGE:
                url = upload_img(rels[rId].target_part.blob)
                if url: img_anchors[rId] = url

        # 2. 构造带有“物理标签”的文本流
        stream = []
        for p in doc.paragraphs:
            txt = p.text.strip()
            # 物理探测：此段落是否有图？
            imgs = p._element.xpath('.//a:blip/@r:embed')
            if imgs:
                for rId in imgs:
                    if rId in img_anchors:
                        txt += f" [物理配图锚点:{img_anchors[rId]}]"
            if txt:
                txt = txt.replace("．", ".").replace("（", "(").replace("）", ")")
                stream.append(txt)
        
        full_raw_text = "\n".join(stream)
        
        # 3. AI 拆解指令：强制穷举识别整份作业 [cite: 1]
        sys_prompt = """你是一个数学特级教师。任务：从混合了图片锚点的文本中完整还原所有23道题目。
        要求：
        1. 必须覆盖从1.到23.的所有题，不准遗漏，不准截断。
        2. 图片关联：若题干有“如图”且紧跟[物理配图锚点:URL]，必须将该URL存入 image_url。
        3. 知识分类：从（相似三角形、二次函数、圆的性质、锐角三角函数）中选。
        4. 公式重构：严禁LaTeX，所有数学表达必须转为汉字文字（如：根号16）。
        格式：严格JSON {"questions": [{"knowledge_point":"", "question_text":"", "options":"", "correct_answer":"", "image_url":""}]}"""
        
        res_json = gao_tao_ai_engine(sys_prompt, f"还原以下整份卷子的23道题：\n\n{full_raw_text[:12000]}", api_key, is_json=True)
        return json.loads(res_json).get("questions", [])
    except: return []

def get_question(m_cat, s_cat, api_key):
    """选题逻辑：优先本地。AI命题时严禁给答案"""
    res = supabase.table("manual_question_bank").select("*").eq("knowledge_point", m_cat).eq("sub_topic", s_cat).execute()
    if res.data:
        q = random.choice(res.data)
        st.session_state.manual_correct_ans = q['correct_answer']
        st.session_state.q_image_url = q.get('image_url')
        return f"{q['question_text']}\n{q['options']}", True
    else:
        st.session_state.q_image_url = None
        # 🌟 此处提示词再次强调：禁止解析
        q_prompt = f"针对【{s_cat}】考点出一道单选题。只给题干和选项，绝对不要给出解析和答案。"
        ai_q = gao_tao_ai_engine("专家", q_prompt, api_key, is_review=False)
        return ai_q, False

# --- 4. 侧边栏：管理中心 ---
with st.sidebar:
    st.header("🏫 皋陶学校管理中心")
    deepseek_key = st.text_input("🔑 API Key", type="password")
    
    # 画像展示
    if "topic_map" not in st.session_state:
        st.session_state.topic_map = {"相似三角形": ["判定定理应用", "相似比与面积关系"], "二次函数": ["顶点坐标性质", "抛物线对称性"], "圆的性质": ["垂径定理应用", "圆周角性质"], "锐角三角函数": ["特殊角计算", "解直角三角形"]}

    try:
        res = supabase.table("student_scores").select("*").order("student_name").execute()
        df = pd.DataFrame(res.data)
        student_list = df["student_name"].tolist()
        curr_student = st.selectbox("👤 选择辅导学生：", student_list)
        s_data = df[df["student_name"] == curr_student].iloc[0]
        active_kps = [col for col in s_data.index if col in st.session_state.topic_map.keys()]
        if active_kps:
            scores = [float(s_data[kp]) if pd.notnull(s_data[kp]) else 60.0 for kp in active_kps]
            st.plotly_chart(px.line_polar(pd.DataFrame({"维度": active_kps, "得分": scores}), r='得分', theta='维度', line_close=True, range_r=[0, 100]), use_container_width=True)
            st.write("---")
            st.plotly_chart(px.imshow(df.set_index("student_name")[active_kps], text_auto=True, color_continuous_scale="RdYlGn").update_layout(height=280, coloraxis_showscale=False), use_container_width=True)
            recommended_kp = active_kps[scores.index(min(scores))]
        else: recommended_kp = "全科"; scores = [0]
        
        st.divider()
        # --- 📂 Word 全自动对齐导入面板 ---
        with st.expander("📂 Word一键图文识别入库", expanded=True):
            st.info("上传试卷，系统将执行物理位置锚点对齐。")
            word_file = st.file_uploader("选择 Word 文件 (.docx)", type=["docx"])
            if word_file and st.button("🚀 执行多模态识别并归档"):
                if not deepseek_key: st.error("请填入 Key")
                else:
                    with st.status("🔍 正在执行图文逻辑对齐并解析...", expanded=True) as status:
                        st.write("📦 正在提取几何图形并同步云端...")
                        imported_qs = process_full_paper(word_file, deepseek_key)
                        if imported_qs:
                            st.write(f"✅ AI 成功还原 {len(imported_qs)} 道题，正在写入数据库...")
                            supabase.table("manual_question_bank").insert(imported_qs).execute()
                            status.update(label="🎉 导入完成！", state="complete")
                            st.success(f"已存入 {len(imported_qs)} 道精品题！")
                            st.balloons(); time.sleep(2); st.rerun()
                        else: st.error("识别结果为空，请检查题号格式。")

    except: st.error("📡 数据连接中...")

# --- 5. 主界面看板 ---
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
            m_cat = st.selectbox("选择分类：", list(st.session_state.topic_map.keys()))
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
                if st.button("🚀 提交并更新图谱"):
                    with st.spinner("导师分析中..."):
                        p_msg = f"题：{st.session_state.q_text}\n已知：{st.session_state.get('manual_correct_ans','')}\n答：{u_ans}"
                        review = gao_tao_ai_engine("批改导师", p_msg, deepseek_key)
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
        if st.button("🔍 开启深度诊断"):
            with st.spinner("扫描中..."):
                if logs:
                    history = "\n".join([f"考点:{l['knowledge_point']} | 判定:{'对' if l['score_impact']>0 else '错'}" for l in logs[:10]])
                    report = gao_tao_ai_engine("诊断专家", f"历史记录：\n{history}\n汉字描述分析，严禁LaTeX。", deepseek_key)
                    st.markdown(f'<div class="report-card"><h2>{curr_student} 诊断报告</h2><hr>{report}</div>', unsafe_allow_html=True); st.balloons()

    with tab4:
        st.subheader("📚 云端全卷题目流式阅览")
        check_res = supabase.table("manual_question_bank").select("*").order("created_at", desc=True).execute()
        if check_res.data:
            st.write(f"📊 当前全卷库内存量：{len(check_res.data)} 道题目")
            for q_item in check_res.data:
                with st.container():
                    st.markdown(f"**[{q_item.get('knowledge_point')}]** {q_item.get('question_text')}")
                    if q_item.get('image_url'):
                        st.image(q_item['image_url'], width=300, caption="系统自动关联图形")
                    st.success(f"正确答案：{q_item.get('correct_answer')}")
                    if st.button("🗑️ 移除此题", key=f"del_{q_item.get('id')}"):
                        supabase.table("manual_question_bank").delete().eq("id", q_item.get('id')).execute(); st.rerun()
                    st.divider()
        else: st.info("库内暂无题目。")
