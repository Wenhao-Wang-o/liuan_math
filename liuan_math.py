import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI
import random

# --- 1. 页面初始化 ---
st.set_page_config(page_title="某某学校-学情分析系统", layout="wide")

# 初始化数据：九年级数学模拟分值
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
# 🌟 仅新增：记录上一题是否答错的状态
if 'last_is_wrong' not in st.session_state: st.session_state.last_is_wrong = False

# --- 2. 侧边栏 ---
with st.sidebar:
    st.title("🏫 教学管理后台")
    st.info("👤 **授课教师：小红**\n\n🏫 **学校：某某学校**\n\n📚 **班级：九年级数学**")
    st.divider()
    api_key = st.text_input("🔑 API Key (DeepSeek)", type="password")
    base_url = st.text_input("🌐 API 代理", value="https://api.deepseek.com")
    
    # 🌟 仅新增：侧边栏强制出题要求输入框
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
def ask_ai_teacher(system_prompt, user_input):
    if not api_key:
        st.error("请先在左侧输入 API Key！")
        return None

    # 🌟 修改点：在原有提示词基础上，强制要求 AI 在批改时给出【正确】或【错误】标签，用于逻辑判定
    identity_prompt = (
        f"你现在是数学老师小红。对话对象是九年级学生。点评时称呼'同学'。要求：必须使用纯文字。"
        "点评要温柔细腻，给出启发式点拨。注意要先给答案，并详细解释，尽量用文字描述，注意篇幅不要太长，直接讲核心，禁止使用LaTeX！"
        "🌟特别注意：如果你在进行批改，请在回复的第一行明确输出【正确】或【错误】。"
    )

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": identity_prompt + system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=1.0
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"AI 调用失败: {str(e)}")
        return None

# --- 4. 主界面 ---
st.title("🤖 智汇皋陶：AI 个性化测评系统")
st.markdown(f"#### 欢迎来到 **小红** 老师的数字教室（某某学校-九年级数学）")

tab1, tab2 = st.tabs(["✍️ 互动练习区", "📖 练习记录本"])

with tab1:
    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.subheader(f"📍 针对【{selected_student}】的精准强化")
        st.write(f"当前诊断薄弱项：**{student_weakest}**")
        
        # 🌟 修改点：按钮文案根据状态改变，引导错题巩固
        btn_label = "🔄 获取相似题巩固" if st.session_state.last_is_wrong else "✨ 获取九年级中考专项题目"
        
        if st.button(btn_label):
            with st.spinner("小红老师正在为您出题..."):
                q_type = random.choice(["带有A/B/C/D选项的选择题", "纯文字填空题"])
                
                # 🌟 核心修改：错题推送逻辑
                if st.session_state.last_is_wrong:
                    q_prompt = f"学生刚才答错了关于【{student_weakest}】的题目：{st.session_state.current_q}。请再出一道逻辑相近、难度相当但数值或背景不同的题目进行巩固。只需给出题目，不要给出答案和解析。"
                else:
                    q_prompt = f"针对【{student_weakest}】出一道九年级中考难度的【{q_type}】。只需给出题目，不要给出答案和解析。"
                
                # 🌟 核心修改：叠加侧边栏的强制出题要求
                if forced_req:
                    q_prompt = f"【硬性要求：{forced_req}】\n" + q_prompt

                res = ask_ai_teacher("你正在为九年级学生命制富有变化的练习题。", q_prompt)
                if res:
                    st.session_state.current_q = res
                    st.session_state.eval_result = ""

        if st.session_state.current_q:
            st.markdown("---")
            st.info(st.session_state.current_q)
            ans_input = st.text_area("输入你的思考：", placeholder="小红老师，我是这样想的...")
            
            if st.button("🚀 提交给老师批改"):
                with st.spinner("小红老师正在阅读你的答案..."):
                    e_prompt = f"题目：{st.session_state.current_q}\n学生答案：{ans_input}\n要求：极简温柔地判断正误并给出点拨，不要超过50字。"
                    eval_res = ask_ai_teacher("你正在批改九年级学生的数学作业。", e_prompt)
                    if eval_res:
                        st.session_state.eval_result = eval_res
                        st.session_state.chat_history.append({"q": st.session_state.current_q, "a": eval_res})
                        
                        # 🌟 修改点：通过 AI 回复判定是否答错，更新状态
                        if "错误" in eval_res or "【错误】" in eval_res:
                            st.session_state.last_is_wrong = True
                        else:
                            st.session_state.last_is_wrong = False
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
