import streamlit as st
import pandas as pd
from pybaseball import playerid_lookup, statcast_batter
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

st.set_page_config(page_title="MLB 球探報告系統", layout="wide")

st.title("⚾ MLB 專業球探報告系統")
st.write("輸入球員姓名，即時產生最近 30 天的擊球分佈圖。")

col1, col2 = st.columns(2)
with col1:
    first_name = st.text_input("名字 (First Name)", "Aaron")
with col2:
    last_name = st.text_input("姓氏 (Last Name)", "Judge")

if st.button("產生報告"):
    with st.spinner('正在抓取大聯盟官方數據...'):
        player_info = playerid_lookup(last_name.capitalize(), first_name.capitalize())
        if not player_info.empty:
            mlbam_id = player_info.key_mlbam.values[0]
            data = statcast_batter((datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                                   datetime.now().strftime('%Y-%m-%d'), mlbam_id)

            if not data.empty:
                # 這裡放你原本的繪圖邏輯 (tx, ty 座標轉換等)
                fig, ax = plt.subplots(figsize=(10, 10))
                # ... (省略中間繪圖代碼，與原本相同) ...

                st.pyplot(fig)  # 在網頁上顯示圖表
                st.success(f"成功產出 {first_name} {last_name} 的報告！")
            else:
                st.error("最近無數據。")
        else:
            st.error("找不到球員。")