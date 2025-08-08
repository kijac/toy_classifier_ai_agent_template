import openai
import os
import json # JSON 파싱을 위해 필요합니다.
from dotenv import load_dotenv
from tools import scrape_website_text # tools 모듈이 필요합니다.
from tenacity import ( # tenacity 라이브러리 임포트
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type
)
from openai import OpenAIError # OpenAI 관련 오류 처리를 위해 임포트
import requests # requests 모듈을 사용하여 HTTP 요청을 보냅니다.

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

class Agent:
    """
    모든 에이전트의 기본이 되는 부모 클래스입니다.
    OpenAI API와의 통신을 담당합니다.
    """
    def __init__(self, model="gpt-4.1-nano", temperature=0.7):
        """
        에이전트 초기화
        :param model: 사용할 OpenAI 모델 이름
        :param temperature: 생성 결과의 창의성을 조절하는 값 (0.0 ~ 2.0)
        """
        self.model = model
        self.temperature = temperature
        self.history = []

    @retry(
        wait=wait_random_exponential(min=1, max=60), # 1초에서 60초 사이 지수 백오프
        stop=stop_after_attempt(6), # 최대 6번 재시도
        retry=(retry_if_exception_type(OpenAIError) | retry_if_exception_type(requests.exceptions.ConnectionError)) # OpenAI API 오류 또는 연결 오류 시 재시도
    )

    def execute_prompt(self, system_prompt, user_prompt):
        """
        주어진 프롬프트를 실행하고 결과를 반환합니다.
        메모리(이전 대화 기록)를 사용하여 연속적인 대화를 지원하며,
        API 오류 발생 시 재시도 로직이 포함됩니다.
        :param system_prompt: AI의 역할과 지침을 정의하는 시스템 메시지
        :param user_prompt: 사용자의 구체적인 요청 메시지
        :return: AI가 생성한 텍스트 응답
        """
        # (기존 코드와 동일)
        try:
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(self.history)
            messages.append({"role": "user", "content": user_prompt})

            response = openai.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
            )
            
            ai_response = response.choices[0].message.content

            self.history.append({"role": "user", "content": user_prompt})
            self.history.append({"role": "assistant", "content": ai_response})
            
            return ai_response
        except OpenAIError as e: # OpenAIError를 명시적으로 잡고 다시 raise하여 tenacity가 처리하도록 합니다.
            print(f"OpenAI API 호출 중 오류 발생 (재시도 예정): {e}")
            raise # tenacity가 재시도 로직을 실행하도록 예외를 다시 발생시킵니다.
        except Exception as e:
            print(f"예상치 못한 API 호출 중 오류가 발생했습니다: {e}")
            return None
        

from tools import scrape_website_text

class WebResearcher(Agent):
    """
    웹 리서치를 수행하고 정보를 요약하는 에이전트입니다.
    """
    def __init__(self, model="gpt-4.1-nano", temperature=0.7):
        super().__init__(model, temperature)
        self.system_prompt = """
        당신은 세계 최고의 리서치 전문가입니다. 당신의 임무는 주어진 주제와 관련된 웹페이지들의 내용을 종합하여,
        각 소주제별로 핵심 내용을 간결하고 객관적으로 요약하는 것입니다.
        주어진 자료 이외의 정보는 사용하지 마세요. 각 요약의 끝에는 반드시 출처 URL을 명시해야 합니다.
        결과는 마크다운 형식으로 정리하여 보고서 형태로 제출해주세요.
        """

    def research(self, topic, urls):
        """
        주어진 URL 목록을 바탕으로 리서치를 수행하고 요약 보고서를 생성합니다.
        :param topic: 리서치 주제
        :param urls: 조사할 URL 리스트
        :return: 요약된 리서치 보고서
        """
        print(f"'{topic}'에 대한 리서치를 시작합니다...")
        
        # 모든 URL의 내용을 스크레이핑하여 하나로 합칩니다.
        scraped_content = []
        for i, url in enumerate(urls):
            print(f"  [{i+1}/{len(urls)}] '{url}' 스크래핑 중...")
            content = scrape_website_text(url)
            if content:
                scraped_content.append(f"--- 출처: {url} ---\n{content}\n\n")

        if not scraped_content:
            return "정보를 수집하는 데 실패했습니다."

        combined_content = "".join(scraped_content)

        # LLM에게 내용 요약을 요청합니다.
        user_prompt = f"""
        다음은 '{topic}'에 대한 리서치 자료입니다. 이 자료들을 바탕으로 핵심 내용을 요약하여 상세한 보고서를 작성해주세요.

        [리서치 자료]
        {combined_content}
        """

        report = self.execute_prompt(self.system_prompt, user_prompt)
        print(report)
        print("리서치 보고서가 생성되었습니다.")
        return report
    
