# Menemory

로컬 기본 + Supabase 백업용 상태형 AI 메모리 CLI입니다.

- 기본 저장소: 현재 프로젝트의 `./.menemory`
- 세션 복구: `tmux` 연동
- 백업/복원: Supabase (`backup push/pull`)
- 컨텍스트 계층: Core / Session Summary / Recent Conversation / Long-term
- 원문 보관: 세션별 raw turn JSONL 자동 저장 (`.menemory/sessions/history/<session_id>.jsonl`)
- 기본 글로벌 스킬 alias 생성: `메네모리`, `menemory-memory-sync`

## 기본 운영 방식 (권장)

1. 로컬에서 작업
2. 필요 시 Supabase로 백업
3. 다른 서버에서 Supabase에서 복원

즉, Supabase는 실시간 주 저장소가 아니라 백업/복구 레이어로 사용합니다.

## Quick Start

```bash
# 프로젝트 루트에서
menemory init --session-id dev-2026-02-20
menemory ask "현재 작업 이어서 정리해줘" --cmd "codex"
menemory status
```

`init`은 아래를 한 번에 수행합니다.
- 로컬 세션 초기화
- 사용자 설정 마법사(이름/이메일/LLM/Supabase)
- 실행환경 점검(tmux/Supabase/gitignore)
- Codex용 기본 menemory 스킬 세트 자동 생성(`~/.codex/skills`)
  - 포함 alias: `메네모리` (빠른 메모리 동기화/복구 트리거)

## 직관 명령어

```bash
menemory init --session-id <id>      # 첫 실행 권장(체크 + 스킬 부트스트랩)
menemory start --session-id <id>     # 세션 시작/초기화
menemory ask "..." --cmd "codex"     # 메모리 포함 질의 (추천)
menemory status                      # 로컬 상태 요약
menemory history --limit 50          # 세션 raw turn 원문 확인
menemory recover                     # 최근 대화/히스토리 기반 빠른 복구 뷰
menemory resume --attach             # SSH 재접속 후 tmux 복구
menemory backup push                 # 로컬 -> Supabase 백업
menemory backup pull --session-id <id> # Supabase -> 로컬 복원
menemory where                       # 현재 MENEMORY_HOME 확인
```

기존 호환 명령(`run`, `show`, `supabase-*`)도 계속 동작합니다.

지원 IDE/서비스에서 skills를 읽는 경우, `메네모리` 또는 `menemory-memory-sync`
만 입력해도 워크스페이스 메모리 동기화 플로우를 바로 호출할 수 있게 기본 스킬이
생성됩니다. 프로젝트에 `docs/MEMORY_SYNC_MAP.md` 와
`scripts/utils/collect_memory_context.sh` 가 있으면 그 경로를 우선 사용합니다.

`init` 옵션:

```bash
menemory init --interactive                 # 설정 마법사 강제 실행
menemory init --configure                   # 기존 config 있어도 다시 입력
menemory init --no-with-skills            # 스킬 생성 스킵
menemory init --skills-dir /path/skills   # 생성 경로 지정
menemory init --overwrite-skills          # 기존 스킬 덮어쓰기
menemory init --user-name minuum --user-email me@example.com
menemory init --llm-cmd codex
menemory init --supabase-url https://<project>.supabase.co
menemory init --supabase-service-role-key <service_role_key>
```

설정은 로컬 워크스페이스의 `./.menemory/config.json`에 저장되며, 이후 `ask`/`backup`에서 자동 재사용됩니다.
환경변수(`MENEMORY_LLM_CMD`, `SUPABASE_*`)가 있으면 설정값보다 우선 적용됩니다.

## 자동 .gitignore 반영

Menemory가 워크스페이스를 생성할 때, 현재 Git 저장소의 `.gitignore`에 아래 경로를 자동 추가합니다.

```gitignore
.menemory/sessions/
.menemory/longterm/chroma_db/
.menemory/longterm/memory.jsonl
```

- 비활성화: `export MENEMORY_AUTO_GITIGNORE=0`
- 커스텀 홈 사용 시: `MENEMORY_HOME` 기준 상대 경로로 자동 반영

