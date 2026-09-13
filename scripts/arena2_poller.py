#!/usr/bin/env python3
"""
AgentScout Arena 2 Autonomous Room Poller and Responder Daemon"""

import sys, os, time, json, urllib.request, urllib.error, uuid
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agentscout_arena_watcher import ArenaRoomWatcher

ROOM_ID = os.environ.get('SHAREDNET_ROOM_ID', 'rom_aNufp2Jck4')
MEMBER_TOKEN = os.environ.get('SHAREDNET_MEMBER_TOKEN', 'sni_89vlAo-BSpbX9TcWtd5CrCkRVRbZfL09KgSVuM5OhJc')
MY_MEMBER_ID = os.environ.get('SHAREDNET_MEMBER_ID', 'i_ZD6urR7YGA')
BASE_URL = os.environ.get('SHAREDNET_BASE_URL', 'https://www.sharednet.ai')

def post_message(text):
    url = f"{BASE_URL}/api/v1/rooms/{ROOM_ID}/messages"
    data = json.dumps({'content': text}).encode('utf-8')
    headers = {
        'Authorization': f'Bearer {MEMBER_TOKEN}',
        'Content-Type': 'application/json',
        'Idempotency-Key': str(uuid.uuid4())
    }
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode())
            print(f"[+] Posted reply (msg_id: {res.get('message', {}).get('id')})", flush=True)
            return True
    except Exception as e:
        print(f"[-] Error posting message: {e}", flush=True)
        return False

def run_loop():
    print(f"[*] Starting AgentScout Arena Poller for Room: {ROOM_ID} (Member: {MY_MEMBER_ID})...")
    watcher = ArenaRoomWatcher(node_id="agentscout.sharedos.net")
    last_seq = 712
    while True:
        try:
            url = f"{BASE_URL}/api/v1/rooms/{ROOM_ID}/wait?after={last_seq}"
            headers = {"Authorization": f"Bearer {MEMBER_TOKEN}"}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                messages = data.get('messages', [])
                for msg in messages:
                    seq = msg.get('sequence', 0)
                    if seq > last_seq:
                        last_seq = seq
                    sender = msg.get('sender', {})
                    sender_id = sender.get('member_id') or msg.get('sender_instance_id') or 'unknown'
                    sender_name = sender.get('name') or sender_id
                    if sender_id == MY_MEMBER_ID:
                        continue
                    content = msg.get('content', '').strip()
                    if not content:
                        continue
                    print(f'[*] [{seq}] Received from {sender_name} ({sender_id}): {content[:100]}...')
                    reply = watcher.handle_message(content, sender_id, sender_name)
                    if reply:
                        print(f'[+] Generated reply for {sender_name}. Posting...')
                        post_message(reply)
        except urllib.error.HTTPError as e:
            if e.code not in (408, 504):
                print(f'_!] HTTP Error {e.code}: {e}')
            time.sleep(2)
        except Exception as e:
            time.sleep(2)

if __name__ == '__main__':
    run_loop()
