#!/usr/bin/env python3
"""
gen_summary_copy_tool.py — 15:30 시황 요약 전용 copy_tool.html 생성

입력: YYYY-MM-DD_summary_blog.md
출력: output/YYYY-MM-DD_summary_copy_tool.html

PNG가 없으면 SVG를 base64로 임베드.
"""

import sys
import base64
import re
import html as htmllib
from pathlib import Path

BASE = Path(__file__).parent.parent


def md_to_naver_html(md_text: str) -> str:
    """매우 단순한 마크다운→네이버 호환 HTML 변환."""
    lines = md_text.split("\n")
    html_lines = []
    in_table = False
    table_lines = []
    in_list = False

    def flush_table():
        nonlocal table_lines
        if not table_lines:
            return ""
        out = ['<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%;font-size:14px;">']
        for i, row in enumerate(table_lines):
            # 헤더 구분선 제거
            if re.match(r"^[\s|:\-]+$", row):
                continue
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            tag = "th" if i == 0 else "td"
            style_h = 'style="padding:6px 10px;border:1px solid #d1d5db;background:#f3f4f6;font-weight:bold;"'
            style_t = 'style="padding:6px 10px;border:1px solid #d1d5db;"'
            cells_html = "".join(
                f"<{tag} {style_h if tag=='th' else style_t}>{c}</{tag}>" for c in cells
            )
            out.append(f"<tr>{cells_html}</tr>")
        out.append("</table>")
        table_lines = []
        return "\n".join(out)

    for ln in lines:
        if ln.startswith("# "):
            html_lines.append(f'<h1 style="font-size:30px;font-weight:bold;margin:24px 0 12px;line-height:1.35;">{ln[2:].strip()}</h1>')
            html_lines.append("<p>&nbsp;</p>")
        elif ln.startswith("## "):
            html_lines.append(f'<h2 style="font-size:21px;font-weight:bold;margin:22px 0 10px;color:#0f172a;">{ln[3:].strip()}</h2>')
        elif ln.startswith("|"):
            in_table = True
            table_lines.append(ln)
        elif in_table and not ln.startswith("|"):
            html_lines.append(flush_table())
            in_table = False
            if ln.strip():
                html_lines.append(_paragraph(ln))
        elif ln.startswith("- "):
            if not in_list:
                in_list = True
                html_lines.append("<ul>")
            html_lines.append(f'<li style="font-size:15px;line-height:1.7;margin:4px 0;">{_inline(ln[2:])}</li>')
        elif in_list and ln.strip() == "":
            html_lines.append("</ul>")
            in_list = False
        elif ln.startswith("---"):
            html_lines.append('<hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0;">')
        elif re.match(r"^\d+\.\s+", ln):
            num_text = re.sub(r"^\d+\.\s+", "", ln)
            html_lines.append(f'<p style="font-size:15px;line-height:1.7;margin:4px 0;">{_inline(ln.split(".",1)[0])}. {_inline(num_text)}</p>')
        elif ln.strip().startswith("#"):
            # 태그 라인 — 별도 처리
            continue
        elif ln.strip():
            html_lines.append(_paragraph(ln))
    if in_table:
        html_lines.append(flush_table())
    if in_list:
        html_lines.append("</ul>")
    return "\n".join(html_lines)


def _paragraph(ln: str) -> str:
    return f'<p style="font-size:15px;line-height:1.7;margin:8px 0;">{_inline(ln)}</p>'


def _inline(text: str) -> str:
    # **bold**
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # *italic*
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    return text


def md_to_plaintext(md_text: str) -> str:
    """마크다운에서 표·기호 정리 후 네이버 텍스트 붙여넣기용."""
    out = []
    for ln in md_text.split("\n"):
        if ln.startswith("#") and not ln.startswith("##") and "#" in ln[2:]:
            # 태그 라인
            continue
        ln_clean = re.sub(r"^\#+\s*", "", ln)
        ln_clean = re.sub(r"\*\*(.+?)\*\*", r"\1", ln_clean)
        ln_clean = re.sub(r"\*(.+?)\*", r"\1", ln_clean)
        out.append(ln_clean)
    return "\n".join(out)


def extract_tags(md_text: str) -> list:
    """본문 마지막 태그 라인에서 태그 추출."""
    tags_section = re.search(r"## 태그\s*\n+(.+?)$", md_text, re.DOTALL)
    if not tags_section:
        return []
    return re.findall(r"#\S+", tags_section.group(1))


