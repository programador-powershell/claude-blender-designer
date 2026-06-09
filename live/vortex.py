"""Vortice (Alice, area 2 / CENA 05 = Ruptura da Sala / Entrada da Toca).
PLANTA OFICIAL (E:\\References\\img\\maps\\cena5\\262a1bf2...): hall ~14.7(X) x 18.6(Y) m,
poco espiral (poco temporal) prof 7.2 m, correntes suspensas, engrenagens, restos da
mesa de cha, aparadores, espelhos trincados, portas duplas, transicao=toca no fundo.
Relevo (relevo\\vortice.png): funil espiral terracado + relogios gigantes + entulho.
Reusa helpers de interior.py (box/cyl/sphere/_rock/_pmat com grime/shade_smooth/boolean/join).
"""
import bpy, bmesh, math, random, sys
from mathutils import Vector
sys.path.insert(0, r'D:\Alice\tools\auto-rig-fix\live')
import interior as I
box=I.box; cyl=I.cyl; sphere=I.sphere; mat=I.mat; setmat=I.setmat; purge=I.purge
join=I.join; bevel=I.bevel; shade_smooth=I.shade_smooth; boolean=I.boolean; _cam=I._cam
look=I.look; _rock=I._rock

def _rng(): random.seed(3); return random

# ---- PLANTA cena5 ----
HX, HY, HZ, WT = 14.7, 18.6, 4.6, 0.45     # hall interno X,Y, parede alt, esp
RMAX, DEPTH, TURNS = 6.5, 7.2, 2.5         # poco: raio boca, prof 7.2m, voltas espiral
FEND = 120

def vmats():
    return dict(
        dirt  = mat('V_Dirt',  (0.11,0.095,0.078),0.95),
        rock  = mat('V_Rock',  (0.14,0.13,0.12),  0.92),
        rock2 = mat('V_Rock2', (0.105,0.075,0.05),0.93),   # marrom
        stone = mat('V_Stone', (0.065,0.058,0.05),0.92),
        cface = mat('V_ClockFace',(0.55,0.52,0.46),0.40),
        cmetal= mat('V_ClockMetal',(0.42,0.31,0.12),0.35,metal=1.0),
        iron  = mat('V_Iron',  (0.09,0.085,0.085),0.45,metal=1.0),
        wood  = mat('V_Wood',  (0.045,0.028,0.016),0.65),
        card  = mat('V_Card',  (0.5,0.48,0.45),   0.5),
        porc  = mat('V_Porc',  (0.46,0.44,0.40),  0.30),
        mirror= mat('V_Mirror',(0.22,0.24,0.27),  0.10,metal=1.0),
        petal = mat('V_Petal', (0.32,0.06,0.24),  0.6),
        glow  = mat('V_Glow',  (0.10,0.30,0.62),  0.4, emis=(0.22,0.52,1.0), estr=4.0),
        wind  = mat('V_Wind',  (0.45,0.55,0.75),  0.85, emis=(0.20,0.35,0.62), estr=0.5, alpha=0.13),
    )

# ---------------- animacao (loop ciclico) ----------------
def _loop(o):
    try:
        act=o.animation_data.action; fcs=getattr(act,'fcurves',None)
        if fcs is None:
            cb=act.layers[0].strips[0].channelbag(o.animation_data.action_slot); fcs=cb.fcurves
        for fc in fcs: fc.modifiers.new('CYCLES')
    except Exception as e: print('loop skip',e)

def _spin(o, turns=1.0, axis=2):
    o.delta_rotation_euler[axis]=0.0; o.keyframe_insert('delta_rotation_euler',index=axis,frame=1)
    o.delta_rotation_euler[axis]=turns*2*math.pi; o.keyframe_insert('delta_rotation_euler',index=axis,frame=FEND)
    _loop(o)

def _fall(o, dist, tumble=1.0):
    z0=o.location.z
    o.keyframe_insert('location',index=2,frame=1)
    o.location.z=z0-dist; o.keyframe_insert('location',index=2,frame=FEND); o.location.z=z0
    for ax in (0,1):
        o.delta_rotation_euler[ax]=0.0; o.keyframe_insert('delta_rotation_euler',index=ax,frame=1)
        o.delta_rotation_euler[ax]=tumble*2*math.pi; o.keyframe_insert('delta_rotation_euler',index=ax,frame=FEND)
    _loop(o)

