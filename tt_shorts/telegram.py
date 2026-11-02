"""Post a finished video to the tbilisi.today Telegram channel.

The bot must be an admin of the channel; the id comes from SHORTS_TELEGRAM_CHANNEL (a numeric id,
usually -100..., or @username). Nothing is sent when it is unset, so local runs stay quiet.
"""
import json
import os
import pathlib
import urllib.request


TOKEN_FILE = "/root/sitech/.secrets/telegram_tbilisi_bot_token"
DEFAULT_CHANNEL = "@tbilisitodayofficial"


def bot_token() -> str:
    """The tbilisi.today bot, never the shared asistent.ge one."""
    try:
        value = pathlib.Path(TOKEN_FILE).read_text(encoding="utf-8").strip()
        if value:
            return value
    except OSError:
        pass
    return os.environ.get("TELEGRAM_BOT_TOKEN", "")


def send_video(path, caption: str, chat: str | None = None, token: str | None = None, buttons=None) -> bool:
    token = token or bot_token()
    chat = chat or os.environ.get("SHORTS_TELEGRAM_CHANNEL") or DEFAULT_CHANNEL
    path = pathlib.Path(path)
    if not token or not chat or not path.exists():
        return False
    boundary = "----tt" + str(int(path.stat().st_mtime))
    parts = []
    fields = [("chat_id", chat), ("caption", caption[:1000]), ("supports_streaming", "true")]
    if buttons:
        fields.append(("reply_markup", json.dumps({"inline_keyboard": buttons}, ensure_ascii=False)))
    for name, value in fields:
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="video"; filename="{path.name}"\r\n'
                 f'Content-Type: video/mp4\r\n\r\n'.encode() + path.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendVideo", data=b"".join(parts),
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.load(r)
    return bool(data.get("ok"))


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--caption", default="")
    a = ap.parse_args()
    print("ok" if send_video(a.file, a.caption) else "skipped or failed")


if __name__ == "__main__":
    main()
