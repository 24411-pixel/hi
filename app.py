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
    return "고령층 안심 복약 가전 '라포(Rapport)' 실버 IoT 서버가 정상 구동 중입니다."


# =====================================================================
# [시나리오 1 / 블록 1 관련] 기기 배터리 및 알약 잔량 상태 원격 조회 스킬
# =====================================================================
@app.route("/device-status", methods=["GET", "POST"])
def device_status():
    status_code = random.randint(1, 3)
    if status_code == 1:
        msg = "🔋 [라포 안심 확인]\n\n어르신, 현재 약통 기기가 정상적으로 잘 연결되어 있습니다. 안심하셔도 좋습니다!\n\n* 남은 배터리: 85% (충분함)"
    elif status_code == 2:
        msg = "⚠️ [라포 알림]\n\n어르신, 1번 약통에 보관된 알약이 얼마 남지 않았습니다. 자녀분이나 생활지원사분께 약을 채워달라고 말씀해 주세요."
    else:
        msg = "ℹ️ [라포 상태 안내]\n\n현재 약통 기기가 절전 모드입니다. 약 드실 시간이 되면 자동으로 알림 불빛이 켜지니 걱정 마세요."
    return jsonify(kakao_text(msg))


# =====================================================================
# [시나리오 2 / 블록 7 관련] 핵심: Gemini AI 건강비서 및 하드웨어 LED 연동 스킬
# =====================================================================
@app.route("/ai-dose-docent", methods=["POST"])
def ai_dose_docent():
    data = request.get_json(silent=True) or {}
    
    # 오픈빌더에 설정한 '파라미터' 값을 먼저 가져오고, 없으면 어르신의 전체 입력 문장을 사용합니다.
    tt = data.get("action", {}).get("params", {}).get("파라미터", "").strip()
    if not tt:
        tt = data.get("userRequest", {}).get("utterance", "").strip()

    if not tt or tt == "약 검색":
        return jsonify(kakao_text("궁금하신 알약의 이름을 입력해 주세요.\n\n(예: 타이레놀 알려줘)"))

    api_key = os.getenv("AIzaSyBBFN99XnZYKjfXmseS4lGwvA7KMH0P1j4
")
    if not api_key:
        return jsonify(kakao_text("서버에 GEMINI_API_KEY가 설정되지 않았습니다."))

    # 실버 디자인 콘셉트에 맞춘 고령층 친화적 프롬프트 엔지니어링 세팅
    system_instruction = (
        "당신은 고령층 어르신들을 위한 스마트 약통 '라포(Rapport)'의 다정한 건강 비서 AI입니다. "
        "글씨가 잘 안 보이고 복잡한 것을 싫어하시는 노년층 사용자가 약 이름을 입력하면 다음 규칙을 무조건 지켜서 답변하세요:\n"
        "1. 전문 용어를 완전히 배제하고, '감기 기운 잡는 약', '피를 맑게 해주는 혈압약'처럼 초등학생도 알기 쉽게 효능을 딱 2줄로 설명하세요.\n"
        "2. 가장 중요한 복용 타이밍(예: 아침 식사하고 바로 드세요!)을 이모티콘을 섞어 아주 크고 명확하게 강조해 주세요.\n"
        "3. 마지막 줄에는 반드시 '💡 [라포 스마트 약통 연동 완료]: 어르신이 헷갈리지 않도록 해당 알약이 들어있는 약통 칸에 밝은 가이드 불빛(LED)을 켰습니다!' 라는 문장으로 마무리하세요."
    )

    try:
        client = genai.Client(api_key=api_key)
        full_prompt = f"{system_instruction}\n\n사용자 질문(약이름): {tt}"

        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=full_prompt
        )
        result_text = response.text if response.text else "AI 분석에 실패했습니다."
    except Exception as e:
        result_text = f"Gemini 건강 비서 시스템 오류: {str(e)}"

    return jsonify(kakao_text(result_text))


# =====================================================================
# [시나리오 2 / 블록 8 관련] 의약품 오남용 및 부작용 방지 최신 뉴스 크롤링 스킬
# =====================================================================
@app.route("/medication-news", methods=["POST"])
def medication_news():
    data = request.get_json(silent=True) or {}
    user_input = data.get("action", {}).get("params", {}).get("파라미터", "").strip()
    if not user_input:
        user_input = data.get("userRequest", {}).get("utterance", "").strip()

    if not user_input or user_input == "부작용 뉴스":
        return jsonify(kakao_text("부작용을 확인할 약 이름을 입력해 주세요."))

    search_query = f"{user_input} 부작용 주의사항"
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
                f"📰 [{user_input}] 꼭 알아야 할 안심 안전 뉴스\n\n"
                + "\n\n".join([f"👵 {title}" for title in titles])
                + f"\n\n⚠️ 다른 약과 함께 드실 때는 자녀분이나 의사 선생님께 꼭 한 번 물어보고 드시는 것이 안전합니다."
            )
        else:
            result_text = f"'{user_input}'에 대한 특이 부작용 뉴스가 최근 없습니다. 안심하고 정량 복용하세요."

    except Exception as e:
        result_text = f"안전 뉴스 확인 중 오류 발생: {str(e)}"

    return jsonify(kakao_text(result_text))


# =====================================================================
# [시나리오 3 / 블록 12 관련] 실시간 울산 날씨 정보 기반 생활 건강 가이드 스킬
# =====================================================================
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
                f"🌦️ [라포 매니저의 오늘의 날씨 가이드]\n\n"
                f"현재 울산 지역은 {weather_brief} 상태이며, {weather_desc}.\n\n"
                f"💡 [어르신 행동 가이드]\n"
                f"오늘같이 환절기 날씨에는 혈압이 갑자기 변할 수 있으니 혈압약을 거르지 말고 꼭 챙겨 드세요. "
                f"외출 시에는 따뜻한 외투를 입으시는 것을 추천합니다!"
            )
        else:
            result_text = "날씨 센서 데이터를 가져오지 못했습니다."

    except Exception as e:
        result_text = f"날씨 조회 중 오류 발생: {str(e)}"

    return jsonify(kakao_text(result_text))


# =====================================================================
# [시나리오 3 / 블록 14 관련] 노년층 사용성 개선 피드백 수집 스킬
# =====================================================================
@app.route("/design-feedback", methods=["POST"])
def design_feedback():
    data = request.get_json(silent=True) or {}
    user_input = data.get("userRequest", {}).get("utterance", "입력값이 없습니다.")
    reply = (
        f"✍️ [의견 접수 완료]\n\n"
        f"보내주신 내용: \"{user_input}\"\n\n"
        f"어르신들이 글씨를 읽거나 약통을 쓰실 때 더 편하도록, 하드웨어 및 글자 크기 디자인 수정에 꼭 반영하겠습니다. 감사합니다!"
    )
    return jsonify(kakao_text(reply))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
