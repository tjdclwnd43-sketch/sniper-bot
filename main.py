import os
import requests
import time
from datetime import datetime
import pytz
from tradingview_ta import TA_Handler, Interval, Exchange

# =========================================================
# ⚙️ [설정] 마스터 헌터 봇
# =========================================================

# 1. 텔레그램 토큰 (깃허브 Secrets에서 가져옴)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# 2. 알림 기준 점수 (테스트할 때는 10, 평소에는 80)
# 🔥 여기를 10으로 바꾸면 바로 알림이 옵니다!
ALERT_THRESHOLD = 10

# 3. 감시할 종목 리스트
SYMBOLS = [
    # [1] 3배 레버리지
    "SOXL", "SOXS", "TQQQ", "SQQQ", "FNGU", "FNGD",
    "BULZ", "LABU", "LABD", "YINN", "YANG", "TMF", "TMV",
    
    # [2] 비트코인 & 크립토
    "MSTR", "MSTX", "MSTU", "COIN", "HOOD",
    "MARA", "RIOT", "CLSK", "BITO", "IBIT",

    # [3] 빅테크
    "NVDA", "TSLA", "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "NFLX", "ADBE",

    # [4] 반도체 & AI
    "AMD", "AVGO", "MU", "INTC", "QCOM", "ARM", "TSM", "SMCI",

    # [5] 바이오 & 기타
    "PLTR", "SOFI", "LLY", "NVO", "GME", "AMC", "RIVN", "LCID"
]

# =========================================================
# 📡 봇 로직
# =========================================================

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ 텔레그램 토큰 없음: Secrets 설정을 확인하세요.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print(f"❌ 전송 실패: {e}")

def calculate_master_score(analysis):
    if analysis is None: return 0, 0, 0
    summary = analysis.summary
    buy = summary['BUY']
    sell = summary['SELL']
    neutral = summary['NEUTRAL']
    total = buy + sell + neutral
    if total == 0: return 0, 0, 0
    score = (buy / total) * 100
    return score, buy, sell

def run_bot():
    korea_tz = pytz.timezone('Asia/Seoul')
    now_str = datetime.now(korea_tz).strftime('%Y-%m-%d %H:%M:%S')
    
    # 🔥 [수정] 현재 설정된 점수를 로그에 정확히 표시
    print(f"[{now_str}] 🔭 마스터 헌터 가동... (기준: {ALERT_THRESHOLD}점 이상)")
    
    alert_messages = []
    
    for sym in SYMBOLS:
        try:
            handler = TA_Handler(
                symbol=sym,
                screener="america",
                exchange="NASDAQ",
                interval=Interval.INTERVAL_5_MINUTES
            )
            analysis = handler.get_analysis()
            score, buys, sells = calculate_master_score(analysis)
            
            # 로그에 점수 출력
            # print(f"👉 {sym}: {score:.0f}점") 
            
            if score >= ALERT_THRESHOLD:
                price = analysis.indicators['close']
                rsi = analysis.indicators.get('RSI', 0)
                
                print(f"🔥 알림 당첨: {sym} ({score:.0f}점)")
                
                icon = "🦄" if score >= 90 else "🔥"
                msg = f"""{icon} **{sym}** 포착!
💯 점수: **{score:.0f}점** (매수 {buys}개)
💰 현재가: ${price}
📊 RSI: {rsi:.1f}
--------------------"""
                alert_messages.append(msg)
                
        except Exception as e:
            continue

    if alert_messages:
        header = f"🚀 **[마스터 리포트]** {now_str}\n기준: {ALERT_THRESHOLD}점 이상\n\n"
        full_msg = header + "\n".join(alert_messages)
        
        if len(full_msg) > 4000:
            send_telegram(full_msg[:4000] + "\n...(생략)")
        else:
            send_telegram(full_msg)
        print(f"🔔 {len(alert_messages)}개 종목 알림 전송 완료")
    else:
        # 🔥 [수정] 설정된 점수에 맞춰서 로그 출력
        print(f"💤 {ALERT_THRESHOLD}점 넘는 종목이 없습니다.")

if __name__ == "__main__":
    run_bot()
