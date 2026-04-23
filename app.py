import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# --- 介面強制明亮模式 ---
st.set_page_config(page_title="MLB Scouting Report", layout="wide")

st.markdown("""
    <style>
    .main { background-color: white !important; color: black !important; }
    div[data-testid="stSidebar"] { background-color: #f0f2f6 !important; }
    h1, h2, h3 { color: #1e3a8a !important; font-family: 'Segoe UI', sans-serif; }
    /* 修正表格字體 */
    div[data-testid="stDataFrame"] td { font-size: 15px !important; color: black !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚾ MLB 專業球探報告系統 (比例校準版)")

# --- 顏色定義 (鮮豔直觀) ---
color_palette = {
    'Single': '#FF4B4B', 'Double': '#FFAA00', 'Triple': '#FFAA00', 
    'Home Run': '#00C9A7', 'Field Out': '#3498DB', 
    'Strikeout': '#95A5A6', 'Walk': '#2ECC71', 'Hit By Pitch': '#2ECC71'
}

def style_number_col(row):
    color = color_palette.get(row['結果'], 'white')
    return [f'background-color: {color}; color: black; font-weight: bold; text-align: center;' if name == '打席' else 'background-color: white; color: black;' for name in row.index]

with st.sidebar:
    st.header("⚙️ 設定")
    first_name = st.text_input("First Name", "Mike").strip().capitalize()
    last_name = st.text_input("Last Name", "Trout").strip().capitalize()
    submit = st.button("更新數據")

if submit:
    with st.spinner('數據計算中...'):
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
                    # --- 比例重新調校繪圖 ---
                    fig, ax = plt.subplots(figsize=(10, 10), facecolor='white')
                    
                    # 比例尺優化
                    def tx(x): return (x - 125.5) * 2.5
                    def ty(y): return (205 - y) * 2.3 

                    # 繪製內野 (調整起點，確保菱形居中且合理)
                    # 內野線條加粗，使用深灰色確保清晰
                    ax.plot([0, 63.6, 0, -63.6, 0], [0, 63.6, 127.2, 63.6, 0], color='#2c3e50', lw=3, zorder=3)
                    # 參考外野牆
                    ax.plot([0, 260, 0, -260, 0], [0, 260, 450, 260, 0], color='#bdc3c7', lw=2, ls='--', zorder=1)

                    for i, row in game_data.iterrows():
                        event_raw = str(row['events'])
                        if event_raw in ['strikeout', 'walk', 'hit_by_pitch']: continue
                            
                        if pd.notna(row['hc_x']):
                            x, y = tx(row['hc_x']), ty(row['hc_y'])
                            # 一壘安打高度修正 (不超過內野太遠)
                            if event_raw == 'single': y = min(y, 140)
                            
                            color = color_palette.get(event_raw.replace('_', ' ').title(), '#95A5A6')
                            marker = '*' if event_raw == 'home_run' else 'o'
                            
                            ax.scatter(x, y, c=color, s=600 if marker == '*' else 400, 
                                       marker=marker, edgecolors='black', linewidths=1.2, zorder=5)
                            ax.text(x, y, str(i+1), color='black' if marker == '*' else 'white', 
                                    ha='center', va='center', fontweight='bold', fontsize=11)

                    ax.set_xlim([-450, 450]); ax.set_ylim([-100, 550]); ax.set_aspect('equal'); ax.axis('off')
                    ax.set_title(f"{first_name} {last_name} | {latest_date}", fontsize=24, fontweight='bold', pad=20)
                    st.pyplot(fig)

                with col2:
                    st.subheader("📋 打席詳細日誌")
                    records = [{"打席": i+1, "結果": str(row['events']).replace('_', ' ').title(), 
                                "初速": f"{row['launch_speed']:.0f} mph" if pd.notna(row['launch_speed']) else "--"} 
                               for i, row in game_data.iterrows()]
                    
                    df_display = pd.DataFrame(records)
                    st.dataframe(df_display.style.apply(style_number_col, axis=1), use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    st.info("💡 **顯示邏輯**：背景已調回明亮模式，內野比例已校準。")

                st.success(f"Report Generated.")
            else: st.warning("No Data.")
        else: st.error("No Player.")
