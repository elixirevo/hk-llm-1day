# HK LLM 1 Day Project

## 패키지 설치

```bash
uv sync
```

## 실행

샘플 JD와 자기소개서를 사용해 최종 질문 리포트를 생성합니다.

```bash
python3 main.py
```

JSON 전체 결과가 필요하면 아래처럼 실행합니다.

```bash
python3 main.py --output json
```

다른 입력 파일을 쓰려면 경로를 지정하면 됩니다.

```bash
python3 main.py --jd path/to/jd.md --essay path/to/essay.md
```

## 현재 구조

- `lib/phase1.py`: JD 멀티워커 분석
- `lib/phase2.py`: 자소서 문항 분석 및 JD 매칭
- `lib/phase3.py`: 질문 생성 오케스트레이션
- `lib/phase4.py`: 질문 평가 및 개선 루프
- `lib/phase5.py`: 질문 분류 및 우선순위 리포트
- `lib/pipeline.py`: Phase 1~5 end-to-end 파이프라인
