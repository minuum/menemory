# Menemory

로컬 기본 + Supabase 백업용 상태형 AI 메모리 CLI입니다.

- 기본 저장소: 현재 프로젝트의 `./.menemory`
- 세션 복구: `tmux` 연동
- 백업/복원: Supabase (`backup push/pull`)
- 컨텍스트 계층: Core / Session / Long-term

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

## 직관 명령어

```bash
menemory init --session-id <id>      # 첫 실행 권장(체크 + 스킬 부트스트랩)
menemory start --session-id <id>     # 세션 시작/초기화
menemory ask "..." --cmd "codex"     # 메모리 포함 질의 (추천)
menemory status                      # 로컬 상태 요약
menemory resume --attach             # SSH 재접속 후 tmux 복구
menemory backup push                 # 로컬 -> Supabase 백업
menemory backup pull --session-id <id> # Supabase -> 로컬 복원
menemory where                       # 현재 MENEMORY_HOME 확인
```

기존 호환 명령(`run`, `show`, `supabase-*`)도 계속 동작합니다.

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
