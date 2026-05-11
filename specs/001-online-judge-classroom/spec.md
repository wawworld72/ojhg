# Feature Specification: Google Classroom-Integrated Online Judge

**Feature Branch**: `001-online-judge-classroom`
**Created**: 2026-05-11
**Status**: Draft
**Input**: User description: "구글 클래스룸에서 연동 가능한 온라인 저지 만들려고 해"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 학생: 코드 제출 및 즉시 채점 (Priority: P1)

학생이 Google Classroom에서 프로그래밍 과제를 열면 온라인 저지 제출 페이지로 이동한다.
코드를 작성하거나 붙여넣고 제출하면 자동으로 채점되어 결과(Accepted / Wrong Answer / Time Limit Exceeded 등)와 함께 점수를 확인한다.

**Why this priority**: 시스템의 핵심 가치. 이것 없이는 다른 모든 기능이 의미 없다.

**Independent Test**: 학생 계정으로 로그인 → 과제 목록에서 문제 선택 → 코드 입력 후 제출 → 채점 결과 화면 확인만으로 MVP 검증 가능.

**Acceptance Scenarios**:

1. **Given** 로그인한 학생이 과제 문제 페이지에 있을 때, **When** 올바른 코드를 작성하고 제출하면, **Then** "Accepted"와 함께 통과한 테스트 케이스 수와 점수가 표시된다.
2. **Given** 학생이 틀린 코드를 제출하면, **When** 채점이 완료되면, **Then** "Wrong Answer"와 어느 테스트 케이스에서 실패했는지(번호)가 표시된다.
3. **Given** 학생이 무한루프 코드를 제출하면, **When** 제한 시간을 초과하면, **Then** "Time Limit Exceeded" 결과가 반환된다.
4. **Given** 학생이 이미 Accepted인 과제에 재제출하면, **When** 채점이 완료되면, **Then** 최신 제출 결과가 저장되고 최고 점수가 Google Classroom에 반영된다.

---

### User Story 2 - 교사: 프로그래밍 문제 생성 및 Google Classroom 과제 연동 (Priority: P1)

교사가 온라인 저지에서 프로그래밍 문제(설명, 입출력 예시, 테스트 케이스, 시간/메모리 제한)를 만들고, 이를 Google Classroom의 기존 과제에 연결한다.
학생이 Google Classroom에서 해당 과제 링크를 클릭하면 온라인 저지의 해당 문제로 바로 이동한다.

**Why this priority**: 교사 없이는 문제가 존재하지 않으므로 학생 스토리와 동급 우선순위.

**Independent Test**: 교사 계정으로 문제 생성 → Google Classroom 과제와 연동 → 학생 계정으로 Classroom 과제 클릭 시 해당 문제 페이지 도달 확인.

**Acceptance Scenarios**:

1. **Given** 교사가 문제 생성 폼을 작성하면, **When** 저장하면, **Then** 문제가 저장되고 공유 가능한 링크가 생성된다.
2. **Given** 교사가 연동할 Google Classroom 과제를 선택하면, **When** 연동을 완료하면, **Then** 해당 과제에 학생이 접근 시 온라인 저지 문제 페이지로 리디렉션된다.
3. **Given** 교사가 테스트 케이스를 업로드하면(입력 파일 + 예상 출력 파일), **When** 문제를 저장하면, **Then** 해당 테스트 케이스들이 모든 학생 제출물에 적용된다.
4. **Given** 교사가 공개/비공개 테스트 케이스를 구분하면, **When** 학생이 채점 결과를 보면, **Then** 공개 케이스의 입출력은 학생에게 표시되고 비공개 케이스는 번호와 결과만 표시된다.

---

### User Story 3 - Google Classroom 자동 성적 반영 (Priority: P2)

학생이 제출하고 Accepted(또는 부분 점수)를 받으면, 교사가 별도 조작 없이 Google Classroom 성적부에 점수가 자동으로 업데이트된다.

**Why this priority**: 핵심 연동 가치지만 수동 반영 임시 대안이 존재하므로 P2.

**Independent Test**: 학생 제출 → 채점 완료 → Google Classroom 성적부에서 해당 과제 점수 확인.

