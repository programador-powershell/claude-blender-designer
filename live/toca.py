"""Toca Mecanica (area 3 / cena6) — MANUAL, layout do RELEVO: warren horizontal de varias CAMARAS
circulares TERRACADAS (camada por camada) com gear-floors GIRANDO, nas posicoes do relevo, ligadas por
TUNEIS + trilho; o boss fica na camara central. Engrenagens/relogios giram, correntes+pendulo balancam.
Ref: relevo\toca mecanica.png (top-down: camaras circulares + gear-floors + tuneis + rail, multi-nivel).
"""
import bpy, bmesh, math, random, sys
from mathutils import Vector
sys.path.insert(0, r'D:\Alice\tools\auto-rig-fix\live')
import interior as I
box=I.box; cyl=I.cyl; sphere=I.sphere; mat=I.mat; setmat=I.setmat; purge=I.purge
join=I.join; bevel=I.bevel; shade_smooth=I.shade_smooth; boolean=I.boolean; _cam=I._cam; look=I.look
_rock=I._rock
def _rng(): random.seed(6); return random
FEND=120
# === LE O BLUEPRINT JSON (pipeline: blueprint -> Blender) ===
import json
BP_PATH=r'D:\Alice\tools\MapVisionBuilder\output\blueprints\03_toca_mecanica.json'
BP=json.load(open(BP_PATH, encoding='utf-8'))
CH={c['id']:(c['center_m'][0], c['center_m'][1], c['r_m'], -c['floor_z'], c['kind']) for c in BP['chambers']}
GND_W, GND_H = BP['size_m'][0]+6, BP['size_m'][1]+6     # +margem de rocha
LINKS=[(p['from'], p['to']) for p in BP.get('paths',[])]
RAIL=BP.get('rail')
def tmats():
    return dict(metal=mat('T_Metal',(0.13,0.12,0.11),0.5,metal=1.0),
        metal2=mat('T_Brass',(0.34,0.26,0.11),0.42,metal=1.0),
        stone=mat('T_Stone',(0.10,0.095,0.088),0.92), floor=mat('T_Floor',(0.12,0.11,0.10),0.88),
        stone2=mat('T_Stone2',(0.095,0.070,0.050),0.93),   # rocha marrom (entulho variado)
        wood=mat('T_Wood',(0.07,0.045,0.025),0.7), cface=mat('T_ClockFace',(0.5,0.47,0.42),0.4),
        chain=mat('T_Chain',(0.16,0.15,0.14),0.5,metal=1.0),
        glow=mat('T_Glow',(0.10,0.32,0.62),0.4,emis=(0.22,0.55,1.0),estr=5.0))   # relogio azul do Coelho
# ---------------- animacao ----------------
def _loop(o):
    try:
        act=o.animation_data.action; fcs=getattr(act,'fcurves',None)
        if fcs is None:
            cb=act.layers[0].strips[0].channelbag(o.animation_data.action_slot); fcs=cb.fcurves
        for fc in fcs: fc.modifiers.new('CYCLES')
    except Exception as e: print('loop skip',e)
def _spin(o,turns=1.0,axis=2):
    o.delta_rotation_euler[axis]=0.0; o.keyframe_insert('delta_rotation_euler',index=axis,frame=1)
    o.delta_rotation_euler[axis]=turns*2*math.pi; o.keyframe_insert('delta_rotation_euler',index=axis,frame=FEND); _loop(o)
def _sway(o,amp=0.15,axis=0):
    for f,val in [(1,0.0),(FEND*0.25,amp),(FEND*0.5,0.0),(FEND*0.75,-amp),(FEND,0.0)]:
        o.delta_rotation_euler[axis]=val; o.keyframe_insert('delta_rotation_euler',index=axis,frame=int(f))
    _loop(o)
