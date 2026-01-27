# ==========================================
# 📡 마스터 헌터: 실시간 시장 주도주 자동 포착 봇
# ==========================================
import os
import yfinance as yf
import pandas_ta as ta
import requests
import pandas as pd
from datetime import datetime
import pytz
import yahoo_fin.stock_info as si

try:
    TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
    CHAT_ID = os.environ['CHAT_ID']
except KeyError:
    print("오류: 깃허브 Secrets 설정이 필요합니다.")
    exit()

KST = pytz.timezone('Asia/Seoul')

def get_now():
    return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')

def send_telegram(msg):
    requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": msg})

# --- [1. 종목 발굴 레이더] ---
def get_hot_symbols():
    print("📡 시장 스캔 중...")
    hot_list = []
    try:
        hot_list.extend(si.get_day_gainers().head(15)['Symbol'].tolist()) # 급등주
        hot_list.extend(si.get_day_most_active().head(5)['Symbol'].tolist()) # 거래량 폭발
        hot_list.extend(["SOXL", "SOXS", "TQQQ", "SQQQ", "NVDA", "TSLA"]) # 고정 감시
        return list(set(hot_list))
    except:
        return ["SOXL", "NVDA", "TQQQ", "TSLA"]

# --- [2. 퀀트 분석 엔진] ---
def analyze_market(ticker, df):
    latest = df.iloc[-1]
    score = 0
    reasons = []
    
    if latest['Close'] < 5: return 0, [], 0 # 동전주 제외

    # 모멘텀 & 급등
    if latest['Close'] > df['Open'].iloc[-1]:
        score += 20
        if (latest['Close'] - df['Open'].iloc[-1]) / df['Open'].iloc[-1] > 0.05:
            score += 10
            reasons.append("🔥 오늘 5% 이상 폭등 중")

    # 거래량
    vol_ma = df['Volume'].rolling(20).mean().iloc[-1]
    if latest['Volume'] > vol_ma * 1.5:
        score += 20
        reasons.append("🟢 거래량 폭발")

    # 보조지표
    rsi = latest['RSI_14']
    if 40 <= rsi <= 75: score += 20 # 상승 추세
    
    macd = latest['MACD_12_26_9']
    if macd > latest['MACDs_12_26_9']: 
        score += 20
        reasons.append("🟢 MACD 상승 지속")

    sma_20 = df['Close'].rolling(20).mean().iloc[-1]
    disparity = (latest['Close'] / sma_20) * 100
    if 98 <= disparity <= 110: score += 10

    return score, reasons, latest['Close']

# --- [3. 메인 실행] ---
print(f"[{get_now()}] 🚀 헌터 봇 가동")
targets = get_hot_symbols()
print(f"👉 타겟: {targets}")

try:
    data = yf.download(targets, period="5d", interval="5m", progress=False)
    if not data.empty:
        for ticker in targets:
            try:
                try: df = data.xs(ticker, axis=1, level=1)
                except: df = data
                if len(df) < 30: continue
                
                df['RSI_14'] = ta.rsi(df['Close'], length=14)
                df = pd.concat([df, ta.macd(df['Close'])], axis=1)
                
                score, reasons, price = analyze_market(ticker, df)
                
                if score >= 70: # 70점 이상이면 알림
                    msg = f"🛰️ [급등주 포착] {ticker}\n점수: {score}점\n현재가: ${price:.2f}\n이유: {', '.join(reasons)}"
                    send_telegram(msg)
                    print(f"🔔 알림: {ticker}")
            except: continue
except Exception as e: print(e)
