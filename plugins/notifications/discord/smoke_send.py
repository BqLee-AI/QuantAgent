from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module():
    module_path = Path(__file__).resolve().parent / "discord_plugin.py"
    module_name = "discord_plugin_smoke_send"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


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


def main() -> int:
    _load_dotenv()
    module = _load_module()
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    message = os.environ.get("DISCORD_WEBHOOK_MESSAGE", "").strip()
    timeout_text = os.environ.get("DISCORD_WEBHOOK_TIMEOUT_SECONDS", "5").strip()

    if not webhook_url:
        print("Missing DISCORD_WEBHOOK_URL.")
        return 2
    if not message:
        print("Missing DISCORD_WEBHOOK_MESSAGE.")
        return 2

    try:
        timeout_seconds = float(timeout_text)
    except ValueError:
        print("DISCORD_WEBHOOK_TIMEOUT_SECONDS must be a number.")
        return 2

    plugin = module.DiscordPlugin()
    result = plugin.send_text(
        {"webhook_secret_ref": "discord.webhooks.primary", "timeout_seconds": timeout_seconds},
        message,
        secrets={"discord.webhooks.primary": webhook_url},
    )

    print(
        {
            "ok": result.ok,
            "code": result.code,
            "message": result.message,
            "retryable": result.retryable,
            "http_status": result.http_status,
            "webhook_secret_ref": result.webhook_secret_ref,
            "response_excerpt": result.response_excerpt,
        }
    )
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