def _orbit(o, r, a0, turns, z, bob=0.0, steps=16):
    """TORNADO: orbita o eixo central (raio r, altura z) em 'turns' voltas INTEIRAS
    no loop -> inicio=fim (loop perfeito com CYCLES). turns>0 anti-horario."""
    turns=int(round(turns)) or 1
    for i in range(steps+1):
        f=int(round(1+(FEND-1)*i/steps))
        th=a0+turns*2*math.pi*i/steps
        o.location=(r*math.cos(th), r*math.sin(th), z+math.sin(th*3.0)*bob)
        o.keyframe_insert('location', frame=f)
    _loop(o)

# ---------------- HALL retangular arruinado (sala rompida) ----------------
def _notch_top(w, n=5):
    """Quebra o topo da parede em entalhes irregulares (ruina)."""
    rng=_rng()
    bb=[w.matrix_world @ Vector(c) for c in w.bound_box]
    xs=[v.x for v in bb]; ys=[v.y for v in bb]; zt=max(v.z for v in bb)
    x0,x1,y0,y1=min(xs),max(xs),min(ys),max(ys); long_x=(x1-x0)>(y1-y0)
    for i in range(rng.randint(n,n+2)):
        d=rng.uniform(0.4,1.3); cz=zt-d+1.2; nw=rng.uniform(0.4,1.1)
        if long_x: cut=box('ntc',(nw,(y1-y0)+0.5,2.4),(rng.uniform(x0+0.4,x1-0.4),(y0+y1)/2,cz))
        else:      cut=box('ntc',((x1-x0)+0.5,nw,2.4),((x0+x1)/2,rng.uniform(y0+0.4,y1-0.4),cz))
        boolean(w,cut)

def build_hall(M):
    # piso retangular com FURO circular (boca do poco)
    fl=box('Floor',(HX+2*WT, HY+2*WT, 0.6),(0,0,-0.3),M['stone'])
    hole=cyl('hole', RMAX, 2.0,(0,0,-0.3),None,verts=80); boolean(fl,hole)
    # paredes (4) - entrada ao SUL (-Y, vao), portas duplas no +X
    box('W_Xp',(WT,HY+2*WT,HZ),( HX/2+WT/2,0,HZ/2),M['stone'])
    box('W_Xn',(WT,HY+2*WT,HZ),(-HX/2-WT/2,0,HZ/2),M['stone'])
    box('W_Yp',(HX+2*WT,WT,HZ),(0, HY/2+WT/2,HZ/2),M['stone'])
    dgap=3.0; seg=(HX+2*WT-dgap)/2; hf=2.3                 # sul = entrada arruinada
    box('W_Yn_L',(seg,WT,hf),(-(dgap/2+seg/2),-HY/2-WT/2,hf/2),M['stone'])
    box('W_Yn_R',(seg,WT,hf),( (dgap/2+seg/2),-HY/2-WT/2,hf/2),M['stone'])
    for wn in ('W_Xp','W_Xn','W_Yp','W_Yn_L','W_Yn_R'):
        w=bpy.data.objects.get(wn);
        if w: _notch_top(w)
    # PORTAS DUPLAS hexagonais no +X (zona portas duplas)
    for sy in (-1.6,1.6):
        d=box(f'DoorHex{sy}',(0.18,1.3,2.6),(HX/2-0.12, sy,1.3),M['wood'])
        sphere(f'DoorKnob{sy}',0.09,(HX/2-0.30,sy+(0.5 if sy<0 else -0.5),1.3),M['cmetal'],seg=10,ring=8)
    # ESPELHOS TRINCADOS no -X
    for sy in (-3.0,0.0,3.0):
        box(f'Mirror{sy}',(0.06,1.0,1.9),(-HX/2+0.10,sy,1.7),M['mirror'])
        box(f'MirrorFrame{sy}',(0.10,1.15,2.05),(-HX/2+0.06,sy,1.7),M['wood'])
    return "hall ok"

