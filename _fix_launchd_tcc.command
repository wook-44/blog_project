#!/bin/bash
# launchd TCC 권한 우회 — 비보호 폴더에 runner.sh 두고 open -a Terminal로 .command 호출
# 5/16~5/17 자동화 실패 원인: launchd가 ~/Documents/ 보호 폴더의 스크립트 직접 실행 차단

set -u
cd "$(dirname "$0")"
BLOG="$(pwd)"
RUNNER_DIR="$HOME/Library/Application Support/blog-runner"
RUNNER="$RUNNER_DIR/runner.sh"
PLIST="$HOME/Library/LaunchAgents/com.user.blog-daily.plist"

echo "🔧 [1/4] 비보호 폴더 + runner.sh 생성..."
mkdir -p "$RUNNER_DIR"
cat > "$RUNNER" <<'EOF'
#!/bin/bash
# blog-runner — launchd → Terminal GUI 세션으로 .command 트리거
# 보호 폴더(~/Documents) TCC 우회: 'open -a Terminal'은 사용자 GUI 컨텍스트에서 실행되어 권한 통과
TARGET="/Users/chanwook/Documents/Claude/Projects/블로그/run_daily_auto.command"
RUNNER_LOG="$HOME/Library/Application Support/blog-runner/launcher.log"
echo "$(date '+%Y-%m-%d %H:%M:%S') launchd 트리거 — open $TARGET" >> "$RUNNER_LOG"
/usr/bin/open -a Terminal "$TARGET"
EOF
chmod +x "$RUNNER"
ls -l "$RUNNER"
echo ""

echo "🔧 [2/4] plist 수정 — ProgramArguments를 runner.sh로..."
launchctl unload "$PLIST" 2>/dev/null || true

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.blog-daily</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${RUNNER}</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>17</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/chanwook/Library/Application Support/blog-runner/launchd_out.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/chanwook/Library/Application Support/blog-runner/launchd_err.log</string>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

echo "✅ plist:"
cat "$PLIST"
echo ""

echo "🔧 [3/4] launchctl 재등록..."
launchctl load "$PLIST"
sleep 1
launchctl list | grep blog-daily || echo "  ⚠️ 등록 확인 실패"
echo ""

echo "🔧 [4/4] runner.sh 즉시 테스트..."
echo "(Terminal 새 창이 뜨고 run_daily_auto.command가 실행됩니다)"
bash "$RUNNER"
sleep 3
echo ""
echo "── 테스트 결과 ──"
tail -5 "$RUNNER_DIR/launcher.log" 2>/dev/null

# 텔레그램 보고
python3 notify.py "🔧 <b>launchd TCC 우회 설치</b>
runner: ~/Library/Application Support/blog-runner/
plist: com.user.blog-daily (17:30 KST 매일)
Terminal GUI 컨텍스트로 .command 호출 → 보호 폴더 권한 통과
즉시 테스트 트리거됨"

echo ""
echo "(60초 후 자동 닫힘)"
read -t 60 || true
