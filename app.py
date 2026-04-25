import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# --- 徹底鎖定視覺樣式 ---
st.set_page_config(page_title="MLB Hitting Chart", layout="wide")

st.markdown("""
    <style>
    /* 1. 背景改為舒服的深藍灰色，絕非全黑 */
    .stApp {
        background-color: #1E293B !important;
    }
    
    /* 2. 標題文字強制白色，並移除所有連結符號 */
    h1 { 
        color: #FFFFFF !important; 
        font-family: 'Segoe UI', sans-serif; 
        font-weight: 800; 
        border-bottom: 2px solid #3B82F6;
    }
    .stMarkdown h1 a, .stMarkdown h1 span { display: none !important; }
    
    /* 3. 側邊欄配色統一 */
    section[data-testid="stSidebar"] {
        background-color: #0F172A !important;
    }
    section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p {
        color: #F8FAFC !important;
    }
    
    /* 4. 表格深色化優化 */
    div[data-testid="stDataFrame"] {
        background-color: #334155 !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("MLB 打者擊球落點圖")

# --- 顏色定義 (鮮豔高對比) ---
color_palette = {
    'Single': '#F87171', 'Double': '#FB923C', 'Triple': '#FBBF24', 
    'Home Run': '#34D399', 'Field Out': '#60A5FA', 
    'Strikeout': '#94A3B8', 'Walk': '#A78BFA', 'Intentional Walk': '#A78BFA', 'Hit By Pitch': '#A78BFA'
}

def style_number_col(row):
    color = color_palette.get(row['結果'], '#FFFFFF')
    return [f'background-color: {color}; color: black; font-weight: bold; text-align: center;' 
            if name == '打席' else 'background-color: #1E293B; color: white;' for name in row.index]

with st.sidebar:
    st.header("🔍 選手查詢")
    first_name = st.text_input("First Name", "Aaron").strip().capitalize()
    last_name = st.text_input("Last Name", "Judge").strip().capitalize()
    submit = st.button("更新數據")

if submit:
    with st.spinner('正在精確校準座標與配色...'):
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
                    fig, ax = plt.subplots(figsize=(10, 10), facecolor='none')
                    
                    # 重新計算倍率，讓內野菱形與點位在畫面中更和諧
                    def tx(x): return (x - 125.5) * 3.2
                    def ty(y): return (205 - y) * 2.2 

                    # 球場實線 (淡藍灰色)
                    ax.plot([0, 125, 0, -125, 0], [0, 125, 250, 125, 0], color='#94A3B8', lw=2.5, zorder=3)
                    ax.plot([0, 270, 0, -270, 0], [0, 270, 460, 270, 0], color='#475569', lw=2.5, ls='-', zorder=1)

                    # 【關鍵修正】：壘包方塊縮進 90 度「角裡面」 (偏移 12 單位)
                    off = 12
                    ax.plot(125-off, 125, marker='s', color='#F8FAFC', markersize=9, zorder=11) # 一壘往內
                    ax.plot(0, 250-off, marker='s', color='#F8FAFC', markersize=9, zorder=11)   # 二壘往下
                    ax.plot(-125+off, 125, marker='s', color='#F8FAFC', markersize=9, zorder=11) # 三壘往內

                    for i, row in game_data.iterrows():
                        event_raw = str(row['events']).lower()
                        if any(x in event_raw for x in ['strikeout', 'walk', 'hit_by_pitch']): continue
                            
                        if pd.notna(row['hc_x']):
                            x, y = tx(row['hc_x']), ty(row['hc_y'])
                            if 'home_run' not in event_raw: y = min(y, 450)
                            
                            event_key = "Home Run" if 'home_run' in event_raw else "Field Out"
                            if 'single' in event_raw: event_key = "Single"
                            elif 'double' in event_raw: event_key = "Double"
                            elif 'triple' in event_raw: event_key = "Triple"
                            
                            color = color_palette.get(event_key, '#94A3B8')
                            marker = '*' if 'home_run' in event_raw else 'o'
                            
                            ax.scatter(x, y, c=color, s=450, marker=marker, edgecolors='black', linewidths=1.2, zorder=5)
                            # 數字標籤標註在旁，避免遮擋
                            ax.text(x+15, y+15, str(i+1), color='#F8FAFC', ha='left', va='bottom', 
                                    fontweight='bold', fontsize=12, zorder=6,
                                    bbox=dict(facecolor='#0F172A', alpha=0.6, edgecolor='none', boxstyle='round,pad=0.2'))

                    ax.set_xlim([-450, 450]); ax.set_ylim([-50, 600]); ax.set_aspect('equal'); ax.axis('off')
                    ax.set_title(f"{first_name} {last_name} | {latest_date}", fontsize=24, fontweight='bold', color='#FFFFFF', pad=40)
                    st.pyplot(fig)

                with col2:
                    st.subheader("📋 打席結果明細")
                    records = []
                    for i, row in game_data.iterrows():
                        e = str(row['events']).lower()
                        event_display = "Intentional Walk" if 'intent' in e else e.replace('_', ' ').title()
                        speed = f"{row['launch_speed']:.0f} mph" if pd.notna(row['launch_speed']) else "--"
                        records.append({"打席": i+1, "結果": event_display, "初速": speed})
                    
                    df_display = pd.DataFrame(records)
                    st.dataframe(df_display.style.apply(style_number_col, axis=1), use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    st.info("💡 **視覺修正**：背景調整為深藍灰，壘包已強制縮進內野角內。")

                st.success(f"數據渲染完成")
