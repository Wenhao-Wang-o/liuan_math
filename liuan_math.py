import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI
import random

# --- 1. 页面初始化 ---
st.set_page_config(page_title="某某学校-学情分析系统", layout="wide")

# 初始化原始数据
if 'class_data' not in st.session_state:
    st.session_state.class_data = pd.DataFrame({
        "姓名": ["张三", "李四", "王五", "赵六"],
        "二次函数": [80, 45, 90, 30],
        "圆的性质": [70, 60, 85, 40],
        "相似三角形": [30, 20, 95, 15],
        "锐角三角函数": [85, 75, 80, 70],
        "反比例函数": [75, 55, 88, 50]
    })

# 知识点细分地图
if 'sub_topic_map' not in st.session_state:
    st.session_state.sub_topic_map = {
        "二次函数": ["1.二次函数概念", "2.二次函数的图象和性质", "3.二次函数与一元二次方程", "4.二次函数的应用"],
        "圆的性质": ["1.旋转", "2.圆的基本性质", "3.圆周角", "4.直线与圆的位置关系", "5.弧长与扇形面积"],
        "相似三角形": ["1.比例线段", "2.相似三角形判定", "3.相似三角形性质"],
        "锐角三角函数": ["1.正弦/余弦/正切", "2.特殊角", "3.解直角三角形"],
        "反比例函数": ["1.反比例函数概念", "2.图象和性质"]
    }

if 'current_q' not in st.session_state: st.session_state.current_q = ""
if 'eval_result' not in st.session_state: st.session_state.eval_result = ""
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'last_is_wrong' not in st.session_state: st.session_state.last_is_wrong = False 
if 'correct_ans' not in st.session_state: st.session_state.correct_ans = "" 
if 'follow_up_resp' not in st.session_state: st.session_state.follow_up_resp = ""

# --- 2. 侧边栏：热力图与雷达图回归 ---
with st.sidebar:
    st.title("🏫 教学管理后台")
    st.info("👤 **授课教师：小红**\n\n🏫 **学校：某某学校**")
    
    api_key = st.text_input("🔑 API Key (DeepSeek)", type="password")
    base_url = st.text_input("🌐 API 代理", value="https://api.deepseek.com")
    
    st.divider()
    # 🌟 恢复：班级学情热力图
    st.subheader("📊 九年级数学学情看板")
    heat_df = st.session_state.class_data.set_index("姓名")
    fig_heat = px.imshow(heat_df, text_auto=True, color_continuous_scale='RdYlGn', aspect="auto")
    st.plotly_chart(fig_heat, key="heatmap", use_container_width=True)

    # 🌟 恢复：学生个人画像诊断
    st.subheader("👤 学生维度诊断")
    selected_student = st.selectbox("选择学生：", st.session_state.class_data["姓名"])
    student_row = st.session_state.class_data[st.session_state.class_data["姓名"] == selected_student]
    plot_data = pd.DataFrame({"知识点": heat_df.columns, "得分": student_row.iloc[0, 1:].values})
    
    fig_radar = px.line_polar(plot_data, r='得分', theta='知识点', line_close=True, range_r=[0, 100])
    st.plotly_chart(fig_radar, key="radar", use_container_width=True)
    
    student_weakest = plot_data.loc[plot_data['得分'].idxmin(), '知识点']
    
    st.divider()
    forced_req = st.text_area("🎯 强制出题要求", placeholder="例如：选项涉及对应边成比例", key="forced_instruction")

# --- 3. AI 调用逻辑：双模式隔离 ---
def ask_ai_teacher(system_prompt, user_input, is_grading=False):
    if not api_key:
        st.error("请输入 API Key！")
        return None
    
    if is_grading:
        final_system_msg = (
            "你现在是数学老师小红。语气温柔鼓励，字数50字内。严禁LaTeX。"
            "第一行必须明确输出【正确】或【错误】。"
        )
    else:
        final_system_msg = (
            "你现在是中考命题专家。只输出题目和选项，绝对严禁解析和评语。"
            "绝对严禁输出【正确/错误】字样。禁止LaTeX。"
        )

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": final_system_msg + system_prompt},{"role": "user", "content": user_input}],
            temperature=0.3 if is_grading else 0.8
        )
        return response.choices[0].message.content
    except: return None