# ---------------- pecas ----------------
def _gear(name,R,teeth,thick,M):
    parts=[cyl(name+'_b',R*0.92,thick,(0,0,0),M['metal'],verts=max(24,teeth*2))]
    for k in range(teeth):
        a=k*2*math.pi/teeth
        parts.append(box(name+f'_t{k}',(R*0.16,R*0.20,thick),(R*0.93*math.cos(a),R*0.93*math.sin(a),0),M['metal'],rot=(0,0,a)))
    parts.append(cyl(name+'_hub',R*0.24,thick*1.4,(0,0,0),M['metal2']))
    for k in range(6): parts.append(box(name+f'_s{k}',(R*1.5,R*0.10,thick*0.6),(0,0,0),M['metal'],rot=(0,0,k*math.pi/6)))
    parts.append(cyl(name+'_hole',R*0.10,thick*1.6,(0,0,0),M['metal2']))
    g=join(parts,name); shade_smooth(g); return g
def _hand(name,L,w,t,M):
    o=box(name,(w,t,L),(0,0,0),M)
    for v in o.data.vertices: v.co.z+=L/2
    return o
def _clock(name,pos,R,M,spin=True):
    parts=[cyl(name+'_f',R,0.30,(0,0,0),M['cface'],verts=40)]
    bpy.ops.mesh.primitive_torus_add(location=(0,0,0.05),major_radius=R,minor_radius=R*0.07,major_segments=40,minor_segments=8)
    rim=bpy.context.active_object; rim.name=name+'_rim'; setmat(rim,M['metal2']); parts.append(rim)
    for k in range(12):
        a=k*math.pi/6; parts.append(box(name+f'_k{k}',(R*0.04,R*0.12,0.12),(math.sin(a)*R*0.82,math.cos(a)*R*0.82,0.12),M['metal2']))
    cl=join(parts,name); shade_smooth(cl); cl.rotation_euler=(math.radians(90),0,0); cl.location=pos
    hh=_hand(name+'_hh',R*0.55,R*0.10,0.12,M['metal2']); hh.location=pos
    mh=_hand(name+'_mh',R*0.85,R*0.07,0.12,M['metal2']); mh.location=pos
    if spin: _spin(hh,-1.0,1); _spin(mh,-6.0,1)
    return cl
def _chain(name,top,length,M,links=7):
    p=[]; r=0.10
    for i in range(links):
        rot=(math.radians(90),0,0) if i%2 else (0,0,0)
        bpy.ops.mesh.primitive_torus_add(location=(top[0],top[1],top[2]-i*length/links),major_radius=r,minor_radius=r*0.3,major_segments=8,minor_segments=6,rotation=rot)
        o=bpy.context.active_object; setmat(o,M['chain']); p.append(o)
    return join(p,name)
def _ramp(p1,p2,wd,M):
    p1=Vector(p1);p2=Vector(p2); mid=(p1+p2)/2; d=p2-p1; L=max(0.3,d.length)
    return box('ramp',(L,wd,0.3),mid,M['floor'],rot=(0,-math.asin(max(-1,min(1,d.z/L))),math.atan2(d.y,d.x)))

# ---------------- camara TERRACADA (camada por camada) ----------------
def _terraced(cx,cy,R,depth,M,nterr=3,inward=0.40):
    """Aneis-terraco (camada por camada) do rim (z=0) ao fundo. Flat=menos inward. Retorna floor."""
    step=depth/max(1,nterr)
    for i in range(nterr):
        z=-i*step; Ro=R - i*(R*inward/nterr)
        ring=cyl('ter',Ro,0.5,(cx,cy,z),M['floor'],verts=48)
        hole=cyl('h',max(0.6,Ro-1.6),1.0,(cx,cy,z),None,verts=48); boolean(ring,hole)
    fz=-depth; ir=R-(R*inward)
    cyl('cfloor',ir+0.3,0.6,(cx,cy,fz-0.1),M['floor'],verts=48)
    return (cx,cy,fz,ir)

def _winding(A,B):
    """CANYON organico: 5 segmentos seguindo curva senoidal, LARGURA VARIADA. Cutters."""
    ax,ay,bx,by=A[0],A[1],B[0],B[1]
    dx,dy=bx-ax,by-ay; L=math.hypot(dx,dy) or 1; ox,oy=-dy/L,dx/L
    amp=L*0.16; sign=1 if (int(abs(ax+bx))%2==0) else -1
    def pt(t):
        w=math.sin(t*math.pi)*amp*sign + math.sin(t*3*math.pi)*amp*0.35
        return (ax+dx*t+ox*w, ay+dy*t+oy*w)
    N=5; pts=[pt(i/N) for i in range(N+1)]; segs=[]
    for i in range(N):
        p,q=pts[i],pts[i+1]
        cx2,cy2=(p[0]+q[0])/2,(p[1]+q[1])/2; ang=math.atan2(q[1]-p[1],q[0]-p[0]); ln=math.hypot(q[0]-p[0],q[1]-p[1])
        wid=3.0+(1.6 if i%2 else 0.4)                 # largura varia = canyon
        segs.append(box('wc',(ln+1.4,wid,3.2),(cx2,cy2,-0.5),None,rot=(0,0,ang)))
    return segs

