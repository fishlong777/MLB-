import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

st.set_page_config(page_title="MLB Scouting Report Pro", layout="wide")

st.title("⚾ MLB 專業球探報告系統 (進階網頁版)")

with st.sidebar:
    st.header("查詢條件")
    first_name = st.text_input("名字 (First)", "Aaron").strip().capitalize()
    last_name = st.text_input("姓氏 (Last)", "Judge").strip().capitalize()
    submit = st.button("產生報告")

if submit:
    with st.spinner('正在分析 Statcast 數據...'):
        player_info = playerid_lookup(last_name, first_name)
        
        if not player_info.empty:
            mlbam_id = player_info.key_mlbam.values[0]
            data = statcast_batter((datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'), 
                                  datetime.now().strftime('%Y-%m-%d'), mlbam_id)
            
            if not data.empty:
                latest_date = data['game_date'].max()
                # 抓取該場比賽所有結果 (包含 BB/K)
                game_data = data[data['game_date'] == latest_date].copy()
                game_data = game_data[game_data['events'].notna()].sort_index(ascending=True).reset_index(drop=True)

                col1, col2 = st.columns([2, 1])

                with col1:
                    fig, ax = plt.subplots(figsize=(10, 10), facecolor='white')
                    
                    def tx(x): return (x - 125.5) * 2.4
                    def ty(y): return (205 - y) * 2.4

                    # 繪製球場
                    ax.plot([0, 63.6, 0, -63.6, 0], [0, 63.6, 127.2, 63.6, 0], color='black', lw=2)
                    ax.plot([0, 240, 0, -240, 0], [0, 240, 430, 240, 0], color='#BDC3C7', lw=3, ls='--')

                    # 顏色地圖
                    color_map = {
                        'single': '#E74C3C', 'double': '#E74C3C', 'triple': '#E74C3C', 
                        'home_run': '#F1C40F', 'field_out': '#3498DB', 
                        'strikeout': '#95A5A6', 'walk': '#2ECC71', 'hit_by_pitch': '#2ECC71'
                    }

                    for i, row in game_data.iterrows():
                        event_raw = str(row['events'])
                        color = color_map.get(event_raw, '#BDC3C7')
                        pa_num = i + 1
                        
                        # 判斷是否有擊球座標
                        if pd.notna(row['hc_x']):
                            x, y = tx(row['hc_x']), ty(row['hc_y'])
                            # 長打視覺位移修正
                            if event_raw in ['double', 'triple', 'home_run'] and y < 155:
                                y = 165 + (np.nan_to_num(row['launch_speed'], nan=80) - 80) * 1.2
                        else:
                            # 三振、保送放在本壘板附近 (稍微錯開避免重疊)
                            x, y = (i % 3 - 1) * 5, -15 + (i // 3) * -5
                        
                        marker = '*' if event_raw == 'home_run' else 'o'
                        ax.scatter(x, y, c=color, s=400 if marker == '*' else 250, 
                                   marker=marker, edgecolors='black', zorder=5)
                        ax.text(x, y, str(pa_num), color='white' if marker != '*' else 'black', 
                                ha='center', va='center', fontweight='bold', fontsize=9)

                    ax.set_xlim([-400, 400]); ax.set_ylim([-80, 520]); ax.set_aspect('equal'); ax.axis('off')
                    st.pyplot(fig)

                with col2:
                    st.subheader(f"📅 {latest_date} 比賽日誌")
                    # 整理每打席結果清單
                    records = []
                    for i, row in game_data.iterrows():
                        event = str(row['events']).replace('_', ' ').title()
                        speed = f"{row['launch_speed']:.0f} mph" if pd.notna(row['launch_speed']) else "N/A"
                        records.append({"打席": i+1, "結果": event, "初速": speed})
                    
                    st.table(pd.DataFrame(records))

                st.success(f"已更新 {first_name} {last_name} 的完整數據（含 BB/K 紀錄）")
            else:
                st.warning("查無最近數據。")
        else:
            st.error("找不到該球員。")
