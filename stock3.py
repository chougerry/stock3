import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 設定網頁標題與外觀（平板友善，版面會隨螢幕寬度自動伸縮）
st.set_page_config(page_title="自選股多日漲跌幅統計", layout="wide")
st.title("📈 自選股即時監控與多日漲跌幅統計")

# 1. 側邊欄設定
st.sidebar.header("⚙️ 設定自選股與天數")

# 股票輸入框
default_tickers = "2330.TW, 2317.TW, 2454.TW, AAPL"
user_input = st.sidebar.text_area(
    "請輸入股票代號（多檔請用逗號隔開）\n台股請加 .TW (例如: 2330.TW)", 
    value=default_tickers
)

# 初始化 Streamlit 的狀態機（用來記錄按鈕加減的天數，預設為 20 天）
if "days_counter" not in st.session_state:
    st.session_state.days_counter = 20

st.sidebar.write(f"### 目前統計天數：**{st.session_state.days_counter}** 天")

# 需求：在平板上極易操作的 加 / 減 按鈕
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("➖ 減少 1 天", use_container_width=True):
        if st.session_state.days_counter > 1:
            st.session_state.days_counter -= 1
            st.rerun()  # 立即重新整理畫面
with col2:
    if st.button("➕ 增加 1 天", use_container_width=True):
        if st.session_state.days_counter < 90: # 設定上限 90 天
            st.session_state.days_counter += 1
            st.rerun()  # 立即重新整理畫面

# 為了方便平板大範圍調整，再補一組 5 天進退按鈕
col3, col4 = st.sidebar.columns(2)
with col3:
    if st.button("⏪ 減少 5 天", use_container_width=True):
        if st.session_state.days_counter > 5:
            st.session_state.days_counter -= 5
            st.rerun()
with col4:
    if st.button("⏩ 增加 5 天", use_container_width=True):
        if st.session_state.days_counter <= 85:
            st.session_state.days_counter += 5
            st.rerun()

current_custom_days = st.session_state.days_counter
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

# 2. 核心抓取與計算邏輯
def get_stock_data(tickers, n_days):
    data_list = []
    
    for ticker_to_search in tickers:
        try:
            # 確保歷史數據足夠計算 N 天 (取 N + 20 天最穩妥)
            fetch_days = max(30, n_days + 20)
            stock = yf.Ticker(ticker_to_search)
            hist = stock.history(period=f"{fetch_days}d")
            
            if hist.empty:
                continue
                
            stock_info = stock.info
            stock_name = stock_info.get('shortName', ticker_to_search)
            
            # 處理即時市價/收盤價
            latest_row = hist.iloc[-1]
            current_price = latest_row['Close']
            prev_close = hist.iloc[-2]['Close'] if len(hist) > 1 else current_price
            
            # 計算各區間漲跌幅
            daily_change_pct = ((current_price - prev_close) / prev_close) * 100
            change_3d = ((current_price - hist.iloc[-4]['Close']) / hist.iloc[-4]['Close']) * 100 if len(hist) >= 4 else 0
            change_5d = ((current_price - hist.iloc[-6]['Close']) / hist.iloc[-6]['Close']) * 100 if len(hist) >= 6 else 0
            change_10d = ((current_price - hist.iloc[-11]['Close']) / hist.iloc[-11]['Close']) * 100 if len(hist) >= 11 else 0
            
            # 計算自訂 N 天的漲跌幅
            target_index = -(n_days + 1)
            if len(hist) >= abs(target_index):
                past_price = hist.iloc[target_index]['Close']
                custom_change = ((current_price - past_price) / past_price) * 100
            else:
                custom_change = 0.0
            
            data_list.append({
                "代號": ticker_to_search,
                "股票名稱": stock_name,
                # 需求 1：所有數字（包含市價）均精準控制在小數點後兩位格式
                "目前市價/收盤價": f"{current_price:.2f}",
                "當日漲跌幅 (%)": round(daily_change_pct, 2),
                "近 3 日漲跌 (%)": round(change_3d, 2),
                "近 5 日漲跌 (%)": round(change_5d, 2),
                "近 10 日漲跌 (%)": round(change_10d, 2),
                f"自訂近 {n_days} 日漲跌 (%)": round(custom_change, 2),
            })
        except Exception as e:
            st.error(f"無法抓取 {ticker_to_search} 的資料，請檢查代號是否正確。")
            
    return pd.DataFrame(data_list)

# 3. 畫面渲染
if ticker_list:
    with st.spinner('正在抓取最新股價與統計多日漲跌幅...'):
        df = get_stock_data(ticker_list, current_custom_days)
        
    if not df.empty:
        # 顏色標示：正數變紅，負數變綠
        def color_change(val):
            if isinstance(val, (int, float)):
                if val > 0:
                    return 'color: #ff4b4b; font-weight: bold;'
                elif val < 0:
                    return 'color: #00b050; font-weight: bold;'
            return ''

        # 套用紅色與綠色樣式
        target_columns = ["當日漲跌幅 (%)", "近 3 日漲跌 (%)", "近 5 日漲跌 (%)", "近 10 日漲跌 (%)", f"自訂近 {current_custom_days} 日漲跌 (%)"]
        
        # 強制將所有表格中的浮點數（小數）在前端都以小數點後兩位顯示
        styled_df = df.style.map(color_change, subset=target_columns).format({
            "當日漲跌幅 (%)": "{:.2f}",
            "近 3 日漲跌 (%)": "{:.2f}",
            "近 5 日漲跌 (%)": "{:.2f}",
            "近 10 日漲跌 (%)": "{:.2f}",
            f"自訂近 {current_custom_days} 日漲跌 (%)": "{:.2f}"
        })
        
        # 顯示最後更新時間
        st.caption(f"最後更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (延遲約15分鐘)")
        
        # 顯示表格
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # 平板上一鍵重新整理按鈕
        if st.button("🔄 重新整理最新股價", use_container_width=True):
            st.rerun()
    else:
        st.warning("查無任何股票資料，請確認側邊欄輸入的代號。")