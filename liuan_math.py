import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI
import random

# --- 1. 页面初始化 ---
st.set_page_config(page_title="某某学校-学情分析系统", layout="wide")

# 初始化数据
if 'class_data' not in st.session_state:
    st.session_state.class_data = pd.DataFrame({
        "姓名": ["张三", "李四", "王五", "赵六"],
        "二次函数": [80, 45, 90, 30],
        "圆的性质": [70, 60, 85, 40],
        "相似三角形": [30, 20, 95, 15],
        "锐角三角函数": [85, 75, 80, 70],
        "反比例函数": [75, 55, 88, 50]
    })

# 🌟 建立知识点细分地图 (根据您的需求定制)
if 'sub_topic_map' not in st.session_state:
    st.session_state.sub_topic_map = {
        "二次函数": ["1.二次函数概念", "2.二次函数的图象和性质", "3.二次函数与一元二次方程", "4.二次函数的应用", "5.综合与实践：获取最大利润"],
        "圆的性质": ["1.旋转", "2.圆的基本性质", "3.圆周角", "4.直线与圆的位置关系", "5.三角形的内切圆", "6.正多边形与圆", "7.弧长与扇形面积", "8.综合复习"],
        "相似三角形": ["1.比例线段", "2.平行线分线段成比例", "3.相似三角形判定", "4.相似三角形性质", "5.位似"],
        "锐角三角函数": ["1.正弦/余弦/正切", "2.特殊角的三角函数值", "3.解直角三角形及其应用"],
        "反比例函数": ["1.反比例函数概念", "2.反比例函数的图象和性质", "3.反比例函数的应用"]
    }

if 'current_q' not in st.session_state: st.session_state.current_q = ""
if 'eval_result' not in st.session_state: st.session_state.eval_result = ""
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'last_is_wrong' not in st.session_state: st.session_state.last_is_wrong = False 
if 'correct_ans' not in st.session_state: st.session_state.correct_ans = "" 

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
    st.subheader("📊 学情看板")
    heat_df = st.session_state.class_data.set_index("姓名")
    st.plotly_chart(px.imshow(heat_df, text_auto=True, color_continuous_scale='RdYlGn', aspect="auto"), key="heatmap", use_container_width=True)
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
    identity_prompt = (
        f"你现在是数学老师小红。点评极其简练（50字内）。"
        "严禁使用 LaTeX 格式（禁止出现 \\frac, \\triangle, ^ 等）。分数用 a/b，三角形写‘三角形ABC’。"
        "批改时第一行必须输出【正确】或【错误】。"
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

tab1, tab2 = st.tabs(["✍️ 互动练习区", "📖 练习记录本"])

with tab1:
    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.subheader(f"📍 针对【{selected_student}】的精准强化")
        
        # 🌟 修改点：双层联动选择考点
        main_kps = list(st.session_state.class_data.columns[1:])
        col_m, col_s = st.columns(2)
        with col_m:
            main_topic = st.selectbox("📚 选择章节：", ["🎯 智能推荐", *main_kps])
        
        with col_s:
            if main_topic == "🎯 智能推荐":
                sub_topic = "弱项强化"
                target_topic_str = student_weakest
            else:
                sub_topic = st.selectbox("🔍 细分考点：", st.session_state.sub_topic_map.get(main_topic, ["综合练习"]))
                target_topic_str = f"{main_topic}下的{sub_topic}"

        st.write(f"当前训练点：**{target_topic_str}**")

        btn_label = "🔄 获取相似题巩固" if st.session_state.last_is_wrong else "✨ 获取专项练习题目"
        
        if st.button(btn_label):
            with st.spinner("小红老师正在为您准备题目..."):
                q_type = random.choice(["选择题", "填空题"])
                # 🌟 将精细化考点植入 Prompt
                base_prompt = f"针对【{target_topic_str}】出一道九年级中考难度的【{q_type}】。绝对严禁 LaTeX。必须在最后标注‘标准答案：[字母或数值]’。"
                
                if st.session_state.last_is_wrong:
                    q_prompt = f"孩子刚才答错了题目：{st.session_state.current_q}。请再出一道逻辑相近的新题。{base_prompt} 开头必须是‘下面给你一道巩固题，仔细想想哦：’"
                else:
                    q_prompt = base_prompt
                
                if forced_req:
                    q_prompt = f"【硬性要求：{forced_req}】\n" + q_prompt

                res = ask_ai_teacher("命题专家", q_prompt, is_grading=False)
                if res and "标准答案：" in res:
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
                with st.spinner("小红老师批改中..."):
                    e_prompt = (f"【标准答案】：{st.session_state.correct_ans}\n【学生答案】：{ans_input}\n"
                                f"判断正误，第一行输出【正确】或【错误】，然后给温柔点拨。")
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
