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
    
    # 动态支持 JSON 返回格式
    response_format = {"type": "json_object"} if is_json else None
    
    if is_review:
        base_instruction = (
            "你现在是皋陶学校数学特级教师李鹏燕。任务：批改。要求：\n"
            "1. 第一行必须写‘【判定】：正确/错误。正确答案是：[字母]’。\n"
            "2. 严禁使用任何 LaTeX 语法（如 $、^、sqrt、/）。\n"
            "3. 严禁使用枯燥代数式。所有几何关系必须用汉字描述（如：‘边长的平方’、‘根号2’、‘30度角’）。\n"
            "4. 一定要用比较温柔的语气，以李鹏燕老师的口吻给出回答\n"
            "5. 启发式点拨，不要给步骤，只给‘题眼’引导学生思考。"
        )
    else:
        base_instruction = "你现在是特级教师李鹏燕。任务：处理数据或命题。要求：严禁 LaTeX，纯文字描述，允许阿拉伯数字。"
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

# --- 🌟 新增：Word 图文识别逻辑模块 ---
def upload_img_to_storage(img_data):
    """提取图片二进制流并上传到 Supabase Storage"""
    file_name = f"math_{uuid.uuid4().hex[:8]}.png"
    try:
        supabase.storage.from_("question-images").upload(path=file_name, file=img_data, file_options={"content-type": "image/png"})
        return supabase.storage.from_("question-images").get_public_url(file_name)
    except: return None

def process_word_auto_import(file, api_key):
    """【加固版】全自动提取 Word 文字、题目及对应图片"""
    try:
        doc = docx.Document(file)
        text_content = []
        found_image_urls = []

        # 1. 物理扫描图片并上传 (保持不变)
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                img_url = upload_img_to_storage(rel.target_part.blob)
                if img_url: found_image_urls.append(img_url)

        # 2. 提取文本并进行“格式清洗”
        for p in doc.paragraphs:
            t = p.text.strip()
            if t and "装订线" not in t and "学号" not in t:
                t = t.replace("．", ".").replace("（", "(").replace("）", ")")
                text_content.append(t)
        
        # 🌟 优化点：增加处理文本长度，确保能识别更多题目
        full_raw_text = "\n".join(text_content)
        
        # 3. 升级 AI 识别指令
        sys_prompt = """你是一个初中数学题库专家。任务：从文本中精准提取“单选题”。
        要求：
        1. 题目序号清晰，大类需匹配：相似三角形、二次函数、圆的性质、锐角三角函数。
        2. 如果题干提到“如图”，必须按顺序关联提供的图片URL。
        3. 格式：严格返回 JSON {"questions": [...]}，包含知识点、题干、选项、答案、图片URL。
        4. 转换：严禁 LaTeX，必须转为汉字描述。"""
        
        # 发送更多内容给 AI 以识别更多题目 
        user_msg = f"内容：\n{full_raw_text[:6000]}\n\n可用图片URL：\n{found_image_urls}"
        res_json = gao_tao_ai_engine(sys_prompt, user_msg, api_key, is_json=True)
        
        result = json.loads(res_json).get("questions", [])
        return result
    except Exception as e:
        st.error(f"解析细节偏差: {str(e)}")
        return []