# --- 4. 主界面 ---
st.title("🤖 智汇皋陶：AI 个性化测评系统")
tab1, tab2 = st.tabs(["✍️ 互动练习区", "📖 练习记录本"])

with tab1:
    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.subheader(f"📍 针对【{selected_student}】的精准强化")
        
        # 联动选择考点
        main_kps = list(st.session_state.class_data.columns[1:])
        col_m, col_s = st.columns(2)
        with col_m:
            main_topic = st.selectbox("📚 选择章节：", ["🎯 智能推荐", *main_kps])
        with col_s:
            if main_topic == "🎯 智能推荐":
                target_topic_str = student_weakest
            else:
                sub_topic = st.selectbox("🔍 细分考点：", st.session_state.sub_topic_map.get(main_topic, ["综合复习"]))
                target_topic_str = f"{main_topic}-{sub_topic}"

        btn_label = "🔄 获取相似题巩固" if st.session_state.last_is_wrong else "✨ 获取专项练习题目"
        
        if st.button(btn_label):
            with st.spinner("小红老师出题中..."):
                st.session_state.eval_result = ""
                st.session_state.follow_up_resp = ""
                q_type = random.choice(["单项选择题", "填空题"])
                base_prompt = f"针对【{target_topic_str}】出一道{q_type}。必须在最后另起一行标注‘标准答案：[答案]’。"
                
                if st.session_state.last_is_wrong:
                    q_prompt = f"孩子刚才答错了题。请针对相同逻辑出一道巩固题。开头须为‘下面给你一道巩固题，仔细想想哦：’{base_prompt}"
                else:
                    q_prompt = base_prompt
                
                if forced_req:
                    q_prompt = f"【指令：{forced_req}】\n" + q_prompt

                res = ask_ai_teacher("命题内容："+target_topic_str, q_prompt, is_grading=False)
                if res and "标准答案：" in res:
                    main_q, _, ans_part = res.partition("标准答案：")
                    st.session_state.current_q = main_q.strip()
                    st.session_state.correct_ans = ans_part.strip().replace("[","").replace("]","")
                    st.rerun()

        if st.session_state.current_q:
            st.markdown("---")
            st.info(st.session_state.current_q)
            ans_input = st.text_area("输入你的思考：", placeholder="小红老师，我是这样想的...")
            if st.button("🚀 提交给老师批改"):
                with st.spinner("小红老师批改中..."):
                    e_prompt = (f"题目内容：{st.session_state.current_q}\n标准答案：{st.session_state.correct_ans}\n学生答案：{ans_input}\n"
                                f"请判断正误并给予温柔点拨。")
                    eval_res = ask_ai_teacher("批改任务", e_prompt, is_grading=True)
                    if eval_res:
                        st.session_state.eval_result = eval_res
                        st.session_state.chat_history.append({"q": st.session_state.current_q, "a": eval_res})
                        st.session_state.last_is_wrong = "错误" in eval_res or "【错误】" in eval_res
                        st.rerun()
                        
    with col_r:
        st.subheader("💡 老师的点拨")
        if st.session_state.eval_result:
            st.success(st.session_state.eval_result)
            if st.session_state.last_is_wrong:
                st.divider()
                u_question = st.text_input("💬 追问老师：", key="follow_up_input")
                if st.button("🙋 确认追问"):
                    f_prompt = f"题目：{st.session_state.current_q}\n疑问：{u_question}\n请耐心用纯文字解答。"
                    st.session_state.follow_up_resp = ask_ai_teacher("答疑", f_prompt, is_grading=True)
                if st.session_state.follow_up_resp:
                    st.info(f"**老师说：** {st.session_state.follow_up_resp}")

with tab2:
    for i, item in enumerate(reversed(st.session_state.chat_history)):
        with st.expander(f"练习记录 {len(st.session_state.chat_history) - i}"):
            st.write(item['q']); st.markdown(f"**点评：**\n{item['a']}")

st.divider()
st.markdown(f'<div style="text-align: center; color: gray; font-size: 14px;">© 2025 某某学校 | 九年级数学组 | 负责人：小红老师</div>', unsafe_allow_html=True)
