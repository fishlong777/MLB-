import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# --- 介面質感配色設定 ---
st.set_page_config(page_title="MLB Hitting Chart", layout="wide")

st.markdown("""
    <style>
    /* 整體背景：深藍灰 */
    .main { background-color: #1A2238 !important; }
    
    /* 側邊欄：略深的灰藍 */
    section[data-testid="stSidebar"] {
        background-color: #111827 !important;
        border-right: 1px solid #374151;
    }
    section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p {
        color: #E5E7EB !important;
    }

    /* 標題：亮白色，帶點淡藍陰影 */
    h1 { 
        color: #FFFFFF !important; 
        font-family: 'Segoe UI', sans-serif; 
        font-weight: 800; 
        border-bottom: 3px solid #3B82F6;
        text-shadow: 0px 2px 4px rgba(0,0,0,0.3);
    }
    
    /* 移除標題雜質 */
    .stMarkdown h1 a, .stMarkdown h1 span { display: none !important; }
    
    /* 表格樣式優化 */
    div[data-testid="stDataFrame"] {
        background-color: #1F2937;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("MLB 打者擊球落點圖")

# --- 配色方案 (鮮豔但不刺眼) ---
color_palette = {
    'Single': '#F87171',      # 珊瑚紅
    'Double': '#FB923C',      # 亮橘
    'Triple': '#FBBF24',      # 琥珀金
    'Home Run': '#34D399',    # 薄荷綠
    'Field Out': '#60A5FA',   # 天空藍
    'Strikeout': '#9CA3AF',   # 冷灰
    'Walk': '#A78BFA',        # 紫羅蘭
    'Intentional Walk': '#A78BFA', 
    'Hit By Pitch': '#A78BFA'
}

def style_number_col(row):
    color = color_palette.get(row['結果'], '#FFFFFF')
    # 針對深色背景優化表格文字
    return [f'background-color: {color}; color: #111827; font-weight: bold; text-align: center;' 
            if name == '打席' else 'background-color: #1F2937; color: #F3F4F6;' for name in row.index]

with st.sidebar:
    st.header("🔍 選手查詢")
    first_name = st.text_input("First Name", "Aaron").strip().capitalize()
    last_name = st.text_input("Last Name", "Judge").strip().capitalize()
    submit = st.button("更新數據")

if submit:
    with st.spinner('正在渲染質感圖表...'):
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
                    # 使用透明背景，讓它融入網頁背景
                    fig, ax = plt.subplots(figsize=(10, 10), facecolor='none')
                    
                    def tx(x): return (x - 125.5) * 3.5
                    def ty(y): return (205 - y) * 2.6 

                    # 球場線條：使用淡灰色 (#D1D5DB)，不會太刺眼也不會看不到
                    court_line_color = '#94A3B8'
                    ax.plot([0, 125, 0, -125, 0], [0, 125, 250, 125, 0], color=court_line_color, lw=2, zorder=3)
                    ax.plot([0, 270, 0, -270, 0], [0, 270, 460, 270, 0], color='#475569', lw=1.5, ls='-', zorder=1)

                    # 壘包位置：放置在內角 (偏移量微調)
                    b_off = 10
                    ax.plot(125-b_off, 125, marker='s', color='#F9FAFB', markersize=8, zorder=11)
                    ax.plot(0, 250-b_off, marker='s', color='#F9FAFB', markersize=8, zorder=11)
                    ax.plot(-125+b_off, 125, marker='s', color='#F9FAFB', markersize=8, zorder=11)

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
                            
                            color = color_palette.get(event_key, '#9CA3AF')
                            marker = '*' if 'home_run' in event_raw else 'o'
                            
                            ax.scatter(x, y, c=color, s=450, marker=marker, edgecolors='#1A2238', linewidths=1.2, zorder=5)
                            # 數字標籤：深色背景配亮色字
                            ax.text(x+15, y+15, str(i+1), color='#F3F4F6', ha='left', va='bottom', 
                                    fontweight='bold', fontsize=12, zorder=6,
                                    bbox=dict(facecolor='#111827', alpha=0.6, edgecolor='none', boxstyle='round,pad=0.2'))

                    ax.set_xlim([-480, 480]); ax.set_ylim([-50, 680]); ax.set_aspect('equal'); ax.axis('off')
                    ax.set_title(f"{first_name} {last_name} | {latest_date}", fontsize=24, fontweight='bold', color='#FFFFFF', pad=50)
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
                    st.info("💡 **視覺優化**：採用午夜藍商務配色，提升對比度與閱讀舒適度。")

                st.success(f"視覺升級完畢")
