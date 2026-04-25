import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# --- 介面強制校準 ---
st.set_page_config(page_title="MLB Hitting Chart", layout="wide")

st.markdown("""
    <style>
    /* 全域白色背景 */
    .stApp { background-color: #FFFFFF !important; }

    /* 1. 側邊欄背景改為明顯的淺灰色 */
    section[data-testid="stSidebar"] {
        background-color: #F0F2F6 !important;
        border-right: 1px solid #D1D5DB;
    }

    /* 2 & 3. 針對輸入框：強制背景為灰色，邊框為深灰色，文字為黑色 */
    /* 這裡必須針對所有可能的狀態進行鎖定 */
    div[data-baseweb="input"], div[data-baseweb="input"] > div {
        background-color: #E2E8F0 !important; 
        border: 1px solid #94A3B8 !important;
    }
    input[data-testid="stTextInputEnterChat"] { color: #000000 !important; }
    input { color: #000000 !important; }

    /* 4. 更新數據按鈕：強制灰色背景與黑色文字 */
    div.stButton > button {
        background-color: #CBD5E1 !important; /* 明確的灰色 */
        color: #000000 !important;
        border: 2px solid #94A3B8 !important;
        font-weight: bold !important;
        transition: all 0.3s;
    }
    div.stButton > button:hover {
        background-color: #94A3B8 !important;
        border-color: #64748B !important;
    }

    /* 文字樣式修正 */
    h1, h2, h3, h4, p, label { color: #111827 !important; }
    .stMarkdown h1 a { display: none !important; }
    h1 { border-bottom: 3px solid #111827; }

    /* 5. 表格標題顏色強制化 */
    div[data-testid="stDataFrame"] thead tr th {
        background-color: #E2E8F0 !important;
        color: #111827 !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("MLB 打者擊球落點圖")

# --- 顏色定義 ---
color_palette = {
    'Single': '#EF4444', 'Double': '#F59E0B', 'Triple': '#F59E0B', 
    'Home Run': '#10B981', 'Field Out': '#3B82F6', 
    'Strikeout': '#64748B', 'Walk': '#8B5CF6', 'Intentional Walk': '#8B5CF6', 'Hit By Pitch': '#8B5CF6'
}

with st.sidebar:
    st.header("🔍 選手查詢")
    # 這裡加入一點標籤提示
    first_name = st.text_input("First Name", "AARON").strip().capitalize()
    last_name = st.text_input("Last Name", "JUDGE").strip().capitalize()
    st.write("")
    submit = st.button("更新數據")

if submit:
    with st.spinner('正在同步灰色層次渲染...'):
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
                    def ty(y): return (205 - y) * 2.8 

                    # 球場繪製 (線條調整為深色)
                    ax.plot([0, 125, 0, -125, 0], [0, 125, 250, 125, 0], color='#1F2937', lw=2.5, zorder=10)
                    ax.plot([0, 270, 0, -270, 0], [0, 270, 460, 270, 0], color='#94A3B8', lw=2.5, ls='-', zorder=1)

                    # 壘包位置
                    off = 12
                    ax.plot(125-off, 125, marker='s', color='#1F2937', markersize=9, zorder=11)
                    ax.plot(0, 250-off, marker='s', color='#1F2937', markersize=9, zorder=11)
                    ax.plot(-125+off, 125, marker='s', color='#1F2937', markersize=9, zorder=11)

                    for i, row in game_data.iterrows():
                        event_raw = str(row['events']).lower()
                        if any(x in event_raw for x in ['strikeout', 'walk', 'hit_by_pitch']): continue
                        if pd.notna(row['hc_x']):
                            x, y = tx(row['hc_x']), ty(row['hc_y'])
                            if 'home_run' not in event_raw: y = min(y, 450)
                            
                            event_key = "Home Run" if 'home_run' in event_raw else "Field Out"
                            if 'single' in event_raw: event_key = 'Single'
                            elif 'double' in event_raw: event_key = 'Double'
                            
                            color = color_palette.get(event_key, '#94A3B8')
                            ax.scatter(x, y, c=color, s=450, marker='*' if 'home_run' in event_raw else 'o', 
                                       edgecolors='black', linewidths=1.2, zorder=5)
                            ax.text(x+15, y+15, str(i+1), color='#111827', fontweight='bold', 
                                    bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', boxstyle='round'))

                    ax.set_xlim([-480, 480]); ax.set_ylim([-50, 680]); ax.axis('off')
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
                    # 表格連動與樣式
                    st.dataframe(df_display.style.apply(lambda r: [f'background-color: {color_palette.get(r["結果"], "white")}; color: black; font-weight: bold; text-align: center;' if n == '打席' else 'background-color: white; color: #111827;' for n in r.index], axis=1), use_container_width=True, hide_index=True)

                st.success(f"手動強制渲染完成")