## 요약 + 원문 하이브리드 저장

- Active 세션(`active_session.json`)은 `summary + recent conversation` 중심으로 유지되어 프롬프트가 과도하게 커지는 문제를 줄입니다.
- 동시에 모든 turn 원문은 세션별 JSONL로 누적됩니다.
  - 경로: `.menemory/sessions/history/<session_id>.jsonl`
  - 조회: `menemory history --limit 100`
- `menemory status`에서 `raw_history_turns`로 원문 누적 개수를 빠르게 확인할 수 있습니다.

## 빠른 복구

SSH가 끊기거나 세션이 날아간 뒤 바로 최근 상태를 훑고 싶으면 아래 중 하나를 사용합니다.

```bash
menemory recover
menemory recover --build-prompt
menemory recover --resume
./scripts/menemory_recover_now.sh
```

- `recover`: 최근 conversation + raw history tail을 한 번에 보여줍니다.
- `--build-prompt`: "작업 재개 요약" 기준의 메모리 프롬프트를 함께 출력합니다.
- `--resume`: 현재 세션 id 기준 tmux 세션이 없으면 다시 만들고 복구 뷰를 출력합니다.

원하면 셸에 아래 alias를 추가해 `메네모리` 한 단어로 실행할 수 있습니다.

```bash
alias 메네모리='cd /path/to/repo && ./scripts/menemory_recover_now.sh'
```

이 alias는 자동 설치되지 않으므로, 실제 적용하려면 `~/.bashrc` 또는 `~/.zshrc`에 추가해야 합니다.

## 주기 자동보존

현재 Menemory에 저장된 상태를 몇 분마다 스냅샷하려면 아래 스크립트를 사용합니다.

```bash
./scripts/menemory_autosave.sh 300
```

- 기본은 300초(5분)입니다.
- 스냅샷은 `.menemory/sessions/autosave/` 아래에 저장됩니다.
- `MENEMORY_AUTO_BACKUP_PUSH=1`을 주면 각 주기마다 `menemory backup push`도 같이 시도합니다.

중요:
- 이 스크립트는 "이미 Menemory에 저장된 상태"를 보존합니다.
- Codex/채팅 자체를 몇 분마다 자동으로 Menemory에 기록하는 기능은 아닙니다.
- 대화 내용을 Menemory에 반영하려면 여전히 `menemory add`, `menemory ask`, 또는 에이전트에게 "메네모리" 저장 요청이 필요합니다.

## Supabase 백업 설정

1. Supabase SQL 적용: `sql/supabase_schema.sql`
2. 환경변수 설정

```bash
export SUPABASE_URL="https://<project>.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="<service_role_key>"
export SUPABASE_SERVER_ID="dev-server-01"
```

3. 백업/복원

```bash
menemory backup push
menemory backup pull --session-id dev-2026-02-20 --server-id dev-server-01
```

## 설치

```bash
cd menemory
python -m pip install .
# 또는
pipx install .
```

## PyPI 배포

GitHub Actions 기반 배포가 포함되어 있습니다.

- `CI Package`: PR/`main`에서 빌드 + `twine check`
- `Publish TestPyPI`: 수동 실행으로 TestPyPI 업로드
- `Publish PyPI`: `v*` 태그 push 시 PyPI 업로드

사전 1회 설정:
1. PyPI/TestPyPI에 프로젝트 생성
2. 각 인덱스에서 Trusted Publisher 등록
3. Trusted Publisher의 repository/workflow를 아래와 정확히 일치:
- owner: `minuum`
- repo: `menemory`
- workflow: `publish-pypi.yml` (PyPI), `publish-testpypi.yml` (TestPyPI)

릴리스 절차:

```bash
cd menemory
# 버전 갱신 (pyproject.toml)
git add .
git commit -m "chore: release v0.1.1"
git tag v0.1.1
git push origin main --tags
```

설치 확인:

```bash
pipx install menemory
# 또는
python -m pip install menemory
menemory --help
```

## 저장소 분리/푸시

```bash
cd menemory
git remote add origin <new-menemory-remote-url>
git push -u origin main
```
