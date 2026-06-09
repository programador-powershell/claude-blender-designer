import bpy

dress = bpy.data.objects['PA_AliceChapeleiroDress']
arm = bpy.data.objects['Alice_Base_Rig']

bpy.context.view_layer.objects.active = dress
for o in bpy.data.objects: o.select_set(False)
dress.select_set(True)

bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.separate(type='MATERIAL')
bpy.ops.object.mode_set(mode='OBJECT')

piece_names = {
    'MAT_Teal_Fabric': 'PA_Saia_Corpete_Teal',
    'MAT_Cream_Lace': 'PA_Hem_Lace_Cream',
    'MAT_Stripes_BW': 'PA_Meias_Listradas',
    'MAT_Black_Leather': 'PA_Botas_Luvas',
    'MAT_Gold_Antique': 'PA_Bow_Gold',
    'MAT_Hair_Black': 'PA_Cabelo',
    'MAT_Cream_Chemise': 'PA_Chemise_Decote',
    'MAT_Black_Lace': 'PA_Lace_Preta',
}
for o in list(bpy.data.objects):
    if o.type == 'MESH' and 'Chapeleiro' in o.name:
        if len(o.data.polygons) == 0:
            bpy.data.objects.remove(o, do_unlink=True); continue
        mat0 = o.data.materials[o.data.polygons[0].material_index]
        if mat0 and mat0.name in piece_names:
            o.name = piece_names[mat0.name]

print('PECAS:')
for o in bpy.data.objects:
    if o.type == 'MESH':
        print(f'  {o.name}: faces={len(o.data.polygons)} parent={o.parent.name if o.parent else None} mods={[m.type for m in o.modifiers]}')
