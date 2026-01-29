import os
import requests
import time
from datetime import datetime
import pytz
from tradingview_ta import TA_Handler, Interval, Exchange

# =========================================================
# ⚙️ [설정] 마스터 헌터 봇 (보안 패치 버전)
# =========================================================

# 🚨 [중요] 여기에 토큰을 직접 적지 마세요!
# 깃허브 'Secrets'에서 안전하게 가져오는 코드입니다.
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# 2. 감시할 종목 리스트 (풀 스펙)
SYMBOLS = [
    # [1] 3배 레버리지 (야수의 심장)
    "SOXL", "SOXS", "TQQQ", "SQQQ", "FNGU", "FNGD",
    "BULZ", "LABU", "LABD", "YINN", "YANG", "TMF", "TMV",
    
    # [2] 비트코인 & 크립토 (MSTR 형제들)
    "MSTR", "MSTX", "MSTU", "COIN", "HOOD",
    "MARA", "RIOT", "CLSK", "BITO", "IBIT",

    # [3] 빅테크 (M7)
    "NVDA", "TSLA", "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "NFLX", "ADBE",

    # [4] 반도체 & AI
    "AMD", "AVGO", "MU", "INTC", "QCOM", "ARM", "TSM", "SMCI",

    # [5] 바이오 & 핀테크 & 기타
    "PLTR", "SOFI", "LLY", "NVO", "GME", "AMC", "RIVN", "LCID"
]

# 3. 알림 기준 점수 (80점 이상이면 알림)
ALERT_THRESHOLD = 80 

# =========================================================
# 📡 봇 로직
# =========================================================

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        # 토큰이 없으면 로그만 남기고 전송 안 함
        print("❌ 텔레그램 토큰을 못 찾았습니다. Settings > Secrets를 확인하세요.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

def calculate_master_score(analysis):
    """트레이딩뷰 보조지표를 0~100점 점수로 환산"""
    if analysis is None: return 0, 0, 0
    
    summary = analysis.summary
    buy = summary['BUY']
    sell = summary['SELL']
    neutral = summary['NEUTRAL']
    total = buy + sell + neutral
    
    if total == 0: return 0, 0, 0
    
    # 점수 공식: 매수 시그널 비율
    score = (buy / total) * 100
    return score, buy, sell

def run_bot():
    korea_tz = pytz.timezone('Asia/Seoul')
    now_str = datetime.now(korea_tz).strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"[{now_str}] 🔭 마스터 헌터 가동... (대상: {len(SYMBOLS)}개)")
    
    alert_messages = []
    
    # 분석 시작
    for sym in SYMBOLS:
        try:
            handler = TA_Handler(
                symbol=sym,
                screener="america",
                exchange="NASDAQ",
                interval=Interval.INTERVAL_5_MINUTES # 5분봉 기준
            )
            analysis = handler.get_analysis()
            
            # 점수 계산
            score, buys, sells = calculate_master_score(analysis)
            
            # 80점 이상인 경우에만 알림 목록에 추가
            if score >= ALERT_THRESHOLD:
                price = analysis.indicators['close']
                rsi = analysis.indicators.get('RSI', 0)
                
                print(f"🔥 포착: {sym} ({score:.0f}점)")
                
                icon = "🦄" if score >= 90 else "🔥"
                msg = f"""{icon} **{sym}** 급등 신호!
💯 점수: **{score:.0f}점** (매수 {buys}개)
💰 현재가: ${price}
📊 RSI: {rsi:.1f}
--------------------"""
                alert_messages.append(msg)
                
        except Exception as e:
            continue

    # 결과 전송
    if alert_messages:
        header = f"🚀 **[마스터 5분봉 리포트]** {now_str}\n기준: 80점 이상\n\n"
        full_msg = header + "\n".join(alert_messages)
        
        if len(full_msg) > 4000:
            send_telegram(full_msg[:4000] + "\n...(생략)")
        else:
            send_telegram(full_msg)
        print("🔔 알림 전송 완료")
    else:
        print("💤 강력한 매수 신호(80점↑)가 없습니다.")

if __name__ == "__main__":
    run_bot()
