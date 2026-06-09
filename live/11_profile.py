"""Live step 11 — perfil do vestido: max|x| e contagem por faixa de altura Z.
Mostra onde estao os bracos/mangas do vestido vs os ossos."""
import bpy
d = bpy.data.objects.get("AliceDress"); M = d.matrix_world
bands = {}
for v in d.data.vertices:
    co = M @ v.co
    z = co.z
    b = round(z*10)/10  # faixa de 0.1
    e = bands.setdefault(b, {"n":0,"xmax":-9,"xmin":9})
    e["n"]+=1
    if co.x>e["xmax"]: e["xmax"]=co.x
    if co.x<e["xmin"]: e["xmin"]=co.x
print("Z-band | n | xmin | xmax")
for b in sorted(bands):
    e=bands[b]
    print(f"  z={b:.1f} n={e['n']:6d} x[{e['xmin']:.3f},{e['xmax']:.3f}]")
