import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# --- 介面配置：極簡白專業風 ---
st.set_page_config(page_title="MLB Hitting Chart", layout="wide")

st.markdown("""
    <style>
    /* 1. 整體背景回歸純白 */
    .stApp { background-color: #FFFFFF !important; }
    
    /* 2. 標題與字體顏色鎖定 (深灰/黑) */
    h1 { 
        color: #111827 !important; 
        font-family: 'Segoe UI', sans-serif; 
        font-weight: 800; 
        border-bottom: 2px solid #E5E7EB;
        padding-bottom: 10px;
    }
    .stMarkdown h1 a, .stMarkdown h1 span { display: none !important; }
    
    /* 3. 側邊欄背景改為極簡淺灰 */
    section[data-testid="stSidebar"] {
        background-color: #F9FAFB !important;
        border-right: 1px solid #E5E7EB;
    }
    
    /* 4. 表格陰影與邊框，營造截圖中的浮空感 */
    div[data-testid="stDataFrame"] {
        background-color: #FFFFFF !important;
        border: 1px solid #F3F4F6;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("MLB 打者擊球落點圖")

# --- 顏色定義 (鮮豔直觀，用於連動表格與圓點) ---
color_palette = {
    'Single': '#FF4B4B',      # 紅
    'Double': '#FFAA00',      # 橘
    'Triple': '#FFAA00',      # 橘
    'Home Run': '#00C9A7',    # 亮青
    'Field Out': '#3498DB',   # 藍
    'Strikeout': '#95A5A6',   # 灰
    'Walk': '#A78BFA',        # 紫
    'Intentional Walk': '#A78BFA', 
    'Hit By Pitch': '#A78BFA'
}

def style_number_col(row):
    """表格標色邏輯：讓[打席]格子的顏色與落點圖圓點完全一致"""
    color = color_palette.get(row['結果'], '#FFFFFF')
    return [f'background-color: {color}; color: black; font-weight: bold; text-align: center;' 
            if name == '打席' else 'background-color: white; color: #111827;' for name in row.index]

with st.sidebar:
    st.header("🔍 選手查詢")
    first_name = st.text_input("First Name", "Aaron").strip().capitalize()
    last_name = st.text_input("Last Name", "Judge").strip().capitalize()
    submit = st.button("更新數據")

if submit:
    with st.spinner('正在同步落點與表格顏色...'):
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
                    # 使用白底繪圖，與介面融合
                    fig, ax = plt.subplots(figsize=(10, 10), facecolor='white')
                    
                    def tx(x): return (x - 125.5) * 3.5
                    def ty(y): return (205 - y) * 2.8 

                    # 球場實線 (中灰色)
                    line_color = '#BDC3C7'
                    ax.plot([0, 125, 0, -125, 0], [0, 125, 250, 125, 0], color='#2C3E50', lw=2, zorder=3)
                    ax.plot([0, 270, 0, -270, 0], [0, 270, 460, 270, 0], color=line_color, lw=2, ls='-', zorder=1)

                    # 壘包位置 (縮進內角)
                    off = 12
                    ax.plot(125-off, 125, marker='s', color='#2C3E50', markersize=8, zorder=11)
                    ax.plot(0, 250-off, marker='s', color='#2C3E50', markersize=8, zorder=11)
                    ax.plot(-125+off, 125, marker='s', color='#2C3E50', markersize=8, zorder=11)

                    for i, row in game_data.iterrows():
                        event_raw = str(row['events']).lower()
                        if any(x in event_raw for x in ['strikeout', 'walk', 'hit_by_pitch']): continue
                            
                        if pd.notna(row['hc_x']):
                            x, y = tx(row['hc_x']), ty(row['hc_y'])
                            if 'home_run' not in event_raw: y = min(y, 450)
                            
                            # 判定結果類型
                            event_key = "Home Run" if 'home_run' in event_raw else "Field Out"
                            if 'single' in event_raw: event_key = "Single"
                            elif 'double' in event_raw: event_key = "Double"
                            elif 'triple' in event_raw: event_key = "Triple"
                            
                            color = color_palette.get(event_key, '#95A5A6')
                            marker = '*' if 'home_run' in event_raw else 'o'
                            
                            # 繪製點位
                            ax.scatter(x, y, c=color, s=450, marker=marker, edgecolors='black', linewidths=1, zorder=5)
                            # 數字標籤標註在旁，確保顏色對應直觀
                            ax.text(x+15, y+15, str(i+1), color='#111827', ha='left', va='bottom', 
                                    fontweight='bold', fontsize=12, zorder=6,
                                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.2'))

                    ax.set_xlim([-480, 480]); ax.set_ylim([-50, 680]); ax.set_aspect('equal'); ax.axis('off')
                    ax.set_title(f"{first_name} {last_name} | {latest_date}", fontsize=24, fontweight='bold', color='#111827', pad=50)
                    st.pyplot(fig)

                with col2:
                    st.subheader("📋 打席結果明細")
                    records = []
                    for i, row in game_data.iterrows():
                        e = str(row['events']).lower()
                        # 拼寫校正
                        event_display = "Intentional Walk" if 'intent' in e else e.replace('_', ' ').title()
                        speed = f"{row['launch_speed']:.0f} mph" if pd.notna(row['launch_speed']) else "--"
                        records.append({"打席": i+1, "結果": event_display, "初速": speed})
                    
                    df_display = pd.DataFrame(records)
                    # 顏色連動核心：透過 Styler 讓打席數字背景 = 落點圓圈顏色
                    st.dataframe(df_display.style.apply(style_number_col, axis=1), use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    st.info("💡 **顏色同步**：表格序號顏色與落點圖圓點完全對應，方便快速比對。")

                st.success(f"同步完成")
            else: st.warning("無數據。")
        else: st.error("找不到球員。")
