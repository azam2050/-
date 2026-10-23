"""وكيل الرندر على جهاز RunPod (كرت شاشة): يثبّت Blender ويستقبل ملفات المشروع ويشغّل الرندر ويرجّع النتائج.
يشتغل تلقائياً عند تشغيل الجهاز (dockerStartCmd)؛ كل طلب لازم يحمل X-Token = AGENT_TOKEN.
"""
import json
import os
import shutil
import subprocess
import tarfile
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

TOKEN = os.environ.get("AGENT_TOKEN", "")
ROOT = "/workspace"
BL_DIR = f"{ROOT}/blender"
BL_URL = "https://download.blender.org/release/Blender4.2/blender-4.2.3-linux-x64.tar.xz"
STATE = {"ready": False, "log": []}
JOBS = {}


def _log(m):
    STATE["log"] = (STATE["log"] + [m])[-40:]
    print(m, flush=True)


def setup():
    try:
        subprocess.run("apt-get update -qq && apt-get install -y -qq libxrender1 libxi6 libxkbcommon0 libsm6 libgl1 "
                       "libxxf86vm1 libxfixes3 libegl1 xz-utils curl > /dev/null 2>&1", shell=True)
        exe = f"{BL_DIR}/blender-4.2.3-linux-x64/blender"
        if not os.path.exists(exe):
            os.makedirs(BL_DIR, exist_ok=True)
            _log("downloading blender")
            subprocess.run(f"curl -sL {BL_URL} | tar -xJ -C {BL_DIR}", shell=True, check=True)
        r = subprocess.run([exe, "-b", "--python-expr", "import bpy;print('BLENDER_OK')"], capture_output=True, text=True)
        STATE["ready"] = "BLENDER_OK" in r.stdout
        STATE["blender"] = exe
        _log("blender ready" if STATE["ready"] else "blender failed: " + r.stderr[-500:])
    except Exception as e:  # noqa: BLE001
        _log(f"setup error {e}")


def run_job(jid, cmd, cwd):
    lf = f"{ROOT}/jobs/{jid}.log"
    os.makedirs(os.path.dirname(lf), exist_ok=True)
    with open(lf, "w") as f:
        p = subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT)
    JOBS[jid]["rc"] = p.returncode
    JOBS[jid]["done"] = True


class H(BaseHTTPRequestHandler):
    def _ok(self, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _auth(self):
        if not TOKEN or self.headers.get("X-Token") != TOKEN:
            self.send_response(403)
            self.end_headers()
            return False
        return True

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path == "/health":
            return self._ok({"ready": STATE["ready"], "log": STATE["log"][-5:]})
        if not self._auth():
            return
        if u.path == "/job":
            j = JOBS.get(q["id"], {})
            tail = ""
            lf = f"{ROOT}/jobs/{q['id']}.log"
            if os.path.exists(lf):
                with open(lf, errors="replace") as f:
                    tail = f.read()[-3000:]
            return self._ok({**j, "tail": tail})
        if u.path == "/file":
            with open(q["path"], "rb") as f:
                return self._ok(f.read(), "application/octet-stream")
        if u.path == "/ls":
            out = []
            for dp, _, fs in os.walk(q["path"]):
                out += [os.path.join(dp, x) for x in fs]
            return self._ok(out)
        self.send_response(404)
        self.end_headers()

    def do_PUT(self):
        if not self._auth():
            return
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        n = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(n)
        os.makedirs(os.path.dirname(q["path"]), exist_ok=True)
        with open(q["path"], "ab" if q.get("append") else "wb") as f:
            f.write(data)
        self._ok({"ok": True, "size": os.path.getsize(q["path"])})

    def do_POST(self):
        if not self._auth():
            return
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        if u.path == "/untar":
            os.makedirs(body["dest"], exist_ok=True)
            with tarfile.open(body["path"]) as t:
                t.extractall(body["dest"])
            if body.get("remove"):
                os.remove(body["path"])
            return self._ok({"ok": True})
        if u.path == "/run":
            jid = uuid.uuid4().hex[:10]
            if not body.get("cmd") or body["cmd"][0] not in ("BLENDER", "tar"):   # بس Blender والضغط
                self.send_response(400)
                self.end_headers()
                return
            cmd = [STATE.get("blender") if c == "BLENDER" else c for c in body["cmd"]]
            JOBS[jid] = {"done": False, "rc": None}
            threading.Thread(target=run_job, args=(jid, cmd, body.get("cwd", ROOT)), daemon=True).start()
            return self._ok({"id": jid})
        if u.path == "/rm":
            shutil.rmtree(body["path"], ignore_errors=True)
            return self._ok({"ok": True})
        self.send_response(404)
        self.end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    os.makedirs(ROOT, exist_ok=True)
    threading.Thread(target=setup, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", 8000), H).serve_forever()
