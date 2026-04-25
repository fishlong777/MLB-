import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# --- 介面質感與層次設定 ---
st.set_page_config(page_title="MLB Hitting Chart", layout="wide")

st.markdown("""
    <style>
    /* 背景改為更深邃的午夜藍黑，增加層次感 */
    .stApp {
        background-color: #0F172A !important; 
    }
    
    /* 標題與分界線：使用亮藍色強調 */
    h1 { 
        color: #F8FAFC !important; 
        font-family: 'Segoe UI', sans-serif; 
        font-weight: 800; 
        border-bottom: 3px solid #3B82F6;
        padding-bottom: 12px;
        letter-spacing: 1px;
    }
    
    /* 移除自動生成的連結符號 */
    .stMarkdown h1 a, .stMarkdown h1 span { display: none !important; }
    
    /* 側邊欄配色 */
    section[data-testid="stSidebar"] {
        background-color: #020617 !important;
        border-right: 1px solid #1E293B;
    }
    
    /* 表格容器區塊：讓它稍微浮現出來 */
    div[data-testid="stDataFrame"] {
        background-color: #1E293B !important;
        border-radius: 8px;
        padding: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("MLB 打者擊球落點圖")

# --- 顏色定義 (高飽和度，確保在深色底清晰) ---
color_palette = {
    'Single': '#EF4444',      # 鮮紅
    'Double': '#F59E0B',      # 亮橘
    'Triple': '#FCD34D',      # 銘黃
    'Home Run': '#10B981',    # 寶石綠
    'Field Out': '#3B82F6',   # 亮藍
    'Strikeout': '#64748B',   # 藍灰
    'Walk': '#8B5CF6',        # 靛紫
    'Intentional Walk': '#8B5CF6', 
    'Hit By Pitch': '#8B5CF6'
}

def style_number_col(row):
    color = color_palette.get(row['結果'], '#FFFFFF')
    return [f'background-color: {color}; color: #0F172A; font-weight: bold; text-align: center;' 
            if name == '打席' else 'background-color: #1E293B; color: #F8FAFC;' for name in row.index]

with st.sidebar:
    st.header("🔍 選手查詢")
    first_name = st.text_input("First Name", "Aaron").strip().capitalize()
    last_name = st.text_input("Last Name", "Judge").strip().capitalize()
    submit = st.button("更新數據")

if submit:
    with st.spinner('正在優化數據視覺渲染...'):
        player_info = playerid_lookup(last_name, first_name)
        if not player_info.empty:
            mlbam_id = player_info.key_mlbam.values[0]
            data = statcast_batter((datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'), 
                                  datetime.now().strftime('%Y-%m-%d'), mlbam_id)
            
            if not data.empty:
                latest_date = data['game_date'].max()
                game_data = data[data['game_date'] == latest_date].copy()
                game_data = game_data[game_data['events'].notna()].sort_index(ascending=True).reset_index(drop=True)

                col1, col2 = st.columns([1.6, 1])

                with col1:
                    # 使用透明背景
                    fig, ax = plt.subplots(figsize=(10, 10), facecolor='none')
                    
                    # 座標倍率
                    def tx(x): return (x - 125.5) * 3.2
                    def ty(y): return (205 - y) * 2.2 

                    # 球場實線：調亮線條顏色 (#CBD5E1) 增加對比
                    line_color = '#94A3B8'
                    ax.plot([0, 125, 0, -125, 0], [0, 125, 250, 125, 0], color=line_color, lw=2.5, zorder=3)
                    ax.plot([0, 270, 0, -270, 0], [0, 270, 460, 270, 0], color='#334155', lw=2.5, ls='-', zorder=1)

                    # 壘包方塊入角
                    off = 12
                    ax.plot(125-off, 125, marker='s', color='#F8FAFC', markersize=9, zorder=11)
                    ax.plot(0, 250-off, marker='s', color='#F8FAFC', markersize=9, zorder=11)
                    ax.plot(-125+off, 125, marker='s', color='#F8FAFC', markersize=9, zorder=11)

                    for i, row in game_data.iterrows():
                        event_raw = str(row['events']).lower()
                        if any(x in event_raw for x in ['strikeout', 'walk', 'hit_by_pitch']): continue
                            
                        if pd.notna(row['hc_x']):
                            x, y = tx(row['hc_x']), ty(row['hc_y'])
                            if 'home_run' not in event_raw: y = min(y, 450)
                            
                            event_key = "Home Run" if 'home_run' in event_raw else "Field Out"
                            if 'single' in event_raw: event_key = "Single"
                            elif 'double' in event_raw: event_key = "Double"
                            elif 'triple' in event_raw: event_key = "Triple"
                            
                            color = color_palette.get(event_key, '#94A3B8')
                            marker = '*' if 'home_run' in event_raw else 'o'
                            
                            # 點位增加白色邊緣，確保在深色底跳出來
                            ax.scatter(x, y, c=color, s=480, marker=marker, edgecolors='#F8FAFC', linewidths=1.5, zorder=5)
                            
                            # 數字標籤改用亮色系背景
                            ax.text(x+15, y+15, str(i+1), color='#F8FAFC', ha='left', va='bottom', 
                                    fontweight='bold', fontsize=12, zorder=6,
                                    bbox=dict(facecolor='#0F172A', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.2'))

                    ax.set_xlim([-450, 450]); ax.set_ylim([-50, 600]); ax.set_aspect('equal'); ax.axis('off')
                    ax.set_title(f"{first_name} {last_name} | {latest_date}", fontsize=24, fontweight='bold', color='#F8FAFC', pad=40)
                    st.pyplot(fig)

                with col2:
                    st.subheader("📋 打席結果明細")
                    records = []
                    for i, row in game_data.iterrows():
                        e = str(row['events']).lower()
                        event_display = "Intentional Walk" if 'intent' in e else e.replace('_', ' ').title()
                        speed = f"{row['launch_speed']:.0f} mph" if pd.notna(row['launch_speed']) else "--"
                        records.append({"打席": i+1, "結果": event_display, "初速": speed})
                    
                    df_display = pd.DataFrame(records)
                    st.dataframe(df_display.style.apply(style_number_col, axis=1), use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    st.info("💡 **視覺修正**：強化背景深度與線條對比，增加點位白色邊緣以利辨識。")

                st.success(f"視覺效果已優化")
