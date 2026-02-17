import warnings

# Suppress noisy urllib3/OpenSSL warnings (e.g. NotOpenSSLWarning) so they
# don't spam the log when run under launchctl.
warnings.filterwarnings("ignore", module="urllib3")

import feedparser
import os
import requests
from typing import Optional, Dict, Any

# -----------------------------------------------------------------------------
# Configuration from environment variables.
# -----------------------------------------------------------------------------
YOUTUBE_CHANNEL_ID = os.environ.get("YOUTUBE_CHANNEL_ID", "")
FEED_URL = os.environ.get(
    "YOUTUBE_FEED_URL",
    f"https://www.youtube.com/feeds/videos.xml?channel_id={YOUTUBE_CHANNEL_ID}" if YOUTUBE_CHANNEL_ID else "",
).strip()
LAST_SEEN_FILE = os.environ.get("LAST_SEEN_FILE", "")
PUSHOVER_USER = os.environ.get("PUSHOVER_USER", "")
PUSHOVER_TOKEN = os.environ.get("PUSHOVER_TOKEN", "")

def send_pushover_notification(to: str, text: str, url: Optional[str] = None) -> None:
    data: Dict[str, Any] = {
        "token": PUSHOVER_TOKEN,
        "user": to,
        "title": "📺 New YouTube Video",
        "message": text,
        "priority": int(os.environ.get("PUSHOVER_PRIORITY", "1")),
    }

    # Only valid for Emergency priority
    if data["priority"] == 2:
        data["retry"] = int(os.environ.get("PUSHOVER_RETRY", "60"))
        data["expire"] = int(os.environ.get("PUSHOVER_EXPIRE", "3600"))

    if url is not None:
        data["url"] = url
        data["url_title"] = "Open Video"

    r = requests.post("https://api.pushover.net/1/messages.json", data=data, timeout=15)
    r.raise_for_status()


def main() -> None:
    """
    Check the YouTube feed and send a notification when there is a new video.
    """
    required = [
        ("YOUTUBE_FEED_URL or YOUTUBE_CHANNEL_ID", FEED_URL),
        ("LAST_SEEN_FILE", LAST_SEEN_FILE),
        ("PUSHOVER_USER", PUSHOVER_USER),
        ("PUSHOVER_TOKEN", PUSHOVER_TOKEN),
    ]
    missing = [name for name, value in required if not (value and value.strip())]
    if missing:
        print("Missing required env: " + ", ".join(missing))
        return

    feed = feedparser.parse(FEED_URL)
    # Avoid crashing if the feed is temporarily empty or failed to load.
    if not getattr(feed, "entries", None):
        print("No entries found in feed. Exiting without sending notification.")
        return

    latest = feed.entries[0]

    video_id = latest.yt_videoid
    title = latest.title
    link = latest.link

    try:
        with open(LAST_SEEN_FILE) as f:
            last_seen = f.read().strip()
    except FileNotFoundError:
        print("LAST_SEEN_FILE not found; treating as first run.")
        last_seen = None

    print(f"Last seen video ID: {last_seen}")

    if video_id != last_seen:
        print("New video detected. Sending notification and updating LAST_SEEN_FILE.")
        send_pushover_notification(PUSHOVER_USER, title, link)

        with open(LAST_SEEN_FILE, "w") as f:
            f.write(video_id)
        print("LAST_SEEN_FILE updated.")
    else:
        print("No new video. Nothing to do.")


if __name__ == "__main__":
    main()
