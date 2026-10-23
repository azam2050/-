"""الرندر على كرت شاشة سحابي (RunPod): يشغّل جهاز، يرفع ملفات المشروع، يرندر، ويرجّع النتائج.

يتفعّل بـ WATAD_GPU=1 (المفتاح في إعدادات البيئة لـ rest.runpod.io — البروكسي يضيفه).
الجهاز يبقى شغّال بين المهام (WATAD_GPU_POD يحفظ رقمه)، ويُطفأ بـ stop_pod() بعد ما نخلص.
"""
import base64
import io
import json
import os
import secrets
import tarfile
import time
import urllib.request
from pathlib import Path

API = "https://rest.runpod.io/v1"
STATE = Path(os.environ.get("WATAD_GPU_STATE", "/tmp/watad_gpu.json"))
GPUS = ["NVIDIA GeForce RTX 4090", "NVIDIA GeForce RTX 5090", "NVIDIA L40S", "NVIDIA RTX 6000 Ada Generation",
        "NVIDIA GeForce RTX 3090", "NVIDIA RTX A6000", "NVIDIA L40", "NVIDIA RTX A5000", "NVIDIA RTX 4000 Ada Generation"]
ROOT = Path(__file__).resolve().parent.parent


def _req(method, url, data=None, headers=None, timeout=120):
    h = {"Content-Type": "application/json", "Authorization": "Bearer proxy-injected", "User-Agent": "curl/8.5.0",
         **(headers or {})}
    body = data if isinstance(data, (bytes, type(None))) else json.dumps(data).encode()
    r = urllib.request.Request(url, data=body, method=method, headers=h)
    with urllib.request.urlopen(r, timeout=timeout) as f:
        raw = f.read()
    try:
        return json.loads(raw)
    except ValueError:
        return raw


def _state():
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def _save(s):
    STATE.write_text(json.dumps(s))


def pod():
    """يرجع (url, token) لجهاز جاهز — يشغّل جهاز جديد أو يكمّل الموجود."""
    s = _state()
    if s.get("id"):
        try:
            p = _req("GET", f"{API}/pods/{s['id']}")
            if p.get("desiredStatus") != "RUNNING":
                _req("POST", f"{API}/pods/{s['id']}/start", {})
        except Exception:  # noqa: BLE001
            s = {}
    if not s.get("id"):
        tok = secrets.token_hex(16)
        body = {"name": "watad-render", "imageName": "runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04",
                "gpuTypeIds": GPUS, "gpuTypePriority": "custom", "gpuCount": 1, "cloudType": "SECURE",
                "containerDiskInGb": 30, "volumeInGb": 30, "volumeMountPath": "/workspace", "ports": ["8000/http"],
                # كود الوكيل ينرسل داخل متغيرات الجهاز نفسه (ما ينشر برابط عام)، ومحمي برمز سري لكل جهاز
                "env": {"AGENT_TOKEN": tok,
                        "AGENT_B64": base64.b64encode((ROOT / "tools" / "gpu_agent.py").read_bytes()).decode()},
                "dockerStartCmd": ["bash", "-c", "python3 -c \"import os,base64;open('/agent.py','wb').write("
                                   "base64.b64decode(os.environ['AGENT_B64']))\" && python3 /agent.py"]}
        try:
            p = _req("POST", f"{API}/pods", body)
        except urllib.error.HTTPError as e:
            if e.code >= 400:          # ما فيه أجهزة متاحة في السحابة الآمنة → السحابة المجتمعية
                body["cloudType"] = "COMMUNITY"
                p = _req("POST", f"{API}/pods", body)
            else:
                raise
        s = {"id": p["id"], "token": tok, "assets": False}
        _save(s)
    url = f"https://{s['id']}-8000.proxy.runpod.net"
    for _ in range(180):            # لين يشتغل الوكيل ويتثبّت Blender
        try:
            h = _req("GET", url + "/health", timeout=20)
            if isinstance(h, dict) and h.get("ready"):
                break
        except Exception:  # noqa: BLE001
            pass
        time.sleep(10)
    else:
        raise RuntimeError("الجهاز ما جهز")
    return url, s


