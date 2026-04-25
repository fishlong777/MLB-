import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# --- 徹底鎖定視覺：白底黑字 + 灰色區塊 (1,2,3,4,5) ---
st.set_page_config(page_title="MLB Hitting Chart", layout="wide")

st.markdown("""
    <style>
    /* 全域背景：白色 */
    .stApp { background-color: #FFFFFF !important; }
    
    /* 【修正 1】側邊欄上方：淺灰色 */
    section[data-testid="stSidebar"] {
        background-color: #F3F4F6 !important; /* 淺灰色 1 */
        border-right: 1px solid #E5E7EB;
    }
    
    /* 【修正 2 & 3】輸入框：稍微深一點的灰色 */
    section[data-testid="stSidebar"] div[data-baseweb="input"] {
        background-color: #E5E7EB !important; /* 灰色 2 & 3 */
        border: 1px solid #9CA3AF !important;
    }
    section[data-testid="stSidebar"] input {
        color: #000000 !important;
    }
    
    /* 【修正 4】按鈕：中灰色背景，黑字 */
    div.stButton > button {
        background-color: #D1D5DB !important; /* 灰色 4 */
        color: #000000 !important;
        border: 1px solid #9CA3AF !important;
        font-weight: bold;
    }

    /* 【修正 5】表格標題列：深灰色背景 */
    /* 這裡透過設定 DataFrame 的樣式來處理 */
    
    /* 所有文字顏色鎖定為黑色 */
    h1, h2, h3, h4, p, span, label {
        color: #000000 !important;
        font-family: 'Segoe UI', sans-serif !important;
    }
    
    /* 移除標題連結雜質 */
    .stMarkdown h1 a, .stMarkdown h1 span { display: none !important; }
    h1 { border-bottom: 2px solid #000000; padding-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("MLB 打者擊球落點圖")

# --- 顏色定義 ---
color_palette = {
    'Single': '#FF4B4B', 'Double': '#FFAA00', 'Triple': '#FFAA00', 
    'Home Run': '#00C9A7', 'Field Out': '#3498DB', 
    'Strikeout': '#95A5A6', 'Walk': '#2ECC71', 'Intentional Walk': '#2ECC71', 'Hit By Pitch': '#2ECC71'
}

def style_df(df):
    """【修正 5】設定表格樣式：標題列為灰色"""
    return df.style.apply(style_rows, axis=1).set_table_styles([
        {'selector': 'th', 'props': [('background-color', '#E5E7EB'), ('color', 'black'), ('font-weight', 'bold')]}
    ])

def style_rows(row):
    color = color_palette.get(row['結果'], 'white')
    return [f'background-color: {color}; color: black; font-weight: bold; text-align: center;' 
            if name == '打席' else 'background-color: white; color: black;' for name in row.index]

with st.sidebar:
    st.header("🔍 選手查詢")
    first_name = st.text_input("First Name", "AARON").strip().capitalize()
    last_name = st.text_input("Last Name", "JUDGE").strip().capitalize()
    submit = st.button("更新數據")

if submit:
    with st.spinner('正在調整灰色區塊層次...'):
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
                    fig, ax = plt.subplots(figsize=(10, 10), facecolor='white')
                    
                    def tx(x): return (x - 125.5) * 3.5
                    def ty(y): return (205 - y) * 2.6 

                    # 球場實線 (深灰色)
                    ax.plot([0, 125, 0, -125, 0], [0, 125, 250, 125, 0], color='#374151', lw=2.5, zorder=10)
                    ax.plot([0, 270, 0, -270, 0], [0, 270, 460, 270, 0], color='#D1D5DB', lw=2.5, ls='-', zorder=1)

                    # 壘包入角
                    off = 12
                    ax.plot(125-off, 125, marker='s', color='#374151', markersize=9, zorder=11)
                    ax.plot(0, 250-off, marker='s', color='#374151', markersize=9, zorder=11)
                    ax.plot(-125+off, 125, marker='s', color='#374151', markersize=9, zorder=11)

                    for i, row in game_data.iterrows():
                        event_raw = str(row['events']).lower()
                        if any(x in event_raw for x in ['strikeout', 'walk', 'hit_by_pitch']): continue
                            
                        if pd.notna(row['hc_x']):
                            x, y = tx(row['hc_x']), ty(row['hc_y'])
                            if 'home_run' not in event_raw: y = min(y, 450)
                            
                            event_name = "Home Run" if 'home_run' in event_raw else "Field Out"
                            if 'single' in event_raw: event_name = "Single"
                            elif 'double' in event_raw: event_name = "Double"
                            
                            color = color_palette.get(event_name, '#95A5A6')
                            marker = '*' if 'home_run' in event_raw else 'o'
                            
                            ax.scatter(x, y, c=color, s=450, marker=marker, edgecolors='black', linewidths=1.2, zorder=5)
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
                    # 套用包含【修正 5】標題灰色的樣式
                    st.dataframe(style_df(df_display), use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    st.info("💡 **視覺修正**：側邊欄、輸入框、按鈕、表格標題已改為淺灰色區隔。")

                st.success(f"數據更新完畢")
