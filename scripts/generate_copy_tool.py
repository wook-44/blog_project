#!/usr/bin/env python3
"""
generate_copy_tool.py
---------------------
블로그 마크다운 + 이미지 PNG → 네이버 블로그 복사 도구 HTML 생성

사용법:
  python3 scripts/generate_copy_tool.py YYYY-MM-DD

결과:
  /Users/chanwook/Documents/Claude/Projects/블로그/output/YYYY-MM-DD_copy_tool.html
"""

import sys
import base64
import re
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent.parent   # 블로그 폴더 루트


def find_md_file(date_str: str) -> Path:
    """날짜 prefix로 시작하는 블로그 md 파일 찾기 (seo 제외)"""
    candidates = sorted(BASE.glob(f"{date_str}*.md"))
    candidates = [p for p in candidates if "seo" not in p.name.lower()
                  and "README" not in p.name and "SECRETS" not in p.name]
    if not candidates:
        raise FileNotFoundError(f"날짜 {date_str}에 해당하는 .md 파일이 없습니다.")
    return candidates[0]


def find_png_files(date_str: str) -> list[Path]:
    """images/YYYY-MM-DD/ 에서 PNG 파일 목록 (정렬, insight 제외)"""
    img_dir = BASE / "images" / date_str
    if not img_dir.exists():
        return []
    pngs = sorted(p for p in img_dir.glob("*.png") if "insight" not in p.name)
    return pngs


def extract_insight(md_text: str) -> str:
    """마크다운에서 인사이트 섹션 첫 단락 추출"""
    lines = md_text.split("\n")
    in_insight = False
    paragraphs = []
    current = []

    for line in lines:
        if re.search(r'^##\s+.*(인사이트|insight)', line, re.IGNORECASE):
            in_insight = True
            continue
        if in_insight:
            # 다음 ## 헤더가 나오면 종료
            if line.startswith("## ") or line.startswith("# "):
                break
            if line.strip() == "---":
                break
            if line.strip():
                current.append(line.strip())
            elif current:
                paragraphs.append(" ".join(current))
                current = []

    if current:
        paragraphs.append(" ".join(current))

    # 첫 번째 의미 있는 단락만 반환
    for p in paragraphs:
        if len(p) > 20:
            return p

    return ""


def md_to_html_body(md_text: str) -> str:
    """간단한 마크다운 → HTML 변환 (블로그 본문용)"""
    lines = md_text.split("\n")
    html_parts = []
    in_table = False
    in_list = False

    for line in lines:
        # 헤더
        if line.startswith("### "):
            if in_list: html_parts.append("</ul>"); in_list = False
            html_parts.append(f"<h3>{line[4:].strip()}</h3>")
        elif line.startswith("## "):
            if in_list: html_parts.append("</ul>"); in_list = False
            html_parts.append(f"<h2>{line[3:].strip()}</h2>")
        elif line.startswith("# "):
            if in_list: html_parts.append("</ul>"); in_list = False
            html_parts.append(f"<h1>{line[2:].strip()}</h1>")
        # 구분선
        elif line.strip() == "---":
            if in_list: html_parts.append("</ul>"); in_list = False
            html_parts.append("<hr>")
        # 테이블 행
        elif "|" in line and "---" not in line:
            if not in_table:
                html_parts.append('<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%;font-size:14px;">')
                in_table = True
            cells = [c.strip() for c in line.split("|") if c.strip()]
            tag = "th" if html_parts and "<th>" not in html_parts[-1] and "<tr>" not in html_parts[-1] else "td"
            row = "".join(f"<{tag}>{c}</{tag}>" for c in cells)
            html_parts.append(f"<tr>{row}</tr>")
        elif in_table and "|" not in line:
            html_parts.append("</table>")
            in_table = False
            if line.strip():
                html_parts.append(f"<p>{line}</p>")
        # 인용/마커 (>)
        elif line.startswith("> "):
            if in_list: html_parts.append("</ul>"); in_list = False
            content = line[2:].strip()
            content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
            # 이미지 마커는 중앙 정렬 빨간색 글자만
            if "👇" in content or "🖼️" in content:
                # 마커는 단순 텍스트로 — 이모지·강조 제거
                clean = re.sub(r"[👇🖼️]\s*", "", content).strip()
                html_parts.append(f'<p style="text-align:center;color:#dc2626;margin:14px 0;">{clean}</p>')
            else:
                content = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line[2:].strip())
                html_parts.append(f"<blockquote>{content}</blockquote>")
        # 리스트
        elif line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            content = line[2:].strip()
            content = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', content)
            html_parts.append(f"<li>{content}</li>")
        elif line.startswith("  - ") or line.startswith("  * "):
            content = line[4:].strip()
            html_parts.append(f"<li style='margin-left:20px'>{content}</li>")
        # 빈 줄
        elif not line.strip():
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            if in_table:
                html_parts.append("</table>")
                in_table = False
        # 일반 텍스트
        else:
            if in_list: html_parts.append("</ul>"); in_list = False
            content = line.strip()
            # 볼드/이탤릭 처리
            content = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', content)
            content = re.sub(r'\*(.+?)\*', r'<i>\1</i>', content)
            if content:
                html_parts.append(f"<p>{content}</p>")

    if in_list: html_parts.append("</ul>")
    if in_table: html_parts.append("</table>")

    return "\n".join(html_parts)


