"""Amostra cor media por REGIAO espacial -> calibra pele vs roupa com numeros reais."""
import bpy, sys, numpy as np
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, game_builder; importlib.reload(game_builder)
mesh=max([o for o in bpy.context.scene.objects if o.type=='MESH'], key=lambda o:len(o.data.vertices))
cols=game_builder._sample_vert_colors(mesh, "texture_pbr_20250901")
co=np.array([v.co for v in mesh.data.vertices])
z=co[:,2]; x=co[:,0]; zmin,zmax=z.min(),z.max(); h=zmax-zmin
def reg(name,mask):
    if mask.sum()<10: print(f"{name}: vazio"); return
    c=cols[mask].mean(0); b=c.mean()
    print(f"{name:12s} n={int(mask.sum()):6d} RGB=({c[0]:.2f},{c[1]:.2f},{c[2]:.2f}) bright={b:.2f}")
zr=(z-zmin)/h
reg("rosto",      (zr>0.85)&(np.abs(x)<0.10))   # face (mas tem cabelo)
reg("pescoço",    (zr>0.78)&(zr<0.85)&(np.abs(x)<0.06))
reg("torso/dress",(zr>0.55)&(zr<0.72)&(np.abs(x)<0.12))
reg("antebraco_L",(zr>0.50)&(zr<0.62)&(x>0.18))
reg("mao_L",      (zr>0.42)&(zr<0.52)&(x>0.20))
reg("perna_baixa",(zr<0.20)&(np.abs(x)<0.12))
reg("saia",       (zr>0.20)&(zr<0.45)&(np.abs(x)<0.20))
print("OK calibrate")
