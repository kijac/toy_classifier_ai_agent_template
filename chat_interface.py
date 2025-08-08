from image_input import get_image
from supervisor_agent import SupervisorAgent

def start_chat():
    print("장난감 기부 판별 챗봇입니다. 이미지를 입력하세요.")
    image = get_image()
    supervisor = SupervisorAgent()
    result = supervisor.process(image)
    print("\n===== 판별 결과 =====")
    for k, v in result.items():
        print(f"{k}: {v}")
