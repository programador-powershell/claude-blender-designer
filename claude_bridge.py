"""Claude Live Bridge ROBUSTO — eu (Claude) opero o Blender GUI ao vivo.

Roda DENTRO do Blender GUI (Text Editor > Run). Re-rodar = RESTART LIMPO.
Timer A PROVA DE MORTE (nunca desregistra por erro). Pega 1a porta livre do range.

Protocolo (newline JSON): envio {"code":"...","shot":bool} -> recebo {"ok","out","shot"}.

ROBUSTEZ:
- start() para instancia antiga antes (clean restart no re-run).
- _timer captura TUDO e sempre re-agenda (op longo/erro nao mata o processamento).
- range de portas: 9877..9881, pega a 1a livre (recupera de bridge morto).
- guarda a porta em work/.bridge_port pro cliente achar.
"""
import bpy, socket, threading, queue, traceback, io, os, base64, json, time
from contextlib import redirect_stdout

PORTS = (9877, 9878, 9879, 9880, 9881)
PORTFILE = r"D:/Alice/tools/auto-rig-fix/work/.bridge_port"

# estado GLOBAL no bpy (sobrevive ao re-exec do Text Editor -> permite stop do antigo)
_S = getattr(bpy, "_claude_bridge_state", None)
if _S is None:
    _S = {"sock": None, "thread": None, "run": False, "port": None, "timer_on": False}
    bpy._claude_bridge_state = _S

_req_q = queue.Queue()
_resp = {}


def _snapshot():
    path = os.path.join(bpy.app.tempdir, "_claude_shot.png")
    try:
        bpy.context.scene.render.filepath = path
        bpy.context.scene.render.image_settings.file_format = "PNG"
        bpy.ops.render.opengl(write_still=True)
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        return f"SHOT_ERR:{e}"


def _process(payload):
    code = payload.get("code", "")
    want_shot = payload.get("shot", False)
    out = io.StringIO(); ok = True
    try:
        with redirect_stdout(out):
            exec(code, {"bpy": bpy, "__name__": "__claude__"})
    except BaseException:
        ok = False
        out.write("\n" + traceback.format_exc())
    resp = {"ok": ok, "out": out.getvalue()[-6000:]}
    if want_shot:
        try: resp["shot"] = _snapshot()
        except Exception as e: resp["shot"] = f"SHOT_ERR:{e}"
    return resp


def _timer():
    # A PROVA DE MORTE: qualquer erro e engolido; SEMPRE re-agenda.
    try:
        n = 0
        while not _req_q.empty() and n < 4:   # processa ate 4 por tick
            n += 1
            try:
                rid, payload = _req_q.get_nowait()
            except queue.Empty:
                break
            try:
                _resp[rid] = _process(payload)
            except BaseException:
                _resp[rid] = {"ok": False, "out": "fatal:\n" + traceback.format_exc()}
    except BaseException:
        pass
    return 0.1


def _client(conn):
    conn.settimeout(600)
    buf = b""
    try:
        while True:
            chunk = conn.recv(65536)
            if not chunk: break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if not line.strip(): continue
                try:
                    payload = json.loads(line.decode())
                except Exception as e:
                    conn.sendall((json.dumps({"ok": False, "out": f"json err {e}"}) + "\n").encode()); continue
                rid = id(payload) ^ int(time.time()*1000) & 0xffffff
                _req_q.put((rid, payload))
                t0 = time.time()
                while rid not in _resp and time.time() - t0 < 590:
                    time.sleep(0.03)
                r = _resp.pop(rid, {"ok": False, "out": "timeout main thread (op>590s)"})
                conn.sendall((json.dumps(r) + "\n").encode())
    except Exception:
        pass
    finally:
        try: conn.close()
        except Exception: pass


def _bind():
    for p in PORTS:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("localhost", p)); s.listen(5)
            return s, p
        except OSError:
            try: s.close()
            except Exception: pass
    return None, None


def _serve(s, p):
    print(f"[claude_bridge] escutando {p}")
    while _S["run"]:
        try:
            s.settimeout(1.0)
            conn, _ = s.accept()
            threading.Thread(target=_client, args=(conn,), daemon=True).start()
        except socket.timeout:
            continue
        except OSError:
            break
    print("[claude_bridge] serve parado")


def stop():
    _S["run"] = False
    if _S.get("sock"):
        try: _S["sock"].close()
        except Exception: pass
    _S["sock"] = None
    if bpy.app.timers.is_registered(_timer):
        try: bpy.app.timers.unregister(_timer)
        except Exception: pass
    _S["timer_on"] = False


def start():
    stop()                       # clean restart (re-run sempre recupera)
    time.sleep(0.3)
    s, p = _bind()
    if s is None:
        print("[claude_bridge] ERRO: nenhuma porta livre em", PORTS); return
    _S["sock"] = s; _S["port"] = p; _S["run"] = True
    _S["thread"] = threading.Thread(target=_serve, args=(s, p), daemon=True)
    _S["thread"].start()
    if not bpy.app.timers.is_registered(_timer):
        bpy.app.timers.register(_timer, persistent=True)
    _S["timer_on"] = True
    try:
        os.makedirs(os.path.dirname(PORTFILE), exist_ok=True)
        open(PORTFILE, "w").write(str(p))
    except Exception: pass
    print(f"[claude_bridge] ON porta {p}. Timer a prova de morte. Pronto.")


start()