class ContentWriter(Agent):
    """
    조사 보고서를 바탕으로 블로그 포스트 초안을 작성하는 에이전트입니다.
    """
    def __init__(self, model="gpt-4.1-nano", temperature=0.8):
        super().__init__(model, temperature)
        self.system_prompt = """
        당신은 IT 분야의 전문 블로그 작가입니다. 당신의 글은 복잡한 기술 개념을
        초보자도 쉽게 이해할 수 있도록 친절하고 명확하게 설명하는 것으로 유명합니다.
        주어진 조사 보고서와 목차를 바탕으로, 독자들이 흥미를 느끼고 유익한 정보를 얻어갈 수 있는
        매력적인 블로그 포스트를 작성해주세요.

        [작성 가이드라인]
        - 서론, 본론, 결론의 구조를 명확히 갖춰주세요.
        - 각 문단은 하나의 핵심 주제를 다루도록 구성해주세요.
        - 전문 용어는 최소화하고, 필요시 쉬운 비유를 들어 설명해주세요.
        - 전체적인 톤앤매너는 '친절하고 유익한 전문가'의 느낌을 유지해주세요.
        - 결과물은 마크다운 형식으로 작성해주세요.
        """

    def write_post(self, research_report, topic, outline):
        """
        리서치 보고서를 바탕으로 블로그 포스트를 작성합니다.
        :param research_report: WebResearcher가 생성한 보고서
        :param topic: 블로그 포스트의 주제
        :param outline: TopicPlanner가 생성한 목차
        :return: 작성된 블로그 포스트 초안
        """
        print(f"'{topic}'에 대한 블로그 포스트 작성을 시작합니다...")

        user_prompt = f"""
        주제: {topic}

        목차:
        {outline}

        참고 자료 (조사 보고서):
        {research_report}

        위 주제, 목차, 참고 자료를 바탕으로 블로그 포스트를 작성해주세요.
        작성 가이드라인을 반드시 준수해야 합니다.
        """

        post_draft = self.execute_prompt(self.system_prompt, user_prompt)
        print(post_draft)
        print("블로그 포스트 초안이 완성되었습니다.")
        return post_draft
    
