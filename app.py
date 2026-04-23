import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# --- 介面初始化 ---
st.set_page_config(page_title="MLB Pro Report", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0E1117; }
    h1 { color: white; border-bottom: 2px solid #E67E22; padding-bottom: 10px; }
    /* 讓表格文字大一點比較好讀 */
    div[data-testid="stDataFrame"] td { font-size: 16px !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚾ MLB 專業球探報告系統 (顏色對應版)")

# --- 顏色定義 (鮮豔直觀版) ---
color_palette = {
    'Single': '#FF4B4B',      # 紅
    'Double': '#FFAA00',      # 橘
    'Triple': '#FFAA00',      # 橘
    'Home Run': '#00F5D4',    # 亮青 (星星)
    'Field Out': '#1B9CE5',   # 藍
    'Strikeout': '#6C757D',   # 灰
    'Walk': '#99FF77',        # 嫩綠
    'Hit By Pitch': '#99FF77' # 嫩綠
}

def style_number_col(row):
    """只針對 [打席] 這一格標色"""
    bg_color = color_palette.get(row['結果'], '#FFFFFF')
    # 打席數字的顏色
    return [f'background-color: {bg_color}; color: black; font-weight: bold; text-align: center;' if name == '打席' else '' for name in row.index]

with st.sidebar:
    st.header("⚙️ 查詢設定")
    first_name = st.text_input("First Name", "Mike").strip().capitalize()
    last_name = st.text_input("Last Name", "Trout").strip().capitalize()
    submit = st.button("更新數據")

if submit:
    with st.spinner('正在分析數據...'):
        player_info = playerid_lookup(last_name, first_name)
        
        if not player_info.empty:
            mlbam_id = player_info.key_mlbam.values[0]
            data = statcast_batter((datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'), 
                                  datetime.now().strftime('%Y-%m-%d'), mlbam_id)
            
            if not data.empty:
                latest_date = data['game_date'].max()
                game_data = data[data['game_date'] == latest_date].copy()
                game_data = game_data[game_data['events'].notna()].sort_index(ascending=True).reset_index(drop=True)

                col1, col2 = st.columns([1.7, 1])

                with col1:
                    # --- 精確繪圖區 ---
                    fig, ax = plt.subplots(figsize=(10, 10), facecolor='none')
                    
                    def tx(x): return (x - 125.5) * 2.5
                    def ty(y): return (205 - y) * 2.2 

                    # 繪製球場
                    ax.plot([0, 63.6, 0, -63.6, 0], [0, 63.6, 127.2, 63.6, 0], color='white', lw=2, zorder=3)
                    ax.plot([0, 250, 0, -250, 0], [0, 250, 440, 250, 0], color='#555555', lw=2, ls='--', zorder=1)

                    for i, row in game_data.iterrows():
                        event_raw = str(row['events'])
                        if event_raw in ['strikeout', 'walk', 'hit_by_pitch']:
                            continue
                            
                        if pd.notna(row['hc_x']):
                            x, y = tx(row['hc_x']), ty(row['hc_y'])
                            if event_raw == 'single': y = min(y, 145)
                            
                            event_name = event_raw.replace('_', ' ').title()
                            color = color_palette.get(event_name, '#FFFFFF')
                            marker = '*' if event_raw == 'home_run' else 'o'
                            
                            ax.scatter(x, y, c=color, s=600 if marker == '*' else 400, 
                                       marker=marker, edgecolors='white', linewidths=1.5, zorder=5)
                            ax.text(x, y, str(i+1), color='black', ha='center', va='center', fontweight='bold', fontsize=11)

                    ax.set_xlim([-420, 420]); ax.set_ylim([-80, 520]); ax.set_aspect('equal'); ax.axis('off')
                    ax.set_title(f"{first_name} {last_name} | {latest_date}", fontsize=24, fontweight='bold', color='white')
                    st.pyplot(fig)

                with col2:
                    st.subheader("📋 打席詳細日誌")
                    records = []
                    for i, row in game_data.iterrows():
                        event = str(row['events']).replace('_', ' ').title()
                        speed = f"{row['launch_speed']:.0f} mph" if pd.notna(row['launch_speed']) else "--"
                        records.append({"打席": i+1, "結果": event, "初速": speed})
                    
                    df_display = pd.DataFrame(records)
                    
                    # --- 關鍵修正：只標色 [打席] 欄位 ---
                    styled_df = df_display.style.apply(style_number_col, axis=1)
                    st.dataframe(styled_df, use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    st.info("💡 顏色說明：打席編號顏色與圖中落點顏色完全對應。")

                st.success(f"Scouting Report for {first_name} {last_name} Generated.")
            else:
                st.warning("查無最近數據。")
        else:
            st.error("查無此球員。")
