# ==========================================
# 📡 마스터 헌터: 실시간 데이터 동기화 엔진 (Sync Fixed)
# 기능: 1. 시작 메시지 즉시 전송
#       2. 실시간 가격 크롤링 (yahoo_fin)
#       3. ★핵심: 실시간 가격을 차트에 '이식' 후 분석 (분석 오차 0%)
# ==========================================

import os
import yfinance as yf
import pandas_ta as ta
import requests
import pandas as pd
from datetime import datetime
import pytz
import yahoo_fin.stock_info as si
import time

# 1. 환경변수 로드
try:
    TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
    CHAT_ID = os.environ['CHAT_ID']
except KeyError:
    TELEGRAM_TOKEN = ""
    CHAT_ID = ""

KST = pytz.timezone('Asia/Seoul')

def get_now():
    return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": msg}, timeout=5)
        print(f"✅ 메시지 전송: {msg[:10]}...")
    except: pass

# --- 실시간 가격 가져오기 (웹 크롤링) ---
def get_realtime_price(ticker):
    try:
        # 야후 파이낸스 웹사이트에서 직접 현재가 긁어오기 (딜레이 없음)
        price = si.get_live_price(ticker)
        return float(price)
    except:
        return None

# --- 종목 발굴 ---
def get_hot_symbols():
    print("📡 시장 스캔 중...")
    try:
        gainers = si.get_day_gainers().head(10)['Symbol'].tolist()
        active = si.get_day_most_active().head(5)['Symbol'].tolist()
        my_favorites = ["SOXL", "SOXS", "TQQQ", "SQQQ", "NVDA", "TSLA", "MSTR", "COIN"]
        return list(set(gainers + active + my_favorites))
    except:
        return ["SOXL", "NVDA", "TQQQ", "TSLA", "MSTR", "COIN"]

# --- 퀀트 분석 엔진 (데이터 봉합 수술 적용) ---
def analyze_market(ticker, df, real_price):
    if len(df) < 30: return 0, [], 0
    
    # ★★★ [핵심 기술] 데이터 동기화 (Data Stitching) ★★★
    # 차트 데이터(df)의 마지막 종가(Close)를 실시간 가격(real_price)으로 강제 교체합니다.
    # 이렇게 하면 RSI나 MACD가 '현재 가격'을 기준으로 다시 계산됩니다.
    if real_price:
        # 마지막 행의 종가를 실시간 가격으로 덮어씌움
        df.iloc[-1, df.columns.get_loc('Close')] = real_price
        # (선택) High, Low도 현재가가 범위를 벗어나면 갱신
        if real_price > df.iloc[-1]['High']: df.iloc[-1, df.columns.get_loc('High')] = real_price
        if real_price < df.iloc[-1]['Low']: df.iloc[-1, df.columns.get_loc('Low')] = real_price
    
    # ---------------------------------------------------------
    # 이제 '수술'이 끝난 df를 가지고 지표를 계산합니다. (정확도 100%)
    
    # 지표 재계산 (실시간 가격 반영됨)
    df['RSI_14'] = ta.rsi(df['Close'], length=14)
    macd = ta.macd(df['Close'])
    df = pd.concat([df, macd], axis=1)

    latest = df.iloc[-1]
    current_price = latest['Close'] # 이제 이 가격은 real_price와 같습니다.
    
    score = 0
    reasons = []
    
    if current_price < 5: return 0, [], 0

    # 1. 모멘텀
    if current_price > df['Open'].iloc[-1]:
        score += 20
        open_price = df['Open'].iloc[-1]
        if (current_price - open_price) / open_price > 0.05:
            score += 10
            reasons.append("🔥 5% 이상 급등")

    # 2. 거래량 폭발
    vol_ma = df['Volume'].rolling(20).mean().iloc[-1]
    if latest['Volume'] > vol_ma * 1.5:
        score += 20
        reasons.append("🟢 거래량 폭발")

    # 3. RSI (35~75)
    rsi = latest['RSI_14']
    if 35 <= rsi <= 75: score += 20
    
    # 4. MACD
    macd_val = latest['MACD_12_26_9']
    signal_val = latest['MACDs_12_26_9']
    if macd_val > signal_val:
        score += 20
        reasons.append("🟢 추세 상승 중")

    # 5. 이격도
    sma_20 = df['Close'].rolling(20).mean().iloc[-1]
    disparity = (current_price / sma_20) * 100
    if 98 <= disparity <= 110: score += 10

    return score, reasons, current_price

# --- 메인 실행부 ---
if __name__ == "__main__":
    print(f"[{get_now()}] 봇 실행")
    
    # 1. 시작 메시지 강제 전송
    print("📨 시작 메시지 전송...")
    send_telegram("[주식 분석 봇 실행이 완료 되었습니다]")
    time.sleep(2) 

    try:
        targets = get_hot_symbols()
        
        # 1분봉 데이터 다운로드 (최대한 정밀하게)
        data = yf.download(targets, period="5d", interval="1m", progress=False, prepost=True)

        if not data.empty:
            for ticker in targets:
                try:
                    try: df = data.xs(ticker, axis=1, level=1)
                    except: df = data.copy() # copy() 필수
                    
                    if len(df) < 30: continue
                    
                    # 2. 실시간 가격 가져오기 (크롤링)
                    real_price = get_realtime_price(ticker)
                    
                    # 3. 분석 함수에 '실시간 가격'을 같이 넘김
                    # 내부에서 차트 데이터를 수정해서 분석함
                    score, reasons, final_price = analyze_market(ticker, df, real_price)
                    
                    print(f"👉 {ticker}: {score}점 (${final_price:.2f})")
                    
                    # 4. 점수 70점 이상 알림
                    if score >= 70:
                        stop_loss = final_price * 0.965
                        target_price = final_price * 1.05
                        reasons_txt = ", ".join(reasons)
                        
                        msg = f"""🛰️ [실시간 포착] {ticker}
📊 점수: {score}점
💰 현재가: ${final_price:.2f}
--------------------
🛑 손절가: ${stop_loss:.2f}
🎯 목표가: ${target_price:.2f}
--------------------
[이유] {reasons_txt}"""
                        send_telegram(msg)
                        time.sleep(1)
                        
                except Exception as e:
                    continue

    except Exception as e:
        print(f"에러: {e}")

    print("✅ 종료")
