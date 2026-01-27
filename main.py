# ==========================================
# 📡 마스터 헌터: 실시간 포착 + 생존 신고 확실화 버전
# ==========================================
import os
import yfinance as yf
import pandas_ta as ta
import requests
import pandas as pd
from datetime import datetime
import pytz
import yahoo_fin.stock_info as si

# 1. 환경변수 및 텔레그램 설정
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
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

# --- [0. 시작 알림] ---
# 봇이 실행되자마자 무조건 보냄 (연결 확인용)
print(f"[{get_now()}] 🚀 봇 실행 시작")
send_telegram(f"[{get_now()}] 🔔 [주식분석 봇이 실행 되었습니다]\n시장 스캔을 시작합니다...")

# --- [1. 종목 발굴 레이더] ---
def get_hot_symbols():
    print("📡 시장 스캔 중...")
    hot_list = []
    try:
        # 급등주(15개) + 거래량상위(5개) + 내 관심종목
        hot_list.extend(si.get_day_gainers().head(15)['Symbol'].tolist())
        hot_list.extend(si.get_day_most_active().head(5)['Symbol'].tolist())
        hot_list.extend(["SOXL", "SOXS", "TQQQ", "SQQQ", "NVDA", "TSLA", "MSTR", "COIN"])
        return list(set(hot_list))
    except Exception as e:
        print(f"스캔 에러(기본 종목 사용): {e}")
        return ["SOXL", "NVDA", "TQQQ", "TSLA", "MSTR", "COIN"]

# --- [2. 퀀트 분석 엔진] ---
def analyze_market(ticker, df):
    latest = df.iloc[-1]
    score = 0
    reasons = []
    
    # 동전주($3 미만) 제외
    if latest['Close'] < 3: return 0, [], 0

    # 전략 1: 모멘텀
    if latest['Close'] > df['Open'].iloc[-1]:
        score += 20
        if (latest['Close'] - df['Open'].iloc[-1]) / df['Open'].iloc[-1] > 0.05:
            score += 10
            reasons.append("🔥 오늘 5% 이상 급등")

    # 전략 2: 거래량
    vol_ma = df['Volume'].rolling(20).mean().iloc[-1]
    if latest['Volume'] > vol_ma * 1.5:
        score += 20
        reasons.append("🟢 거래량 폭발")

    # 전략 3: 보조지표
    rsi = latest['RSI_14']
    if 40 <= rsi <= 75: score += 20 
    
    macd = latest['MACD_12_26_9']
    if macd > latest['MACDs_12_26_9']: 
        score += 20
        reasons.append("🟢 MACD 상승신호")

    # 전략 4: 이격도
    sma_20 = df['Close'].rolling(20).mean().iloc[-1]
    disparity = (latest['Close'] / sma_20) * 100
    if 98 <= disparity <= 110: score += 10

    return score, reasons, latest['Close']

# --- [3. 메인 실행 루프] ---
try:
    targets = get_hot_symbols()
    print(f"👉 타겟: {targets}")
    
    found_stocks = 0  # 찾은 종목 수

    data = yf.download(targets, period="5d", interval="5m", progress=False)
    
    if not data.empty:
        for ticker in targets:
            try:
                # 데이터 추출
                try: df = data.xs(ticker, axis=1, level=1)
                except: df = data
                
                if len(df) < 30: continue # 데이터 부족하면 패스
                
                # 지표 계산
                df['RSI_14'] = ta.rsi(df['Close'], length=14)
                df = pd.concat([df, ta.macd(df['Close'])], axis=1)
                
                # 분석
                score, reasons, price = analyze_market(ticker, df)
                
                # [조건 1] 70점 이상이면 매수 신호 발송
                if score >= 70:
                    found_stocks += 1
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
[이유]
{', '.join(reasons)}"""
                    send_telegram(msg)
                    print(f"🔔 알림 전송 완료: {ticker}")

                # [디버깅용] 점수 낮아도 로그는 남김
                else:
                    print(f"❌ {ticker}: {score}점")
                    
            except Exception as e:
                print(f"종목 분석 중 에러({ticker}): {e}")
                continue

    # --- [4. 생존 신고 (결과 보고)] ---
    # 종목을 하나도 못 찾았으면, 살아있다고 보고함
    if found_stocks == 0:
        print("📭 조건 만족 종목 없음")
        # 여기가 핵심! 샵(#) 없이 무조건 보내게 설정함
        send_telegram(f"[{get_now()}] 📭 현재 70점 넘는 급등주가 없습니다.\n(봇은 정상 작동 중입니다. 5분 뒤 다시 봅니다.)")

except Exception as e:
    print(f"심각한 에러 발생: {e}")
    send_telegram(f"⚠️ 봇 에러 발생: {e}")
