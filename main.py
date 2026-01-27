# ==========================================
# 📡 마스터 헌터: 프리장/애프터장 데이터 잠금해제 (Real Final)
# 기능: 1. 실행 알림
#       2. 프리마켓(prepost) 데이터 강제 로드 ★핵심★
#       3. 진입/손절/목표가 리포트
# ==========================================

import os
import yfinance as yf
import pandas_ta as ta
import requests
import pandas as pd
from datetime import datetime
import pytz
import yahoo_fin.stock_info as si

# 1. 환경변수 로드
try:
    TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
    CHAT_ID = os.environ['CHAT_ID']
except KeyError:
    print("⚠️ 깃허브 환경변수 미설정")
    TELEGRAM_TOKEN = ""
    CHAT_ID = ""

KST = pytz.timezone('Asia/Seoul')

def get_now():
    return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": msg})
    except: pass

# --- 종목 발굴 레이더 ---
def get_hot_symbols():
    print("📡 시장 스캔 중...")
    try:
        # 급등주 + 거래량 상위 + 내 관심종목
        gainers = si.get_day_gainers().head(10)['Symbol'].tolist()
        active = si.get_day_most_active().head(5)['Symbol'].tolist()
        my_favorites = ["SOXL", "SOXS", "TQQQ", "SQQQ", "NVDA", "TSLA", "MSTR", "COIN"]
        
        hot_list = list(set(gainers + active + my_favorites))
        return hot_list
    except:
        return ["SOXL", "NVDA", "TQQQ", "TSLA", "MSTR", "COIN", "SOXS"]

# --- 퀀트 분석 엔진 ---
def analyze_market(ticker, df):
    if len(df) < 30: return 0, [], 0
    
    latest = df.iloc[-1]
    score = 0
    reasons = []
    
    # 5달러 미만 잡주 제외
    if latest['Close'] < 5: return 0, [], 0

    # 1. 모멘텀
    if latest['Close'] > df['Open'].iloc[-1]:
        score += 20
        open_price = df['Open'].iloc[-1]
        if (latest['Close'] - open_price) / open_price > 0.05:
            score += 10
            reasons.append("🔥 5% 이상 급등")

    # 2. 거래량 폭발
    vol_ma = df['Volume'].rolling(20).mean().iloc[-1]
    if latest['Volume'] > vol_ma * 1.5:
        score += 20
        reasons.append("🟢 거래량 터짐")

    # 3. RSI (35~75)
    rsi = latest['RSI_14']
    if 35 <= rsi <= 75: score += 20
    
    # 4. MACD 골든크로스
    macd = latest['MACD_12_26_9']
    signal = latest['MACDs_12_26_9']
    if macd > signal:
        score += 20
        reasons.append("🟢 추세 상승 중")

    # 5. 이격도
    sma_20 = df['Close'].rolling(20).mean().iloc[-1]
    disparity = (latest['Close'] / sma_20) * 100
    if 98 <= disparity <= 110: score += 10

    return score, reasons, latest['Close']

# --- 메인 실행부 ---
if __name__ == "__main__":
    print(f"[{get_now()}] 봇 실행")
    
    # 실행 알림
    send_telegram(f"🤖 봇 재가동 (프리장 데이터 적용)\n({get_now()})")

    try:
        targets = get_hot_symbols()
        
        # ★★★ [여기가 핵심입니다] prepost=True 추가 ★★★
        # 이제 프리마켓(장전) 실시간 가격을 가져옵니다.
        data = yf.download(targets, period="5d", interval="5m", progress=False, prepost=True)

        if not data.empty:
            for ticker in targets:
                try:
                    try: df = data.xs(ticker, axis=1, level=1)
                    except: df = data
                    
                    if len(df) < 30: continue
                    
                    # 지표 계산
                    df['RSI_14'] = ta.rsi(df['Close'], length=14)
                    macd = ta.macd(df['Close'])
                    df = pd.concat([df, macd], axis=1)
                    
                    score, reasons, price = analyze_market(ticker, df)
                    
                    # 손절/목표가 계산
                    stop_loss = price * 0.965
                    target_price = price * 1.05
                    
                    # 70점 이상 알림
                    if score >= 70:
                        reasons_txt = ", ".join(reasons)
                        msg = f"""🛰️ [실시간 포착] {ticker}
📊 점수: {score}점
💰 현재가: ${price:.2f}
--------------------
🛑 손절가: ${stop_loss:.2f}
🎯 목표가: ${target_price:.2f}
--------------------
[이유] {reasons_txt}"""
                        send_telegram(msg)
                        print(f"🔔 알림: {ticker}")
                        
                except: continue

    except Exception as e:
        print(f"에러: {e}")

    print("✅ 종료")
