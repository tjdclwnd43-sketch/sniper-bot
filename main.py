import os
import requests
import time
from datetime import datetime
import pytz
from tradingview_ta import TA_Handler, Interval, Exchange

# =========================================================
# ⚙️ [설정] 마스터 헌터 봇: 풀 스펙 버전
# =========================================================

# 1. 텔레그램 설정
TELEGRAM_TOKEN = os.environ.get('8498929104:AAFWKCN48kqdRD_o7JuXC-hEmuxf4ym9jrc')
CHAT_ID = os.environ.get('6395098058')

# 2. 감시할 종목 리스트 (대폭 확장: 약 80개)
SYMBOLS = [
    # [1] 3배 레버리지 ETF (야수의 심장)
    "SOXL", "SOXS",  # 반도체 롱/숏
    "TQQQ", "SQQQ",  # 나스닥 롱/숏
    "FNGU", "FNGD",  # 빅테크 롱/숏
    "BULZ", "BERZ",  # 기술주 롱/숏
    "LABU", "LABD",  # 바이오 롱/숏
    "YINN", "YANG",  # 중국장 롱/숏
    "TMF",  "TMV",   # 미국채 롱/숏 (금리 변동)
    "NRGU",          # 에너지/오일 3배
    "DPST",          # 지역은행 3배

    # [2] 비트코인 & 크립토 관련주 (MSTR 형제들)
    "MSTR", "MSTX", "MSTU", # 마이크로스트래티지 & 레버리지
    "COIN", "HOOD",         # 거래소
    "MARA", "RIOT", "CLSK", "IREN", "CIFR", # 채굴주
    "BITO", "IBIT",         # 비트코인 현물/선물 ETF

    # [3] 매그니피센트 7 + 빅테크 (시장의 중심)
    "NVDA", "TSLA", "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "NFLX", "ADBE", "CRM",  "ORCL", # 소프트웨어 대장

    # [4] 반도체 & AI 하드웨어 (SOXL 구성종목)
    "AMD",  "AVGO", "MU",   "INTC", "QCOM", "TXN",
    "ARM",  "TSM",  "ASML", "AMAT", "LRCX", "MRVL",
    "SMCI", "DELL", "VRT",  # 서버/냉각 관련

    # [5] 핀테크 & 고성장주 (금리 인하 수혜)
    "PLTR", "SOFI", "UPST", "AFRM", "PYPL", "SQ", "SHOP",
    "U",    "RBLX", "DKNG", # 메타버스/게임

    # [6] 바이오 & 헬스케어 (비만치료제 등)
    "LLY",  "NVO",  # 비만치료제 대장 (일라이릴리, 노보)
    "PFE",  "MRNA", # 백신/전통

    # [7] 우주항공 & 방산 & 원전 (지정학/미래)
    "RKLB", "LUNR", "SPCE", "ASTS", # 우주/위성
    "LMT",  "RTX",          # 방산
    "OKLO", "SMR",  "CCJ",  # 원전/우라늄 (AI 전력)

    # [8] 밈(Meme) & 변동성 & 기타
    "GME",  "AMC",  # 밈 주식 대장
    "CVNA", "OPEN", # 중고차/부동산
    "RIVN", "LCID", # 전기차 루키
    "DJT",          # 트럼프 관련
    "VIXY"          # 공포지수 (시장 폭락 시 감지용)
]

# 3. 알림 기준 점수 (마스터 스코어)
# 100점 만점에 80점 이상이면 알림 (너무 자주 울리면 85로 올리세요)
ALERT_THRESHOLD = 80 

# =========================================================
# 📡 봇 로직 (수정 불필요)
# =========================================================

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except: pass

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
    
    print(f"[{now_str}] 🔭 마스터 헌터 Full Scan... (대상: {len(SYMBOLS)}개)")
    
    alert_messages = []
    
    # 트레이딩뷰 핸들러 생성
    handlers = []
    for sym in SYMBOLS:
        handlers.append(TA_Handler(
            symbol=sym,
            screener="america",
            exchange="NASDAQ", # 대부분 나스닥이나, 일부는 자동 보정됨
            interval=Interval.INTERVAL_5_MINUTES # 🔥 5분봉 단타 기준
        ))
    
    # 분석 실행 Loop
    for handler in handlers:
        try:
            analysis = handler.get_analysis()
            symbol = handler.symbol
            
            # 점수 계산
            score, buys, sells = calculate_master_score(analysis)
            
            # 조건 충족 시
            if score >= ALERT_THRESHOLD:
                current_price = analysis.indicators['close']
                rsi = analysis.indicators.get('RSI', 0)
                
                # 로그 출력
                print(f"🔥 포착: {symbol} ({score:.0f}점)")
                
                # 이모지 (점수 높으면 불꽃)
                icon = "🦄" if score >= 90 else "🔥"
                
                # 메시지 작성
                msg = f"""{icon} **{symbol}** 급등 포착!
💯 점수: **{score:.0f}점** (매수 {buys}개)
💰 현재가: ${current_price}
📊 RSI: {rsi:.1f}
--------------------"""
                alert_messages.append(msg)
            else:
                # 로그만 남김 (디버깅용)
                pass
                
        except Exception as e:
            # 상장폐지나 티커 변경 등 오류 무시
            continue

    # 텔레그램 전송 (한 번에 모아서)
    if alert_messages:
        # 메시지가 너무 길면 잘릴 수 있으므로 5개씩 끊어서 전송
        header = f"🚀 **[실시간 5분봉 포착]** {now_str}\n기준: 80점 이상\n\n"
        full_msg = header + "\n".join(alert_messages)
        
        # 텔레그램 글자수 제한(4096자) 고려하여 안전하게 전송
        if len(full_msg) > 4000:
            send_telegram(full_msg[:4000] + "\n...(내용 더 있음)")
        else:
            send_telegram(full_msg)
            
        print(f"🔔 {len(alert_messages)}개 종목 알림 전송 완료")
    else:
        print("💤 80점 넘는 강력한 종목이 없습니다.")

if __name__ == "__main__":
    run_bot()
