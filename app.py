import os
import random
import requests
import ssl
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from google import genai

app = Flask(__name__)


def kakao_text(text):
    """카카오톡 텍스트 응답 규격 생성 (1000자 제한 안전장치)"""
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {"simpleText": {"text": text[:950] + "..." if len(text) > 950 else text}}
            ]
        },
    }


@app.route("/", methods=["GET"])
def home():
    return "유니버셜 복약 가전 '라포(Rapport)' IoT 제어 서버가 구동 중입니다."


# [블록 1용] 테스트 및 하드웨어 페어링 확인용 랜덤 코드
@app.route("/device-status", methods=["GET", "POST"])
def device_status():
    status_code = random.randint(1, 3)
    if status_code == 1:
        msg = "🔄 [라포 디바이스 상태]: 정상 연결됨 / 잔여 배터리 85%"
    elif status_code == 2:
        msg = "⚠️ [라포 디바이스 상태]: 내부 약통(1번 모듈)의 약이 부족합니다. 충전해 주세요."
    else:
        msg = "ℹ️ [라포 디바이스 상태]: 디바이스가 절전 모드입니다. 카톡 명령 시 해제됩니다."
    return jsonify(kakao_text(msg))


# [블록 2용] 사용자가 등록한 제품 외형 및 UI 가이드 이미지 출력
@app.route("/device-image", methods=["GET", "POST"])
def device_image():
    response = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleImage": {
                        "imageUrl": "https://t1.daumcdn.net/friends/prod/category/M001_friends_ryan2.jpg",
                        "altText": "유니버셜 복약 가전 '라포' 하드웨어 CMF 가이드 라인",
                    }
                }
            ]
        },
    }
    return jsonify(response)


# [블록 3용] 사용자 불편사항/개선 아이디어 수집 (서비스 디자인 에셋)
@app.route("/design-feedback", methods=["POST"])
def design_feedback():
    data = request.get_json(silent=True) or {}
    user_input = data.get("userRequest", {}).get("utterance", "입력값이 없습니다.")
    reply = (
        f"✍️ [디자인 피드백 접수완료]\n\n"
        f"보내주신 내용: \"{user_input}\"\n\n"
        f"시각장애인 사용성 개선을 위한 제품 2차 고도화(UI/UX 수정) 과정에 소중히 반영하겠습니다."
    )
    return jsonify(kakao_text(reply))


# [블록 4용] 사용자가 입력한 약에 대한 최신 뉴스/부작용 정보 검색 크롤링
@app.route("/medication-news", methods=["POST"])
def medication_news():
    data = request.get_json(silent=True) or {}
    user_input = (
        data.get("action", {}).get("params", {}).get("파라미터", "").strip()
    )
    if not user_input:
        user_input = data.get("userRequest", {}).get("utterance", "").strip()

    if not user_input:
        return jsonify(kakao_text("조회할 의약품 이름을 입력해 주세요."))

    search_query = f"{user_input} 주의사항"
    query = urllib.parse.quote(search_query)
    url = f"https://search.naver.com/search.naver?where=news&query={query}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".news_tit")

        titles = []
        for item in items[:4]:
            titles.append(item.get("title", item.get_text(strip=True)))

        if titles:
            result_text = (
                f"📰 [{user_input}] 관련 필수 안전 정보 뉴스:\n\n"
                + "\n\n".join([f"{i+1}. {title}" for i, title in enumerate(titles)])
                + "\n\n⚠️ 복용 전 위 뉴스 항목의 부작용 사례를 반드시 확인하세요."
            )
        else:
            result_text = f"'{user_input}'에 대한 최근 안전 뉴스가 없습니다. 정량 복용을 권장합니다."

    except Exception as e:
        result_text = f"안전 정보 조회 중 시스템 오류: {str(e)}"

    return jsonify(kakao_text(result_text))


# [블록 5용] 시각장애인 외출 환경 분석을 위한 실시간 울산 날씨 가이드 크롤링
@app.route("/blind-weather-guide", methods=["GET", "POST"])
def blind_weather_guide():
    try:
        context = ssl._create_unverified_context()
        url = "https://search.naver.com/search.naver?query=%EC%9A%B8%EC%82%B0%20%EB%82%A0%EC%94%A8"

        webpage = urllib.request.urlopen(url, context=context)
        soup = BeautifulSoup(webpage, "html.parser")

        temps = soup.find("div", class_="temperature_text")
        summary = soup.find("p", class_="summary")

        if temps and summary:
            weather_brief = temps.get_text(strip=True)
            weather_desc = summary.get_text(strip=True)

            result_text = (
                f"☀️ [라포 웰니스 매니저: 실시간 외출 가이드]\n\n"
                f"현재 울산 지역은 {weather_brief} 상태이며, {weather_desc}.\n\n"
                f"💡 시각장애인 사용자의 안전한 도보 이동을 위해 우산 소지 여부나 눈/비로 인한 미끄러짐에 주의하라고 제품 음성(TTS) 가이드를 송출합니다."
            )
        else:
            result_text = "날씨 센서 데이터를 가져오지 못했습니다."

    except Exception as e:
        result_text = f"외출 가이드 조회 중 오류 발생: {str(e)}"

    return jsonify(kakao_text(result_text))


# [블록 6용] 핵심: Gemini를 활용한 약 인지 및 제품 VUI 인터랙션
@app.route("/ai-dose-docent", methods=["POST"])
def ai_dose_docent():
    data = request.get_json(silent=True) or {}
    tt = data.get("action", {}).get("params", {}).get("파라미터", "").strip()

    if not tt:
        return jsonify(kakao_text("알아보고자 하는 약 이름을 말씀해 주세요."))

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return jsonify(kakao_text("서버에 GEMINI_API_KEY가 설정되지 않았습니다."))

    system_instruction = (
        "당신은 유니버셜 스마트 약통 '라포(Rapport)'의 지능형 음성 UI 인터페이스입니다. "
        "시각장애인이나 약을 헷갈리기 쉬운 노약자가 약 이름을 입력하면 "
        "1. 어떤 효능이 있는 약인지 초등학생도 이해할 수 있게 2줄로 요약하고 "
        "2. 반드시 지켜야 할 복용 타이밍(식전/식후 등)을 큰 글씨 느낌으로 강조해 주세요. "
        "3. 마지막 줄에는 반드시 '[라포 하드웨어 연동 부가알림]: 해당 약이 보관된 모듈 가이드 LED 점등 및 점자 돌기 개방 완료.' 라는 문장을 출력하세요."
    )

    try:
        client = genai.Client(api_key=api_key)
        full_prompt = f"{system_instruction}\n\n사용자 질문(약이름): {tt}"

        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=full_prompt
        )
        result_text = response.text if response.text else "AI 분석에 실패했습니다."
    except Exception as e:
        result_text = f"Gemini 인터페이스 구동 오류: {str(e)}"

    return jsonify(kakao_text(result_text))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
