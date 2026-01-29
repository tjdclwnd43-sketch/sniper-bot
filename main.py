import os
import requests
import time
from datetime import datetime
import pytz
from tradingview_ta import TA_Handler, Interval, Exchange

# =========================================================
# ⚙️ [설정] 마스터 헌터 봇 (재시도 강화 버전)
# =========================================================

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# 🔥 기준 점수: 80 (테스트 때는 10)
ALERT_THRESHOLD = 80

# 감시할 종목 리스트
SYMBOLS = [
    # [1] 3배 레버리지 (AMEX/NASDAQ 혼합)
    "SOXL", "SOXS", "TQQQ", "SQQQ", "FNGU", "FNGD",
    "BULZ", "LABU", "LABD", "YINN", "YANG", "TMF", "TMV",
    
    # [2] 비트코인 & 코인주
    "MSTR", "MSTX", "MSTU", "COIN", "HOOD",
    "MARA", "RIOT", "CLSK", "BITO", "IBIT",

    # [3] 빅테크 & 반도체
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

def get_exchange(symbol):
    """거래소 자동 분류 (AMEX ETF와 NASDAQ 구분)"""
    # AMEX에서 거래되는 주요 3배 ETF들
    amex_etfs = ["SOXL", "SOXS", "LABU", "LABD", "FNGU", "FNGD", "BULZ", "DPST", "NAIL", "YINN", "YANG"]
    if symbol in amex_etfs:
        return "AMEX"
    return "NASDAQ" # TQQQ, SQQQ, MSTR 등은 NASDAQ임

def get_data_with_retry(symbol):
    """실패하면 3번까지 다시 시도하는 함수"""
    my_exchange = get_exchange(symbol)
    
    for i in range(3): # 총 3번 시도
        try:
            handler = TA_Handler(
                symbol=symbol,
                screener="america",
                exchange=my_exchange,
                interval=Interval.INTERVAL_5_MINUTES
            )
            analysis = handler.get_analysis()
            
            # 데이터가 정상인지 확인 (가격이 없으면 재시도)
            if analysis is None or analysis.indicators['close'] is None:
                raise Exception("데이터 없음")
                
            return analysis # 성공하면 리턴
            
        except Exception:
            # 실패하면 1초 쉬고 다시 시도
            time.sleep(1)
            continue
            
    return None # 3번 다 실패하면 포기

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
            # 🔥 [핵심] 재시도 기능으로 데이터 가져오기
            analysis = get_data_with_retry(sym)
            
            if analysis is None:
                print(f"⚠️ {sym}: 데이터 불러오기 실패 ($nan)")
                continue

            score, buys = calculate_master_score(analysis)
            price = analysis.indicators['close']
            
            # 로그 출력 (성공한 것만)
            # print(f"👉 {sym}: {score:.0f}점 (${price})")
            
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
            
            # 🔥 [안전] 봇 차단 방지를 위해 3초 휴식 (천천히)
            time.sleep(3)

        except Exception as e:
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