**Acceptance Scenarios**:

1. **Given** 학생이 Accepted를 받으면, **When** 채점이 완료되면, **Then** 5분 이내에 Google Classroom 성적부에 해당 학생 점수가 갱신된다.
2. **Given** 학생이 이전 점수보다 낮은 점수로 재제출하면, **When** Google Classroom에 반영될 때, **Then** 최고 점수가 유지된다.
3. **Given** Google Classroom API가 일시적으로 응답하지 않으면, **When** 재시도 시, **Then** 재시도 후 성적이 반영되고 학생/교사에게 알림이 전달된다.

---

### User Story 4 - 교사: 제출 현황 및 통계 조회 (Priority: P3)

교사가 특정 문제에 대한 전체 학생의 제출 현황(제출 수, Accepted 비율, 평균 점수)을 한눈에 볼 수 있다.

**Why this priority**: 편의 기능이며 MVP 이후 추가 가능.

**Independent Test**: 교사 대시보드 → 문제별 통계 페이지에서 제출 현황 확인.

**Acceptance Scenarios**:

1. **Given** 교사가 문제 통계 페이지를 열면, **When** 페이지가 로드되면, **Then** 전체 학생 수, 제출 완료 학생 수, Accepted 학생 수, 평균 점수가 표시된다.
2. **Given** 교사가 특정 학생의 제출물을 클릭하면, **When** 상세 페이지가 열리면, **Then** 해당 학생의 모든 제출 이력(시각, 결과, 코드)을 볼 수 있다.

---

### Edge Cases

- 학생이 Google Classroom에 등록되지 않은 상태에서 저지 링크에 직접 접근하면? → 접근 불가, Classroom 등록 안내 메시지 표시.
- 교사가 마감 시간 이후 학생 제출을 허용/차단 설정은? → 기본값은 마감 후 제출 허용하되 "지각 제출" 표시.
- 동일 학생이 동시에 여러 탭에서 제출하면? → 먼저 채점 완료된 결과만 반영, 중복 채점 방지.
- 지원하지 않는 언어로 제출하면? → 제출 폼에서 지원 언어 목록만 선택 가능하게 차단.
- 빈 코드나 최소 크기 미달 코드를 제출하면? → 제출 전 클라이언트 측에서 차단, 안내 메시지 표시.
- 학생이 Google 계정을 탈퇴/변경하면? → 해당 계정의 제출 이력은 보존, 교사만 조회 가능.

## Requirements *(mandatory)*

### Functional Requirements

**인증 & 접근 제어**
- **FR-001**: 시스템은 Google OAuth 2.0을 통한 로그인만 허용해야 한다.
- **FR-002**: 시스템은 Google Classroom의 역할(교사/학생)을 자동으로 인식하여 접근 권한을 부여해야 한다.
- **FR-003**: 학생은 자신이 등록된 수업의 과제에만 접근할 수 있어야 한다.

**문제 관리 (교사)**
- **FR-004**: 교사는 문제 제목, 설명, 입출력 예시, 시간 제한(초), 메모리 제한(MB), 배점을 설정하여 문제를 생성할 수 있어야 한다.
- **FR-005**: 교사는 문제당 최소 1개, 최대 100개의 테스트 케이스를 업로드할 수 있어야 한다.
- **FR-006**: 교사는 각 테스트 케이스를 공개(학생에게 입출력 노출) 또는 비공개(결과만 노출)로 설정할 수 있어야 한다.
- **FR-007**: 교사는 문제를 Google Classroom의 특정 과제에 연결할 수 있어야 한다. 하나의 과제에는 하나의 문제만 연결된다.
- **FR-008**: 교사는 허용할 프로그래밍 언어를 문제별로 지정할 수 있어야 한다.

