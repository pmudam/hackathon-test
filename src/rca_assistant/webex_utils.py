from __future__ import annotations

import json
import os
from urllib import request
from urllib.error import HTTPError, URLError

WEBEX_MESSAGES_URL = os.getenv("WEBEX_MESSAGES_URL", "https://webexapis.com/v1/messages")


def send_webex_message(markdown: str) -> None:
    bot_token = os.getenv("WEBEX_BOT_TOKEN", "").strip()
    room_id = os.getenv("WEBEX_ROOM_ID", "").strip()

    if not bot_token:
        raise ValueError("Set WEBEX_BOT_TOKEN to enable Webex notifications")
    if not room_id:
        raise ValueError("Set WEBEX_ROOM_ID to enable Webex notifications")

    payload = json.dumps({"roomId": room_id, "markdown": markdown}).encode("utf-8")
    req = request.Request(
        WEBEX_MESSAGES_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=20) as response:
            status = getattr(response, "status", None) or response.getcode()
            if status >= 400:
                raise RuntimeError(f"Webex API returned status {status}")
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Webex API error {error.code}: {details}") from error
    except URLError as error:
        raise RuntimeError(f"Unable to reach Webex API: {error.reason}") from error
