# -*- coding: utf-8 -*-
"""Wrapper CLI pipeline_layered_v21 - executa V2.1 builder via Blender bridge.

REQUIREMENTS:
  - source mesh: AI-generated whole-outfit GLB (ex via Trellis2/Hunyuan).
    O mesh DEVE ter UV layer com layout consistente onde mascaras serao aplicadas.
  - template: GLB/FBX com Alice body + Mixamo armature
  - manifest: JSON listando 10 layers (chapeleiro example incluido)
  - masks_dir: pasta com 10 PNGs UV-space (uma por layer)

Uso:
  python pipeline_layered_v21.py --source path.glb --template alice_rigged.fbx \\
      --manifest manifests/alice_chapeleiro_layer_manifest.json \\
      --masks-dir masks_uv/ --export export.glb --clear-scene
"""
import os, sys, argparse, subprocess, tempfile, json

ROOT = r"D:/Alice/tools/auto-rig-fix"
LIVE = os.path.join(ROOT, "live")
BRIDGE = os.path.join(ROOT, "bridge_cmd.py")


def run_bridge(source, template, manifest, masks_dir, export, clear_scene, name):
    script = f"""
import sys, importlib
sys.path.insert(0, r'{LIVE}')
import project_alice_layered_builder as builder
importlib.reload(builder)
result = builder.execute_layered_pipeline(
    source_path=r'{source}',
    template_path=r'{template}',
    manifest_path=r'{manifest}',
    masks_dir=r'{masks_dir}',
    export_path=r'{export}' if r'{export}' else None,
    clear_scene={clear_scene!r},
    character_name=r'{name}',
)
print(result)
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script); p = f.name
    try:
        env = os.environ.copy(); env['PYTHONIOENCODING'] = 'utf-8'
        r = subprocess.run([sys.executable, BRIDGE, '--file', p],
                            capture_output=True, text=True, timeout=900, env=env)
        sys.stdout.write(r.stdout)
        if r.returncode: sys.stderr.write(r.stderr); return False
        return True
    finally:
        try: os.unlink(p)
        except: pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', required=True, help='AI fused outfit mesh (.glb/.fbx/.obj)')
    ap.add_argument('--template', required=True, help='Alice body + rig (.glb/.fbx)')
    ap.add_argument('--manifest', default=os.path.join(ROOT, 'manifests', 'alice_chapeleiro_layer_manifest.json'))
    ap.add_argument('--masks-dir', required=True, help='Dir com mascaras UV-space PNG')
    ap.add_argument('--export', default='', help='Output GLB path (vazio = skip)')
    ap.add_argument('--clear-scene', action='store_true')
    ap.add_argument('--name', default='Alice_Final')
    a = ap.parse_args()

    # Pre-check inputs
    missing = []
    for p in [a.source, a.template, a.manifest]:
        if not os.path.exists(p): missing.append(p)
    if not os.path.isdir(a.masks_dir): missing.append(a.masks_dir)
    if missing:
        print("FALTA:")
        for m in missing: print(f"  - {m}")
        sys.exit(1)

    ok = run_bridge(a.source, a.template, a.manifest, a.masks_dir,
                     a.export, a.clear_scene, a.name)
    sys.exit(0 if ok else 1)


if __name__ == '__main__': main()