**코드 제출 & 채점 (학생)**
- **FR-009**: 학생은 허용된 프로그래밍 언어 중 하나를 선택하고 코드를 에디터에 직접 입력하거나 파일로 업로드하여 제출할 수 있어야 한다.
- **FR-010**: 시스템은 제출된 코드를 격리된 환경에서 실행하고, 각 테스트 케이스에 대해 Accepted / Wrong Answer / Time Limit Exceeded / Memory Limit Exceeded / Runtime Error / Compilation Error 중 하나의 결과를 반환해야 한다.
- **FR-011**: 채점 결과는 제출 후 30초 이내에 학생에게 표시되어야 한다 (일반적인 문제 기준).
- **FR-012**: 학생은 자신의 모든 제출 이력(제출 시각, 언어, 결과, 점수)을 조회할 수 있어야 한다.
- **FR-013**: 학생은 과거 제출의 코드를 재열람할 수 있어야 한다.

**Google Classroom 성적 연동**
- **FR-014**: 채점 완료 후 시스템은 학생의 점수를 Google Classroom 성적부에 자동으로 반영해야 한다.
- **FR-015**: Google Classroom 성적 반영은 멱등적이어야 한다 — 동일 점수를 두 번 반영해도 중복 항목이 생기지 않아야 한다.
- **FR-016**: 이미 기록된 점수보다 낮은 점수로 재제출 시 Google Classroom의 기존 점수는 유지되어야 한다.
- **FR-017**: Google Classroom API 호출 실패 시 시스템은 최대 3회 재시도 후, 실패 이력을 기록하고 교사에게 알림을 전달해야 한다.

**통계 & 관리 (교사)**
- **FR-018**: 교사는 문제별로 전체 학생의 제출 현황(제출 수, Accepted 수, 평균 점수)을 조회할 수 있어야 한다.
- **FR-019**: 교사는 특정 학생의 제출 이력과 코드를 조회할 수 있어야 한다.

### Key Entities

- **Problem**: 문제 제목, 설명, 시간/메모리 제한, 배점, 허용 언어, 공개 여부, 연결된 Classroom 과제 ID.
- **TestCase**: 입력 데이터, 예상 출력 데이터, 공개 여부, 속한 Problem.
- **Submission**: 제출 학생, 속한 Problem, 코드 내용, 언어, 제출 시각, 채점 결과, 점수, 각 테스트 케이스 결과 목록.
- **ClassroomCourse**: Google Classroom 수업 ID, 수업명, 교사 목록, 학생 목록.
- **ClassroomAssignment**: Google Classroom 과제 ID, 속한 Course, 연결된 Problem, 배점, 마감 시각.
- **User**: Google 계정 ID, 이름, 이메일, 역할(교사/학생).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 학생은 문제 페이지 진입 후 3번의 클릭 이내에 코드를 제출할 수 있다.
- **SC-002**: 채점 결과가 제출 후 30초 이내에 학생 화면에 표시된다 (코드 길이 500줄, 테스트 케이스 20개 기준).
- **SC-003**: Google Classroom 성적 반영이 채점 완료 후 5분 이내에 완료된다.
- **SC-004**: 시스템은 동시에 50명의 학생이 제출하는 부하를 처리할 수 있다.
- **SC-005**: 악의적인 제출 코드(무한루프, 포크 폭탄, 파일시스템 접근)가 호스트 시스템에 영향을 미치지 않는다.
- **SC-006**: 교사가 새 문제를 만들고 Google Classroom 과제에 연동하는 전체 과정을 10분 이내에 완료할 수 있다.
- **SC-007**: Google Classroom 성적 반영 성공률이 99% 이상이다 (재시도 포함).

## Assumptions

- 지원 언어 초기 범위: Python 3, Java 17, C++17 (추후 확장 가능).
- 모바일 웹 지원은 v1 범위 밖; 데스크탑 브라우저(Chrome, Firefox, Edge 최신 버전) 기준.
- Google Workspace for Education 계정을 가진 교육기관을 주요 사용자로 가정.
- 교사는 이미 Google Classroom에서 수업과 과제를 생성한 상태에서 온라인 저지와 연동한다.
- 한 문제에 하나의 정답(output matching) 방식으로 채점; 스페셜 저지(커스텀 채점자)는 v1 범위 밖.
- 부분 점수는 통과한 테스트 케이스 수 / 전체 테스트 케이스 수 × 배점으로 계산.
- 코드 실행 환경의 최대 시간 제한은 10초, 메모리 제한은 512MB로 제한.
