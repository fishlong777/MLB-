import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# --- 介面徹底美化與雜質清理 ---
st.set_page_config(page_title="MLB Hitting Chart", layout="wide")

st.markdown("""
    <style>
    /* 清除標題後方的奇怪鏈結圖示 */
    .element-container:has(#mlb) a { display: none; }
    .stMarkdown h1 a { display: none !important; }
    
    /* 強制整體視覺對比 */
    .main { background-color: #0E1117 !important; }
    h1 { color: #FFFFFF !important; font-family: 'Microsoft JhengHei', sans-serif; font-weight: 800; }
    h2, h3, p { color: #E0E0E0 !important; }
    
    /* 表格字體優化 */
    div[data-testid="stDataFrame"] td { font-size: 16px !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("MLB 打者擊球落點圖")

# --- 配色方案 (鮮豔高對比) ---
color_palette = {
    'Single': '#FF4B4B', 'Double': '#FFAA00', 'Triple': '#FFAA00', 
    'Home Run': '#00F5D4', 'Field Out': '#1B9CE5', 
    'Strikeout': '#6C757D', 'Walk': '#99FF77', 'Hit By Pitch': '#99FF77'
}

def style_number_col(row):
    color = color_palette.get(row['結果'], '#FFFFFF')
    return [f'background-color: {color}; color: black; font-weight: bold; text-align: center;' 
            if name == '打席' else 'background-color: #1A1C24; color: white;' for name in row.index]

with st.sidebar:
    st.header("🔍 選手查詢")
    first_name = st.text_input("First Name", "Nick").strip().capitalize()
    last_name = st.text_input("Last Name", "Kurtz").strip().capitalize()
    submit = st.button("更新數據")

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
                    # --- 球場幾何重新定義 ---
                    fig, ax = plt.subplots(figsize=(10, 10), facecolor='none')
                    
                    # 重新計算轉換公式，讓本壘靠近底部，菱形放大
                    def tx(x): return (x - 125.5) * 3.2
                    def ty(y): return (205 - y) * 3.2

                    # 繪製加大的內野菱形 (壘間距離感優化)
                    # 座標：本壘(0,0), 一壘(85,85), 二壘(0,170), 三壘(-85,85)
                    ax.plot([0, 85, 0, -85, 0], [0, 85, 170, 85, 0], color='#FFFFFF', lw=3.5, zorder=3)
                    
                    # 繪製全壘打牆參考 (稍微向內收縮以填滿畫面)
                    ax.plot([0, 280, 0, -280, 0], [0, 280, 480, 280, 0], color='#4A4E69', lw=2, ls='--', zorder=1)

                    for i, row in game_data.iterrows():
                        event_raw = str(row['events'])
                        if event_raw in ['strikeout', 'walk', 'hit_by_pitch']: continue
                            
                        if pd.notna(row['hc_x']):
                            x, y = tx(row['hc_x']), ty(row['hc_y'])
                            
                            # 嚴格過濾一壘安打：必須在內野周邊
                            if event_raw == 'single': y = min(y, 190)
                            
                            color = color_palette.get(event_raw.replace('_', ' ').title(), '#6C757D')
                            marker = '*' if event_raw == 'home_run' else 'o'
                            
                            ax.scatter(x, y, c=color, s=750 if marker == '*' else 500, 
                                       marker=marker, edgecolors='white', linewidths=1.5, zorder=5)
                            ax.text(x, y, str(i+1), color='black', ha='center', va='center', fontweight='bold', fontsize=12)

                    # 裁剪畫面範圍，讓內野成為視覺中心
                    ax.set_xlim([-450, 450]); ax.set_ylim([-50, 500]); ax.set_aspect('equal'); ax.axis('off')
                    
                    # 標題優化
                    ax.set_title(f"{first_name} {last_name} | {latest_date}", fontsize=26, fontweight='bold', color='white', pad=20)
                    st.pyplot(fig)

                with col2:
                    st.subheader("打席結果明細")
                    records = [{"打席": i+1, "結果": str(row['events']).replace('_', ' ').title(), 
                                "初速": f"{row['launch_speed']:.0f} mph" if pd.notna(row['launch_speed']) else "--"} 
                               for i, row in game_data.iterrows()]
                    
                    df_display = pd.DataFrame(records)
                    st.dataframe(df_display.style.apply(style_number_col, axis=1), use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    st.info("📍 **校準完畢**：內野壘包已放大至合理比例，名字旁的連結圖示已移除。")

                st.success(f"數據加載完成")
            else: st.warning("無數據。")
        else: st.error("找不到球員。")
