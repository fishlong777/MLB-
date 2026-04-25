import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# --- 徹底鎖定視覺：直接在 HTML 標籤內下強制令 ---
st.set_page_config(page_title="MLB Hitting Chart", layout="wide")

st.markdown("""
    <style>
    /* 全域白色 */
    .stApp { background-color: #FFFFFF !important; }
    
    /* 【1】側邊欄整體灰色 */
    section[data-testid="stSidebar"] {
        background-color: #F0F2F6 !important;
        border-right: 1px solid #D1D5DB;
    }

    /* 【2, 3】強制側邊欄輸入框變成灰色 */
    section[data-testid="stSidebar"] div[data-baseweb="input"] {
        background-color: #E2E8F0 !important;
        border: 2px solid #94A3B8 !important;
    }
    section[data-testid="stSidebar"] input { color: #000000 !important; }

    /* 【4】按鈕改為深灰色 */
    div.stButton > button {
        background-color: #64748B !important;
        color: white !important;
        width: 100%;
        border-radius: 5px;
    }

    /* 文字全黑 */
    h1, h2, h3, h4, p, label { color: #000000 !important; }
    .stMarkdown h1 a { display: none !important; }
    h1 { border-bottom: 3px solid #000000; }
    </style>
    """, unsafe_allow_html=True)

st.title("MLB 打者擊球落點圖")

# --- 顏色定義 ---
color_palette = {
    'Single': '#FF4B4B', 'Double': '#FFAA00', 'Triple': '#FFAA00', 
    'Home Run': '#00C9A7', 'Field Out': '#3498DB', 
    'Strikeout': '#95A5A6', 'Walk': '#2ECC71', 'Intentional Walk': '#2ECC71', 'Hit By Pitch': '#2ECC71'
}

with st.sidebar:
    st.header("🔍 選手查詢")
    # 直接在元件上方加個灰色背景的標示 (物理隔離)
    st.markdown('<div style="background-color:#E2E8F0; padding:10px; border-radius:5px;">', unsafe_allow_html=True)
    first_name = st.text_input("First Name", "AARON").strip().capitalize()
    last_name = st.text_input("Last Name", "JUDGE").strip().capitalize()
    st.markdown('</div>', unsafe_allow_html=True)
    st.write("")
    submit = st.button("更新數據")

if submit:
    with st.spinner('正在同步灰色層次...'):
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

                    # 球場線條
                    ax.plot([0, 125, 0, -125, 0], [0, 125, 250, 125, 0], color='#334155', lw=2.5, zorder=10)
                    ax.plot([0, 270, 0, -270, 0], [0, 270, 460, 270, 0], color='#CBD5E1', lw=2.5, ls='-', zorder=1)

                    # 壘包入角
                    ax.plot(113, 125, marker='s', color='#334155', markersize=9, zorder=11)
                    ax.plot(0, 238, marker='s', color='#334155', markersize=9, zorder=11)
                    ax.plot(-113, 125, marker='s', color='#334155', markersize=9, zorder=11)

                    for i, row in game_data.iterrows():
                        event_raw = str(row['events']).lower()
                        if any(x in event_raw for x in ['strikeout', 'walk', 'hit_by_pitch']): continue
                        if pd.notna(row['hc_x']):
                            x, y = tx(row['hc_x']), ty(row['hc_y'])
                            if 'home_run' not in event_raw: y = min(y, 450)
                            color = color_palette.get("Home Run" if 'home_run' in event_raw else "Field Out", '#94A3B8')
                            if 'single' in event_raw: color = color_palette['Single']
                            
                            ax.scatter(x, y, c=color, s=450, marker='*' if 'home_run' in event_raw else 'o', edgecolors='black', zorder=5)
                            ax.text(x+15, y+15, str(i+1), color='black', fontweight='bold', bbox=dict(facecolor='white', alpha=0.8, edgecolor='black', boxstyle='round'))

                    ax.set_xlim([-480, 480]); ax.set_ylim([-50, 680]); ax.axis('off')
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
                    # 【5】標題灰色強制化
                    st.dataframe(df_display.style.apply(lambda r: [f'background-color: {color_palette.get(r["結果"], "white")}; color: black; font-weight: bold; text-align: center;' if n == '打席' else 'background-color: white; color: black;' for n in r.index], axis=1).set_table_styles([{'selector': 'th', 'props': [('background-color', '#CBD5E1'), ('color', 'black')]}], overwrite=False), use_container_width=True, hide_index=True)

                st.success(f"手動強制渲染完成")
