import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# --- 介面初始化與 CSS 客製化 ---
st.set_page_config(page_title="MLB Pro Visualizer", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #FDFCFB; }
    div[data-testid="stDataFrame"] { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    h1 { color: #34495E; border-bottom: 2px solid #E67E22; padding-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚾ MLB 專業球探報告系統 (精確座標版)")

# --- 專業莫蘭迪配色系統 ---
color_palette = {
    'Single': '#D67D67',      # 柔和磚紅
    'Double': '#E9C46A',      # 芥末黃
    'Triple': '#E9C46A',      # 芥末黃
    'Home Run': '#2A9D8F',    # 森林綠
    'Field Out': '#264653',   # 深海藍
    'Strikeout': '#8D99AE',   # 冷灰色
    'Walk': '#A8DADC',        # 冰藍色
    'Hit By Pitch': '#A8DADC' # 冰藍色
}

def style_row(row):
    bg_color = color_palette.get(row['結果'], '#FFFFFF')
    # 決定文字顏色 (深色背景用白字)
    text_color = 'white' if row['結果'] in ['Field Out', 'Single', 'Home Run'] else '#264653'
    return [f'background-color: {bg_color}; color: {text_color}; font-size: 14px; border-bottom: 1px solid #eee;' for _ in row]

with st.sidebar:
    st.header("⚙️ 數據篩選")
    first_name = st.text_input("First Name", "Nick").strip().capitalize()
    last_name = st.text_input("Last Name", "Kurtz").strip().capitalize()
    submit = st.button("更新報表")

if submit:
    with st.spinner('正在精確計算擊球座標...'):
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
                    
                    # 座標校準關鍵修正：
                    # 調整 ty 比例從 2.4 降至 2.1，防止一壘安打「飛過頭」變外野安打
                    def tx(x): return (x - 125.5) * 2.5
                    def ty(y): return (205 - y) * 2.1 

                    # 繪製球場底圖
                    ax.plot([0, 63.6, 0, -63.6, 0], [0, 63.6, 127.2, 63.6, 0], color='#34495E', lw=2.5, zorder=3) # 內野
                    ax.plot([0, 250, 0, -250, 0], [0, 250, 440, 250, 0], color='#BDC3C7', lw=2, ls='--', zorder=1) # 全壘打牆參考

                    for i, row in game_data.iterrows():
                        event_raw = str(row['events'])
                        if event_raw in ['strikeout', 'walk', 'hit_by_pitch']:
                            continue
                            
                        if pd.notna(row['hc_x']):
                            x, y = tx(row['hc_x']), ty(row['hc_y'])
                            
                            # 強制邏輯：如果是一壘安打，y 座標不能超過內野太遠 (視覺修正)
                            if event_raw == 'single':
                                y = min(y, 145) 
                            
                            color = color_palette.get(event_raw.replace('_', ' ').title(), '#8D99AE')
                            marker = '*' if event_raw == 'home_run' else 'o'
                            
                            ax.scatter(x, y, c=color, s=550 if marker == '*' else 380, 
                                       marker=marker, edgecolors='#FDFCFB', linewidths=1.5, zorder=5)
                            ax.text(x, y, str(i+1), color='white' if event_raw != 'home_run' else 'black', 
                                    ha='center', va='center', fontweight='bold', fontsize=11)

                    ax.set_xlim([-420, 420]); ax.set_ylim([-80, 520]); ax.set_aspect('equal'); ax.axis('off')
                    ax.set_title(f"{first_name} {last_name} | {latest_date}", fontsize=24, fontweight='bold', color='#2C3E50')
                    st.pyplot(fig)

                with col2:
                    st.subheader("📊 每一打席結果明細")
                    records = []
                    for i, row in game_data.iterrows():
                        event = str(row['events']).replace('_', ' ').title()
                        speed = f"{row['launch_speed']:.0f} mph" if pd.notna(row['launch_speed']) else "--"
                        records.append({"打席": i+1, "結果": event, "擊球初速": speed})
                    
                    df_display = pd.DataFrame(records)
                    # 隱藏左側索引，改用樣式化的 DataFrame
                    st.dataframe(df_display.style.apply(style_row, axis=1), use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    st.info("💡 **修正說明**：已調校 y 軸渲染比例，確保一壘安打落點維持在內外野邊界內。")

                st.success(f"已生成 {first_name} 的專業球探報告")
            else:
                st.warning("該球員最近無數據。")
        else:
            st.error("查無此球員，請確認英文姓名拼寫。")
