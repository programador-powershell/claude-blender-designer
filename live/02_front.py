"""Live step 02 — vista frontal ortho + mede bbox de cada mesh (centro/min/max)."""
import bpy

def bb(o):
    cs = [o.matrix_world @ v.co for v in o.data.vertices]
    xs=[c.x for c in cs]; ys=[c.y for c in cs]; zs=[c.z for c in cs]
    return dict(xmin=min(xs),xmax=max(xs),ymin=min(ys),ymax=max(ys),zmin=min(zs),zmax=max(zs),
                cx=(min(xs)+max(xs))/2, cy=(min(ys)+max(ys))/2)

for o in bpy.data.objects:
    if o.type=='MESH':
        b=bb(o)
        print(f"{o.name}: X[{b['xmin']:.3f},{b['xmax']:.3f}] cx={b['cx']:.3f} | Y[{b['ymin']:.3f},{b['ymax']:.3f}] cy={b['cy']:.3f} | Z[{b['zmin']:.3f},{b['zmax']:.3f}]")

# vista frontal ortho (-Y), enquadra
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        region=next((r for r in area.regions if r.type=='WINDOW'),None)
        with bpy.context.temp_override(area=area, region=region):
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.view3d.view_axis(type='FRONT')
            bpy.ops.view3d.view_all()
        break
print("OK front")