def build_ground(M):
    g=box('Ground',(GND_W,GND_H,2.0),(0,0,-1.0),M['stone'])      # slab QUADRADA (como relevo)
    for nm,(cx,cy,R,d,k) in CH.items():
        hole=cyl('gh',R,3.0,(cx,cy,-1.0),None,verts=48); boolean(g,hole)
    for a,b in LINKS:                                            # passagens sinuosas
        for seg in _winding(CH[a],CH[b]): boolean(g,seg)
    railcut=box('rc',(20,4,3),(CH['grail'][0]-12,CH['grail'][1],-0.5),None); boolean(g,railcut)
    ent=box('ent',(5,18,3),(-1,-GND_H/2+9,-0.5),None); boolean(g,ent)     # tunel de ENTRADA (sul) -> pbc
    setmat(g,M['stone']); shade_smooth(g)
    return "ground ok"

def _gearfloor(nm,cx,cy,ir,fz,M,rng):
    """Piso de ENGRENAGEM denso (relevo: cogs CONCENTRICOS finos). Aneis escalonados
    de raio decrescente, sentidos ALTERNADOS, + mostrador + cogs satelites offset."""
    nrings=max(3,int(ir/1.3))
    for i in range(nrings):
        rr=ir*(0.97 - i*0.92/nrings)
        if rr<0.5: break
        teeth=max(12,int(rr*4.0))                       # cogs FINOS
        zz=fz+0.28+i*0.11                               # escalonado (anel por anel sobe)
        g=_gear(f'{nm}_cg{i}', rr, teeth, 0.26, M); g.location=(cx,cy,zz)
        _spin(g, turns=((-1)**i)*rng.uniform(0.15,0.45))
    cyl(nm+'_axle', max(0.18,ir*0.10), 1.0,(cx,cy,fz+0.6),M['metal2'])
    ring=cyl(nm+'_mr', ir*0.99, 0.22,(cx,cy,fz+0.12), M['metal2'], verts=48)
    hole=cyl('mh', ir*0.90, 0.5,(cx,cy,fz+0.12),None,verts=48); boolean(ring,hole); shade_smooth(ring)
    for k in range(12):
        a=k*math.pi/6
        box(nm+f'_tk{k}',(0.10,0.30,0.18),(cx+math.cos(a)*ir*0.94, cy+math.sin(a)*ir*0.94, fz+0.22),M['metal2'],rot=(0,0,a))
    for s in range(rng.randint(1,2)):                    # cogs satelites engrenando na borda
        a=rng.uniform(0,2*math.pi); sr=ir*rng.uniform(0.28,0.40)
        g2=_gear(f'{nm}_sat{s}', sr, max(12,int(sr*4)), 0.30, M)
        g2.location=(cx+math.cos(a)*(ir*0.7), cy+math.sin(a)*(ir*0.7), fz+0.34)
        _spin(g2, turns=rng.choice([-1,1])*rng.uniform(0.4,0.8))

