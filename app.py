import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# --- 徹底鎖定視覺樣式 ---
st.set_page_config(page_title="MLB Hitting Chart", layout="wide")

st.markdown("""
    <style>
    /* 1. 左半邊側邊欄不要白色：強制深色 */
    section[data-testid="stSidebar"] {
        background-color: #111827 !important;
    }
    section[data-testid="stSidebar"] .stMarkdown p, section[data-testid="stSidebar"] label {
        color: white !important;
    }

    /* 2. 大標題強制白色 */
    .main { background-color: #0E1117 !important; }
    h1 { 
        color: #FFFFFF !important; 
        font-family: 'Segoe UI', sans-serif; 
        font-weight: 800; 
        border-bottom: 2px solid #3498DB;
    }
    
    /* 清理雜質 */
    .stMarkdown h1 a, .stMarkdown h1 span { display: none !important; }
    
    /* 表格樣式 */
    div[data-testid="stDataFrame"] td { font-size: 16px !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("MLB 打者擊球落點圖")

# --- 顏色定義 ---
color_palette = {
    'Single': '#FF4B4B', 'Double': '#FFAA00', 'Triple': '#FFAA00', 
    'Home Run': '#00C9A7', 'Field Out': '#3498DB', 
    'Strikeout': '#95A5A6', 'Walk': '#2ECC71', 'Intentional Walk': '#2ECC71', 'Hit By Pitch': '#2ECC71'
}

def style_number_col(row):
    color = color_palette.get(row['結果'], 'white')
    return [f'background-color: {color}; color: black; font-weight: bold; text-align: center;' 
            if name == '打席' else 'background-color: #1A1C24; color: white;' for name in row.index]

with st.sidebar:
    st.header("🔍 選手查詢")
    first_name = st.text_input("First Name", "Aaron").strip().capitalize()
    last_name = st.text_input("Last Name", "Judge").strip().capitalize()
    submit = st.button("更新數據")

if submit:
    with st.spinner('正在精確校準視覺...'):
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
                    fig, ax = plt.subplots(figsize=(10, 10), facecolor='none')
                    
                    def tx(x): return (x - 125.5) * 3.5
                    def ty(y): return (205 - y) * 2.6 

                    # 【修正3】菱形線條改回灰色 (不塗黑)
                    court_color = '#7F8C8D'
                    ax.plot([0, 125, 0, -125, 0], [0, 125, 250, 125, 0], color=court_color, lw=2.5, zorder=3)
                    ax.plot([0, 270, 0, -270, 0], [0, 270, 460, 270, 0], color='#4A4E69', lw=2, ls='-', zorder=1)

                    # 【修正4】壘包放在 90 度「角裡面」 (透過小幅座標偏移)
                    b_off = 8 # 偏移量，讓它往裡面縮一點
                    ax.plot(125-b_off, 125, marker='s', color='#FFFFFF', markersize=10, zorder=11) # 一壘往左縮
                    ax.plot(0, 250-b_off, marker='s', color='#FFFFFF', markersize=10, zorder=11) # 二壘往下縮
                    ax.plot(-125+b_off, 125, marker='s', color='#FFFFFF', markersize=10, zorder=11) # 三壘往右縮

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
                            
                            color = color_palette.get(event_key, '#95A5A6')
                            marker = '*' if 'home_run' in event_raw else 'o'
                            
                            ax.scatter(x, y, c=color, s=450, marker=marker, edgecolors='black', linewidths=1.2, zorder=5)
                            ax.text(x+15, y+15, str(i+1), color='#FFFFFF', ha='left', va='bottom', 
                                    fontweight='bold', fontsize=12, zorder=6,
                                    bbox=dict(facecolor='black', alpha=0.5, edgecolor='none', boxstyle='round,pad=0.2'))

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
                    st.info("💡 **修正紀錄**：側邊欄深色化、標題強制亮白、壘包入角、線條灰化。")

                st.success(f"視覺校準完畢")