def get_question(m_cat, s_cat, api_key):
    """选题逻辑：优先从已导入的含图题库中选取"""
    res = supabase.table("manual_question_bank").select("*").eq("knowledge_point", m_cat).eq("sub_topic", s_cat).execute()
    if res.data:
        q_data = random.choice(res.data)
        st.session_state.manual_correct_ans = q_data['correct_answer']
        st.session_state.q_image_url = q_data.get('image_url')
        return f"{q_data['question_text']}\n{q_data['options']}", True
    else:
        st.session_state.q_image_url = None
        q_prompt = f"针对【{s_cat}】考点出一道单选题。不准提图。只给题干和选项。"
        ai_q = gao_tao_ai_engine("专家", q_prompt, api_key)
        return ai_q, False

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
            st.plotly_chart(px.line_polar(radar_df, r='得分', theta='维度', line_close=True, range_r=[0, 100]).update_traces(fill='toself', fillcolor='rgba(30, 136, 229, 0.4)', line_color='#1E88E5'), use_container_width=True)
            
            st.write("---")
            st.subheader("📊 全员能力概览")
            heat_df = df.set_index("student_name")[active_kps].copy()
            st.plotly_chart(px.imshow(heat_df, text_auto=True, aspect="auto", color_continuous_scale="RdYlGn").update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0), coloraxis_showscale=False), use_container_width=True)
            recommended_kp = active_kps[scores.index(min(scores))]
        else:
            recommended_kp = "全科"; scores = [0]
        
        st.divider()

        # --- 最终修复版：Word 导入面板 ---
        with st.expander("📂 Word一键智能识别入库", expanded=True):
            st.info("上传 Word 作业，系统将自动拆解并匹配几何图形。")
            word_file = st.file_uploader("选择 Word 文件 (.docx)", type=["docx"])
            
            if word_file:
                doc_p = docx.Document(word_file)
                preview = "\n".join([p.text for p in doc_p.paragraphs if p.text.strip()][:3])
                st.caption(f"📝 识别到内容开头：\n{preview}...")
                
                if st.button("🚀 开始 AI 深度识别并入库"):
                    if not deepseek_key: st.error("🔑 请先填入 API Key")
                    else:
                        with st.status("🔍 正在图文逻辑对齐...", expanded=True) as status:
                            st.write("📦 正在物理提取几何图形并同步云端...")
                            qs = process_word_auto_import(word_file, deepseek_key)
                            
                            if qs:
                                st.write(f"🚀 AI 已识别 {len(qs)} 道题目，准备批量入库...")
                                try:
                                    valid_qs = [q for q in qs if len(q.get("question_text","")) > 5]
                                    if valid_qs:
                                        supabase.table("manual_question_bank").insert(valid_qs).execute()
                                        status.update(label="🎉 导入全流程已完成！", state="complete")
                                        st.success(f"成功导入 {len(valid_qs)} 道精品题！")
                                        st.balloons()
                                        time.sleep(2); st.rerun()
                                    else: st.warning("识别结果为空，请检查文档题号格式。")
                                except Exception as db_err:
                                    status.update(label="❌ 数据库写入出错", state="error")
                                    st.error(f"写入失败: {str(db_err)}")
                            else:
                                status.update(label="❌ AI 未能识别题目", state="error")

        with st.expander("🛠️ 系统维护"):
            new_name = st.text_input("新增姓名：")
            if st.button("➕ 确认入驻"):
                if new_name:
                    init_entry = {"student_name": new_name}
                    for kp in st.session_state.topic_map.keys(): init_entry[kp] = 60
                    supabase.table("student_scores").insert(init_entry).execute(); st.rerun()
            if st.button("❌ 注销当前学生"):
                supabase.table("student_scores").delete().eq("student_name", curr_student).execute(); st.rerun()

        # --- 🌟 核心新增模块：库内题目“图、文、答”核验中心 ---
        with st.expander("📚 云端题库核验中心（可视化展示）", expanded=False):
            try:
                check_res = supabase.table("manual_question_bank").select("*").order("created_at", desc=True).execute()
                if check_res.data:
                    st.write(f"✅ 当前云端共有 {len(check_res.data)} 道精品题")
                    for i, q_item in enumerate(check_res.data):
                        with st.container():
                            st.markdown(f"**题 {i+1}：[{q_item.get('knowledge_point')}]**")
                            st.write(f"{q_item.get('question_text')}")
                            # 验证图片是否存在并显示 
                            if q_item.get('image_url'):
                                st.image(q_item['image_url'], caption="系统自动关联的几何图", width=200)
                            else:
                                st.warning("⚠️ 此题未成功匹配到图片")
                            st.info(f"正确答案：{q_item.get('correct_answer')}")
                            if st.button("🗑️ 移除此题", key=f"del_{q_item.get('id')}"):
                                supabase.table("manual_question_bank").delete().eq("id", q_item.get('id')).execute()
                                st.rerun()
                            st.divider()
                else: st.info("目前库内暂无题目。")
            except: st.error("题库同步中...")

    except: st.error(f"📡 数据同步中...")

# --- 5. 主界面看板 (保持不变) ---
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
                for key in ["last_review", "last_impact"]: st.session_state.pop(key, None)
                if "user_ans_widget" in st.session_state: st.session_state["user_ans_widget"] = ""
                st.session_state.q_text, is_manual = get_question(m_cat, s_cat, deepseek_key)
                st.session_state.is_manual, st.session_state.active_m, st.session_state.active_s = is_manual, m_cat, s_cat
                st.rerun()

            if "q_text" in st.session_state:
                st.markdown(f'<div class="question-display">{st.session_state.q_text}</div>', unsafe_allow_html=True)
                if st.session_state.get("q_image_url"):
                    st.image(st.session_state.q_image_url, caption="几何参考图形", use_column_width=True)
                
                u_ans = st.text_area("✍️ 录入你的思考：", height=100, key="user_ans_widget")
                if st.button("🚀 提交并更新图谱"):
                    with st.spinner("名师正在分析中..."):
                        p_msg = f"题目：{st.session_state.q_text}\n"
                        if st.session_state.is_manual: p_msg += f"参考正确答案：{st.session_state.manual_correct_ans}\n"
                        review = gao_tao_ai_engine("导师", p_msg + f"学生回答：{u_ans}", deepseek_key, is_review=True)
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
                st.subheader("💡 名师点评反馈")
                color = "#10b981" if st.session_state.last_impact > 0 else "#ef4444"
                st.markdown(f'<h2 style="color:{color};">变动：{"+" if st.session_state.last_impact > 0 else ""}{st.session_state.last_impact}</h2>', unsafe_allow_html=True)
                st.info(st.session_state.last_review)

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
                report = gao_tao_ai_engine("诊断专家", f"历史记录：\n{history}\n请写汉字点拨式诊断分析。严禁LaTeX。", deepseek_key)
                st.markdown(f'<div class="report-card"><h2 style="text-align:center;">{curr_student} 诊断报告</h2><hr>{report}</div>', unsafe_allow_html=True)
                st.balloons()
