import bpy, os
sc=bpy.context.scene; sc.render.engine='BLENDER_EEVEE'
c=bpy.data.objects.get('Cam_Iso');
if c: sc.camera=c
for o in bpy.data.objects:
    if o.get('trellis_ref'): o.hide_set(True)
for a in bpy.context.screen.areas:
    if a.type=='VIEW_3D':
        sp=a.spaces[0]; sp.shading.type='MATERIAL'
        sp.shading.use_scene_lights=False; sp.shading.use_scene_world=False; sp.overlay.show_overlays=False
        rg=next(r for r in a.regions if r.type=='WINDOW')
        with bpy.context.temp_override(area=a,region=rg): sp.region_3d.view_perspective='CAMERA'
        break
OUT=r'D:\Alice\tools\auto-rig-fix\work\anim'; os.makedirs(OUT, exist_ok=True)
sc.render.resolution_x=480; sc.render.resolution_y=380; sc.render.image_settings.file_format='PNG'
frames=list(range(1,121,8))
for i,f in enumerate(frames):
    sc.frame_set(f)
    sc.render.filepath=os.path.join(OUT, f'vx_{i:02d}.png')
    bpy.ops.render.opengl(write_still=True)
print('ANIM_DONE', len(frames))