# ---------------- funil + espiral terracada (o POCO) ----------------
def build_funnel(M):
    bpy.ops.mesh.primitive_cone_add(vertices=96, radius1=0.55, radius2=RMAX, depth=DEPTH,
                                    location=(0,0,-DEPTH/2), end_fill_type='NOTHING')
    cone=bpy.context.active_object; cone.name='Funnel'; setmat(cone,M['dirt']); shade_smooth(cone)
    pitch=RMAX/TURNS; riser=DEPTH/TURNS
    bm=bmesh.new(); segs=int(TURNS*90); vin=[]; vout=[]
    for i in range(segs+1):
        t=i/segs; th=t*TURNS*2*math.pi; rho=RMAX*(1-t); z=-DEPTH*t
        c,s=math.cos(th),math.sin(th)
        vin.append(bm.verts.new((rho*c, rho*s, z+0.05)))
        ro=rho+pitch*0.92
        vout.append(bm.verts.new((ro*c, ro*s, z+riser*0.55)))   # borda externa erguida (degrau)
    for i in range(segs):
        bm.faces.new((vin[i],vout[i],vout[i+1],vin[i+1]))
    me=bpy.data.meshes.new('Spiral'); bm.to_mesh(me); bm.free()
    sp=bpy.data.objects.new('SpiralLedge',me); bpy.context.collection.objects.link(sp)
    sp.modifiers.new('s','SOLIDIFY').thickness=0.35; setmat(sp,M['rock']); shade_smooth(sp)
    # dreno + brilho temporal (transicao p/ toca)
    cyl('Drain', 0.85, 1.2,(0,0,-DEPTH+0.4),M['rock'],verts=32)
    g=cyl('TemporalGlow',0.7,0.1,(0,0,-DEPTH+0.55),M['glow'],verts=32)
    bpy.ops.object.light_add(type='POINT', location=(0,0,-DEPTH+1.2))
    L=bpy.context.active_object; L.name='L_Temporal'; L.data.energy=120; L.data.color=(0.3,0.55,1.0); L.data.shadow_soft_size=1.2
    return "funnel ok"

def _pos_on_cone(ang, t, lift=0.0):
    rho=RMAX*(1-t); z=-DEPTH*t+lift
    return Vector((rho*math.cos(ang), rho*math.sin(ang), z)), rho

# ---------------- relogios gigantes encravados ----------------
def _clock(name, pos, inward, r, M):
    face=cyl(name+'_f', r, 0.12, (0,0,0), M['cface'], verts=44); shade_smooth(face)
    bpy.ops.mesh.primitive_torus_add(location=(0,0,0.03), major_radius=r, minor_radius=r*0.10,
                                     major_segments=44, minor_segments=12)
    rim=bpy.context.active_object; rim.name=name+'_rim'; setmat(rim,M['cmetal']); shade_smooth(rim)
    h1=box(name+'_h1',(r*0.06,r*0.66,0.06),(0,r*0.30,0.11),M['cmetal'])
    h2=box(name+'_h2',(r*0.05,r*0.92,0.06),(0,r*0.12,0.13),M['cmetal'],rot=(0,0,math.radians(72)))
    pin=cyl(name+'_pin',r*0.05,0.18,(0,0,0.09),M['cmetal'],verts=16)
    ticks=[box(name+f'_t{k}',(r*0.04,r*0.10,0.05),
               (math.sin(k*math.pi/6)*r*0.82,math.cos(k*math.pi/6)*r*0.82,0.10),M['cmetal']) for k in range(12)]
    cl=join([face,rim,h1,h2,pin]+ticks, name); shade_smooth(cl)
    cl.rotation_euler=inward.normalized().to_track_quat('Z','Y').to_euler(); cl.location=pos
    return cl

def giant_clocks(M):
    specs=[(math.radians(35),0.12,2.0),(math.radians(135),0.30,1.5),
           (math.radians(225),0.52,1.1),(math.radians(310),0.70,0.85)]
    for i,(ang,t,r) in enumerate(specs):
        pos,rho=_pos_on_cone(ang,t,lift=r*0.55)
        _clock(f'Clock{i}', pos, Vector((-math.cos(ang),-math.sin(ang),0.30)), r, M)
    return "clocks ok"

# ---------------- engrenagens (estrutura de relogio) ----------------
def _gear(name, r, teeth, thick, loc, M, rot=None):
    body=cyl(name+'_b', r, thick, (0,0,0), M['cmetal'], verts=max(24,teeth*2)); shade_smooth(body)
    hub=cyl(name+'_h', r*0.22, thick*1.2, (0,0,0), M['iron'], verts=20)
    ts=[]
    for k in range(teeth):
        a=k*2*math.pi/teeth
        ts.append(box(name+f'_t{k}',(r*0.16,r*0.16,thick*0.95),
                  (math.cos(a)*r*1.04, math.sin(a)*r*1.04, 0), M['cmetal'], rot=(0,0,a)))
    g=join([body,hub]+ts,name);
    if rot: g.rotation_euler=rot
    g.location=Vector(loc); return g

