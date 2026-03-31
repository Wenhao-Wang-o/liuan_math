import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI
from supabase import create_client
import time
import random
import docx
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
    .question-display { background: #e3f2fd; border-left: 10px solid #1E88E5; padding: 20px; border-radius: 10px; font-size: 1.1em; color: #0d47a1; }
    .report-card { background: #fff; padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); line-height: 1.8; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心 AI 引擎 ---
def gao_tao_ai_engine(sys_msg, user_msg, api_key, is_review=False, is_json=False):
    if not api_key: return "⚠️ 请在侧边栏输入 API Key"
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response_format = {"type": "json_object"} if is_json else None
    
    if is_review:
        base_instruction = "你现在是特级教师李鹏燕。任务：批改。第一行写判定结果。严禁LaTeX，用汉字描述几何逻辑，语气温柔。"
    else:
        base_instruction = "你现在是数学题库专家。任务：拆解Word文档题目。严格保持题目的逻辑顺序。严禁LaTeX。"
        
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": base_instruction + sys_msg},{"role": "user", "content": user_msg}],
            temperature=0.3 if is_json else 0.7,
            max_tokens=8192, # 🌟 开启超长返回，确保23道题不截断
            response_format=response_format
        )
        return response.choices[0].message.content
    except: return "{}" if is_json else "AI老师正在整理思路..."

# --- 4. 🌟 核心：Word 图文“物理锚点”提取逻辑 ---
def upload_img_to_storage(img_data):
    file_name = f"math_{uuid.uuid4().hex[:8]}.png"
    try:
        supabase.storage.from_("question-images").upload(path=file_name, file=img_data, file_options={"content-type": "image/png"})
        return supabase.storage.from_("question-images").get_public_url(file_name)
    except: return None

def process_word_physics_sync(file, api_key):
    """【物理锚点版】在Word原文中植入图片标记，让AI绝对对齐"""
    try:
        from docx.opc.constants import RELATIONSHIP_TYPE as RT
        doc = docx.Document(file)
        
        # 1. 扫描所有图片并上传，建立 ID 与 URL 的映射
        img_anchors = {}
        rels = doc.part.rels
        for rId in rels:
            if rels[rId].reltype == RT.IMAGE:
                url = upload_img_to_storage(rels[rId].target_part.blob)
                if url: img_anchors[rId] = url

        # 2. 遍历段落，在图片物理位置植入锚点文本
        final_stream = []
        for p in doc.paragraphs:
            text = p.text.strip()
            # 物理检查：该段落里是否引用了图片？
            imgs_in_p = p._element.xpath('.//a:blip/@r:embed')
            if imgs_in_p:
                for rId in imgs_in_p:
                    if rId in img_anchors:
                        text += f" [物理图源锚点:{img_anchors[rId]}]"
            
            if text:
                # 标准化题号和括号
                text = text.replace("．", ".").replace("（", "(").replace("）", ")")
                final_stream.append(text)
        
        full_text_with_anchors = "\n".join(final_stream)

        # 3. 让 AI 进行穷举式拆解
        sys_prompt = """你是一个数学题库自动化专家。任务：将文本拆解为23道题目列表。
        要求：
        1. 必须识别文档中所有题目（1.到23.），不准遗漏，不准只识别前几道。
        2. 如果题干中有“如图”或类似描述，且后面紧跟[物理图源锚点:URL]，必须将该URL存入 image_url 字段。
        3. 分类：相似三角形、二次函数、圆的性质、锐角三角函数。
        4. 转换：严禁使用 LaTeX，所有数学式子转为汉字大白话。
        格式：严格返回 JSON {"questions": [{"knowledge_point":"", "question_text":"", "options":"", "correct_answer":"", "image_url":""}]}"""
        
        # 针对长文档，分段或扩大输入
        res_json = gao_tao_ai_engine(sys_prompt, f"请还原以下整份卷子的23道题：\n\n{full_text_with_anchors[:12000]}", api_key, is_json=True)
        return json.loads(res_json).get("questions", [])
    except Exception as e:
        st.error(f"解析中断：{str(e)}")
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
        return gao_tao_ai_engine("专家", f"针对【{s_cat}】考点出一道单选题。", api_key), False

# --- 5. 侧边栏：管理中心 ---
with st.sidebar:
    st.header("🏫 皋陶学校管理中心")
    deepseek_key = st.text_input("🔑 API Key", type="password")
    
    # 基础逻辑
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
            # 绘制画像图
            scores = [float(s_data[kp]) if pd.notnull(s_data[kp]) else 60.0 for kp in active_kps]
            st.plotly_chart(px.line_polar(pd.DataFrame({"维度": active_kps, "得分": scores}), r='得分', theta='维度', line_close=True, range_r=[0, 100]), use_container_width=True)
            # 绘制全员热力图
            st.write("---")
            st.plotly_chart(px.imshow(df.set_index("student_name")[active_kps], text_auto=True, color_continuous_scale="RdYlGn").update_layout(height=280, coloraxis_showscale=False), use_container_width=True)
            recommended_kp = active_kps[scores.index(min(scores))]
        else: recommended_kp = "全科"; scores = [0]
        
        st.divider()
        # --- 📂 Word 全流程自动入库面板 ---
        with st.expander("📂 Word一键图文识别入库", expanded=True):
            word_file = st.file_uploader("选择 Word 文件", type=["docx"])
            if word_file and st.button("🚀 开始 AI 物理对齐入库"):
                if not deepseek_key: st.error("请填入 Key")
                else:
                    with st.status("🔍 正在执行物理锚点对齐与 AI 拆解...", expanded=True) as status:
                        st.write("📦 正在物理提取几何图形并同步云端...")
                        imported_qs = process_word_physics_sync(word_file, deepseek_key)
                        
                        if imported_qs:
                            st.write(f"✅ AI 成功还原 {len(imported_qs)} 道题目，准备存入数据库...")
                            try:
                                # 🌟 批量写入数据库，只需1次请求，解决卡顿
                                supabase.table("manual_question_bank").insert(imported_qs).execute()
                                status.update(label="🎉 导入全部完成！", state="complete")
                                st.success(f"成功导入 {len(imported_qs)} 道题！")
                                st.balloons()
                                time.sleep(2); st.rerun()
                            except Exception as e: st.error(f"数据库繁忙：{str(e)}")
                        else: st.error("识别结果为空，请检查题号格式。")

        # --- 📚 题库可视化核验中心（满足您的展示需求） ---
        with st.expander("📚 云端题库核验（图片与答案）", expanded=False):
            check_res = supabase.table("manual_question_bank").select("*").order("created_at", desc=True).execute()
            if check_res.data:
                st.write(f"📊 当前库内共有 {len(check_res.data)} 道题")
                for q_item in check_res.data:
                    with st.container():
                        st.markdown(f"**[{q_item.get('knowledge_point')}]** {q_item.get('question_text')}")
                        if q_item.get('image_url'):
                            st.image(q_item['image_url'], width=220, caption="几何原图")
                        else: st.caption("（无配图）")
                        st.success(f"正确答案：{q_item.get('correct_answer')}")
                        if st.button("🗑️ 移除", key=f"del_{q_item.get('id')}"):
                            supabase.table("manual_question_bank").delete().eq("id", q_item.get('id')).execute(); st.rerun()
                        st.divider()

        with st.expander("🛠️ 学生档案维护"):
            new_name = st.text_input("新增姓名：")
            if st.button("➕ 入驻"):
                if new_name: supabase.table("student_scores").insert({"student_name": new_name, **{k:60 for k in st.session_state.topic_map}}).execute(); st.rerun()
            if st.button("❌ 注销"): supabase.table("student_scores").delete().eq("student_name", curr_student).execute(); st.rerun()
    except: st.error("📡 数据连接中...")

# --- 6. 主界面 (保持原样，仅支持图片渲染) ---
if "curr_student" in locals() and curr_student:
    st.title(f"🛡️ 智汇皋陶：{curr_student} 的智慧空间")
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
            m_cat = st.selectbox("选择大类：", list(st.session_state.topic_map.keys()))
            s_cat = st.selectbox("精细主题：", st.session_state.topic_map[m_cat])
            if st.button("✨ 生成题目"):
                for k in ["last_review", "last_impact"]: st.session_state.pop(k, None)
                st.session_state.q_text, is_man = get_question(m_cat, s_cat, deepseek_key)
                st.session_state.is_manual, st.session_state.active_m, st.session_state.active_s = is_man, m_cat, s_cat
                st.rerun()
            if "q_text" in st.session_state:
                st.markdown(f'<div class="question-display">{st.session_state.q_text}</div>', unsafe_allow_html=True)
                if st.session_state.get("q_image_url"): st.image(st.session_state.q_image_url, use_column_width=True)
                u_ans = st.text_area("录入思考（字母）：", key="ans_box")
                if st.button("🚀 提交"):
                    with st.spinner("分析中..."):
                        review = gao_tao_ai_engine("导师", f"题：{st.session_state.q_text}\n已知：{st.session_state.get('manual_correct_ans','')}\n答：{u_ans}", deepseek_key, is_review=True)
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
                st.markdown(f'<div class="report-card"><h3>诊断报告</h3><hr>{report}</div>', unsafe_allow_html=True); st.balloons()
