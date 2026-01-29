import os
import requests
import time
from datetime import datetime
import pytz
from tradingview_ta import TA_Handler, Interval, get_multiple_analysis

# =========================================================
# ⚙️ [설정] 마스터 헌터 봇 (그룹 스캔 버전)
# =========================================================

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# 🔥 기준 점수: 80 (테스트할 땐 10)
ALERT_THRESHOLD = 80

# =========================================================
# 📋 감시할 종목 리스트 (거래소:티커 형식)
# =========================================================
# 이렇게 하면 봇이 헷갈리지 않고 정확히 찾아냅니다.

SYMBOLS_LIST = [
    # [AMEX 거래소] 3배 레버리지 ETF들
    "AMEX:SOXL", "AMEX:SOXS", "AMEX:LABU", "AMEX:LABD", 
    "AMEX:FNGU", "AMEX:FNGD", "AMEX:BULZ", "AMEX:DPST",
    "AMEX:NAIL", "AMEX:YINN", "AMEX:YANG", "AMEX:TMF", "AMEX:TMV",

    # [NASDAQ 거래소] 빅테크 & 반도체 & 코인
    "NASDAQ:MSTR", "NASDAQ:MSTX", "NASDAQ:MSTU", "NASDAQ:COIN", "NASDAQ:HOOD",
    "NASDAQ:NVDA", "NASDAQ:TSLA", "NASDAQ:AAPL", "NASDAQ:MSFT", "NASDAQ:GOOGL",
    "NASDAQ:AMZN", "NASDAQ:META", "NASDAQ:AMD",  "NASDAQ:AVGO", "NASDAQ:MU",
    "NASDAQ:INTC", "NASDAQ:ARM",  "NASDAQ:TSM",  "NASDAQ:SMCI", "NASDAQ:PLTR",
    "NASDAQ:TQQQ", "NASDAQ:SQQQ", "NASDAQ:MARA", "NASDAQ:RIOT", "NASDAQ:CLSK",
    "NASDAQ:RIVN", "NASDAQ:LCID", "NASDAQ:GME",  "NASDAQ:AMC"
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
    
    print(f"[{now_str}] 🔭 마스터 헌터 (그룹 스캔) 가동... (기준: {ALERT_THRESHOLD}점)")
    
    alert_messages = []
    
    try:
        # 🔥 [핵심] 50개 종목을 한 번에 조회 (Batch Request)
        # 이렇게 하면 속도가 빠르고 서버 차단을 안 당합니다.
        analyses = get_multiple_analysis(
            screener="america",
            interval=Interval.INTERVAL_5_MINUTES,
            symbols=SYMBOLS_LIST
        )
        
        # 결과 분석 Loop
        for symbol_key, analysis in analyses.items():
            try:
                if analysis is None: continue
                
                # 티커 이름만 깔끔하게 (AMEX:SOXL -> SOXL)
                clean_symbol = symbol_key.split(":")[1]
                
                score, buys = calculate_master_score(analysis)
                price = analysis.indicators['close']
                
                # 로그 출력 (이제 $nan 없이 가격이 잘 나올 겁니다)
                # print(f"👉 {clean_symbol}: {score:.0f}점 (${price})")
                
                if score >= ALERT_THRESHOLD:
                    rsi = analysis.indicators.get('RSI', 0)
                    print(f"🔥 포착: {clean_symbol} ({score:.0f}점)")
                    
                    icon = "🦄" if score >= 90 else "🔥"
                    msg = f"""{icon} **{clean_symbol}** 포착!
💯 점수: **{score:.0f}점** (매수 {buys}개)
💰 현재가: ${price}
📊 RSI: {rsi:.1f}
--------------------"""
                    alert_messages.append(msg)
                    
            except Exception as e:
                # 데이터 오류 나면 패스
                continue
                
    except Exception as e:
        print(f"❌ 전체 조회 중 오류 발생: {e}")

    # 결과 전송
    if alert_messages:
        full_msg = f"🚀 **[마스터 리포트]** {now_str}\n기준: {ALERT_THRESHOLD}점 이상\n\n" + "\n".join(alert_messages)
        if len(full_msg) > 4000: send_telegram(full_msg[:4000])
        else: send_telegram(full_msg)
        print(f"🔔 {len(alert_messages)}개 알림 전송 완료")
    else:
        print(f"💤 {ALERT_THRESHOLD}점 넘는 종목이 없습니다.")

if __name__ == "__main__":
    run_bot()