def img_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def extract_title(md_text: str) -> str:
    for line in md_text.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return "블로그 제목"


def strip_appendix_sections(md_text: str) -> str:
    """본문 복사용 — '## 태그'와 '## [부록]...' 섹션 제거. 투자 주의 문구는 유지."""
    # 투자 주의 문구 미리 추출 (잘려도 되살리기 위함)
    disclaimer = ""
    m = re.search(r"\*[^*\n]*(?:본인에게 있|투자의 책임|참고용)[^*\n]*\*", md_text)
    if m:
        disclaimer = m.group()

    # ## 태그 / ## [부록] 섹션을 다음 ## 헤더 또는 EOF까지 통째 삭제
    text = re.sub(r"^##\s+태그.*?(?=^##\s|\Z)", "", md_text,
                  flags=re.DOTALL | re.MULTILINE)
    text = re.sub(r"^##\s+\[부록\].*?(?=^##\s|\Z)", "", text,
                  flags=re.DOTALL | re.MULTILINE)

    # 투자 주의 문구가 잘렸으면 본문 끝에 다시 부착
    if disclaimer and disclaimer not in text:
        text = text.rstrip() + "\n\n---\n\n" + disclaimer + "\n"

    # 연속된 빈 줄 정리
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def inject_image_markers(md_text: str) -> str:
    """본문 안에 이미지 삽입 마커 추가. ## 시장 분석 등 키워드 헤더 직후."""
    markers = [
        (r"^(##\s+.*시장 분석.*)$", "이미지 1 여기에 붙여넣기"),
        (r"^(##\s+.*투자 심리.*)$", "이미지 2 여기에 붙여넣기"),
        (r"^(##\s+.*핵심 포인트.*)$", "이미지 3 여기에 붙여넣기"),
    ]
    lines = md_text.split("\n")
    out = []
    for line in lines:
        out.append(line)
        for pat, label in markers:
            if re.match(pat, line):
                out.append("")
                out.append(f"> 🖼️ {label}")
                out.append("")
                break
    return "\n".join(out)


def extract_tags(md_text: str) -> list[str]:
    """본문 어디서든 ## 태그 섹션 또는 마지막 #해시태그 라인에서 태그 추출."""
    # 1) ## 태그 섹션 우선
    in_tag = False
    bucket = []
    for line in md_text.split("\n"):
        if re.match(r"^##\s+태그", line):
            in_tag = True
            continue
        if in_tag:
            if line.startswith("##") or line.startswith("# "):
                break
            if line.strip().startswith("---"):
                break
            bucket.append(line)
    chunk = "\n".join(bucket) if bucket else md_text
    tags = re.findall(r"#([\w가-힣]+)", chunk)
    # 중복 제거하면서 순서 유지
    seen, ordered = set(), []
    for t in tags:
        if t not in seen and len(t) > 0:
            seen.add(t)
            ordered.append(t)
    return ordered


