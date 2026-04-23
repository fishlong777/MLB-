import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

st.set_page_config(page_title="MLB Scouting Report Pro", layout="wide")

st.title("⚾ MLB 專業球探報告系統 (視覺優化版)")

# 顏色定義 (與圖表同步)
color_map = {
    'Single': '#E74C3C', 'Double': '#E74C3C', 'Triple': '#E74C3C', 
    'Home Run': '#F1C40F', 'Field Out': '#3498DB', 
    'Strikeout': '#95A5A6', 'Walk': '#2ECC71', 'Hit By Pitch': '#2ECC71'
}

def style_row(row):
    """為表格行標色"""
    color = color_map.get(row['結果'], '#FFFFFF')
    return [f'background-color: {color}; color: {"black" if row["結果"] == "Home Run" else "white"}' for _ in row]

with st.sidebar:
    st.header("查詢條件")
    first_name = st.text_input("名字 (First)", "Aaron").strip().capitalize()
    last_name = st.text_input("姓氏 (Last)", "Judge").strip().capitalize()
    submit = st.button("產生報告")

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

                col1, col2 = st.columns([1.5, 1])

                with col1:
                    fig, ax = plt.subplots(figsize=(10, 10), facecolor='white')
                    
                    def tx(x): return (x - 125.5) * 2.4
                    def ty(y): return (205 - y) * 2.4

                    # 繪製球場
                    ax.plot([0, 63.6, 0, -63.6, 0], [0, 63.6, 127.2, 63.6, 0], color='black', lw=2)
                    ax.plot([0, 240, 0, -240, 0], [0, 240, 430, 240, 0], color='#BDC3C7', lw=3, ls='--')

                    for i, row in game_data.iterrows():
                        event_raw = str(row['events'])
                        # 核心邏輯：過濾掉三振與保送，不顯示在圖上
                        if event_raw in ['strikeout', 'walk', 'hit_by_pitch']:
                            continue
                            
                        if pd.notna(row['hc_x']):
                            x, y = tx(row['hc_x']), ty(row['hc_y'])
                            if event_raw in ['double', 'triple', 'home_run'] and y < 155:
                                y = 165 + (np.nan_to_num(row['launch_speed'], nan=80) - 80) * 1.2
                            
                            color = color_map.get(event_raw.replace('_', ' ').title(), '#BDC3C7')
                            marker = '*' if event_raw == 'home_run' else 'o'
                            ax.scatter(x, y, c=color, s=450 if marker == '*' else 300, 
                                       marker=marker, edgecolors='black', zorder=5)
                            ax.text(x, y, str(i+1), color='white' if marker != '*' else 'black', 
                                    ha='center', va='center', fontweight='bold', fontsize=10)

                    ax.set_xlim([-400, 400]); ax.set_ylim([-60, 520]); ax.set_aspect('equal'); ax.axis('off')
                    ax.set_title(f"Spray Chart: {first_name} {last_name}", fontsize=18)
                    st.pyplot(fig)

                with col2:
                    st.subheader(f"📅 {latest_date} 打席明細")
                    records = []
                    for i, row in game_data.iterrows():
                        event = str(row['events']).replace('_', ' ').title()
                        speed = f"{row['launch_speed']:.0f} mph" if pd.notna(row['launch_speed']) else "N/A"
                        records.append({"打席": i+1, "結果": event, "初速": speed})
                    
                    df_display = pd.DataFrame(records)
                    # 使用 Styler 進行表格標色
                    st.dataframe(df_display.style.apply(style_row, axis=1), use_container_width=True)
                    
                    st.info("💡 提示：K 與 BB 僅顯示於表格中，維持球場圖簡潔。")

                st.success(f"已生成 {first_name} {last_name} 的專業球探報表")
            else:
                st.warning("查無最近數據。")
        else:
            st.error("找不到該球員。")
