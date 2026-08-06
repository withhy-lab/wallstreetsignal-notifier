"""
네이버 프리미엄콘텐츠 '월스트릿 시그널' 채널 신규 글 감지 -> 텔레그램 알림

동작 방식:
1. 채널 홈 페이지(HTML)를 요청해서 글 목록을 파싱한다.
2. data/seen.json에 저장된 "이미 알림 보낸 글 ID" 목록과 비교한다.
3. 새 글이 있으면 텔레그램으로 "제목 + 링크"를 전송한다.
4. seen.json을 갱신한다. (GitHub Actions에서 커밋까지 처리)

최초 실행(seen.json이 비어있을 때)은 기존 글들을 한꺼번에 스팸으로 보내지 않도록,
현재 목록을 seen 처리만 하고 텔레그램 전송은 하지 않는다.
"""

import json
import os
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

CHANNEL_URL = "https://contents.premium.naver.com/nomadand/wallstreetsignal"
BASE_URL = "https://contents.premium.naver.com"

REPO_ROOT = Path(__file__).resolve().parent.parent
SEEN_FILE = REPO_ROOT / "data" / "seen.json"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


def load_seen() -> tuple[set, bool]:
    """저장된 seen id 목록을 불러온다. (seen_ids, is_first_run) 반환."""
    if not SEEN_FILE.exists():
        return set(), True
    try:
        data = json.loads(SEEN_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set(), True
    seen_ids = set(data.get("seen_ids", []))
    # 파일은 있지만 비어있는 경우도 최초 실행으로 취급
    is_first_run = len(seen_ids) == 0
    return seen_ids, is_first_run


def save_seen(seen_ids: set) -> None:
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(
        json.dumps({"seen_ids": sorted(seen_ids)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def fetch_posts() -> list[dict]:
    resp = requests.get(CHANNEL_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    posts = []
    items = soup.select("ul.channel_content_list > li.channel_content_item")
    for li in items:
        link = li.select_one("a.channel_content_link")
        title_el = li.select_one(".channel_content_title_text")
        if not link or not title_el:
            continue

        href = link.get("href", "").strip()
        if not href:
            continue

        content_id = href.rstrip("/").split("/")[-1]
        title = title_el.get_text(strip=True)
        full_url = href if href.startswith("http") else BASE_URL + href

        posts.append({"id": content_id, "title": title, "url": full_url})

    return posts


def send_telegram(title: str, url: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 환경변수가 설정되지 않았습니다.")

    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    text = f"🆕 {title}\n{url}"

    resp = requests.post(
        api_url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "disable_web_page_preview": "false",
        },
        timeout=20,
    )
    resp.raise_for_status()
    result = resp.json()
    if not result.get("ok", False):
        raise RuntimeError(f"텔레그램 전송 실패: {result}")


def main() -> int:
    seen_ids, is_first_run = load_seen()

    try:
        posts = fetch_posts()
    except Exception as e:
        print(f"[오류] 채널 페이지 조회 실패: {e}", file=sys.stderr)
        return 1

    if not posts:
        print("[경고] 글 목록을 하나도 찾지 못했습니다. 페이지 구조가 바뀌었을 수 있습니다.")
        return 1

    if is_first_run:
        # 최초 실행: 현재 보이는 글들은 전송 없이 seen 처리만 함
        for p in posts:
            seen_ids.add(p["id"])
        save_seen(seen_ids)
        print(f"[초기화] 최초 실행 감지. 현재 글 {len(posts)}개를 seen 처리했습니다. (텔레그램 전송 없음)")
        return 0

    new_posts = [p for p in posts if p["id"] not in seen_ids]

    if not new_posts:
        print("새 글 없음.")
        return 0

    # 오래된 글부터 순서대로 전송 (자연스러운 게시 순서 유지)
    for p in reversed(new_posts):
        try:
            send_telegram(p["title"], p["url"])
            print(f"[전송 완료] {p['title']}")
            seen_ids.add(p["id"])
        except Exception as e:
            print(f"[전송 실패] {p['title']} - {e}", file=sys.stderr)
            # 실패한 글은 seen에 추가하지 않음 -> 다음 실행에서 재시도

    save_seen(seen_ids)
    return 0


if __name__ == "__main__":
    sys.exit(main())