def _agent(url, s, method, path, data=None, timeout=300):
    return _req(method, url + path, data, {"X-Token": s["token"]}, timeout)


def _put_tar(url, s, files, dest):
    """يضغط ملفات/مجلدات (مسار محلي → اسم داخل dest) ويرفعها بقطع 40 م.ب ثم يفكها هناك."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as t:
        for local, arc in files:
            t.add(str(local), arcname=arc)
    data = buf.getvalue()
    remote = f"/workspace/up_{secrets.token_hex(4)}.tar"
    step = 40 * 1024 * 1024
    for i in range(0, len(data), step):
        _agent(url, s, "PUT", f"/file?path={remote}" + ("&append=1" if i else ""), data[i:i + step], timeout=900)
    _agent(url, s, "POST", "/untar", {"path": remote, "dest": dest, "remove": True}, timeout=900)


def ensure_assets(url, s, tex_dir, models_dir):
    if s.get("assets"):
        return
    _put_tar(url, s, [(tex_dir, "tex")], "/workspace/assets")
    _put_tar(url, s, [(models_dir, "models")], "/workspace/assets")
    s["assets"] = True
    _save(s)


def run(cfg, out):
    """نفس realistic._run بس على الكرت: يرفع scene.glb + السكربتات، يرندر، ويرجّع كل المخرجات لمجلد out."""
    url, s = pod()
    ensure_assets(url, s, cfg["tex_dir"], cfg.get("models_dir", cfg["tex_dir"]))
    jid = secrets.token_hex(5)
    jd = f"/workspace/jobs/{jid}"
    tools = ROOT / "tools"
    files = [(cfg["glb"], "scene.glb")] + [(p, f"tools/{p.name}") for p in tools.glob("*.py")]
    c = dict(cfg)
    c.update({"glb": f"{jd}/scene.glb", "out_dir": f"{jd}/out", "tex_dir": "/workspace/assets/tex",
              "models_dir": "/workspace/assets/models", "furnish_py": f"{jd}/tools/blender_furnish.py", "gpu": True})
    if c.get("bake"):
        c["bake"] = {**c["bake"], "script": f"{jd}/tools/bake_web.py", "out_dir": f"{jd}/out"}
    cj = Path(out) / f"cfg-gpu-{jid}.json"
    cj.write_text(json.dumps(c, ensure_ascii=False))
    files.append((cj, "cfg.json"))
    _put_tar(url, s, files, jd)
    j = _agent(url, s, "POST", "/run", {"cmd": ["BLENDER", "-b", "-P", f"{jd}/tools/render_blender.py", "--",
                                                 f"{jd}/cfg.json"], "cwd": jd})
    while True:
        time.sleep(8)
        st = _agent(url, s, "GET", f"/job?id={j['id']}")
        if st.get("done"):
            break
    (Path(out) / f"gpu-{jid}.log").write_text(st.get("tail", ""))
    # نرجّع المخرجات مضغوطة
    t = _agent(url, s, "POST", "/run", {"cmd": ["tar", "cf", f"{jd}/out.tar", "-C", f"{jd}/out", "."], "cwd": jd})
    while not _agent(url, s, "GET", f"/job?id={t['id']}").get("done"):
        time.sleep(2)
    raw = _agent(url, s, "GET", f"/file?path={jd}/out.tar", timeout=900)
    with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
        tf.extractall(out)
    _agent(url, s, "POST", "/rm", {"path": jd})
    if st.get("rc"):
        raise RuntimeError(f"GPU render failed rc={st.get('rc')}: {st.get('tail', '')[-800:]}")


def stop_pod(terminate=False):
    s = _state()
    if not s.get("id"):
        return
    if terminate:
        _req("DELETE", f"{API}/pods/{s['id']}")
        STATE.unlink(missing_ok=True)
    else:
        _req("POST", f"{API}/pods/{s['id']}/stop", {})
