from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

from nacl.encoding import HexEncoder
from nacl.signing import SigningKey


REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_dotenv() -> None:
    dotenv_path = REPO_ROOT / ".env"
    if not dotenv_path.is_file():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        os.environ.setdefault(key, value.strip())


def _generate_body() -> bytes:
    payload = {
        "id": os.environ.get("DISCORD_INTERACTION_ID", "1234567890"),
        "application_id": os.environ.get("DISCORD_APPLICATION_ID", "app-1"),
        "type": int(os.environ.get("DISCORD_INTERACTION_TYPE", "2")),
        "guild_id": os.environ.get("DISCORD_GUILD_ID", "guild-1"),
        "channel_id": os.environ.get("DISCORD_CHANNEL_ID", "channel-1"),
        "member": {
            "user": {
                "id": os.environ.get("DISCORD_AUTHOR_ID", "user-1"),
            }
        },
        "data": {
            "name": os.environ.get("DISCORD_COMMAND_NAME", "notify"),
            "options": [
                {
                    "name": os.environ.get("DISCORD_OPTION_NAME", "text"),
                    "type": 3,
                    "value": os.environ.get("DISCORD_OPTION_VALUE", "hello from smoke receive"),
                }
            ],
        },
    }
    return json.dumps(payload).encode("utf-8")


def main() -> int:
    _load_dotenv()
    endpoint = os.environ.get(
        "NOTIFICATION_INGRESS_ENDPOINT_URL",
        "http://127.0.0.1:8000/api/v1/integrations/notifications/ingress",
    ).strip()
    private_key = os.environ.get("NOTIFICATION_INGRESS_TEST_PRIVATE_KEY", "").strip()
    timeout_text = os.environ.get("NOTIFICATION_INGRESS_TIMEOUT_SECONDS", "5").strip()
    timestamp = os.environ.get("NOTIFICATION_INGRESS_TEST_TIMESTAMP", str(int(time.time()))).strip()

    if not endpoint:
        print("Missing NOTIFICATION_INGRESS_ENDPOINT_URL.")
        return 2
    if not private_key:
        print("Missing NOTIFICATION_INGRESS_TEST_PRIVATE_KEY.")
        return 2

    try:
        timeout_seconds = float(timeout_text)
    except ValueError:
        print("NOTIFICATION_INGRESS_TIMEOUT_SECONDS must be a number.")
        return 2

    body = _generate_body()
    signing_key = SigningKey(bytes.fromhex(private_key))
    public_key = signing_key.verify_key.encode(encoder=HexEncoder).decode("utf-8")
    signature = signing_key.sign(timestamp.encode("utf-8") + body).signature.hex()

    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature-Timestamp": timestamp,
            "X-Signature-Ed25519": signature,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            print(
                {
                    "ok": True,
                    "http_status": response.status,
                    "response_body": response_body,
                    "derived_public_key": public_key,
                }
            )
            return 0
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        print(
            {
                "ok": False,
                "http_status": exc.code,
                "response_body": response_body,
                "derived_public_key": public_key,
            }
        )
        return 1
    except OSError as exc:
        print(
            {
                "ok": False,
                "error": exc.__class__.__name__,
                "message": str(exc),
                "derived_public_key": public_key,
            }
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
