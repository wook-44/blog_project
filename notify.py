#!/usr/bin/env python3
"""
텔레그램 알림 유틸 — 블로그 워크플로우 각 단계 완료 시 호출

사용법:
    python3 notify.py "메시지 텍스트"
    python3 notify.py "메시지 텍스트" --photo /path/to/image.png
    python3 notify.py "메시지 텍스트" --doc /path/to/file.html

종료 코드:
    0  성공
    1  config 누락 / 토큰·chat_id 없음
    2  네트워크/API 실패
"""
import os
import sys
import json
import argparse
import urllib.request
import urllib.parse
import mimetypes
import uuid
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / ".telegram_config"


def load_config():
    if not CONFIG_PATH.exists():
        print(f"[notify] config 파일 없음: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    cfg = {}
    for line in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip()
    if not cfg.get("BOT_TOKEN"):
        print("[notify] BOT_TOKEN 비어있음", file=sys.stderr)
        sys.exit(1)
    if not cfg.get("CHAT_ID"):
        print("[notify] CHAT_ID 비어있음 — setup_chat_id.command 먼저 실행하세요", file=sys.stderr)
        sys.exit(1)
    return cfg


def api_url(token, method):
    return f"https://api.telegram.org/bot{token}/{method}"


def send_text(token, chat_id, text):
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    req = urllib.request.Request(api_url(token, "sendMessage"), data=data)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_file(token, chat_id, caption, file_path, kind):
    """kind: 'photo' or 'document'"""
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"[notify] 파일 없음: {file_path}", file=sys.stderr)
        sys.exit(1)

    method = "sendPhoto" if kind == "photo" else "sendDocument"
    field_name = "photo" if kind == "photo" else "document"

    boundary = uuid.uuid4().hex
    mime, _ = mimetypes.guess_type(str(file_path))
    mime = mime or "application/octet-stream"

    body = []
    # chat_id
    body.append(f"--{boundary}\r\n".encode())
    body.append(b'Content-Disposition: form-data; name="chat_id"\r\n\r\n')
    body.append(f"{chat_id}\r\n".encode())
    # caption
    if caption:
        body.append(f"--{boundary}\r\n".encode())
        body.append(b'Content-Disposition: form-data; name="caption"\r\n\r\n')
        body.append(f"{caption}\r\n".encode())
        body.append(f"--{boundary}\r\n".encode())
        body.append(b'Content-Disposition: form-data; name="parse_mode"\r\n\r\n')
        body.append(b"HTML\r\n")
    # file
    body.append(f"--{boundary}\r\n".encode())
    body.append(
        f'Content-Disposition: form-data; name="{field_name}"; filename="{file_path.name}"\r\n'.encode()
    )
    body.append(f"Content-Type: {mime}\r\n\r\n".encode())
    body.append(file_path.read_bytes())
    body.append(f"\r\n--{boundary}--\r\n".encode())

    data = b"".join(body)
    req = urllib.request.Request(
        api_url(token, method),
        data=data,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("text", help="보낼 메시지 (HTML 태그 허용: <b>, <i>, <code>)")
    p.add_argument("--photo", help="첨부할 이미지 경로")
    p.add_argument("--doc", help="첨부할 문서 경로")
    args = p.parse_args()

    cfg = load_config()
    token = cfg["BOT_TOKEN"]
    chat_id = cfg["CHAT_ID"]

    try:
        if args.photo:
            res = send_file(token, chat_id, args.text, args.photo, "photo")
        elif args.doc:
            res = send_file(token, chat_id, args.text, args.doc, "document")
        else:
            res = send_text(token, chat_id, args.text)
    except Exception as e:
        print(f"[notify] 전송 실패: {e}", file=sys.stderr)
        sys.exit(2)

    if not res.get("ok"):
        print(f"[notify] API 실패: {res}", file=sys.stderr)
        sys.exit(2)

    print(f"[notify] 전송 OK (message_id={res['result'].get('message_id')})")


if __name__ == "__main__":
    main()
