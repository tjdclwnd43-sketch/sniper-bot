import os
import requests
import time
from datetime import datetime
import pytz
from tradingview_ta import TA_Handler, Interval, Exchange

# =========================================================
# ⚙️ [설정] 마스터 헌터 봇 (최종 완성본)
# =========================================================

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# 🔥 기준 점수: 80 (테스트하려면 10으로 낮추세요)
ALERT_THRESHOLD = 80

# 감시할 종목 리스트
SYMBOLS = [
    # [1] 3배 레버리지 (대부분 AMEX)
    "SOXL", "SOXS", "TQQQ", "SQQQ", "FNGU", "FNGD",
    "BULZ", "LABU", "LABD", "YINN", "YANG", "TMF", "TMV",
    
    # [2] 비트코인 & 코인주 (NASDAQ)
    "MSTR", "MSTX", "MSTU", "COIN", "HOOD",
    "MARA", "RIOT", "CLSK", "BITO", "IBIT",

    # [3] 빅테크 & 반도체 (NASDAQ)
    "NVDA", "TSLA", "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "AMD", "AVGO", "MU", "INTC", "ARM", "TSM", "SMCI",
    "PLTR", "SOFI", "GME", "AMC", "RIVN", "LCID"
]

# =========================================================
# 📡 봇 로직
# =========================================================

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except: pass

def get_exchange_and_screener(symbol):
    """종목에 맞는 거래소를 자동으로 찾아줍니다"""
    # AMEX 거래소 목록 (주로 3배 레버리지 ETF)
    amex_list = ["SOXL", "SOXS", "LABU", "LABD", "FNGU", "FNGD", "BULZ", "DPST", "NAIL", "YINN", "YANG"]
    
    if symbol in amex_list:
        return "AMEX"
    
    # 나머지는 대부분 NASDAQ
    return "NASDAQ"

def calculate_master_score(analysis):
    if analysis is None: return 0, 0
    summary = analysis.summary
    total = summary['BUY'] + summary['SELL'] + summary['NEUTRAL']
    if total == 0: return 0, 0
    score = (summary['BUY'] / total) * 100
    return score, summary['BUY']

def run_bot():
    korea_tz = pytz.timezone('Asia/Seoul')
    now_str = datetime.now(korea_tz).strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"[{now_str}] 🔭 마스터 헌터 가동... (기준: {ALERT_THRESHOLD}점)")
    
    alert_messages = []
    
    for sym in SYMBOLS:
        try:
            # 1. 거래소 자동 선택
            my_exchange = get_exchange_and_screener(sym)
            
            # 2. 데이터 가져오기
            handler = TA_Handler(
                symbol=sym,
                screener="america",
                exchange=my_exchange,
                interval=Interval.INTERVAL_5_MINUTES
            )
            analysis = handler.get_analysis()
            
            # 3. 점수 및 가격 계산
            score, buys = calculate_master_score(analysis)
            price = analysis.indicators['close']
            
            # 로그 출력 (확인용)
            # print(f"👉 {sym}: {score:.0f}점 (${price})")
            
            # 4. 알림 조건 체크
            if score >= ALERT_THRESHOLD:
                rsi = analysis.indicators.get('RSI', 0)
                print(f"🔥 포착: {sym} ({score:.0f}점)")
                
                icon = "🦄" if score >= 90 else "🔥"
                msg = f"""{icon} **{sym}** 포착!
💯 점수: **{score:.0f}점** (매수 {buys}개)
💰 현재가: ${price}
📊 RSI: {rsi:.1f}
--------------------"""
                alert_messages.append(msg)
            
            # 🔥 [핵심] 차단 방지를 위해 1초 쉬기 (천천히)
            time.sleep(1)

        except Exception as e:
            # 에러 나면 그냥 넘어가고 다음 종목 봄
            # print(f"⚠️ {sym} 패스")
            time.sleep(1)
            continue

    if alert_messages:
        full_msg = f"🚀 **[마스터 리포트]** {now_str}\n기준: {ALERT_THRESHOLD}점 이상\n\n" + "\n".join(alert_messages)
        if len(full_msg) > 4000: send_telegram(full_msg[:4000])
        else: send_telegram(full_msg)
        print(f"🔔 {len(alert_messages)}개 알림 전송 완료")
    else:
        print(f"💤 {ALERT_THRESHOLD}점 넘는 종목이 없습니다.")

if __name__ == "__main__":
    run_bot()
