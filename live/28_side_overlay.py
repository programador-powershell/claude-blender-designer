"""Side view (RIGHT) do esqueleto+mesh -> ve alinhamento em Y (profundidade).
Tambem mede bbox Y do esqueleto vs mesh."""
import bpy
name="cheshire"
try: name=open(r"D:/Alice/tools/auto-rig-fix/work/outfit.txt").read().strip().split("|")[0]
except Exception: pass
mesh=bpy.data.objects.get(name); arm=bpy.data.objects.get(f"Rig_{name}")
# bbox Y
mco=[mesh.matrix_world@v.co for v in mesh.data.vertices]
mys=[c.y for c in mco]; mzs=[c.z for c in mco]
pts=[]
for b in arm.data.bones:
    pts.append(arm.matrix_world@b.head_local); pts.append(arm.matrix_world@b.tail_local)
sys_=[p.y for p in pts]; szs=[p.z for p in pts]
print(f"mesh  Y[{min(mys):.3f},{max(mys):.3f}] Z[{min(mzs):.3f},{max(mzs):.3f}]")
print(f"skel  Y[{min(sys_):.3f},{max(sys_):.3f}] Z[{min(szs):.3f},{max(szs):.3f}]")
arm.hide_set(False); arm.show_in_front=True; arm.data.display_type='STICK'
bpy.context.view_layer.objects.active=mesh
if bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        region=next((r for r in area.regions if r.type=='WINDOW'),None)
        with bpy.context.temp_override(area=area,region=region):
            bpy.ops.object.select_all(action='DESELECT'); mesh.select_set(True)
            bpy.ops.view3d.view_axis(type='RIGHT'); bpy.ops.view3d.view_selected()
        break
print("OK side")