def extract_title(md_text: str) -> str:
    m = re.match(r"^#\s+(.+)", md_text)
    return m.group(1).strip() if m else "(제목 없음)"


def main(date_str: str):
    md_path = BASE / f"{date_str}_summary_blog.md"
    if not md_path.exists():
        print(f"❌ {md_path} 없음", file=sys.stderr)
        sys.exit(1)

    md_text = md_path.read_text(encoding="utf-8")
    title = extract_title(md_text)
    body_html = md_to_naver_html(md_text)
    body_plain = md_to_plaintext(md_text)
    tags = extract_tags(md_text)
    tag_chips = "\n".join(
        f'<span class="tag-chip" onclick="copyOneTag(this, this.innerText)">{t}</span>' for t in tags
    )
    tags_full = " ".join(tags)

    # 이미지 (PNG 우선, 없으면 SVG)
    img_dir = BASE / "images" / f"{date_str}-summary"
    png = img_dir / f"{date_str}-summary-market.png"
    svg = img_dir / f"{date_str}-summary-market.svg"

    img_html = ""
    if png.exists():
        b64 = base64.b64encode(png.read_bytes()).decode("ascii")
        img_html = (
            '<canvas id="canvasMarket" style="display:none;"></canvas>\n'
            f'<img class="preview" id="imgMarket" src="data:image/png;base64,{b64}" onload="loadImgToCanvas(\'canvasMarket\', this.src)">\n'
            '<button class="btn btn-img" onclick="copyImg(\'canvasMarket\',\'toastImg\')">📷 이미지 복사</button>\n'
            '<span class="toast" id="toastImg">✅ 복사됨!</span>'
        )
    elif svg.exists():
        svg_text = svg.read_text(encoding="utf-8")
        b64 = base64.b64encode(svg_text.encode("utf-8")).decode("ascii")
        img_html = (
            f'<img class="preview" id="imgMarket" src="data:image/svg+xml;base64,{b64}">\n'
            '<p style="font-size:12px;color:#dc2626;margin-top:8px;">⚠️ PNG 미생성 (Mac에서 <code>_render_'
            f'{date_str}-summary.command</code> 실행 후 재생성 필요)</p>'
        )
    else:
        img_html = '<p style="font-size:13px;color:#dc2626;">⚠️ 인포그래픽 이미지 없음</p>'

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>네이버 블로그 시황 요약 복사 도구 — {date_str} (15:30)</title>
<style>
  body {{ font-family: 'Apple SD Gothic Neo', sans-serif; max-width: 860px; margin: 0 auto; padding: 30px 20px; background: #f8fafc; color: #1e293b; }}
  h1 {{ font-size: 20px; margin-bottom: 6px; }}
  .desc {{ font-size: 14px; color: #64748b; margin-bottom: 30px; line-height: 1.7; }}
  .step {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px 24px; margin-bottom: 20px; }}
  .step-title {{ font-size: 15px; font-weight: 700; color: #0f172a; margin-bottom: 10px; }}
  .btn {{ display: inline-block; padding: 10px 20px; border-radius: 8px; border: none; cursor: pointer; font-size: 14px; font-weight: 600; }}
  .btn-text {{ background: #3b82f6; color: #fff; }}
  .btn-img  {{ background: #10b981; color: #fff; margin-top: 10px; }}
  .btn-tag  {{ background: #f59e0b; color: #fff; margin-top: 10px; }}
  .tag-chip {{ display: inline-block; padding: 4px 10px; margin: 3px; background: #fef3c7; color: #92400e; border-radius: 999px; font-size: 12px; font-weight: 600; cursor: pointer; user-select: none; }}
  .tag-chip.copied {{ background: #10b981; color: #fff; }}
  .body-preview {{ background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 10px; padding: 16px 22px; margin: 12px 0; line-height: 1.7; font-size: 15px; color: #1e293b; max-height: 500px; overflow-y: auto; }}
  .toast {{ display: none; margin-left: 10px; font-size: 13px; color: #10b981; font-weight: 600; }}
  img.preview {{ width: 100%; border-radius: 8px; margin-top: 12px; border: 1px solid #e2e8f0; }}
  .order {{ display: inline-block; background: #3b82f6; color: #fff; border-radius: 50%; width: 22px; height: 22px; text-align: center; line-height: 22px; font-size: 12px; font-weight: 700; margin-right: 6px; }}
  .text-box {{ background: #f1f5f9; border-radius: 8px; padding: 16px 18px; font-size: 13px; line-height: 1.8; color: #475569; max-height: 200px; overflow-y: auto; white-space: pre-wrap; }}
  .hidden-body {{ display: none; }}
  .tag-box {{ background: #fffbeb; border: 1px solid #fde68a; border-radius: 10px; padding: 12px 14px; margin: 10px 0 4px; line-height: 1.8; }}
  .summary-badge {{ display: inline-block; padding: 2px 8px; background: #dc2626; color: #fff; border-radius: 4px; font-size: 11px; font-weight: 700; margin-left: 6px; vertical-align: middle; }}
</style>
</head>
<body>

<h1>📋 네이버 블로그 포스팅 도구 <span class="summary-badge">15:30 시황 요약</span></h1>
<p class="desc">장 마감 직후의 시황 요약 포스트입니다.<br><b>① 제목 → ② 본문 → ③ 인포그래픽 1장 → ④ 태그</b> 순서로 진행하세요.</p>

<div class="step">
  <div class="step-title"><span class="order" style="background:#8b5cf6;">0</span> 블로그 제목</div>
  <div class="text-box" id="titleBox">{htmllib.escape(title)}</div>
  <button class="btn btn-text" style="background:#8b5cf6;margin-top:10px;" onclick="copyPlain('titleBox','toastTitle')">📋 제목 복사</button>
  <span class="toast" id="toastTitle">✅ 복사됨!</span>
</div>

<div class="step">
  <div class="step-title"><span class="order">1</span> 블로그 본문 텍스트 복사 → 네이버 붙여넣기</div>
  <button class="btn btn-text" onclick="copyText()">📄 텍스트 전체 복사</button>
  <span class="toast" id="toastText">✅ 복사됨!</span>
  <div class="body-preview" id="blogBodyHtml">
{body_html}
  </div>
  <div class="hidden-body" id="blogBodyPlain">{htmllib.escape(body_plain)}</div>
</div>

<div class="step">
  <div class="step-title"><span class="order">2</span> 인포그래픽 1장 — 시장 분석 (market)</div>
  {img_html}
</div>

<div class="step">
  <div class="step-title"><span class="order">3</span> 태그 30개 (개별 클릭 또는 전체 복사)</div>
  <div class="tag-box">
    {tag_chips}
  </div>
  <button class="btn btn-tag" onclick="copyTags()">🏷️ 태그 전체 복사</button>
  <span class="toast" id="toastTags">✅ 복사됨!</span>
  <div class="hidden-body" id="allTags">{htmllib.escape(tags_full)}</div>
</div>

<script>
async function copyOneTag(el, tag) {{
  await navigator.clipboard.writeText(tag);
  el.classList.add('copied');
  setTimeout(() => el.classList.remove('copied'), 1200);
}}
async function copyTags() {{
  const t = document.getElementById('allTags').innerText;
  await navigator.clipboard.writeText(t);
  showToast('toastTags');
}}
function showToast(id) {{
  const e = document.getElementById(id);
  e.style.display = 'inline';
  setTimeout(() => {{ e.style.display = 'none'; }}, 1500);
}}
async function copyPlain(boxId, toastId) {{
  const text = document.getElementById(boxId).innerText;
  await navigator.clipboard.writeText(text);
  showToast(toastId);
}}
async function copyText() {{
  const html = document.getElementById('blogBodyHtml').innerHTML;
  const plain = document.getElementById('blogBodyPlain').innerText;
  try {{
    const item = new ClipboardItem({{
      'text/html': new Blob([html], {{type:'text/html'}}),
      'text/plain': new Blob([plain], {{type:'text/plain'}})
    }});
    await navigator.clipboard.write([item]);
  }} catch(e) {{
    await navigator.clipboard.writeText(plain);
  }}
  showToast('toastText');
}}
function loadImgToCanvas(canvasId, src) {{
  const canvas = document.getElementById(canvasId);
  const ctx = canvas.getContext('2d');
  const img = new Image();
  img.onload = function() {{ canvas.width = img.width; canvas.height = img.height; ctx.drawImage(img, 0, 0); }};
  img.src = src;
}}
function copyImg(canvasId, toastId) {{
  const canvas = document.getElementById(canvasId);
  canvas.toBlob(async (blob) => {{
    await navigator.clipboard.write([new ClipboardItem({{'image/png': blob}})]);
    showToast(toastId);
  }}, 'image/png');
}}
</script>
</body>
</html>"""

    out_dir = BASE / "output"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{date_str}_summary_copy_tool.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"✅ {out_path}")


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    if not date_arg:
        from datetime import date
        date_arg = date.today().isoformat()
    main(date_arg)
