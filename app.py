import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# --- 網頁配置與明亮模式設定 ---
st.set_page_config(page_title="MLB Hitting Chart", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #FFFFFF !important; }
    h1 { color: #2C3E50 !important; font-family: 'Arial Black', sans-serif; }
    div[data-testid="stDataFrame"] td { font-size: 15px !important; border-bottom: 1px solid #f0f0f0 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚾ MLB 打者擊球落點圖")

# --- 顏色定義 (高對比鮮明版) ---
color_palette = {
    'Single': '#E74C3C', 'Double': '#F39C12', 'Triple': '#F39C12', 
    'Home Run': '#27AE60', 'Field Out': '#2980B9', 
    'Strikeout': '#95A5A6', 'Walk': '#8E44AD', 'Hit By Pitch': '#8E44AD'
}

def style_number_col(row):
    """只針對 [打席] 欄位進行與落點圖同步的標色"""
    bg_color = color_palette.get(row['結果'], '#FFFFFF')
    # 數字顏色設定：全壘打用亮白，其餘深色用白，淺色用黑
    text_color = 'white' if row['結果'] in ['Single', 'Home Run', 'Field Out', 'Walk'] else 'black'
    return [f'background-color: {bg_color}; color: {text_color}; font-weight: bold; text-align: center;' 
            if name == '打席' else 'background-color: white; color: black;' for name in row.index]

with st.sidebar:
    st.header("🔍 選手查詢")
    first_name = st.text_input("First Name", "Nick").strip().capitalize()
    last_name = st.text_input("Last Name", "Kurtz").strip().capitalize()
    submit = st.button("更新落點圖")

if submit:
    with st.spinner('正在精確繪製落點...'):
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
                    # --- 球場比例精確校準 ---
                    fig, ax = plt.subplots(figsize=(10, 10), facecolor='white')
                    
                    # 重新定義轉換公式，放大內野
                    def tx(x): return (x - 125.5) * 2.8
                    def ty(y): return (199 - y) * 2.8

                    # 繪製標準比例內野 (壘間距離 90ft 比例轉換)
                    # 菱形頂點：本壘(0,0), 二壘(0, 127.3), 一壘(63.6, 63.6), 三壘(-63.6, 63.6)
                    ax.plot([0, 63.6, 0, -63.6, 0], [0, 63.6, 127.2, 63.6, 0], color='#34495E', lw=3.5, zorder=3)
                    
                    # 繪製參考全壘打牆 (適度縮小外野視覺範圍)
                    ax.plot([0, 240, 0, -240, 0], [0, 240, 420, 240, 0], color='#BDC3C7', lw=2, ls='--', zorder=1)

                    for i, row in game_data.iterrows():
                        event_raw = str(row['events'])
                        if event_raw in ['strikeout', 'walk', 'hit_by_pitch']: continue
                            
                        if pd.notna(row['hc_x']):
                            x, y = tx(row['hc_x']), ty(row['hc_y'])
                            
                            # 一壘安打高度物理過濾：不應超過淺外野
                            if event_raw == 'single': y = min(y, 160)
                            
                            color = color_palette.get(event_raw.replace('_', ' ').title(), '#95A5A6')
                            marker = '*' if event_raw == 'home_run' else 'o'
                            
                            ax.scatter(x, y, c=color, s=700 if marker == '*' else 450, 
                                       marker=marker, edgecolors='black', linewidths=1.2, zorder=5)
                            ax.text(x, y, str(i+1), color='white' if marker != '*' else 'black', 
                                    ha='center', va='center', fontweight='bold', fontsize=11)

                    # 縮減顯示邊界，讓內野看起來更大
                    ax.set_xlim([-400, 400]); ax.set_ylim([-60, 480]); ax.set_aspect('equal'); ax.axis('off')
                    ax.set_title(f"{first_name} {last_name} | {latest_date}", fontsize=22, fontweight='bold', color='#2C3E50')
                    st.pyplot(fig)

                with col2:
                    st.subheader("📅 打席結果明細")
                    records = [{"打席": i+1, "結果": str(row['events']).replace('_', ' ').title(), 
                                "初速": f"{row['launch_speed']:.0f} mph" if pd.notna(row['launch_speed']) else "--"} 
                               for i, row in game_data.iterrows()]
                    
                    df_display = pd.DataFrame(records)
                    # 僅針對「打席」數字列標色
                    st.dataframe(df_display.style.apply(style_number_col, axis=1), use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    st.caption("📍 **比例說明**：已調大內野菱形占比，並校準外野扇區。數字顏色與落點圖對應。")

                st.success(f"已更新為【MLB 打者擊球落點圖】")
            else: st.warning("近 30 天無比賽數據。")
        else: st.error("找不到球員，請檢查英文拼寫。")
