"""Live step 01 — limpa cena, importa corpo+vestido, mata scale 89x, enquadra."""
import bpy, mathutils

BODY  = r"D:\Alice\tools\body-rebuild\out\alice_body_clean.fbx"
DRESS = r"E:\References\3D\SK_AliceDress.fbx"

# --- limpa tudo (cube/light/camera default + qualquer coisa) ---
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for blk in (bpy.data.meshes, bpy.data.armatures):
    for d in list(blk):
        if d.users == 0:
            blk.remove(d)

def imp(path, tag):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    print(f"[{tag}] importou {len(new)}: {[o.name for o in new]}")
    return new

body = imp(BODY, "BODY")
dress = imp(DRESS, "DRESS")

# --- mata scale 89x do vestido: apply transform em TUDO que veio do dress ---
bpy.ops.object.select_all(action='DESELECT')
for o in dress:
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# --- stats: cada mesh, verts, bbox dims, world loc ---
def dims(o):
    if o.type != 'MESH': return None
    cs = [o.matrix_world @ v.co for v in o.data.vertices]
    if not cs: return None
    xs=[c.x for c in cs]; ys=[c.y for c in cs]; zs=[c.z for c in cs]
    return (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))

print("\n=== STATS ===")
for o in bpy.data.objects:
    if o.type == 'MESH':
        d = dims(o)
        print(f"  MESH {o.name}: verts={len(o.data.vertices)} dims={tuple(round(x,3) for x in d) if d else '?'} vgroups={len(o.vertex_groups)}")
    elif o.type == 'ARMATURE':
        print(f"  ARMATURE {o.name}: bones={len(o.data.bones)}")

# --- viewport solid + enquadra tudo ---
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        area.spaces[0].shading.type = 'SOLID'
        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
        with bpy.context.temp_override(area=area, region=region):
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.view3d.view_all()
        break
print("OK import done")
