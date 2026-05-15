#!/bin/bash
# 텔레그램 봇의 DM chat_id를 한 번에 가져와 .telegram_config에 저장
# 사용 전: 봇에게 아무 메시지(예: /start)를 한 번 보내야 함

cd "$(dirname "$0")"
CONFIG=".telegram_config"

if [ ! -f "$CONFIG" ]; then
  echo "❌ $CONFIG 파일이 없습니다."
  echo "엔터로 창 닫기..."
  read
  exit 1
fi

TOKEN=$(grep '^BOT_TOKEN=' "$CONFIG" | cut -d= -f2-)
if [ -z "$TOKEN" ]; then
  echo "❌ BOT_TOKEN이 비어있습니다."
  echo "엔터로 창 닫기..."
  read
  exit 1
fi

echo "▶ Telegram getUpdates 호출 중..."
RESPONSE=$(curl -s "https://api.telegram.org/bot${TOKEN}/getUpdates")
echo "$RESPONSE" > .last_telegram_response.json

CONFIG_PATH="$CONFIG" python3 <<'PYEOF'
import os, json, sys

path = '.last_telegram_response.json'
with open(path, encoding='utf-8') as f:
    data = json.load(f)

if not data.get('ok'):
    print('❌ API 오류:', data)
    sys.exit(1)

results = data.get('result', [])
if not results:
    print('❌ 업데이트가 비어있습니다.')
    print('→ 텔레그램에서 봇을 검색해 /start 또는 아무 메시지를 보낸 뒤 다시 실행하세요.')
    sys.exit(2)

chat_id = None
who = None
for upd in reversed(results):
    msg = upd.get('message') or upd.get('edited_message') or {}
    chat = msg.get('chat') or {}
    if chat.get('type') == 'private':
        chat_id = chat.get('id')
        who = chat.get('username') or chat.get('first_name', '')
        break

if chat_id is None:
    print('❌ private 채팅을 찾지 못했습니다. 봇에게 직접 DM을 보냈는지 확인하세요.')
    sys.exit(3)

print(f'✅ chat_id={chat_id} (사용자: {who})')

cfg_path = os.environ['CONFIG_PATH']
with open(cfg_path, encoding='utf-8') as f:
    lines = f.read().splitlines()
new_lines, replaced = [], False
for ln in lines:
    if ln.startswith('CHAT_ID='):
        new_lines.append(f'CHAT_ID={chat_id}')
        replaced = True
    else:
        new_lines.append(ln)
if not replaced:
    new_lines.append(f'CHAT_ID={chat_id}')
with open(cfg_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines) + '\n')
print(f'💾 {cfg_path} 업데이트 완료')
PYEOF

EXIT=$?
rm -f .last_telegram_response.json

if [ $EXIT -ne 0 ]; then
  echo ""
  echo "위 오류 메시지 확인 후 엔터로 창 닫기..."
  read
  exit $EXIT
fi

echo ""
echo "✅ 다음: test_notify.command 실행해서 알림 정상 도착 확인"
echo "엔터로 창 닫기..."
read
