# Sandbox Contract: Code Execution

**Date**: 2026-05-11

채점 워커(Celery)와 코드 실행 샌드박스 간의 인터페이스 계약.

---

## 입력 (채점 요청)

```json
{
  "submission_id": "uuid",
  "language": "python3|java17|cpp17|c17",
  "code": "string",
  "time_limit_sec": "number",
  "memory_limit_mb": "integer",
  "test_cases": [
    {
      "order": "integer",
      "input_storage_key": "string",
      "expected_output_storage_key": "string"
    }
  ]
}
```

---

## 출력 (채점 결과)

```json
{
  "submission_id": "uuid",
  "overall_verdict": "ACCEPTED|WRONG_ANSWER|TIME_LIMIT_EXCEEDED|MEMORY_LIMIT_EXCEEDED|RUNTIME_ERROR|COMPILATION_ERROR",
  "compilation_error_message": "string|null",
  "test_case_results": [
    {
      "order": "integer",
      "verdict": "ACCEPTED|WRONG_ANSWER|TIME_LIMIT_EXCEEDED|MEMORY_LIMIT_EXCEEDED|RUNTIME_ERROR",
      "time_ms": "integer",
      "memory_mb": "number",
      "actual_output_preview": "string|null"
    }
  ]
}
```

**판정 우선순위**: COMPILATION_ERROR → (테스트 케이스 순서대로) TLE/MLE/RE/WA → 모두 AC면 ACCEPTED.

---

## 실행 환경 보안 제약

| 제약 | 값 | 목적 |
|------|-----|------|
| 네트워크 | `--network none` | 외부 통신 차단 |
| 파일시스템 | 루트 읽기 전용, `/tmp` tmpfs 32MB | 디스크 쓰기 제한 |
| 실행 사용자 | uid=1001 (비루트) | 권한 상승 방지 |
| CPU | `--cpus 1` | 공정한 제한 |
| 메모리 | `--memory <limit>m` | MLE 강제 적용 |
| PID 제한 | `--pids-limit 64` | 포크 폭탄 방지 |
| seccomp | 기본 Docker seccomp 프로필 | 위험 시스템콜 차단 |

---

## 언어별 실행 명령

| 언어 | 컴파일 | 실행 |
|------|--------|------|
| python3 | (없음) | `python3 solution.py < input.txt` |
| java17 | `javac Solution.java` | `java -Xmx<mem>m Solution < input.txt` |
| cpp17 | `g++ -O2 -std=c++17 -o solution solution.cpp` | `./solution < input.txt` |
| c17 | `gcc -O2 -std=c17 -o solution solution.c` | `./solution < input.txt` |

---

## 출력 비교 방식 (v1)

- 표준 출력(stdout)과 예상 출력 파일을 **trailing whitespace 무시, 개행 정규화** 후 바이트 비교.
- 일치하면 ACCEPTED, 불일치하면 WRONG_ANSWER.
