import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# --- 1. 介面樣式徹底鎖定：徹底解決「變黑」與「看不到」的問題 ---
st.set_page_config(page_title="MLB Hitting Chart", layout="wide")

st.markdown("""
    <style>
    /* 全域背景強制白色 */
    .stApp { background-color: #FFFFFF !important; }

    /* 【區域 1】側邊欄整體背景：淺灰色 */
    [data-testid="stSidebar"] {
        background-color: #F1F5F9 !important;
        border-right: 1px solid #E2E8F0;
    }

    /* 【區域 2】徹底解決輸入框變黑問題：強制白底黑字 */
    div[data-baseweb="input"], div[data-baseweb="input"] input {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
    }
    label[data-testid="stWidgetLabel"] p {
        color: #1E293B !important;
        font-weight: bold !important;
    }

    /* 【區域 3】表格標頭：深色商務灰底白字 */
    [data-testid="stDataFrame"] thead tr th {
        background-color: #334155 !important;
        color: #FFFFFF !important;
        font-weight: bold !important;
    }

    /* 文字全黑化 */
    h1, h2, h3, h4, p, span {
        color: #0F172A !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
    }

    /* 移除標題雜質 */
    .stMarkdown h1 a { display: none !important; }
    h1 { border-bottom: 2px solid #0F172A; padding-bottom: 12px; }
    </style>
    """, unsafe_allow_html=True)

st.title("MLB 打者擊球落點圖")

# --- 2. 顏色方案：嚴格同步表格與點位 (莫蘭迪高對比) ---
color_palette = {
    'Single': '#E27367',      # 珊瑚紅
    'Double': '#E9C46A',      # 芥末金
    'Triple': '#F4A261',      # 琥珀橘
    'Home Run': '#2A9D8F',    # 翡翠綠
    'Field Out': '#3B82F6',   # 亮藍 (與截圖 4 號圓圈同步)
    'Strikeout': '#94A3B8',   # 鋼鐵灰
    'Walk': '#A78BFA',        # 薰衣草紫
    'Intentional Walk': '#A78BFA', 
    'Hit By Pitch': '#A78BFA'
}

def style_df(df):
    """【區域 4】表格標色：確保與圖表點位顏色完全 100% 同步"""
    return df.style.apply(lambda r: [
        f'background-color: {color_palette.get(r["結果"], "#FFFFFF")}; color: #FFFFFF; font-weight: bold; text-align: center;' 
        if n == '打席' else 'background-color: #FFFFFF; color: #0F172A;' for n in r.index
    ], axis=1)

with st.sidebar:
    st.header("🔍 選手查詢")
    first_name = st.text_input("First Name", "AARON").strip().upper()
    last_name = st.text_input("Last Name", "JUDGE").strip().upper()
    submit = st.button("更新落點數據")

if submit:
    with st.spinner('正在精確校正物理座標...'):
        player_info = playerid_lookup(last_name.capitalize(), first_name.capitalize())
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
                    # 球場繪製：鎖定座標比例
                    fig, ax = plt.subplots(figsize=(10, 10), facecolor='white')
                    
                    def tx(x): return (x - 125.5) * 3.8
                    def ty(y): return (205 - y) * 2.8 

                    # 內野菱形與球場線
                    ax.plot([0, 125, 0, -125, 0], [0, 125, 250, 125, 0], color='#1E293B', lw=2.5, zorder=10)
                    ax.plot([0, 280, 0, -280, 0], [0, 280, 480, 280, 0], color='#CBD5E1', lw=2.5, ls='-', zorder=1)

                    # 壘包位置 (入角)
                    ax.plot(113, 125, marker='s', color='#1E293B', markersize=9, zorder=11)
                    ax.plot(0, 238, marker='s', color='#1E293B', markersize=9, zorder=11)
                    ax.plot(-113, 125, marker='s', color='#1E293B', markersize=9, zorder=11)

                    for i, row in game_data.iterrows():
                        event_raw = str(row['events']).lower()
                        if any(x in event_raw for x in ['strikeout', 'walk', 'hit_by_pitch']): continue
                            
                        if pd.notna(row['hc_x']):
                            x, y = tx(row['hc_x']), ty(row['hc_y'])
                            if 'home_run' not in event_raw: y = min(y, 450)
                            
                            # 判定事件類別
                            if 'home_run' in event_raw: k = 'Home Run'
                            elif 'single' in event_raw: k = 'Single'
                            elif 'double' in event_raw: k = 'Double'
                            elif 'triple' in event_raw: k = 'Triple'
                            else: k = 'Field Out'
                            
                            color = color_palette.get(k, '#94A3B8')
                            ax.scatter(x, y, c=color, s=550, marker='*' if k == 'Home Run' else 'o', 
                                       edgecolors='black', linewidths=1.5, zorder=5)
                            
                            # 數字標籤 (白底黑字)
                            ax.text(x+16, y+16, str(i+1), color='#0F172A', fontweight='bold', fontsize=12,
                                    bbox=dict(facecolor='white', alpha=0.9, edgecolor='#1E293B', boxstyle='round,pad=0.2'))

                    ax.set_xlim([-500, 500]); ax.set_ylim([-50, 700]); ax.set_aspect('equal'); ax.axis('off')
                    ax.set_title(f"{first_name} {last_name} | {latest_date}", fontsize=24, fontweight='bold', color='#0F172A', pad=50)
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
                    # 套用表格樣式：打席顏色連動
                    st.dataframe(style_df(df_display), use_container_width=True, hide_index=True)

                st.success("✅ 視覺渲染與色彩同步校正完畢")
