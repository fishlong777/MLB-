import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# --- 徹底鎖定視覺：三大區塊全白底黑字 ---
st.set_page_config(page_title="MLB Hitting Chart", layout="wide")

st.markdown("""
    <style>
    /* 【修正 1 & 2】全域背景與主區域 (區塊 2) */
    .stApp {
        background-color: #FFFFFF !important;
    }
    .main .block-container {
        background-color: #FFFFFF !important;
    }
    
    /* 【修正 1】側邊欄 (區塊 1) 改為全白，文字改全黑 */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E5E7EB;
    }
    section[data-testid="stSidebar"] .stMarkdown p, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2 {
        color: #000000 !important;
    }
    /* 側邊欄輸入框樣式：白底黑框黑字 */
    section[data-testid="stSidebar"] div[data-baseweb="input"] {
        background-color: #FFFFFF !important;
        border: 1px solid #000000 !important;
    }
    section[data-testid="stSidebar"] input {
        color: #000000 !important;
    }

    /* 所有標題與文字 (區塊 2 & 3) 改為全黑 */
    h1, h2, h3, h4, p, span, label {
        color: #000000 !important;
        font-family: 'Segoe UI', sans-serif !important;
    }
    
    /* 移除標題連結雜質 */
    .stMarkdown h1 a, .stMarkdown h1 span { display: none !important; }
    h1 { border-bottom: 3px solid #000000; padding-bottom: 10px; }

    /* 【修正 3】表格區塊背景改為全白 */
    div[data-testid="stDataFrame"] {
        background-color: #FFFFFF !important;
        border: 1px solid #000000;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("MLB 打者擊球落點圖")

# --- 顏色定義 (鮮豔色用於對應，背景設為透明) ---
color_palette = {
    'Single': '#FF4B4B', 'Double': '#FFAA00', 'Triple': '#FFAA00', 
    'Home Run': '#00C9A7', 'Field Out': '#3498DB', 
    'Strikeout': '#95A5A6', 'Walk': '#2ECC71', 'Intentional Walk': '#2ECC71', 'Hit By Pitch': '#2ECC71'
}

def style_number_col(row):
    color = color_palette.get(row['結果'], 'white')
    # 打席數字列標色，其餘純白底黑字
    return [f'background-color: {color}; color: black; font-weight: bold; text-align: center;' 
            if name == '打席' else 'background-color: white; color: black;' for name in row.index]

with st.sidebar:
    st.header("🔍 選手查詢")
    # 將名字與姓氏預設為大寫，符合你的截圖風格
    first_name = st.text_input("First Name", "AARON").strip().capitalize()
    last_name = st.text_input("Last Name", "JUDGE").strip().capitalize()
    submit = st.button("更新數據")

if submit:
    with st.spinner('正在同步三大區塊視覺...'):
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
                    # 繪圖區背景設為純白
                    fig, ax = plt.subplots(figsize=(10, 10), facecolor='white')
                    
                    def tx(x): return (x - 125.5) * 3.5
                    def ty(y): return (205 - y) * 2.6 

                    # 球場實線 (深灰色)
                    ax.plot([0, 125, 0, -125, 0], [0, 125, 250, 125, 0], color='#000000', lw=2.5, zorder=10)
                    ax.plot([0, 270, 0, -270, 0], [0, 270, 460, 270, 0], color='#BDC3C7', lw=2.5, ls='-', zorder=1)

                    # 壘包入角
                    off = 12
                    ax.plot(125-off, 125, marker='s', color='#000000', markersize=9, zorder=11)
                    ax.plot(0, 250-off, marker='s', color='#000000', markersize=9, zorder=11)
                    ax.plot(-125+off, 125, marker='s', color='#000000', markersize=9, zorder=11)

                    for i, row in game_data.iterrows():
                        event_raw = str(row['events']).lower()
                        if any(x in event_raw for x in ['strikeout', 'walk', 'hit_by_pitch']): continue
                            
                        if pd.notna(row['hc_x']):
                            x, y = tx(row['hc_x']), ty(row['hc_y'])
                            if 'home_run' not in event_raw: y = min(y, 450)
                            
                            event_name = "Home Run" if 'home_run' in event_raw else "Field Out"
                            if 'single' in event_raw: event_name = "Single"
                            elif 'double' in event_raw: event_key = "Double"
                            
                            color = color_palette.get(event_name, '#95A5A6')
                            marker = '*' if 'home_run' in event_raw else 'o'
                            
                            ax.scatter(x, y, c=color, s=450, marker=marker, edgecolors='black', linewidths=1.2, zorder=5)
                            # 數字標籤
                            ax.text(x+15, y+15, str(i+1), color='black', ha='left', va='bottom', 
                                    fontweight='bold', fontsize=12, zorder=6,
                                    bbox=dict(facecolor='white', alpha=0.8, edgecolor='black', boxstyle='round,pad=0.2'))

                    ax.set_xlim([-480, 480]); ax.set_ylim([-50, 680]); ax.set_aspect('equal'); ax.axis('off')
                    ax.set_title(f"{first_name} {last_name} | {latest_date}", fontsize=24, fontweight='bold', color='black', pad=50)
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
                    st.info("💡 **視覺修正**：側邊欄、主圖區、表格區已全部轉為白底黑字。")

                st.success(f"更新完畢")
