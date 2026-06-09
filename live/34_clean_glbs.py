"""Reexporta os 5 GLBs vazados, limpos (isola personagem). Sobrescreve."""
import bpy, sys, json, pygltflib
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, game_builder; importlib.reload(game_builder)
RIG=r"D:/Alice/tools/auto-rig-fix/work/rigged"
for name in ("cheshire","rainha","chapeleiro","coelho","lagarta"):
    p=f"{RIG}/{name}_rigged.glb"
    r=json.loads(game_builder.clean_reexport(p, name, p))
    # confere nodes apos
    try:
        g=pygltflib.GLTF2().load(p); nodes=len(g.nodes); meshes=len(g.meshes)
    except Exception as e:
        nodes=meshes=f"?{e}"
    print(f"{name}: {r.get('size_MB','?')}MB nodes={nodes} meshes={meshes}")
print("OK clean_glbs")
