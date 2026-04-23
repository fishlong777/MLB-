import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# --- 介面設定：強制明亮模式與標題優化 ---
st.set_page_config(page_title="MLB Hitting Chart", layout="wide")

st.markdown("""
    <style>
    /* 強制明亮背景 */
    .main { background-color: #FFFFFF !important; }
    /* 移除標題後方的奇怪符號 */
    .stMarkdown h1 a { display: none !important; }
    .stMarkdown h1 { color: #1A1A1A !important; font-family: 'Microsoft JhengHei', sans-serif; }
    /* 表格樣式優化 */
    div[data-testid="stDataFrame"] td { font-size: 15px !important; color: black !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("MLB 打者擊球落點圖")

# --- 顏色定義 (鮮豔高對比) ---
color_palette = {
    'Single': '#FF4B4B', 'Double': '#FFAA00', 'Triple': '#FFAA00', 
    'Home Run': '#00C9A7', 'Field Out': '#3498DB', 
    'Strikeout': '#95A5A6', 'Walk': '#2ECC71', 'Hit By Pitch': '#2ECC71'
}

def style_number_col(row):
    color = color_palette.get(row['結果'], 'white')
    # 打席數字列標色，其餘純白底
    return [f'background-color: {color}; color: black; font-weight: bold; text-align: center;' 
            if name == '打席' else 'background-color: white; color: black;' for name in row.index]

with st.sidebar:
    st.header("選手查詢")
    first_name = st.text_input("First Name", "Nick").strip().capitalize()
    last_name = st.text_input("Last Name", "Kurtz").strip().capitalize()
    submit = st.button("更新落點圖")

if submit:
    with st.spinner('正在精確校準球場比例...'):
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
                    # --- 球場比例精確校準 (白底版) ---
                    fig, ax = plt.subplots(figsize=(10, 10), facecolor='white')
                    
                    # 重新計算倍率，讓內野菱形向外擴張
                    def tx(x): return (x - 125.5) * 3.5
                    def ty(y): return (205 - y) * 3.5

                    # 繪製加大的內野菱形 (白色實線要出去一點)
                    # 頂點座標放大到 100 單位，讓內野看起來更寬廣合理
                    ax.plot([0, 100, 0, -100, 0], [0, 100, 200, 100, 0], color='#2c3e50', lw=4, zorder=3)
                    
                    # 繪製全壘打牆參考 (虛線往內收縮，避免外野過大)
                    ax.plot([0, 260, 0, -260, 0], [0, 260, 440, 260, 0], color='#bdc3c7', lw=2, ls='--', zorder=1)

                    for i, row in game_data.iterrows():
                        event_raw = str(row['events'])
                        if event_raw in ['strikeout', 'walk', 'hit_by_pitch']: continue
                            
                        if pd.notna(row['hc_x']):
                            x, y = tx(row['hc_x']), ty(row['hc_y'])
                            
                            # 修正一壘安打落點落入外野的問題：限制高度
                            if event_raw == 'single': y = min(y, 220)
                            
                            color = color_palette.get(event_raw.replace('_', ' ').title(), '#95A5A6')
                            marker = '*' if event_raw == 'home_run' else 'o'
                            
                            ax.scatter(x, y, c=color, s=700 if marker == '*' else 450, 
                                       marker=marker, edgecolors='black', linewidths=1.2, zorder=5)
                            ax.text(x, y, str(i+1), color='black' if marker == '*' else 'white', 
                                    ha='center', va='center', fontweight='bold', fontsize=11)

                    # 裁切顯示範圍：減少頂部空白，讓內野佔據視覺中心
                    ax.set_xlim([-420, 420]); ax.set_ylim([-50, 480]); ax.set_aspect('equal'); ax.axis('off')
                    ax.set_title(f"{first_name} {last_name} | {latest_date}", fontsize=24, fontweight='bold', color='#1A1A1A')
                    st.pyplot(fig)

                with col2:
                    st.subheader("📋 打席結果明細")
                    records = [{"打席": i+1, "結果": str(row['events']).replace('_', ' ').title(), 
                                "初速": f"{row['launch_speed']:.0f} mph" if pd.notna(row['launch_speed']) else "--"} 
                               for i, row in game_data.iterrows()]
                    
                    df_display = pd.DataFrame(records)
                    st.dataframe(df_display.style.apply(style_number_col, axis=1), use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    st.info("💡 **比例修正**：已將內野菱形向外擴張，外野比例調整為合理範圍。")

                st.success(f"落點圖已更新")
            else: st.warning("無數據。")
        else: st.error("找不到球員。")
