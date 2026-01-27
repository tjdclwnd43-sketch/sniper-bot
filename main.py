# ==========================================
# 📡 마스터 헌터: 메세지 전송 강화판 (Final Fixed)
# 기능: 1. 시작 메세지 전송 후 2초 대기 (씹힘 방지)
#       2. 프리마켓 실시간 데이터 적용
#       3. 퀀트 점수 70점 이상 시 리포트 전송
# ==========================================

import os
import yfinance as yf
import pandas_ta as ta
import requests
import pandas as pd
from datetime import datetime
import pytz
import yahoo_fin.stock_info as si
import time  # 대기 시간을 위해 필수

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
        # 타임아웃 5초 설정 (무한 대기 방지)
        response = requests.get(url, params={"chat_id": CHAT_ID, "text": msg}, timeout=5)
        if response.status_code == 200:
            print("✅ 텔레그램 전송 성공")
        else:
            print(f"❌ 전송 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ 전송 에러: {e}")
        pass

# --- 종목 발굴 레이더 ---
def get_hot_symbols():
    print("📡 시장 스캔 중...")
    try:
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

    # 3. RSI
    rsi = latest['RSI_14']
    if 35 <= rsi <= 75: score += 20
    
    # 4. MACD
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
    print(f"[{get_now()}] 봇 실행 시작")
    
    # 1. 시작 메세지 전송
    print("📨 시작 메세지 전송 시도...")
    send_telegram("[주식 분석 봇 실행이 완료 되었습니다]")
    
    # ★ 핵심 수정: 메세지 보내고 2초 쉬기 (전송 보장)
    time.sleep(2)

    try:
        targets = get_hot_symbols()
        
        # 프리장 데이터 적용 (prepost=True)
        data = yf.download(targets, period="5d", interval="5m", progress=False, prepost=True)

        if not data.empty:
            for ticker in targets:
                try:
                    try: df = data.xs(ticker, axis=1, level=1)
                    except: df = data
                    
                    if len(df) < 30: continue
                    
                    df['RSI_14'] = ta.rsi(df['Close'], length=14)
                    macd = ta.macd(df['Close'])
                    df = pd.concat([df, macd], axis=1)
                    
                    score, reasons, price = analyze_market(ticker, df)
                    
                    stop_loss = price * 0.965
                    target_price = price * 1.05
                    
                    # 70점 이상이면 알림
                    if score >= 70:
                        reasons_txt = ", ".join(reasons)
                        msg = f"""🛰️ [실시간 포착] {ticker}
📊 점수: {score}점
💰 현재가: ${price:.2f}
--------------------
🛑 손절가: ${stop_loss:.2f} (-3.5%)
🎯 목표가: ${target_price:.2f} (+5.0%)
--------------------
[이유] {reasons_txt}"""
                        send_telegram(msg)
                        print(f"🔔 알림: {ticker}")
                        # 연속 전송 시 씹힘 방지를 위해 1초 대기
                        time.sleep(1)
                        
                except: continue

    except Exception as e:
        print(f"에러: {e}")

    print("✅ 종료")
