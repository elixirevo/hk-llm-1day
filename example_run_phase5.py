import os
import sys

# 프로젝트 루트를 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from lib.phase5 import phase5, format_phase5_output

def main():
    # 1. 테스트용 데이터 준비 (Phase 4를 통과했다고 가정한 질문들)
    test_questions = [
        "LLM 기반의 멀티 에이전트 시스템 설계 경험이 있으신가요?",
        "RAG(Retrieval-Augmented Generation) 성능을 높이기 위해 어떤 기법을 사용하셨나요?",
        "대규모 트래픽이 발생하는 환경에서 추론 속도를 개선한 사례가 있나요?",
        "협업하는 과정에서 의견 차이가 발생했을 때 어떻게 해결하셨나요?",
        "우리 회사의 AI 엔지니어 포지션에 지원하게 된 가장 큰 동기는 무엇인가요?",
        "향후 3년 내 AI 분야에서 본인의 성장 계획은 무엇인가요?"
    ]
    
    # 2. 직무 카테고리 설정
    job_category = "AI 에이전트 개발자"
    
    print(f"🚀 [테스트 실행] '{job_category}' 직무의 예상 질문 분석 중...\n")
    
    try:
        # 3. Phase 5 실행 (분류, 채점, 정렬, 요약)
        # ※ 실제 LLM API 호출이 발생하므로 시간이 약간 소요될 수 있습니다.
        result_data = phase5(test_questions, job_category)
        
        # 4. 결과 포맷팅 및 출력
        report_text = format_phase5_output(result_data)
        
        print("=" * 50)
        print(report_text)
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