def build_chambers(M):
    rng=_rng(); KN={'gear':2,'rail':2,'pit':1,'terrace':5,'boss':3}
    for nm,(cx,cy,R,d,k) in CH.items():
        nt=KN.get(k,3); inw=0.55 if k=='terrace' else 0.40
        cx2,cy2,fz,ir=_terraced(cx,cy,R,d,M,nterr=nt,inward=inw)
        if k in ('gear','rail','terrace'):                       # gear-floor rico (relevo)
            _gearfloor(nm,cx,cy,ir,fz,M,rng)
        if k=='rail':
            for sx in (-0.7,0.7): box('rail',(2*R+14,0.12,0.16),(cx-7,cy+sx,fz+0.12),M['metal'])
            for j in range(13): box('slp',(0.3,1.8,0.12),(cx-R-6+j*1.4,cy,fz+0.03),M['wood'])
            bpy.ops.mesh.primitive_cylinder_add(radius=2.2,depth=3,location=(cx-R-10,cy,fz+1.0),vertices=20,rotation=(0,math.radians(90),0))
            ar=bpy.context.active_object; ar.name='TunArch'; setmat(ar,M['stone'])
        # entulho no RIM (fora do cog, sobre os terracos)
        RM=[M['stone'],M['stone2'],M['floor']]
        for j in range(rng.randint(4,7)):
            a=rng.uniform(0,2*math.pi); dd=rng.uniform(ir*1.05,R*0.95); r=rng.uniform(0.2,0.6)
            zz=-( (R-dd)/max(0.1,R-ir) )*d*0.25 + r*0.4      # acompanha o terraco
            _rock('rb',(cx+dd*math.cos(a),cy+dd*math.sin(a),zz),r,M,rng,RM,flat_sq=(0.4,0.9))
    return "chambers ok"

def build_boss(M):
    rng=_rng(); bx,by,R,d,_=CH['boss']; fz=-d
    cyl('BossPlat',4.0,1.0,(bx,by,fz+0.6),M['floor'],verts=48)
    cyl('BossStep',5.0,0.5,(bx,by,fz+0.3),M['floor'],verts=48)
    teeth=32
    for k in range(teeth):
        a=k*2*math.pi/teeth; box('bt',(0.4,0.5,0.5),(bx+4.1*math.cos(a),by+4.1*math.sin(a),fz+0.85),M['metal'],rot=(0,0,a))
    # parede de engrenagens (norte da camara) em varias alturas/CAMADAS
    yw=by+R-1.0
    box('GWback',(15,0.6,d+2),(bx,yw+0.4,fz/2+1),M['stone'])
    gi=0
    for z in (fz+1.0,fz+3.0,fz+5.0):
        for j in range(2):
            x=rng.uniform(-5,5); gr=rng.uniform(1.6,2.6)
            g=_gear(f'GW{gi}',gr,max(12,int(gr*7)),0.5,M); g.rotation_euler=(math.radians(90),0,0)
            g.location=(bx+x,yw,z); _spin(g,(1 if gi%2 else -1)*rng.uniform(.4,1.1),1); gi+=1
    _clock('MonClock',(bx,yw-0.1,fz+5.5),2.6,M)
    # ENGRENAGENS GIGANTES (cena6) flanqueando a parede do boss, meio encravadas
    for sx,gr,tn in ((-1,4.6,0.6),(1,3.8,-0.5)):
        G=_gear(f'GiantGear{sx}', gr, max(28,int(gr*6)), 0.8, M); G.rotation_euler=(math.radians(90),0,0)
        G.location=(bx+sx*(R*0.62), yw-0.2, fz+gr*0.7); _spin(G, tn*rng.uniform(0.2,0.4), 1)
    # suspensos + pendulo no poco da camara
    for i,(x,y,z,r) in enumerate([(-3,0,fz+4,1.3),(3,-2,fz+5,1.0),(0,3,fz+3,0.9)]):
        cl=_clock(f'Sus{i}',(bx+x,by+y,z),r,M); _sway(cl,rng.uniform(.04,.08),0)
        ch=_chain(f'Ch{i}',(bx+x,by+y,1.0),1.0-z,M); _sway(ch,rng.uniform(.05,.1),rng.choice([0,1]))
    rod=box('PendRod',(0.2,0.2,d),(0,0,0),M['metal2'])
    for v in rod.data.vertices: v.co.z-=d/2
    rod.location=(bx-2,by-2,1.0); bob=sphere('PendBob',0.6,(0,0,-d),M['metal2']); bob.parent=rod
    _sway(rod,0.4,0)
    # RELOGIO AZUL DO COELHO (boss reveal) — orbe brilhante no centro + luz azul
    orb=sphere('RabbitClock',0.55,(bx,by,fz+1.6),M['glow'],seg=28,ring=16); shade_smooth(orb)
    bpy.ops.mesh.primitive_torus_add(location=(bx,by,fz+1.6),major_radius=0.6,minor_radius=0.06,
                                     major_segments=32,minor_segments=10,rotation=(math.radians(90),0,0))
    rr=bpy.context.active_object; rr.name='RabbitClockRim'; setmat(rr,M['metal2']); _spin(rr,1.0,1)
    bpy.ops.object.light_add(type='POINT', location=(bx,by,fz+2.2))
    L=bpy.context.active_object; L.name='L_RabbitClock'; L.data.energy=500; L.data.color=(0.35,0.6,1.0); L.data.shadow_soft_size=1.2
    # PASSARELA DE APROXIMACAO (planta: 14x3 m) da entrada sul ao arena
    box('Passarela',(3.0,14.0,0.4),(bx, by-R-6.0, fz+0.2),M['floor'])
    return "boss ok"

