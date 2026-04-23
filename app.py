import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# 網頁標題設定
st.set_page_config(page_title="MLB Scouting Report", layout="wide")

st.title("⚾ MLB 專業球探報告系統 (Cloud Version)")
st.write("輸入球員姓名，即時產出最近 30 天的擊球分佈圖。")

# 側邊欄輸入
with st.sidebar:
    st.header("查詢條件")
    first_name = st.text_input("名字 (First Name)", "Aaron").capitalize()
    last_name = st.text_input("姓氏 (Last Name)", "Judge").capitalize()
    submit = st.button("產生報告")

if submit:
    with st.spinner('正在從大聯盟官方資料庫抓取數據...'):
        player_info = playerid_lookup(last_name, first_name)
        
        if not player_info.empty:
            mlbam_id = player_info.key_mlbam.values[0]
            data = statcast_batter((datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'), 
                                  datetime.now().strftime('%Y-%m-%d'), mlbam_id)
            
            if not data.empty:
                latest_date = data['game_date'].max()
                game_data = data[data['game_date'] == latest_date].copy()
                game_data = game_data[game_data['events'].notna()].sort_index(ascending=True).reset_index(drop=True)

                # --- 繪圖邏輯開始 ---
                fig, ax = plt.subplots(figsize=(10, 10), facecolor='white')
                
                def tx(x): return (x - 125.5) * 2.4
                def ty(y): return (205 - y) * 2.4

                ax.plot([0, 63.6, 0, -63.6, 0], [0, 63.6, 127.2, 63.6, 0], color='black', lw=1.5)
                ax.plot([0, 240, 0, -240, 0], [0, 240, 430, 240, 0], color='#BDC3C7', lw=3, ls='--')

                color_map = {'single': '#E74C3C', 'double': '#E74C3C', 'triple': '#E74C3C', 
                             'home_run': '#F1C40F', 'field_out': '#3498DB', 'strikeout': '#95A5A6', 'walk': '#2ECC71'}

                for i, row in game_data.iterrows():
                    if pd.notna(row['hc_x']):
                        x, y = tx(row['hc_x']), ty(row['hc_y'])
                        event_raw = str(row['events'])
                        color = color_map.get(event_raw, '#BDC3C7')
                        ax.scatter(x, y, c=color, s=300, edgecolors='black', zorder=5)
                        ax.text(x, y, str(i+1), color='white', ha='center', va='center', fontweight='bold')

                ax.set_xlim([-400, 400]); ax.set_ylim([-50, 500]); ax.set_aspect('equal'); ax.axis('off')
                ax.set_title(f"{first_name} {last_name} - {latest_date}", fontsize=20)
                
                # 在網頁顯示圖表
                st.pyplot(fig)
                # --- 繪圖邏輯結束 ---
                
                st.table(game_data[['events', 'launch_speed', 'launch_angle']].dropna())
            else:
                st.warning("最近 30 天無比賽數據。")
        else:
            st.error("找不到該球員，請檢查拼字。")
