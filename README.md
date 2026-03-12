# 6-Agent 직렬 자동화: 3분 극영화 스크립트 → 60컷 스타트프레임 프롬프트

이 저장소에는 입력 스크립트를 받아 **6명의 에이전트가 직렬(순차)로 처리**하고,
최종적으로 **60개의 이미지 생성 프롬프트**를 산출하는 파이프라인이 포함되어 있습니다.

## 파이프라인 구조

1. **ScriptIngestAgent**: 스크립트 정규화 및 섹션 분리
2. **BeatPlannerAgent**: 섹션을 드라마 비트로 요약
3. **ShotAllocatorAgent**: 비트별 컷 수 배분(총 60컷 고정 가능)
4. **ShotDesignerAgent**: 컷 단위 시각 요소(카메라/조명/구도/행동) 확장
5. **PromptRefinerAgent**: 이미지 생성 모델용 프롬프트 문장화
6. **QAAgent**: 개수/중복률 검증 후 결과 확정

## 실행 방법

```bash
python3 pipeline.py --input sample_script.txt --output-dir output --shots 60
```

실행 후 생성물:

- `output/result.json`: 비트/컷/프롬프트 전체 구조화 데이터
- `output/prompts.txt`: 최종 60개 프롬프트 텍스트 목록

## 입력 예시 포맷

`sample_script.txt`처럼 장면 단위로 적으면 됩니다.

```text
SCENE 1
새벽의 골목. 주인공이 달린다.
뒤에서 누군가 쫓아온다.

SCENE 2
지하철 플랫폼. 기차가 들어오기 직전,
주인공은 선택의 기로에 선다.
```

## 커스터마이징 포인트

- `ShotDesignerAgent`의 카메라/조명/로케이션 후보
- `PromptRefinerAgent`의 스타일 suffix
- `QAAgent`의 중복 허용 기준
- `--shots` 값(기본 60)

원한다면 다음 단계로 LLM API를 각 에이전트 내부에 연결해 실제 의미 기반 생성 품질을 높일 수 있습니다.
