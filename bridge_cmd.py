"""Cliente do claude_bridge — EU (Claude) uso via Bash pra operar o Blender vivo.

Uso:
  python bridge_cmd.py "<codigo python blender>"          # executa, mostra out
  python bridge_cmd.py --shot "<codigo>"                   # executa + salva shot.png
  python bridge_cmd.py --shot-only                         # so screenshot do viewport
  python bridge_cmd.py --file <script.py> [--shot]         # roda arquivo

Salva screenshot em D:/Alice/tools/auto-rig-fix/work/live_shot.png pra eu ler.
"""
import sys, socket, json, base64, os

PORTS = (9877, 9878, 9879, 9880, 9881)   # range do bridge robusto
SHOT = r"D:/Alice/tools/auto-rig-fix/work/live_shot.png"
PORTCACHE = r"D:/Alice/tools/auto-rig-fix/work/.bridge_port"

def _recv_line(s):
    buf = b""
    while b"\n" not in buf:
        c = s.recv(65536)
        if not c: break
        buf += c
    return buf

def _probe(port, t=2.5):
    """Probe rapido: bridge meu responde <2.5s; addon 9876 trava -> False."""
    try:
        s = socket.socket(); s.settimeout(t); s.connect(("localhost", port))
        s.sendall((json.dumps({"code": "print('pong')"}) + "\n").encode())
        buf = _recv_line(s); s.close()
        return b"pong" in buf or b'"ok"' in buf
    except Exception:
        return False

def _live_port():
    """Descobre porta viva: cache -> probe. Cacheia a que responde."""
    cached = None
    try:
        cached = int(open(PORTCACHE).read().strip())
    except Exception:
        pass
    order = ([cached] if cached else []) + [p for p in PORTS if p != cached]
    for p in order:
        if _probe(p):
            try:
                os.makedirs(os.path.dirname(PORTCACHE), exist_ok=True)
                open(PORTCACHE, "w").write(str(p))
            except Exception: pass
            return p
    return None

def send(payload):
    p = _live_port()
    if p is None:
        raise SystemExit(f"[bridge_cmd] sem bridge vivo. Rode claude_bridge.py no Blender (Text Editor > Run).")
    s = socket.socket(); s.settimeout(300); s.connect(("localhost", p))
    s.sendall((json.dumps(payload) + "\n").encode())
    buf = _recv_line(s); s.close()
    if not buf.strip():
        raise SystemExit(f"[bridge_cmd] porta {p} respondeu vazio.")
    return json.loads(buf.split(b"\n")[0].decode())

GEO_PRELUDE = (
    "import sys\n"
    "sys.path.insert(0, r'D:\\Alice\\tools\\auto-rig-fix\\live')\n"
    "import importlib, live_geo; importlib.reload(live_geo)\n"
)

def main():
    args = sys.argv[1:]
    want_shot = "--shot" in args or "--shot-only" in args
    args = [a for a in args if a not in ("--shot","--shot-only")]
    if "--geo" in args:
        # --geo <func> '<json kwargs>'  -> chama live_geo.<func>(**kwargs), data only
        i = args.index("--geo"); func = args[i+1]
        kw = args[i+2] if len(args) > i+2 else "{}"
        code = GEO_PRELUDE + f"print(live_geo.{func}(**({kw})))"
    elif "--gb" in args:
        # --gb <func> '<json kwargs>' -> chama game_builder.<func>(**kwargs)
        i = args.index("--gb"); func = args[i+1]
        kw = args[i+2] if len(args) > i+2 else "{}"
        code = ("import sys\nsys.path.insert(0, r'D:\\Alice\\tools\\auto-rig-fix\\live')\n"
                "import importlib, game_builder; importlib.reload(game_builder)\n"
                f"print(game_builder.{func}(**({kw})))")
    elif "--shot-only" in sys.argv:
        code = "pass"
    elif "--file" in args:
        i = args.index("--file"); code = open(args[i+1], encoding="utf-8").read()
    else:
        code = args[0] if args else "pass"
    r = send({"code": code, "shot": want_shot})
    print("OK" if r.get("ok") else "FAIL")
    if r.get("out"): print(r["out"])
    if r.get("shot") and not r["shot"].startswith("SHOT_ERR"):
        os.makedirs(os.path.dirname(SHOT), exist_ok=True)
        with open(SHOT, "wb") as f:
            f.write(base64.b64decode(r["shot"]))
        print(f"[shot] {SHOT}")
    elif r.get("shot"):
        print(r["shot"])

if __name__ == "__main__":
    main()
