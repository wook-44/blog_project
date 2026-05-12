#!/usr/bin/env python3
"""
블로그 이미지 자동 업로드 (표준 라이브러리만 사용 - 별도 설치 불필요)
사용법: python3 upload_images.py 2026-04-27
"""

import sys, os, json, base64, glob, urllib.request, urllib.parse
from datetime import date

IMGBB_API_KEY = "f1487d42e522939e8c7bb70feacde1f9"
BLOG_ROOT = os.path.dirname(os.path.abspath(__file__))


def upload_image(path: str, name: str) -> dict:
    with open(path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    data = urllib.parse.urlencode({
        "key": IMGBB_API_KEY,
        "image": img_b64,
        "name": name,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.imgbb.com/1/upload",
        data=data,
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    if not result.get("success"):
        raise RuntimeError(f"업로드 실패: {result}")

    d = result["data"]
    return {
        "name": name,
        "url": d["url"],
        "display_url": d.get("display_url", d["url"]),
        "viewer_url": d.get("url_viewer", ""),
        "delete_url": d.get("delete_url", ""),
    }


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else str(date.today())
    folder = os.path.join(BLOG_ROOT, date_str)

    if not os.path.isdir(folder):
        print(f"❌ 폴더 없음: {folder}")
        sys.exit(1)

    images = sorted(glob.glob(os.path.join(folder, "*.jpg")) +
                    glob.glob(os.path.join(folder, "*.png")))

    if not images:
        print(f"❌ 이미지 없음: {folder}")
        sys.exit(1)

    print(f"\n📁 {folder}")
    print(f"🖼  {len(images)}개 이미지 업로드 시작\n")

    results = []
    for path in images:
        filename = os.path.basename(path)
        name = os.path.splitext(filename)[0] + f"_{date_str}"
        print(f"  ⬆️  {filename}...", end=" ", flush=True)
        try:
            info = upload_image(path, name)
            results.append(info)
            print(f"✅  {info['url']}")
        except Exception as e:
            print(f"❌  {e}")

    if results:
        out = os.path.join(folder, "image_urls.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 완료! → {out}")
    else:
        print("\n❌ 업로드된 이미지 없음")


if __name__ == "__main__":
    main()