def build_roof(M):
    """MONTANHA de rocha cobrindo o warren (caverna fechada) — domo ROCHOSO (displace) + boca de caverna."""
    rng=_rng()
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=72, ring_count=36, location=(0,0,0.1))
    d=bpy.context.active_object; d.name='Roof'
    d.scale=(GND_W/2+4, GND_H/2+4, 6.0); bpy.ops.object.transform_apply(scale=True)
    bm=bmesh.new(); bm.from_mesh(d.data)            # so o domo (metade de cima)
    for v in list(bm.verts):
        if v.co.z < 0.1: bm.verts.remove(v)
    bm.to_mesh(d.data); bm.free(); d.data.update()
    # ROCHOSO: displace com ruido
    tex=bpy.data.textures.get('RockTex') or bpy.data.textures.new('RockTex','CLOUDS')
    tex.noise_scale=3.0; tex.noise_depth=5
    dp=d.modifiers.new('disp','DISPLACE'); dp.texture=tex; dp.strength=2.6; dp.mid_level=0.35
    bpy.context.view_layer.objects.active=d; bpy.ops.object.modifier_apply(modifier='disp')
    d.modifiers.new('s','SOLIDIFY').thickness=1.6
    setmat(d,M['stone']); shade_smooth(d)
    # BOCA da caverna no sul (maior)
    mouth=cyl('mouth',4.2,16,(-1,-GND_H/2+2.5,1.6),None,rot=(math.radians(90),0,0)); boolean(d,mouth)
    bpy.ops.mesh.primitive_torus_add(location=(-1,-GND_H/2+2.5,1.6),major_radius=4.4,minor_radius=0.7,
                                     major_segments=24,minor_segments=8,rotation=(math.radians(90),0,0))
    fr=bpy.context.active_object; fr.name='MouthArch'; setmat(fr,M['stone'])
    # pedregulhos na base (montanha natural)
    RM=[M['stone'],M['stone2']]
    for k in range(26):
        a=rng.uniform(0,2*math.pi); rx=(GND_W/2+3)*math.cos(a); ry=(GND_H/2+3)*math.sin(a)*0.86
        r=rng.uniform(0.8,2.4)
        _rock('boulder',(rx*rng.uniform(0.85,1.05),ry*rng.uniform(0.85,1.05),rng.uniform(0.2,2.0)),r,M,rng,RM,flat_sq=(0.6,1.1))
    return "roof ok"

def ttex(M=None):
    M=M or tmats()
    I._pmat(M['metal'],'metal',(0.16,0.15,0.14),(0.07,0.065,0.06),0.50,1.0,9.0,0.10)
    I._pmat(M['metal2'],'metal',(0.36,0.27,0.11),(0.22,0.16,0.06),0.42,1.0,9.0,0.08)
    I._pmat(M['stone'],'stone',(0.13,0.12,0.11),(0.05,0.045,0.04),0.92,0.0,6.0,0.45)
    I._pmat(M['stone2'],'stone',(0.12,0.085,0.06),(0.05,0.034,0.022),0.93,0.0,8.0,0.45)
    I._pmat(M['floor'],'stone',(0.14,0.13,0.12),(0.06,0.055,0.05),0.88,0.0,7.0,0.40)
    I._pmat(M['wood'],'wood',(0.07,0.045,0.025),(0.03,0.02,0.01),0.7,0.0,7.0,0.3)
    I._pmat(M['cface'],'ceramic',(0.52,0.49,0.43),(0.36,0.33,0.29),0.4,0.0,12.0,0.06)
    I._pmat(M['chain'],'metal',(0.18,0.17,0.16),(0.09,0.085,0.08),0.5,1.0,10.0,0.08)
    return "ttex ok"
