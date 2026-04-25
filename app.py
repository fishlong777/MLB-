import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# --- 介面樣式設定 ---
st.set_page_config(page_title="MLB Hitting Chart", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #FFFFFF !important; }
    h1 { color: #1F2937 !important; font-family: 'Segoe UI', sans-serif; font-weight: 800; border-bottom: 3px solid #3498DB; }
    .stMarkdown h1 a, .stMarkdown h1 span { display: none !important; }
    div[data-testid="stDataFrame"] td { font-size: 16px !important; color: #333333 !important; }
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
            if name == '打席' else 'background-color: white; color: black;' for name in row.index]

with st.sidebar:
    st.header("選手查詢")
    first_name = st.text_input("First Name", "Aaron").strip().capitalize()
    last_name = st.text_input("Last Name", "Judge").strip().capitalize()
    submit = st.button("更新數據")

if submit:
    with st.spinner('正在優化視覺細節...'):
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
                    fig, ax = plt.subplots(figsize=(10, 10), facecolor='white')
                    
                    def tx(x): return (x - 125.5) * 3.5
                    def ty(y): return (205 - y) * 3.5

                    # 【修正1】：線條粗細一致化 (lw=2.5)
                    ax.plot([0, 125, 0, -125, 0], [0, 125, 250, 125, 0], color='#2C3E50', lw=2.5, zorder=3) # 內野
                    ax.plot([0, 270, 0, -270, 0], [0, 270, 460, 270, 0], color='#7F8C8D', lw=2.5, ls='-', zorder=1) # 外野

                    for i, row in game_data.iterrows():
                        event_raw = str(row['events'])
                        if event_raw in ['strikeout', 'walk', 'intentional_walk', 'hit_by_pitch']: continue
                            
                        if pd.notna(row['hc_x']):
                            x, y = tx(row['hc_x']), ty(row['hc_y'])
                            
                            color = color_palette.get(event_raw.replace('_', ' ').title(), '#95A5A6')
                            marker = '*' if event_raw == 'home_run' else 'o'
                            
                            # 繪製點
                            ax.scatter(x, y, c=color, s=400, marker=marker, edgecolors='black', linewidths=1.2, zorder=5)
                            
                            # 【修正2】：數字標籤外移至點的右上角，確保可辨識性
                            ax.text(x+10, y+10, str(i+1), color='#1F2937', ha='left', va='bottom', 
                                    fontweight='bold', fontsize=12, zorder=6,
                                    bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=1))

                    ax.set_xlim([-480, 480]); ax.set_ylim([-50, 680]); ax.set_aspect('equal'); ax.axis('off')
                    ax.set_title(f"{first_name} {last_name} | {latest_date}", fontsize=24, fontweight='bold', color='#1F2937', pad=50)
                    st.pyplot(fig)

                with col2:
                    st.subheader("📋 打席結果明細")
                    records = []
                    for i, row in game_data.iterrows():
                        e = str(row['events'])
                        # 【修正3】：確保 Intentional Walk 拼寫
                        event_display = "Intentional Walk" if e == "intentional_walk" else e.replace('_', ' ').title()
                        speed = f"{row['launch_speed']:.0f} mph" if pd.notna(row['launch_speed']) else "--"
                        records.append({"打席": i+1, "結果": event_display, "初速": speed})
                    
                    df_display = pd.DataFrame(records)
                    st.dataframe(df_display.style.apply(style_number_col, axis=1), use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    st.info("💡 **視覺微調**：線條粗細已統一，打席編號已從圓心移至旁側以利辨識。")

                st.success(f"更新完畢")
            else: st.warning("無數據。")
        else: st.error("找不到球員。")
