import streamlit as st
import pandas as pd
import numpy as np

# 设置页面配置（美化界面并设置为宽屏模式）
st.set_page_config(page_title="🃏 Jester 智能笑话推荐系统", layout="wide", initial_sidebar_state="expanded")

# --- 1. 数据加载与缓存 (使用 @st.cache_data 优化数据读取性能) ---
@st.cache_data
def load_data():
    # 读取在 Notebook 中成功导出的相似度矩阵
    similarity_df = pd.read_csv("joke_similarity_matrix.csv", index_col=0)
    # 将列名强制转换为 int 类型，确保后续索引匹配时不会因类型不一致报错
    similarity_df.columns = similarity_df.columns.astype(int)
    
    # 读取原始笑话文本
    jokes_df = pd.read_excel("Dataset4JokeSet.xlsx", header=None)
    jokes_df.columns = ['joke_text']
    jokes_df['joke_id'] = range(1, len(jokes_df) + 1)
    
    # 获取有效笑话的 ID 列表（即在相似度矩阵中存在的笑话）
    valid_joke_ids = similarity_df.index.tolist()
    
    return jokes_df, similarity_df, valid_joke_ids

jokes_df, similarity_df, valid_joke_ids = load_data()


# --- 2. 核心算法改造：基于物品的 Item-Item 协同过滤推荐 ---
def get_top_recommendations(user_ratings, similarity_df, top_k=5):
    """
    user_ratings: 字典格式，如 {笑话ID: 评分值}
    """
    # 初始化所有候选笑话的综合推荐得分向量
    all_joke_ids = similarity_df.index
    combined_scores = pd.Series(0.0, index=all_joke_ids)
    
    # 遍历当前用户评价过的笑话，根据用户评分对相似度向量进行加权求和
    for j_id, score in user_ratings.items():
        if j_id in similarity_df.index:
            # 相似度向量 * 用户的真实评分
            combined_scores += similarity_df[j_id] * score
            
    # 过滤掉用户刚刚评价过的这 3 个笑话，防止重复推荐 [参考实验注意事项]
    rated_jokes = list(user_ratings.keys())
    combined_scores = combined_scores.drop(index=rated_jokes, errors='ignore')
    
    # 按照综合得分从高到低排序，过滤并筛选出得分最高的前 Top-K 个笑话
    recommended_joke_ids = combined_scores.sort_values(ascending=False).head(top_k).index.tolist()
    return recommended_joke_ids


# --- 3. 初始化 Session State (利用状态保持，防止滑动滑块时随机笑话频繁刷新) ---
if 'selected_jokes' not in st.session_state:
    # 随机抽取 3 个有评分记录的有效笑话 ID（完美避开那 22 个无评分的空笑话）[参考实验注意事项]
    st.session_state.selected_jokes = np.random.choice(valid_joke_ids, 3, replace=False).tolist()
if 'recommended' not in st.session_state:
    st.session_state.recommended = False


# --- 4. 界面设计与前端交互布局 ---
st.title("🃏 Jester 个性化笑话推荐系统")
st.markdown("---")

# 侧边栏布局展示应用和实验信息
with st.sidebar:
    st.header("📌 实验项目说明")
    st.markdown("""
    **核心主线：** 提取 → 改造 → 包装 → 部署  
    **推荐算法：** 基于物品的 Item-Item 协同过滤  
    **数据集：** Jester 匿名笑话评分数据集  
    """)
    # 换一批按钮
    if st.button("🔄 换一批笑话评分", type="secondary"):
        st.session_state.selected_jokes = np.random.choice(valid_joke_ids, 3, replace=False).tolist()
        st.session_state.recommended = False
        st.rerun()

# 步骤 1：展示随机抽取的笑话并收集评分
st.subheader("第一步：请阅读以下 3 个随机笑话并为它们评分")
user_ratings = {}

# 使用 st.columns 完美的将 3 个笑话并排并行展示，让界面不显拥挤
cols = st.columns(3)
for i, joke_id in enumerate(st.session_state.selected_jokes):
    with cols[i]:
        st.info(f"**笑话卡片 #{joke_id}**")
        # 提取当前 ID 的笑话文本内容
        joke_text = jokes_df[jokes_df['joke_id'] == joke_id]['joke_text'].values[0]
        st.write(joke_text)
        
        # 评分组件：根据 Jester 数据集标准，连续值评分范围设定为 -10.0 到 10.0 [参考实验注意事项]
        user_ratings[joke_id] = st.slider(f"请为笑话 #{joke_id} 打分", -10.0, 10.0, 0.0, step=0.5, key=f"slide_{joke_id}")

st.markdown("---")

# 步骤 2：生成个性化推荐触发按钮
if st.button("🚀 生成我的个性化推荐", type="primary"):
    st.session_state.recommended = True
    # 调用改造后的推荐算法计算结果，并写入全局状态中
    st.session_state.rec_joke_ids = get_top_recommendations(user_ratings, similarity_df, top_k=5)

# 步骤 3：展示推荐结果与计算用户满意度
if st.session_state.recommended:
    st.subheader("🎯 根据您的喜好，为您精准推荐以下 5 个笑话：")
    
    rec_feedback = []
    # 循环渲染展现 5 个推荐出来的笑话
    for idx, r_id in enumerate(st.session_state.rec_joke_ids):
        rec_text = jokes_df[jokes_df['joke_id'] == r_id]['joke_text'].values[0]
        with st.container():
            st.markdown(f"**🔥 推荐推荐 #{idx+1} (笑话 ID: {r_id})**")
            st.code(rec_text, language="markdown") # 用 code 格式包裹展示文本，视觉更有层次感
            
            # 收集用户对推荐结果的即时反馈评分（用于后续满意度归一化计算）
            feedback = st.slider(f"您对该推荐笑话的喜爱程度", -10.0, 10.0, 0.0, step=0.5, key=f"rec_{r_id}")
            rec_feedback.append(feedback)
            st.markdown("")
            
    st.markdown("---")
    st.subheader("📊 推荐系统满意度报告")
    
    # 满意度计算：将 [-10, 10] 的平均评分线性归一化映射到 [0%, 100%] [参考实验步骤2]
    # 归一化公式： (当前分值 - 最小值) / (最大值 - 最小值) * 100
    avg_feedback = np.mean(rec_feedback)
    satisfaction_score = (avg_feedback - (-10)) / (10 - (-10)) * 100
    
    # 动态渲染满意度指标卡与进度条
    st.metric(label="推荐满意度 (Satisfaction Score)", value=f"{satisfaction_score:.2f} %")
    st.progress(int(satisfaction_score))
    
    # 根据满意度分数给予用户不同的情感反馈
    if satisfaction_score >= 70:
        st.success("🎉 太棒了！看来系统推荐的笑话非常符合您的胃口！")
    elif satisfaction_score >= 40:
        st.warning("😐 效果似乎中规中矩，我们会继续不断优化协同过滤模型。")
    else:
        st.error("😭 很抱歉，本次推荐的笑话未能逗笑您。您可以尝试重新调整上方评分！")