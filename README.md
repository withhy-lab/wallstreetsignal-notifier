# 월스트릿 시그널 → 텔레그램 신규 글 알림

네이버 프리미엄콘텐츠 '월스트릿 시그널' 채널(`nomadand/wallstreetsignal`)에 새 글이 올라오면
GitHub Actions가 주기적으로 확인해서 텔레그램 채널로 **제목 + 링크**를 자동 전송합니다.

## 1. 텔레그램 봇 준비

1. 텔레그램에서 [@BotFather](https://t.me/BotFather)와 대화 시작
2. `/newbot` 입력 → 봇 이름/아이디 설정 → **Bot Token** 발급받기 (예: `123456:ABC-DEF...`)
3. 알림을 보낼 텔레그램 **채널**을 만들고, 방금 만든 봇을 그 채널의 **관리자(admin)**로 추가
4. 채널의 chat_id 확인 방법 (아래 중 하나):
   - 채널이 public이면: chat_id는 `@채널아이디` 형태로 그대로 사용 가능 (예: `@my_signal_channel`)
   - private 채널이면: 채널에 아무 메시지나 하나 올린 뒤, 브라우저에서
     `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates` 접속 → 응답 JSON에서
     `"chat":{"id": -1001234567890, ...}` 형태의 숫자를 chat_id로 사용

## 2. GitHub 저장소에 올리기

1. 이 폴더 전체를 새 GitHub 저장소(private 추천)에 push
2. 저장소 **Settings → Secrets and variables → Actions → New repository secret**에서 아래 2개 등록:
   - `TELEGRAM_BOT_TOKEN` : 1번에서 발급받은 봇 토큰
   - `TELEGRAM_CHAT_ID` : 1번에서 확인한 chat_id
3. 저장소 **Settings → Actions → General → Workflow permissions**에서
   **"Read and write permissions"** 로 설정 (seen.json을 커밋하기 위해 필요)

## 3. 동작 확인

- 저장소의 **Actions** 탭 → `Check new posts and notify Telegram` 워크플로우 →
  **Run workflow** 버튼으로 수동 실행 가능
- 최초 1회 실행 시에는 현재 목록을 "이미 본 글"로만 기록하고 텔레그램 전송은 하지 않습니다.
  (기존 글들이 한꺼번에 스팸으로 전송되는 것을 막기 위함)
- 그 다음부터 새 글이 올라오면 자동으로 텔레그램에 전송됩니다.

## 4. 주의사항

- GitHub Actions의 스케줄(cron)은 1분 단위로 설정해도 **GitHub 서버 부하에 따라 실행이
  몇 분 지연될 수 있습니다.** "발행 후 1분 이내"를 100% 보장하지는 못하며, 보통은
  1~3분 내로 도는 경우가 많습니다. 더 엄격한 실시간성이 필요하면 상시 켜져 있는
  서버/PC에서 `while true; do python scripts/check_new_posts.py; sleep 60; done` 형태로
  직접 도는 방식으로 전환할 수 있습니다.
- 네이버 프리미엄콘텐츠 페이지의 HTML 구조가 바뀌면(`li.channel_content_item` 클래스명 등)
  스크립트가 글을 못 찾을 수 있습니다. 이 경우 `scripts/check_new_posts.py`의 CSS 선택자를
  최신 구조에 맞게 수정해야 합니다.
- 90일 동안 저장소에 아무 커밋도 없으면 GitHub가 스케줄 워크플로우를 자동으로
  비활성화합니다. 이 경우 Actions 탭에서 다시 활성화해주면 됩니다.

## 로컬에서 테스트하기

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="여기에 토큰"
export TELEGRAM_CHAT_ID="여기에 chat id"
python scripts/check_new_posts.py
```