class TopicPlanner(Agent):
    """
    주어진 주제에 대해 블로그 포스트의 제목과 목차를 기획하는 에이전트입니다.
    """
    def __init__(self, model="gpt-3.5-turbo", temperature=0.7):
        super().__init__(model, temperature)
        self.system_prompt = """
        당신은 최고의 콘텐츠 전략가입니다. 당신의 임무는 사용자가 제공한 주제를 바탕으로
        독자들의 흥미를 끌 만한 블로그 포스트 제목과 상세한 목차를 생성하는 것입니다.

        [요구사항]
        1. 주어진 주제에 대해 가장 매력적이라고 생각되는 제목 1개를 제안하세요.
        2. 해당 제목에 맞춰, 서론, 본론(3~5개의 소주제), 결론으로 구성된 목차를 작성하세요.
        3. 결과는 반드시 아래와 같은 JSON 형식으로만 출력해야 합니다. 다른 설명은 절대 추가하지 마세요.

        {
          "title": "블로그 포스트 제목",
          "outline": [
            "서론:...",
            "본론 1:...",
            "본론 2:...",
            "결론:..."
          ]
        }
        """

    def plan_topic(self, topic):
        """
        주제에 대한 제목과 목차를 기획합니다.
        :param topic: 사용자가 입력한 블로그 포스트 주제
        :return: 제목과 목차를 담은 딕셔너리 또는 오류 발생 시 None
        """
        print(f"'{topic}'에 대한 콘텐츠 기획을 시작합니다...")
        
        # TopicPlanner는 매번 새로운 기획을 해야 하므로, 이 에이전트의 history를 비웁니다.
        self.history = [] 

        user_prompt = f"블로그 포스트 주제: {topic}"
        
        # 예상치 못한 출력 처리를 위한 재시도 로직 추가
        max_retries = 3
        for attempt in range(max_retries):
            response_json_str = self.execute_prompt(self.system_prompt, user_prompt)
            
            if not response_json_str:
                print(f"API 호출 실패 또는 응답 없음 (시도 {attempt + 1}/{max_retries})")
                continue # 다음 시도로 넘어갑니다.

            try:
                planned_result = json.loads(response_json_str)
                print("콘텐츠 기획이 완료되었습니다.")
                return planned_result
            except json.JSONDecodeError:
                print(f"오류: TopicPlanner가 유효한 JSON을 생성하지 못했습니다. 재시도합니다. (시도 {attempt + 1}/{max_retries})")
                print("받은 응답:", response_json_str)
                # 잘못된 형식의 응답을 받으면 AI에게 JSON 형식으로 다시 출력하도록 프롬프트 수정 (선택 사항)
                # 이 경우 user_prompt를 업데이트하고 다시 execute_prompt를 호출해야 합니다.
                # 예: user_prompt = f"이전 응답이 JSON 형식이 아닙니다. 반드시 JSON 형식으로 다시 출력해주세요: {topic}"
                continue # JSON 파싱 실패 시 다음 시도로 넘어갑니다.

        print("최대 재시도 횟수를 초과하여 콘텐츠 기획에 실패했습니다.")
        return None
        
class ReviewAndEditor(Agent):
    """
    작성된 초안을 검토하고 편집하여 최종 원고를 완성하는 에이전트입니다.
    """
    def __init__(self, model="gpt-4", temperature=0.5):
        super().__init__(model, temperature)
        self.system_prompt = """
        당신은 최고의 실력을 가진 수석 편집자입니다. 당신의 역할은 주어진 블로그 포스트 초안을
        검토하고, 글의 수준을 한 단계 끌어올리는 것입니다.

        [편집 가이드라인]
        - 문법 및 철자 오류를 완벽하게 수정하세요.
        - 문장 구조를 개선하여 가독성을 높이세요. 어색하거나 반복되는 표현을 다듬어주세요.
        - 전체 글의 흐름이 논리적이고 자연스러운지 확인하고, 필요하다면 문단 순서를 조정하거나 연결어를 추가하세요.
        - 글의 톤앤매너가 '친절하고 유익한 전문가' 컨셉에 맞게 일관적으로 유지되는지 확인하세요.
        - 단, 원문의 핵심 사실이나 주장은 변경해서는 안 됩니다.
        
        수정된 최종 원고만 마크다운 형식으로 출력해주세요.
        """

    def review_and_edit(self, draft, topic):
        """
        초안을 검토하고 편집합니다.
        :param draft: ContentWriter가 작성한 초안
        :param topic: 블로그 포스트의 주제
        :return: 최종 편집된 원고
        """
        print(f"'{topic}' 포스트에 대한 최종 검토 및 편집을 시작합니다...")

        user_prompt = f"""
        다음은 '{topic}'에 대한 블로그 포스트 초안입니다.
        편집 가이드라인에 따라 검토하고 수정하여 최종 원고를 완성해주세요.

        [초안]
        {draft}
        """
        
        final_post = self.execute_prompt(self.system_prompt, user_prompt)
        print("최종 원고가 완성되었습니다.")
        return final_post