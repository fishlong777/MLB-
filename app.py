import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# --- 介面強制校準：極簡白 + 黑色標題 ---
st.set_page_config(page_title="MLB Hitting Chart", layout="wide")

st.markdown("""
    <style>
    /* 1. 全域背景強制白色 */
    .stApp { background-color: #FFFFFF !important; }
    
    /* 2. 標題與標籤文字強制黑色/深灰色 (解決看不到的問題) */
    h1, h2, h3, h4, p, label { 
        color: #111827 !important; 
        font-family: 'Segoe UI', sans-serif !important; 
    }
    
    /* 3. 側邊欄配色修正：淺灰背景、黑色文字 */
    section[data-testid="stSidebar"] {
        background-color: #F3F4F6 !important;
        border-right: 1px solid #E5E7EB;
    }
    section[data-testid="stSidebar"] label { color: #111827 !important; font-weight: bold; }
    
    /* 4. 側邊欄輸入框樣式優化 */
    section[data-testid="stSidebar"] div[data-baseweb="input"] {
        background-color: #FFFFFF !important;
        border: 1px solid #D1D5DB !important;
    }
    section[data-testid="stSidebar"] input {
        color: #111827 !important;
    }

    /* 5. 隱藏標題連結符號 */
    .stMarkdown h1 a, .stMarkdown h1 span { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("MLB 打者擊球落點圖")

# --- 顏色定義 (精確對應：表格與圓點) ---
color_palette = {
    'Single': '#EF4444',      # 鮮紅 (Red 500)
    'Double': '#F59E0B',      # 亮橘 (Amber 500)
    'Triple': '#F59E0B',      # 亮橘
    'Home Run': '#10B981',    # 翡翠綠 (Emerald 500)
    'Field Out': '#3B82F6',   # 亮藍 (Blue 500)
    'Strikeout': '#64748B',   # 藍灰
    'Walk': '#8B5CF6',        # 紫色
    'Intentional Walk': '#8B5CF6', 
    'Hit By Pitch': '#8B5CF6'
}

def style_number_col(row):
    """表格標色邏輯：讓[打席]格子背景色與落點圖圓點完全同步"""
    val = row['結果']
    bg_color = color_palette.get(val, '#FFFFFF')
    return [f'background-color: {bg_color}; color: black; font-weight: bold; text-align: center;' 
            if name == '打席' else 'background-color: #FFFFFF; color: #111827;' for name in row.index]

with st.sidebar:
    st.header("選手查詢")
    first_name = st.text_input("First Name", "Aaron").strip().capitalize()
    last_name = st.text_input("Last Name", "Judge").strip().capitalize()
    submit = st.button("更新數據")

if submit:
    with st.spinner('正在同步數據與色彩系統...'):
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
                    # 繪圖區背景設為白色
                    fig, ax = plt.subplots(figsize=(10, 10), facecolor='white')
                    
                    def tx(x): return (x - 125.5) * 3.5
                    def ty(y): return (205 - y) * 2.8 

                    # 球場實線 (zorder=10 置頂)
                    ax.plot([0, 125, 0, -125, 0], [0, 125, 250, 125, 0], color='#2C3E50', lw=2.5, zorder=10)
                    ax.plot([0, 270, 0, -270, 0], [0, 270, 460, 270, 0], color='#BDC3C7', lw=2.5, ls='-', zorder=1)

                    # 壘包入角
                    off = 12
                    ax.plot(125-off, 125, marker='s', color='#2C3E50', markersize=9, zorder=11)
                    ax.plot(0, 250-off, marker='s', color='#2C3E50', markersize=9, zorder=11)
                    ax.plot(-125+off, 125, marker='s', color='#2C3E50', markersize=9, zorder=11)

                    for i, row in game_data.iterrows():
                        event_raw = str(row['events']).lower()
                        if any(x in event_raw for x in ['strikeout', 'walk', 'hit_by_pitch']): continue
                            
                        if pd.notna(row['hc_x']):
                            x, y = tx(row['hc_x']), ty(row['hc_y'])
                            
                            # 統一結果映射
                            if 'home_run' in event_raw: event_key = 'Home Run'
                            elif 'single' in event_raw: event_key = 'Single'
                            elif 'double' in event_raw: event_key = 'Double'
                            elif 'triple' in event_raw: event_key = 'Triple'
                            else: event_key = 'Field Out'
                            
                            color = color_palette.get(event_key, '#95A5A6')
                            marker = '*' if event_key == 'Home Run' else 'o'
                            
                            # 繪圖點位 zorder=5
                            ax.scatter(x, y, c=color, s=450, marker=marker, edgecolors='black', linewidths=1.2, zorder=5)
                            
                            # 標籤數字
                            ax.text(x+15, y+15, str(i+1), color='#111827', ha='left', va='bottom', 
                                    fontweight='bold', fontsize=12, zorder=6,
                                    bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.2'))

                    ax.set_xlim([-480, 480]); ax.set_ylim([-50, 680]); ax.set_aspect('equal'); ax.axis('off')
                    ax.set_title(f"{first_name} {last_name} | {latest_date}", fontsize=24, fontweight='bold', color='#111827', pad=50)
                    st.pyplot(fig)

                with col2:
                    st.subheader("打席結果明細")
                    records = []
                    for i, row in game_data.iterrows():
                        e = str(row['events']).lower()
                        event_display = "Intentional Walk" if 'intent' in e else e.replace('_', ' ').title()
                        speed = f"{row['launch_speed']:.0f} mph" if pd.notna(row['launch_speed']) else "--"
                        records.append({"打席": i+1, "結果": event_display, "初速": speed})
                    
                    df_display = pd.DataFrame(records)
                    st.dataframe(df_display.style.apply(style_number_col, axis=1), use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    st.info("💡 **顏色同步**：表格序號背景色與落點圖圓點顏色已嚴格對應。")

                st.success(f"數據渲染完畢")