def gears(M):
    # estrutura de engrenagens encravada na parede do fundo (+Y) + uma na borda do poco
    g1=_gear('GearA',1.7,18,0.4,( 3.0, HY/2-1.2, 2.4),M, rot=(math.radians(90),0,0)); _spin(g1,0.5)
    g2=_gear('GearB',1.1,14,0.35,(1.4, HY/2-1.0, 1.3),M, rot=(math.radians(90),0,0)); _spin(g2,-0.8)
    g3=_gear('GearC',1.3,16,0.35,(-RMAX-0.3, 1.5, 0.2),M, rot=(0,math.radians(90),0)); _spin(g3,0.6,axis=0)
    return "gears ok"

# ---------------- correntes suspensas ----------------
def _chain(name, p0, p1, sag=1.2, links=11, lr=0.12, M=None):
    p0=Vector(p0); p1=Vector(p1); parts=[]
    for i in range(links):
        t=i/(links-1); p=p0.lerp(p1,t); p.z-=math.sin(math.pi*t)*sag
        bpy.ops.mesh.primitive_torus_add(location=p, major_radius=lr, minor_radius=lr*0.34,
                                         major_segments=14, minor_segments=7,
                                         rotation=(0,0,math.radians(90)*(i%2)))
        o=bpy.context.active_object; o.name=f'{name}_{i}'; setmat(o,M['iron']); shade_smooth(o); parts.append(o)
    return join(parts,name)

def chains(M):
    rng=_rng()
    spans=[((-RMAX,0,0.2),(RMAX,0,0.2),2.6),
           ((0,-RMAX,0.0),(0,RMAX,0.1),2.2),
           ((-RMAX*0.7,-RMAX*0.7,0.1),(RMAX*0.7,RMAX*0.7,0.1),2.4)]
    for i,(a,b,sg) in enumerate(spans):
        _chain(f'Chain{i}', a, b, sag=sg, links=13, lr=0.13, M=M)
    # algumas penduradas das engrenagens
    _chain('ChainG', (3.0,HY/2-1.2,2.0),(2.0,2.0,-1.0), sag=1.0, links=10, lr=0.11, M=M)
    return "chains ok"

# ---------------- restos da mesa de cha (continuidade) ----------------
def tea_remains(M):
    rng=_rng()
    # mesa TOMBADA inclinada na borda norte (+Y), caindo p/ o poco
    t=box('BrokenTable',(1.10,2.40,0.10),(0.0, HY/2-3.0, 0.9),M['wood'],
          rot=(math.radians(18),0,math.radians(8)))
    for sx in (-1,1):
        for sy in (-1,1):
            box('tleg',(0.10,0.10,0.7),(sx*0.45+0.0, HY/2-3.0+sy*1.0, 0.5),M['wood'],
                rot=(math.radians(18),0,0))
    # aparadores ao longo das paredes laterais
    for sy in (-4.5,4.0):
        box(f'Aparador{sy}',(0.6,1.5,1.2),(-HX/2+0.5, sy, 0.6),M['wood'])
        box(f'Aparador2{sy}',(0.6,1.5,1.2),( HX/2-0.5, sy*0.8, 0.6),M['wood'])
    # cacos de porcelana espalhados na borda
    for k in range(26):
        ang=rng.uniform(0,2*math.pi); rr=rng.uniform(RMAX+0.4, RMAX+3.5)
        x,y=rr*math.cos(ang), rr*math.sin(ang)
        if abs(x)>HX/2-0.4 or abs(y)>HY/2-0.4: continue
        sc=rng.uniform(0.05,0.13)
        o=sphere(f'Shard{k}',sc,(x,y,sc*0.5),M['porc'],seg=8,ring=5); o.scale=(rng.uniform(1,2),rng.uniform(0.6,1.2),0.3)
    return "tea remains ok"

# ---------------- entulho (rocha angular variada) ----------------
def debris(M):
    rng=_rng(); RM=[M['rock'],M['rock2'],M['stone']]; rocks=[]
    for k in range(44):                              # nos terracos do poco
        t=rng.uniform(0.08,0.9); ang=rng.uniform(0,2*math.pi)
        pos,rho=_pos_on_cone(ang,t,lift=0.22)
        rocks.append(_rock('slab',(pos.x,pos.y,pos.z),rng.uniform(0.18,0.5),M,rng,RM))
    for k in range(50):                              # no piso do hall (borda)
        x=rng.uniform(-HX/2+0.4,HX/2-0.4); y=rng.uniform(-HY/2+0.4,HY/2-0.4)
        if x*x+y*y < (RMAX+0.5)**2: continue
        rocks.append(_rock('rub',(x,y,0.08),rng.uniform(0.12,0.4),M,rng,RM,flat_sq=(0.35,0.7)))
    if rocks: join(rocks,'Debris')
    return "debris ok"

