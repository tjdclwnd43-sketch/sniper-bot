# ==========================================
# 📡 마스터 헌터: 실시간 포착 + 매매 전략 가이드
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
        # 급등주 + 거래량 상위 + 내 관심종목
        hot_list.extend(si.get_day_gainers().head(15)['Symbol'].tolist())
        hot_list.extend(si.get_day_most_active().head(5)['Symbol'].tolist())
        hot_list.extend(["SOXL", "SOXS", "TQQQ", "SQQQ", "NVDA", "TSLA", "MSTR", "COIN"])
        return list(set(hot_list))
    except:
        return ["SOXL", "NVDA", "TQQQ", "TSLA"]

# --- [2. 퀀트 분석 및 가격 전략 수립] ---
def analyze_market(ticker, df):
    latest = df.iloc[-1]
    score = 0
    reasons = []
    
    # 동전주($3 미만) 제외 - 너무 위험함
    if latest['Close'] < 3: return 0, [], 0

    # 전략 1: 모멘텀 (오늘 오르는 놈이 더 간다)
    if latest['Close'] > df['Open'].iloc[-1]:
        score += 20
        # 5% 이상 급등 중이면 가산점
        if (latest['Close'] - df['Open'].iloc[-1]) / df['Open'].iloc[-1] > 0.05:
            score += 10
            reasons.append("🔥 오늘 5% 이상 급등 중")

    # 전략 2: 거래량 (수급은 거짓말 안 한다)
    vol_ma = df['Volume'].rolling(20).mean().iloc[-1]
    if latest['Volume'] > vol_ma * 1.5:
        score += 20
        reasons.append("🟢 거래량 1.5배 폭발")

    # 전략 3: 보조지표 (RSI, MACD)
    rsi = latest['RSI_14']
    if 40 <= rsi <= 75: 
        score += 20 # 상승 추세 구간
    
    macd = latest['MACD_12_26_9']
    if macd > latest['MACDs_12_26_9']: 
        score += 20
        reasons.append("🟢 MACD 골든크로스 (상승신호)")

    # 전략 4: 이격도 (눌림목 체크)
    sma_20 = df['Close'].rolling(20).mean().iloc[-1]
    disparity = (latest['Close'] / sma_20) * 100
    if 98 <= disparity <= 110: 
        score += 10 # 너무 과열되지 않은 좋은 자리

    return score, reasons, latest['Close']

# --- [3. 메인 실행] ---
print(f"[{get_now()}] 🚀 헌터 봇 가동")

# (테스트용) 시작 알림 - 필요 없으면 주석 처리 하세요
# send_telegram(f"[{get_now()}] 🔔 헌터 봇 가동 시작 (감시 중...)")

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
                
                # 지표 계산
                df['RSI_14'] = ta.rsi(df['Close'], length=14)
                df = pd.concat([df, ta.macd(df['Close'])], axis=1)
                
                score, reasons, price = analyze_market(ticker, df)
                
                # [알림 발송] 70점 이상일 때 매매 가이드 포함해서 전송
                if score >= 70:
                    # [자동 매매 가이드 계산]
                    # 급등주 특성상: 손절은 짧게(-3%), 익절은 길게(+5%~10%) 잡음
                    stop_loss = price * 0.97
                    target_price = price * 1.05
                    
                    msg = f"""🎯 [매수 신호 포착]
종목: {ticker}
점수: {score}점
--------------------
💰 현재가: ${price:.2f}
🚀 목표가: ${target_price:.2f} (+5%)
🛡️ 손절가: ${stop_loss:.2f} (-3%)
--------------------
[추천 이유]
{', '.join(reasons)}
--------------------
※ 이 가격 전략은 봇의 추천입니다.
진입 시 손절가는 반드시 HTS에 걸어두세요."""
                    
                    send_telegram(msg)
                    print(f"🔔 알림 전송: {ticker}")
            except: continue
except Exception as e: print(e)
