import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta

# --- 1. 介面強制校準：解決背景與文字看不見的問題 ---
st.set_page_config(page_title="MLB Hitting Chart", layout="wide")

st.markdown("""
    <style>
    /* 全域背景白色 */
    .stApp { background-color: #FFFFFF !important; }

    /* 【修正 1】側邊欄與輸入框灰色背景 */
    [data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
        border-right: 1px solid #E2E8F0;
    }
    /* 針對輸入框與按鈕的強制灰色 */
    div[data-baseweb="input"], div[data-baseweb="select"] > div {
        background-color: #F1F5F9 !important;
        border: 1px solid #CBD5E1 !important;
    }
    
    /* 【修正 3 & 4】表格視覺優化：商務灰色標頭 */
    [data-testid="stDataFrame"] thead tr th {
        background-color: #475569 !important;
        color: white !important;
        font-weight: bold !important;
    }
    
    /* 文字全黑鎖定 */
    h1, h2, h3, h4, p, label, span {
        color: #0F172A !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* 移除標題連結 */
    .stMarkdown h1 a { display: none !important; }
    h1 { border-bottom: 2px solid #0F172A; padding-bottom: 8px; }
    </style>
    """, unsafe_allow_html=True)

st.title("MLB 打者擊球落點圖")

# --- 4. 好看的商務配色方案 (莫蘭迪色系) ---
color_palette = {
    'Single': '#E27367',      # 磚紅
    'Double': '#E9C46A',      # 芥末黃
    'Triple': '#F4A261',      # 橘
    'Home Run': '#2A9D8F',    # 灰綠
    'Field Out': '#8ECAE6',   # 淺藍
    'Strikeout': '#94A3B8',   # 鋼鐵灰
    'Walk': '#A78BFA',        # 薰衣草紫
    'Intentional Walk': '#A78BFA', 
    'Hit By Pitch': '#A78BFA'
}

def style_df(df):
    """表格顏色連動：打席格子與圖相同，其餘白底黑字"""
    return df.style.apply(lambda r: [
        f'background-color: {color_palette.get(r["結果"], "#FFFFFF")}; color: white; font-weight: bold; text-align: center;' 
        if n == '打席' else 'background-color: #FFFFFF; color: #0F172A;' for n in r.index
    ], axis=1)

with st.sidebar:
    st.header("🔍 選手查詢")
    first_name = st.text_input("First Name", "AARON").strip().capitalize()
    last_name = st.text_input("Last Name", "JUDGE").strip().capitalize()
    submit = st.button("更新數據")

if submit:
    with st.spinner('正在精確校正落點座標與視覺配置...'):
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
                    # 【修正 2】固定座標比例，防止落點圖變形
                    fig, ax = plt.subplots(figsize=(10, 10), facecolor='white')
                    
                    # 鎖定倍率：x 軸拉寬、y 軸適中
                    def tx(x): return (x - 125.5) * 3.8
                    def ty(y): return (205 - y) * 2.8 

                    # 球場實線 (深灰)
                    ax.plot([0, 125, 0, -125, 0], [0, 125, 250, 125, 0], color='#1E293B', lw=2.5, zorder=10)
                    ax.plot([0, 280, 0, -280, 0], [0, 280, 480, 280, 0], color='#CBD5E1', lw=2, ls='-', zorder=1)

                    # 壘包位置 (修正為固定偏移量)
                    ax.plot(113, 125, marker='s', color='#1E293B', markersize=9, zorder=11)
                    ax.plot(0, 238, marker='s', color='#1E293B', markersize=9, zorder=11)
                    ax.plot(-113, 125, marker='s', color='#1E293B', markersize=9, zorder=11)

                    for i, row in game_data.iterrows():
                        event_raw = str(row['events']).lower()
                        if any(x in event_raw for x in ['strikeout', 'walk', 'hit_by_pitch']): continue
                            
                        if pd.notna(row['hc_x']):
                            x, y = tx(row['hc_x']), ty(row['hc_y'])
                            # 強制將非全壘打的球限制在場內視覺範圍
                            if 'home_run' not in event_raw: y = min(y, 450)
                            
                            # 對應配色方案
                            if 'home_run' in event_raw: k = 'Home Run'
                            elif 'single' in event_raw: k = 'Single'
                            elif 'double' in event_raw: k = 'Double'
                            elif 'triple' in event_raw: k = 'Triple'
                            else: k = 'Field Out'
                            
                            color = color_palette.get(k, '#94A3B8')
                            ax.scatter(x, y, c=color, s=450, marker='*' if k == 'Home Run' else 'o', 
                                       edgecolors='black', linewidths=1.2, zorder=5)
                            
                            # 數字標籤：白底黑字黑邊
                            ax.text(x+15, y+15, str(i+1), color='#0F172A', fontweight='bold', fontsize=12,
                                    bbox=dict(facecolor='white', alpha=0.8, edgecolor='#0F172A', boxstyle='round,pad=0.2'))

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
                    # 套用【修正 3 & 4】的商務配色樣式
                    st.dataframe(style_df(df_display), use_container_width=True, hide_index=True)

                st.success("視覺渲染與座標校正完成")