# ---------------- objetos flutuantes ANIMADOS (caos temporal) ----------------
def floating(M):
    """TORNADO: detritos ORBITAM o eixo em bandas conicas (fundo=raio menor+rapido,
    topo=raio maior+lento) -> redemoinho. Cada peca tb gira em si."""
    rng=_rng(); ci=0
    # (z, raio, voltas, n) — cone do tornado, rotacao diferencial (inner mais rapido)
    bands=[(-4.6,1.2,3,3),(-2.9,2.4,3,4),(-1.1,3.6,2,5),(0.7,4.8,2,5),(2.4,5.9,1,4)]
    for (z,r,turns,n) in bands:
        for k in range(n):
            a0=rng.uniform(0,2*math.pi); rr=r*rng.uniform(0.9,1.08); zz=z+rng.uniform(-0.35,0.35)
            kind=rng.random()
            if kind<0.40:
                o=_clock(f'FClock{ci}',Vector((rr,0,zz)),Vector((0,0,1)),rng.uniform(0.3,0.6),M)
            elif kind<0.62:
                o=box(f'FDoor{ci}',(0.7,0.08,1.4),(rr,0,zz),M['wood'])
                sphere(f'FKnob{ci}',0.05,(rr+0.30,0,zz),M['cmetal'],seg=8,ring=6).parent=o
            elif kind<0.82:
                o=cyl(f'FCup{ci}',0.13,0.15,(rr,0,zz),M['porc'],verts=20); shade_smooth(o)
            else:
                o=box(f'FBook{ci}',(0.30,0.40,0.10),(rr,0,zz),M['wood'])
            _orbit(o, rr, a0, turns, zz, bob=0.22)
            _spin(o, rng.choice([-2,-1,1,2]))          # gira em si tb
            ci+=1
    # cartas + petalas = leves, SUGADAS rapido (orbita + queda) em loop
    for k in range(20):
        a0=rng.uniform(0,2*math.pi); rr=rng.uniform(1.8,5.2); zz=rng.uniform(-3.5,2.6)
        c=box(f'Card{k}',(0.34,0.012,0.50),(rr,0,zz),M['card'],
              rot=(rng.uniform(0,3),rng.uniform(0,3),0))
        _orbit(c, rr, a0, rng.choice([2,3]), zz, bob=0.55)
    for k in range(16):
        a0=rng.uniform(0,2*math.pi); rr=rng.uniform(1.5,5.4); zz=rng.uniform(-4.0,2.8)
        p=box(f'Pet{k}',(0.16,0.02,0.09),(rr,0,zz),M['petal'],
              rot=(rng.uniform(0,3),rng.uniform(0,3),0))
        _orbit(p, rr, a0, 3, zz, bob=0.7)
    return f"floating(tornado) ok ({ci})"

def vortex_wind(M):
    """Funil de VENTO/POEIRA girando = a forma visivel do tornado. Streaks tangenciais
    + motes presos a um pivot central que ROTACIONA (loop) -> redemoinho continuo."""
    rng=_rng()
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,0,0))
    piv=bpy.context.active_object; piv.name='WindPivot'
    kids=[]
    for k in range(54):                                # streaks tangenciais (riscos de vento)
        z=rng.uniform(-6.0,3.0); t=(z+6.0)/9.0         # 0 fundo -> 1 topo
        r=(0.5+RMAX*0.98*t)*rng.uniform(0.92,1.07); a=rng.uniform(0,2*math.pi)
        x,y=r*math.cos(a), r*math.sin(a)
        s=box(f'Wind{k}',(0.035, rng.uniform(0.5,1.4), 0.035),(x,y,z),M['wind'],
              rot=(0,0,a+math.pi/2))                    # alongado na tangente (direcao do giro)
        kids.append(s)
    for k in range(46):                                # motes de poeira
        z=rng.uniform(-6.0,3.0); t=(z+6.0)/9.0
        r=(0.45+RMAX*0.92*t)*rng.uniform(0.8,1.1); a=rng.uniform(0,2*math.pi)
        m=sphere(f'Mote{k}', rng.uniform(0.02,0.05),(r*math.cos(a),r*math.sin(a),z),M['wind'],seg=6,ring=4)
        kids.append(m)
    for o in kids:
        o.parent=piv; o.matrix_parent_inverse=piv.matrix_world.inverted()
    # gira o pivot: 2 voltas no loop (continuo)
    piv.delta_rotation_euler[2]=0.0; piv.keyframe_insert('delta_rotation_euler',index=2,frame=1)
    piv.delta_rotation_euler[2]=2*2*math.pi; piv.keyframe_insert('delta_rotation_euler',index=2,frame=FEND)
    _loop(piv)
    return f"wind ok ({len(kids)})"