def wall_cogs(M):
    """Cogs encravados nas PAREDES dos tuneis (relevo: engrenagens nos caniones)."""
    rng=_rng()
    for a,b in LINKS:
        ax,ay=CH[a][0],CH[a][1]; bx,by=CH[b][0],CH[b][1]
        mx,my=(ax+bx)/2,(ay+by)/2; ang=math.atan2(by-ay,bx-ax)
        ox,oy=-math.sin(ang),math.cos(ang)
        for s in range(rng.randint(1,2)):
            r=rng.uniform(1.0,2.0); side=rng.choice([-1,1]); along=rng.uniform(-2.5,2.5)
            px=mx+math.cos(ang)*along+ox*side*(2.4+r*0.5)
            py=my+math.sin(ang)*along+oy*side*(2.4+r*0.5)
            g=_gear(f'WC_{a}_{b}_{s}', r, max(12,int(r*5)), 0.5, M)
            g.rotation_euler=(math.radians(90),0,ang)               # de pe na parede
            g.location=(px,py,-1.2-r*0.2); _spin(g, rng.choice([-1,1])*rng.uniform(0.3,0.7), 1)
    return "wall cogs ok"

def lighting(M):
    """Caverna ESCURA+AZUL (cena6): boca fria, fill azul por camara, glint quente nos gears."""
    sc=bpy.context.scene
    w=bpy.data.worlds.get('World') or bpy.data.worlds.new('World'); sc.world=w; w.use_nodes=True
    bg=w.node_tree.nodes.get('Background')
    if bg: bg.inputs[0].default_value=(0.020,0.030,0.055,1); bg.inputs[1].default_value=0.30  # ambiente azul (le no escuro)
    bpy.ops.object.light_add(type='AREA', location=(-1,-GND_H/2+3,3.2))    # boca de caverna (luz fria sul)
    a=bpy.context.active_object; a.name='L_Mouth'; a.data.energy=900; a.data.size=7.0
    a.data.color=(0.55,0.70,1.0); a.rotation_euler=(math.radians(62),0,0)
    for nm,(cx,cy,R,d,k) in CH.items():
        fz=-d
        bpy.ops.object.light_add(type='POINT', location=(cx,cy,fz+R*0.8))  # fill azul forte
        p=bpy.context.active_object; p.name=f'LF_{nm}'; p.data.energy=R*R*4
        p.data.color=(0.35,0.55,1.0); p.data.shadow_soft_size=R*0.6
        if k in ('gear','rail','terrace','boss'):                          # glint quente no maquinario
            bpy.ops.object.light_add(type='POINT', location=(cx+R*0.3,cy,fz+1.4))
            g=bpy.context.active_object; g.name=f'LG_{nm}'; g.data.energy=R*R*2
            g.data.color=(1.0,0.66,0.30); g.data.shadow_soft_size=0.6
    return "lighting ok"

def cameras():
    a=_cam('Cam_Top',(0,0,72),(0,0,-3),40); a.data.type='ORTHO'; a.data.ortho_scale=74
    iso=_cam('Cam_Iso',(42,-42,36),(0,-2,-3),35); iso.data.type='ORTHO'; iso.data.ortho_scale=78
    _cam('Cam_Boss',(2,-9.5,-2.2),(2,11,-0.6),30)   # sul->norte: orbe azul + parede engrenagens + relogio monumental
    _cam('Cam_Ext',(0,-52,24),(0,-12,2),35)        # EXTERIOR: montanha + boca de caverna (sul)
    return "cameras ok"
def build_all():
    purge(); M=tmats()
    build_ground(M); build_chambers(M); wall_cogs(M); build_boss(M); build_roof(M)
    ttex(M); lighting(M); cameras()
    sc=bpy.context.scene; sc.frame_start=1; sc.frame_end=FEND
    look('Cam_Boss')
    return "TOCA DONE (relevo)"
