"""بوت تلقرام لمصنع وتد: يستقبل طلب المخطط (نص/صور/فويس/ملفات) ويمرّره لـ Claude Code داخل المستودع،
ويرجّع المخططات (PDF/DXF/صور) لنفس المحادثة.

التشغيل (على جهاز شغّال دايماً فيه المستودع و Claude Code مسجّل الدخول):
    export TELEGRAM_BOT_TOKEN=...            # من @BotFather — لا يُكتب في أي ملف بالمستودع
    export TELEGRAM_ALLOWED_IDS=123456789     # أرقام محادثات صاحب المصنع فقط (مفصولة بفاصلة)
    python tools/telegram_bot.py

- بدون TELEGRAM_ALLOWED_IDS البوت يرد برقم المحادثة بس (عشان تعرفه) وما ينفّذ شي.
- الملفات الواردة تنحفظ خارج المستودع في ~/.watad-telegram/inbox (خصوصية العملاء).
- كل محادثة لها جلسة Claude مستمرة (يتذكر الطلب السابق). /new يبدأ جلسة جديدة.
"""
import json
import os
import pathlib
import subprocess
import threading
import time

import requests

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED = {s.strip() for s in os.environ.get("TELEGRAM_ALLOWED_IDS", "").split(",") if s.strip()}
REPO = pathlib.Path(__file__).resolve().parents[1]
HOME = pathlib.Path(os.environ.get("WATAD_TG_HOME", pathlib.Path.home() / ".watad-telegram"))
INBOX = HOME / "inbox"
STATE = HOME / "sessions.json"
API = f"https://api.telegram.org/bot{TOKEN}"
FILE_API = f"https://api.telegram.org/file/bot{TOKEN}"
CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
TOOLS = "Bash Read Write Edit Glob Grep"

SYSTEM = (
    "الطلب جاي من صاحب المصنع عبر تلقرام. اتبع CLAUDE.md بالكامل (الأوتوكاد أول ومراجعة المصمم، "
    "الصور بعد الموافقة فقط، الخصوصية، commit و push). ردّك يوصله كرسالة تلقرام: خلّه قصير وبالعربي. "
    "كل ملف تبي ترسله له (PDF/DXF/صورة) اكتبه في سطر لوحده بالشكل: SEND: <المسار الكامل>"
)

lock = threading.Lock()
busy = set()
albums = {}   # media_group_id → رسائل الألبوم (الصور المتعددة توصل كرسائل منفصلة)


def tg(method, **kw):
    r = requests.post(f"{API}/{method}", timeout=70, **kw)
    r.raise_for_status()
    return r.json()["result"]


def say(chat, text):
    text = text.strip() or "تم."
    for i in range(0, len(text), 4000):
        tg("sendMessage", data={"chat_id": chat, "text": text[i:i + 4000]})


def send_file(chat, path):
    p = pathlib.Path(path)
    if not p.is_absolute():
        p = REPO / p
    if not p.is_file():
        say(chat, f"ما لقيت الملف: {p.name}")
        return
    photo = p.suffix.lower() in (".png", ".jpg", ".jpeg") and p.stat().st_size < 10e6
    with open(p, "rb") as f:
        tg("sendPhoto" if photo else "sendDocument", data={"chat_id": chat},
           files={"photo" if photo else "document": (p.name, f)})


def load_state():
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {}


def save_state(st):
    STATE.write_text(json.dumps(st))


def download(msg):
    """ينزّل المرفقات (صور/فويس/فيديو/ملفات) ويرجّع مساراتها."""
    items = []
    if msg.get("photo"):
        items.append((msg["photo"][-1]["file_id"], ".jpg"))
    for k, ext in (("voice", ".ogg"), ("audio", ".mp3"), ("video", ".mp4"), ("video_note", ".mp4")):
        if msg.get(k):
            items.append((msg[k]["file_id"], ext))
    if msg.get("document"):
        d = msg["document"]
        items.append((d["file_id"], pathlib.Path(d.get("file_name", "file")).suffix or ".bin"))
    out = []
    day = INBOX / time.strftime("%Y-%m-%d")
    day.mkdir(parents=True, exist_ok=True)
    for fid, ext in items:
        info = tg("getFile", data={"file_id": fid})
        dst = day / f"{msg['message_id']}_{len(out)}{ext}"
        dst.write_bytes(requests.get(f"{FILE_API}/{info['file_path']}", timeout=300).content)
        out.append(str(dst))
    return out


def run_claude(chat, text, files):
    st = load_state()
    prompt = text or "(بدون نص — شوف المرفقات)"
    if files:
        prompt += "\n\nالمرفقات (اقرأها/شوفها؛ الفويس والفيديو فرّغها بـ faster_whisper عربي):\n" + "\n".join(files)
    cmd = [CLAUDE, "-p", prompt, "--output-format", "json", "--append-system-prompt", SYSTEM,
           "--allowedTools", TOOLS, "--permission-mode", "acceptEdits", "--add-dir", str(HOME)]
    if st.get(str(chat)):
        cmd += ["--resume", st[str(chat)]]
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=4 * 3600)
    try:
        res = json.loads(r.stdout)
    except ValueError:
        return f"صار خطأ بالتشغيل:\n{(r.stderr or r.stdout)[-1500:]}", []
    if res.get("session_id"):
        with lock:
            st = load_state()
            st[str(chat)] = res["session_id"]
            save_state(st)
    lines, sends = [], []
    for ln in (res.get("result") or "").splitlines():
        (sends.append(ln.split(":", 1)[1].strip()) if ln.strip().startswith("SEND:") else lines.append(ln))
    return "\n".join(lines), sends


def handle(msgs):
    msg = msgs[0]
    chat = msg["chat"]["id"]
    text = "\n".join((m.get("text") or m.get("caption") or "").strip() for m in msgs).strip()
    if str(chat) not in ALLOWED:
        say(chat, f"هذا البوت خاص بمصنع وتد. رقم محادثتك: {chat}")
        return
    if text == "/new":
        with lock:
            st = load_state()
            st.pop(str(chat), None)
            save_state(st)
        say(chat, "بدأت جلسة جديدة.")
        return
    if chat in busy:
        say(chat, "لسا أشتغل على الطلب السابق — أرسل بعد ما أخلص.")
        return
    busy.add(chat)
    try:
        files = [f for m in msgs for f in download(m)]
        say(chat, "وصل الطلب ✅ جاري العمل…")
        reply, sends = run_claude(chat, text, files)
        say(chat, reply)
        for p in sends:
            send_file(chat, p)
    except Exception as e:  # noqa: BLE001 — أي خطأ يوصل لصاحب المصنع بدل ما يطيح البوت
        say(chat, f"صار خطأ: {e}")
    finally:
        busy.discard(chat)


def main():
    if not TOKEN:
        raise SystemExit("عيّن TELEGRAM_BOT_TOKEN أول (من @BotFather).")
    INBOX.mkdir(parents=True, exist_ok=True)
    off = 0
    print("بوت وتد شغّال…")
    while True:
        try:
            ups = tg("getUpdates", data={"offset": off, "timeout": 50})
        except requests.RequestException:
            time.sleep(5)
            continue
        for u in ups:
            off = u["update_id"] + 1
            m = u.get("message")
            if not m:
                continue
            gid = m.get("media_group_id")
            if not gid:
                threading.Thread(target=handle, args=([m],), daemon=True).start()
            elif gid not in albums:
                albums[gid] = [m]
                threading.Timer(3.0, lambda g=gid: handle(albums.pop(g))).start()
            else:
                albums[gid].append(m)


if __name__ == "__main__":
    main()