# ---------------- texturas procedurais (grime herdado do _pmat) ----------------
def vtex(M=None):
    M=M or vmats()
    I._pmat(M['dirt'],'stone', (0.12,0.10,0.08),(0.05,0.04,0.03),0.95,0.0, 5.0,0.5)
    I._pmat(M['rock'],'stone', (0.15,0.14,0.12),(0.06,0.055,0.05),0.92,0.0, 8.0,0.5)
    I._pmat(M['rock2'],'stone',(0.13,0.09,0.055),(0.055,0.035,0.022),0.93,0.0, 9.0,0.5)
    I._pmat(M['stone'],'stone',(0.085,0.075,0.063),(0.030,0.026,0.022),0.93,0.0,7.0,0.42)
    I._pmat(M['cface'],'ceramic',(0.58,0.55,0.48),(0.40,0.38,0.33),0.40,0.0,12.0,0.06)
    I._pmat(M['cmetal'],'metal',(0.45,0.34,0.14),(0.28,0.20,0.07),0.35,1.0,10.0,0.05)
    I._pmat(M['iron'],'metal', (0.10,0.095,0.095),(0.04,0.038,0.038),0.45,1.0,9.0,0.05)
    I._pmat(M['wood'],'wood',  (0.07,0.045,0.025),(0.03,0.02,0.01),0.70,0.0, 7.0,0.30)
    I._pmat(M['card'],'cloth', (0.55,0.52,0.48),(0.35,0.33,0.30),0.50,0.0,18.0,0.05)
    I._pmat(M['porc'],'ceramic',(0.50,0.48,0.44),(0.34,0.32,0.29),0.30,0.0,16.0,0.06)
    I._pmat(M['petal'],'cloth',(0.34,0.07,0.25),(0.18,0.03,0.13),0.60,0.0,12.0,0.10)
    # mirror/glow: SEM grime (reflexo/emissivo)
    return "vtex ok"

# ---------------- cameras ----------------
def cameras():
    a=_cam('Cam_Aerial',(0,0,26),(0,0,-3),40); a.data.type='ORTHO'; a.data.ortho_scale=21
    iso=_cam('Cam_Iso',(16,-16,15),(0,0,-3),35); iso.data.type='ORTHO'; iso.data.ortho_scale=23
    _cam('Cam_Edge',(0,-(HY/2-1.2),2.6),(0,0.5,-4.0),26)      # da entrada sul olhando p/ dentro do poco
    _cam('Cam_Estab',(-3.0,-(HY/2-1.0),1.7),(1.5,2.0,-1.5),24)
    return "cameras ok"

# ---------------- iluminacao base (VFX depois) ----------------
def lighting(M):
    sc=bpy.context.scene
    w=bpy.data.worlds.get('World') or bpy.data.worlds.new('World'); sc.world=w; w.use_nodes=True
    bg=w.node_tree.nodes.get('Background')
    if bg: bg.inputs[0].default_value=(0.012,0.014,0.022,1); bg.inputs[1].default_value=0.12
    bpy.ops.object.light_add(type='SUN', location=(0,6,14)); s=bpy.context.active_object
    s.name='L_Sky'; s.data.energy=1.4; s.data.color=(0.6,0.7,1.0); s.rotation_euler=(math.radians(120),0,0)
    return "lighting ok"

def build_all():
    purge(); M=vmats()
    build_hall(M); build_funnel(M); gears(M); chains(M); giant_clocks(M)
    tea_remains(M); debris(M); floating(M); vortex_wind(M); vtex(M); lighting(M); cameras()
    sc=bpy.context.scene; sc.frame_start=1; sc.frame_end=FEND
    look('Cam_Estab')
    return "VORTEX DONE"
