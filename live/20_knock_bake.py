"""Anima mesa puxada (kinematic) -> copo/xicara caem -> estilhacam. Bake + ve."""
import bpy, sys
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, game_builder; importlib.reload(game_builder)

sc=bpy.data.scenes.get("PhysicsLab"); bpy.context.window.scene=sc
chao=bpy.data.objects.get("Chao_Fisico")
if chao: chao.hide_set(False)
mesa=bpy.data.objects.get("AI_Mesa_Suporte")

# keyframe mesa: puxa rapido pro lado (frames 1->6), some de baixo dos objetos
sc.frame_start=1; sc.frame_end=60
bpy.context.view_layer.objects.active=mesa
mesa.animation_data_clear()
mesa.location=(0,0,0.9); mesa.keyframe_insert("location", frame=1)
mesa.location=(2.5,0,0.9); mesa.keyframe_insert("location", frame=7)
mesa.location=(2.5,0,0.9); mesa.keyframe_insert("location", frame=60)

# rigidbody cache range
w=bpy.context.scene.rigidbody_world
if w and w.point_cache: w.point_cache.frame_start=1; w.point_cache.frame_end=60

# bake: avanca frame a frame (sim roda)
for f in range(1,61): sc.frame_set(f)

# mede shards do copo (z baixo + x espalhado = caiu e quebrou)
zs=[]; xs=[]
for o in sc.collection.objects:
    if "Copo" in o.name and "shard" in o.name:
        t=o.matrix_world.translation
        zs.append(t.z); xs.append(t.x)
if zs:
    print(f"copo shards n={len(zs)} z[{min(zs):.3f},{max(zs):.3f}] x_spread={max(xs)-min(xs):.3f}")

# enquadra
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        region=next((r for r in area.regions if r.type=='WINDOW'),None)
        with bpy.context.temp_override(area=area, region=region):
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.view3d.view_axis(type='FRONT')
            for _ in range(3): bpy.ops.view3d.view_orbit(type='ORBITRIGHT')
            for _ in range(1): bpy.ops.view3d.view_orbit(type='ORBITUP')
            bpy.ops.view3d.view_selected()
        break
print("OK knock_bake frame=",sc.frame_current)
