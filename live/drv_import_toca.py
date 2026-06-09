import bpy, sys
from mathutils import Vector
sys.path.insert(0, r'D:\Alice\tools\auto-rig-fix\live')
import importlib, interior as I; importlib.reload(I)
I.purge()
fp=r'D:\Project Alice 2\Project Alice\Saved\Heightmaps\Terrains_Final\SM_Terrain_MAP03_TocaMecanica.fbx'
bpy.ops.import_scene.fbx(filepath=fp)
ms=[o for o in bpy.data.objects if o.type=='MESH']
mn=Vector((1e9,1e9,1e9)); mx=Vector((-1e9,-1e9,-1e9))
for o in ms:
    for c in o.bound_box:
        w=o.matrix_world@Vector(c)
        for i in range(3):
            mn[i]=min(mn[i],w[i]); mx[i]=max(mx[i],w[i])
ctr=(mn+mx)/2; size=mx-mn; d=max(size.x,size.y)
print('meshes',len(ms),'verts',sum(len(o.data.vertices) for o in ms))
print('bbox min',[round(v,1) for v in mn],'max',[round(v,1) for v in mx],'size',[round(v,1) for v in size])
cam=I._cam('Cam_T',(ctr.x+d*0.8,ctr.y-d*0.8,ctr.z+d*0.7),(ctr.x,ctr.y,ctr.z),35)
cam.data.type='ORTHO'; cam.data.ortho_scale=d*1.35
I.look('Cam_T','clay')
print('OK import')