def generate_html(date_str: str, title: str, body_html: str, png_files: list[Path], tags: list[str] = None) -> str:
    """HTML 복사 도구 생성"""
    tags = tags or []

    # 이미지 섹션 생성
    img_sections = ""
    for i, png in enumerate(png_files[:5], 1):
        b64 = img_to_base64(png)
        img_name = png.name
        img_sections += f"""
<!-- STEP {i+1}: 이미지 {i} -->
<div class="step">
  <div class="step-title"><span class="order">{i+1}</span> 이미지 {i} 복사 → 해당 위치에 붙여넣기</div>
  <p style="font-size:13px;color:#64748b;margin-bottom:8px;">{img_name}</p>
  <img class="preview" src="data:image/png;base64,{b64}" alt="이미지{i}">
  <br>
  <button class="btn btn-img" onclick="copyImg('img{i}','toast{i+1}')">🖼️ 이미지 {i} 복사</button>
  <span class="toast" id="toast{i+1}">✅ 복사됨!</span>
  <canvas id="img{i}" style="display:none"></canvas>
</div>
"""

    # 태그 섹션 (마지막 STEP)
    tag_step_idx = len(png_files[:5]) + 2  # 0(제목) + 1(본문) + N(이미지) 다음
    tags_for_paste = " ".join(f"#{t}" for t in tags)
    tags_pretty = " ".join(f'<span class="tag-chip">#{t}</span>' for t in tags)
    tag_section = f"""
<!-- STEP {tag_step_idx}: 태그 -->
<div class="step">
  <div class="step-title"><span class="order" style="background:#f59e0b;">{tag_step_idx}</span> 해시태그 복사 → 네이버 에디터 하단 태그칸에 붙여넣기</div>
  <p style="font-size:13px;color:#64748b;margin-bottom:10px;">총 {len(tags)}개 — 네이버 권장 30개</p>
  <div class="tag-box" id="tagBox">{tags_pretty}</div>
  <button class="btn btn-tag" onclick="copyTags()">🏷️ 태그 전체 복사</button>
  <span class="toast" id="toastTag">✅ 복사됨!</span>
  <div class="hidden-body" id="tagsRaw">{tags_for_paste}</div>
</div>
"""

    # 이미지 JS 로더
    img_loaders = ""
    for i, png in enumerate(png_files[:5], 1):
        b64 = img_to_base64(png)
        img_loaders += f"""
  loadImgToCanvas('img{i}', 'data:image/png;base64,{b64}');"""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>네이버 블로그 이미지 복사 도구 — {date_str}</title>
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
  .tag-chip {{ display: inline-block; padding: 4px 10px; margin: 3px; background: #fef3c7; color: #92400e; border-radius: 999px; font-size: 12px; font-weight: 600; }}
  .tag-box  {{ background: #fffbeb; border: 1px solid #fde68a; border-radius: 10px; padding: 12px 14px; margin: 10px 0 4px; line-height: 1.8; }}
  .body-preview {{ background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 10px; padding: 16px 22px; margin: 12px 0; line-height: 1.7; font-size: 15px; color: #1e293b; max-height: 500px; overflow-y: auto; }}
  .body-preview h1 {{ font-size: 20px; margin: 8px 0 12px; color: #0f172a; }}
  .body-preview h2 {{ font-size: 17px; margin: 18px 0 8px; color: #1e293b; padding-top: 8px; border-top: 1px solid #e2e8f0; }}
  .body-preview p {{ margin: 8px 0; }}
  .body-preview ul {{ margin: 8px 0 8px 12px; }}
  .body-preview li {{ margin: 4px 0; }}
  .body-preview hr {{ border: none; border-top: 1px dashed #cbd5e1; margin: 16px 0; }}
  .body-preview blockquote {{ margin: 8px 0; padding: 8px 14px; background: #eff6ff; border-left: 3px solid #3b82f6; border-radius: 4px; font-size: 14px; }}
  .body-preview table {{ border-collapse: collapse; margin: 10px 0; font-size: 13px; }}
  .body-preview th, .body-preview td {{ border: 1px solid #cbd5e1; padding: 6px 10px; }}
  .body-preview th {{ background: #f1f5f9; }}
  .btn:active {{ opacity: 0.8; }}
  .toast {{ display: none; margin-left: 10px; font-size: 13px; color: #10b981; font-weight: 600; }}
  img.preview {{ width: 100%; border-radius: 8px; margin-top: 12px; border: 1px solid #e2e8f0; }}
  .order {{ display: inline-block; background: #3b82f6; color: #fff; border-radius: 50%; width: 22px; height: 22px; text-align: center; line-height: 22px; font-size: 12px; font-weight: 700; margin-right: 6px; }}
  .text-box {{ background: #f1f5f9; border-radius: 8px; padding: 16px 18px; font-size: 13px; line-height: 1.8; color: #475569; max-height: 200px; overflow-y: auto; white-space: pre-wrap; }}
  #copyStatus {{ display: none; background: #d1fae5; border: 1px solid #6ee7b7; border-radius: 8px; padding: 10px 16px; font-size: 14px; color: #065f46; margin-top: 10px; }}
  .hidden-body {{ display: none; }}
</style>
</head>
<body>

<h1>📋 네이버 블로그 포스팅 도구</h1>
<p class="desc">
  아래 순서대로 진행하세요:<br>
  <b>① 텍스트 복사 → 네이버 블로그 본문에 붙여넣기</b><br>
  <b>② 이미지1~{len(png_files)} 순서대로 복사 → 네이버 블로그 본문의 해당 위치에 붙여넣기</b>
</p>

<!-- STEP 0: 제목 -->
<div class="step">
  <div class="step-title"><span class="order" style="background:#8b5cf6;">0</span> 블로그 제목 (에디터 제목칸에 입력)</div>
  <div class="text-box" id="titleBox">{title}</div>
  <button class="btn btn-text" style="background:#8b5cf6;margin-top:10px;" onclick="copyPlain('titleBox','toastTitle')">📋 제목 복사</button>
  <span class="toast" id="toastTitle">✅ 복사됨!</span>
</div>

<!-- STEP 1: 텍스트 복사 -->
<div class="step">
  <div class="step-title"><span class="order">1</span> 블로그 본문 텍스트 복사 → 네이버 붙여넣기</div>
  <p style="font-size:13px;color:#64748b;margin-bottom:8px;">아래 본문 미리보기 확인 후 복사 버튼을 누르면 서식 포함 전체 텍스트가 클립보드에 복사됩니다.</p>
  <button class="btn btn-text" onclick="copyText()">📄 텍스트 전체 복사</button>
  <span class="toast" id="toastText">✅ 복사됨!</span>
  <div id="copyStatus">텍스트가 복사되었습니다. 네이버 블로그 에디터에 Cmd+V 로 붙여넣으세요.</div>

  <!-- 본문 미리보기 (화면에 보임 + 복사 대상) -->
  <div class="body-preview" id="blogBodyHtml">
{body_html}
  </div>
</div>

{img_sections}

{tag_section}

<script>
async function copyTags() {{
  const raw = document.getElementById('tagsRaw').innerText;
  try {{
    await navigator.clipboard.writeText(raw);
    showToast('toastTag');
  }} catch(e) {{
    const ta = document.createElement('textarea');
    ta.value = raw;
    document.body.appendChild(ta);
    ta.select();
    try {{ document.execCommand('copy'); showToast('toastTag'); }}
    catch(e2) {{ alert('태그 복사 실패'); }}
    document.body.removeChild(ta);
  }}
}}
function showToast(id) {{
  const el = document.getElementById(id);
  el.style.display = 'inline';
  setTimeout(() => el.style.display = 'none', 2000);
}}

async function copyPlain(boxId, toastId) {{
  const text = document.getElementById(boxId).innerText;
  try {{
    await navigator.clipboard.writeText(text);
    showToast(toastId);
  }} catch(e) {{
    // Fallback — 임시 textarea + execCommand
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    try {{ document.execCommand('copy'); showToast(toastId); }}
    catch(e2) {{ alert('복사 실패 — 직접 선택하여 복사하세요'); }}
    document.body.removeChild(ta);
  }}
}}

async function copyText() {{
  const body = document.getElementById('blogBodyHtml');
  const html = body.innerHTML;
  const text = body.innerText;
  let ok = false;

  // 1) 최신 Clipboard API — HTML + plain 같이 (네이버 에디터가 HTML 인식)
  try {{
    if (window.ClipboardItem && navigator.clipboard && navigator.clipboard.write) {{
      const item = new ClipboardItem({{
        'text/html': new Blob([html], {{type: 'text/html'}}),
        'text/plain': new Blob([text], {{type: 'text/plain'}})
      }});
      await navigator.clipboard.write([item]);
      ok = true;
    }}
  }} catch(e) {{ console.warn('ClipboardItem 실패:', e); }}

  // 2) Fallback — Selection + execCommand
  if (!ok) {{
    try {{
      const range = document.createRange();
      range.selectNodeContents(body);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      ok = document.execCommand('copy');
      sel.removeAllRanges();
    }} catch(e) {{ console.warn('execCommand 실패:', e); }}
  }}

  // 3) 최후 fallback — 일반 텍스트만
  if (!ok) {{
    try {{
      await navigator.clipboard.writeText(text);
      ok = true;
    }} catch(e) {{ console.error('clipboard.writeText 실패:', e); }}
  }}

  if (ok) {{
    document.getElementById('copyStatus').style.display = 'block';
    showToast('toastText');
    setTimeout(() => document.getElementById('copyStatus').style.display = 'none', 3000);
  }} else {{
    alert('복사 실패 — 본문을 마우스로 드래그하여 직접 복사해주세요');
  }}
}}

function loadImgToCanvas(canvasId, src) {{
  const canvas = document.getElementById(canvasId);
  const ctx = canvas.getContext('2d');
  const img = new Image();
  img.onload = function() {{
    canvas.width = img.width;
    canvas.height = img.height;
    ctx.drawImage(img, 0, 0);
  }};
  img.src = src;
}}

function copyImg(canvasId, toastId) {{
  const canvas = document.getElementById(canvasId);
  canvas.toBlob(blob => {{
    const item = new ClipboardItem({{'image/png': blob}});
    navigator.clipboard.write([item]).then(() => showToast(toastId));
  }});
}}

// 이미지 캔버스 로드
window.onload = function() {{{img_loaders}
}};
</script>
</body>
</html>
"""


def main():
    if len(sys.argv) < 2:
        today = datetime.now().strftime("%Y-%m-%d")
        date_str = today
        print(f"날짜 미입력, 오늘({date_str}) 기준으로 실행합니다.")
    else:
        date_str = sys.argv[1]

    print(f"📅 날짜: {date_str}")

    # md 파일 찾기
    md_file = find_md_file(date_str)
    print(f"📄 블로그 파일: {md_file.name}")
    md_text = md_file.read_text(encoding="utf-8")

    # 제목 추출
    title = extract_title(md_text)
    print(f"📝 제목: {title}")

    # 본문 HTML 변환 (부록 영상정보 + 태그 섹션 제거 + 이미지 삽입 마커 추가)
    body_md = strip_appendix_sections(md_text)
    body_md = inject_image_markers(body_md)
    body_html = md_to_html_body(body_md)

    # 인사이트 추출 → 본문 맨 아래에 텍스트 한 줄 추가
    insight_text = extract_insight(md_text)
    if insight_text:
        body_html += (
            '\n<hr style="margin:32px 0 16px;">'
            '\n<p style="font-size:14px;color:#64748b;font-style:italic;line-height:1.8;">'
            f'💡 {insight_text}'
            '</p>'
        )
        print(f"💡 인사이트: {insight_text[:60]}...")

    # PNG 파일 찾기
    png_files = find_png_files(date_str)
    print(f"🖼️  이미지: {len(png_files)}개")
    for p in png_files:
        print(f"   {p.name}")

    # 태그 추출
    tags = extract_tags(md_text)
    print(f"🏷️  태그: {len(tags)}개")

    # HTML 생성
    html = generate_html(date_str, title, body_html, png_files, tags)

    # 저장 (output/ 폴더)
    out_dir = BASE / "output"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{date_str}_copy_tool.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"\n✅ 저장 완료: output/{out_path.name}")
    print(f"   파일 크기: {out_path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
