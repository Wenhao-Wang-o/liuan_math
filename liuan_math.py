import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI
import random

# --- 1. 页面初始化 ---
st.set_page_config(page_title="某某学校-学情分析系统", layout="wide")

if 'class_data' not in st.session_state:
    st.session_state.class_data = pd.DataFrame({
        "姓名": ["张三", "李四", "王五", "赵六"],
        "二次函数": [80, 45, 90, 30],
        "圆的性质": [70, 60, 85, 40],
        "相似三角形": [30, 20, 95, 15],
        "锐角三角函数": [85, 75, 80, 70],
        "反比例函数": [75, 55, 88, 50]
    })
if 'current_q' not in st.session_state: st.session_state.current_q = ""
if 'eval_result' not in st.session_state: st.session_state.eval_result = ""
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'last_is_wrong' not in st.session_state: st.session_state.last_is_wrong = False 
if 'correct_ans' not in st.session_state: st.session_state.correct_ans = "" # 🌟 新增：存储标准答案

# --- 2. 侧边栏 ---
with st.sidebar:
    st.title("🏫 教学管理后台")
    st.info("👤 **授课教师：小红**\n\n🏫 **学校：某某学校**\n\n📚 **班级：九年级数学**")
    st.divider()
    api_key = st.text_input("🔑 API Key (DeepSeek)", type="password")
    base_url = st.text_input("🌐 API 代理", value="https://api.deepseek.com")
    st.divider()
    st.subheader("🎯 强制出题要求")
    forced_req = st.text_area("输入特定指令：", placeholder="例如：请出一道关于相似三角形的选择题，要求四个选项涉及对应边成比例或对应角相等", key="forced_instruction")
    st.divider()
    st.subheader("📊 九年级数学学情看板")
    heat_df = st.session_state.class_data.set_index("姓名")
    st.plotly_chart(px.imshow(heat_df, text_auto=True, color_continuous_scale='RdYlGn', aspect="auto"), key="heatmap", use_container_width=True)
    st.subheader("👤 学生维度诊断")
    selected_student = st.selectbox("选择学生：", st.session_state.class_data["姓名"])
    student_row = st.session_state.class_data[st.session_state.class_data["姓名"] == selected_student]
    plot_data = pd.DataFrame({"知识点": heat_df.columns, "得分": student_row.iloc[0, 1:].values})
    st.plotly_chart(px.line_polar(plot_data, r='得分', theta='知识点', line_close=True, range_r=[0, 100]), key="radar", use_container_width=True)
    student_weakest = plot_data.loc[plot_data['得分'].idxmin(), '知识点']

# --- 3. AI 调用逻辑 ---
def ask_ai_teacher(system_prompt, user_input, is_grading=False):
    if not api_key:
        st.error("请先在左侧输入 API Key！")
        return None
    # 🌟 强化指令：死命令禁止 LaTeX，确保数学表达纯文字化
    identity_prompt = (
        f"你现在是数学老师小红。点评极其简练（50字内）。"
        "严禁使用 LaTeX 格式（禁止出现 \\frac, \\triangle, ^ 等反斜杠符号）。"
        "分数请写成 a/b，三角形写成‘三角形ABC’。批改时第一行必须输出【正确】或【错误】。"
    )
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": identity_prompt + system_prompt},{"role": "user", "content": user_input}],
            temperature=0.3 if is_grading else 1.0
        )
        return response.choices[0].message.content
    except: return None

# --- 4. 主界面 ---
st.title("🤖 智汇皋陶：AI 个性化测评系统")
st.markdown(f"#### 欢迎来到 **小红** 老师的数字教室")

tab1, tab2 = st.tabs(["✍️ 互动练习区", "📖 练习记录本"])

with tab1:
    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.subheader(f"📍 针对【{selected_student}】的精准强化")
        btn_label = "🔄 获取相似题巩固" if st.session_state.last_is_wrong else "✨ 获取九年级中考专项题目"
        
        if st.button(btn_label):
            with st.spinner("小红老师正在为您准备题目..."):
                q_type = random.choice(["带有A/B/C/D选项的选择题", "纯文字填空题"])
                # 🌟 核心修改：要求 AI 在输出末尾带上答案
                base_prompt = f"针对【{student_weakest}】出一道九年级中考难度的【{q_type}】。绝对严禁 LaTeX。必须在题目最后另起一行标注‘标准答案：[字母或数值]’。"
                
                if st.session_state.last_is_wrong:
                    q_prompt = f"孩子刚才答错了题目：{st.session_state.current_q}。请再出一道逻辑相近的新题。{base_prompt} 开头必须是‘下面给你一道巩固题，仔细想想哦：’"
                else:
                    q_prompt = base_prompt
                
                if forced_req:
                    q_prompt = f"【硬性要求：{forced_req}】\n" + q_prompt

                res = ask_ai_teacher("命题专家", q_prompt, is_grading=False)
                if res and "标准答案：" in res:
                    # 🌟 核心修改：截断答案，不让学生看见，但存入后台
                    main_q, _, ans_part = res.partition("标准答案：")
                    st.session_state.current_q = main_q.strip()
                    st.session_state.correct_ans = ans_part.strip().replace("[","").replace("]","")
                    st.session_state.eval_result = ""
                    st.rerun()

        if st.session_state.current_q:
            st.markdown("---")
            st.info(st.session_state.current_q)
            ans_input = st.text_area("输入你的思考：", placeholder="小红老师，我是这样想的...")
            
            if st.button("🚀 提交给老师批改"):
                with st.spinner("小红老师正在阅读你的答案..."):
                    # 🌟 核心修改：批改时直接告诉 AI 刚才锁定的正确答案是什么
                    e_prompt = (
                        f"【标准参考答案】：{st.session_state.correct_ans}\n"
                        f"【学生提交内容】：{ans_input}\n"
                        f"请严格比对参考答案进行批改。第一行输出【正确】或【错误】，然后给温柔点拨。"
                    )
                    eval_res = ask_ai_teacher("批改老师", e_prompt, is_grading=True)
                    if eval_res:
                        st.session_state.eval_result = eval_res
                        st.session_state.chat_history.append({"q": st.session_state.current_q, "a": eval_res})
                        st.session_state.last_is_wrong = "错误" in eval_res or "【错误】" in eval_res
                        st.rerun()
                        
    with col_r:
        st.subheader("💡 老师的点拨")
        if st.session_state.eval_result:
            st.success(st.session_state.eval_result)

with tab2:
    for i, item in enumerate(reversed(st.session_state.chat_history)):
        with st.expander(f"练习记录 {len(st.session_state.chat_history) - i}"):
            st.write(item['q'])
            st.markdown(f"**点评：**\n{item['a']}")

# --- 5. 页脚 ---
st.divider()
st.markdown(f'<div style="text-align: center; color: gray; font-size: 14px;">© 2025 某某学校 | 九年级数学组 | 负责人：小红老师</div>', unsafe_allow_html=True)
