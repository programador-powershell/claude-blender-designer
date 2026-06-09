"""Interior de Cha (Alice, cena4) — build manual AAA, peca por peca, dims EXATAS do storyboard.
Roda dentro do Blender via bridge. Namespace do bridge so da `bpy`; aqui importo o resto.

DIMS (cena4 bloqueio 3D, metros):
  Sala interna 8.0(X) x 6.0(Y) x 3.2(Z), parede esp 0.40
  Mesa longa 2.6 x 1.3, topo 0.75 | Cadeira 0.52x0.50, costa 1.20
  Janela 1.80 x 2.20, peitoril 0.70 (luz lua 4200K)
  Candelabro 1.20 alt | Bule-OLHO gigante O1.40 base, 1.05 alt, olho frio 4500K
  Faca 0.30 (arma inicial) | toalha manchada, porcelana suja, entulho, trepadeiras
Paleta: lua fria + vela quente 2000K, neblina 0.02-0.04, EV100~8, teal-orange, MUITO escuro.
"""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler

R = 4
def _rng():
    random.seed(R);
    return random

# ---------------- helpers ----------------
def purge():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras,
                 bpy.data.curves, bpy.data.images):
        for b in list(coll):
            if b.users == 0:
                try: coll.remove(b)
                except Exception: pass

def mat(name, color, rough=0.85, metal=0.0, emis=None, estr=0.0, alpha=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (color[0], color[1], color[2], 1.0)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if 'Alpha' in b.inputs: b.inputs['Alpha'].default_value = alpha
    if emis is not None:
        try:
            b.inputs['Emission Color'].default_value = (emis[0], emis[1], emis[2], 1.0)
            b.inputs['Emission Strength'].default_value = estr
        except Exception: pass
    if alpha < 1.0:
        m.blend_method = 'BLEND'
    return m

def setmat(o, m):
    o.data.materials.clear(); o.data.materials.append(m)

def box(name, dims, loc, m=None, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object; o.name = name
    o.scale = (dims[0], dims[1], dims[2])
    if rot: o.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=bool(rot), scale=True)
    if m: setmat(o, m)
    return o

def cyl(name, r, depth, loc, m=None, rot=None, verts=32):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, vertices=verts)
    o = bpy.context.active_object; o.name = name
    if rot: o.rotation_euler = rot; bpy.ops.object.transform_apply(rotation=True)
    if m: setmat(o, m)
    return o

def sphere(name, r, loc, m=None, seg=24, ring=12):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=ring)
    o = bpy.context.active_object; o.name = name
    if m: setmat(o, m)
    return o

def bevel(o, w=0.01, seg=2):
    md = o.modifiers.new('bev', 'BEVEL'); md.width = w; md.segments = seg
    md.limit_method = 'ANGLE'; md.angle_limit = math.radians(40)

def shade_smooth(o):
    for p in o.data.polygons: p.use_smooth = True

def join(objs, name):
    objs = [o for o in objs if o]
    if not objs: return None
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.active_object; o.name = name
    return o

def boolean(target, cutter, op='DIFFERENCE'):
    md = target.modifiers.new('bool', 'BOOLEAN'); md.operation = op
    md.object = cutter; md.solver = 'FLOAT'
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=md.name)
    bpy.data.objects.remove(cutter, do_unlink=True)

# ---------------- materials ----------------
def materials():
    return dict(
        stone   = mat('M_Stone',   (0.060,0.052,0.045), 0.92),
        floor   = mat('M_Floor',   (0.050,0.044,0.038), 0.90),
        wood    = mat('M_Wood',    (0.045,0.028,0.016), 0.62),
        wood_d  = mat('M_WoodDk',  (0.030,0.018,0.010), 0.70),
        cloth   = mat('M_Cloth',   (0.205,0.175,0.125), 0.95),
        stain   = mat('M_Stain',   (0.110,0.085,0.055), 0.95),
        porc    = mat('M_Porcelain',(0.46,0.44,0.40),  0.28),
        brass   = mat('M_Brass',   (0.45,0.32,0.12),   0.35, metal=1.0),
        steel   = mat('M_Steel',   (0.58,0.58,0.60),   0.20, metal=1.0),
        wax     = mat('M_Wax',     (0.82,0.76,0.62),   0.55),
        flame   = mat('M_Flame',   (1.0,0.55,0.18),    0.5, emis=(1.0,0.5,0.16), estr=10.0),
        glaze   = mat('M_Glaze',   (0.07,0.085,0.10),  0.30, metal=0.2),
        sclera  = mat('M_Sclera',  (0.66,0.64,0.58),   0.40, emis=(0.45,0.62,0.80), estr=0.06),
        iris    = mat('M_Iris',    (0.10,0.34,0.46),   0.28, emis=(0.34,0.74,0.98), estr=2.2),
        iris_dim= mat('M_IrisDim', (0.10,0.30,0.42),   0.30, emis=(0.30,0.62,0.85), estr=1.1),
        pupil   = mat('M_Pupil',   (0.01,0.01,0.01),   0.40),
        vine    = mat('M_Vine',    (0.040,0.075,0.030),0.80),
        rubble  = mat('M_Rubble',  (0.070,0.065,0.058),0.92),   # cinza
        rubble2 = mat('M_Rubble2', (0.090,0.060,0.038),0.93),   # marrom (tijolo/terra)
        rubble3 = mat('M_Rubble3', (0.052,0.058,0.044),0.92),   # cinza-musgo
        web     = mat('M_Web',     (0.55,0.55,0.58),   0.95, alpha=0.14),
        glass   = mat('M_Glass',   (0.05,0.06,0.08),   0.05, alpha=0.15),
    )

# ---------------- texturas procedurais ----------------
def _grime(nt, color, mp, scale):
    """Camada de ENCARDIDO: manchas escuras (noise grande) MULTIPLY + poeira nas faces
    pra cima (Geometry Normal Z, marrom-claro) MIX. Da o look 'abandonado/tomado pelo tempo'."""
    def _mix(blend):
        n=nt.nodes.new('ShaderNodeMix'); n.data_type='RGBA'; n.blend_type=blend
        return n   # inputs[0]=Factor, [6]=A(color), [7]=B(color); outputs[2]=Result(color)
    # 1) MANCHAS grandes escuras
    ns=nt.nodes.new('ShaderNodeTexNoise'); ns.location=(-260,-280)
    ns.inputs['Scale'].default_value=max(1.5, scale*0.4)
    try: ns.inputs['Detail'].default_value=6.0
    except Exception: pass
    nt.links.new(mp.outputs['Vector'], ns.inputs['Vector'])
    sr=nt.nodes.new('ShaderNodeValToRGB'); sr.location=(-80,-280)
    sr.color_ramp.elements[0].position=0.34; sr.color_ramp.elements[0].color=(0.16,0.12,0.09,1)
    sr.color_ramp.elements[1].position=0.72; sr.color_ramp.elements[1].color=(0.85,0.85,0.85,1)
    nt.links.new(ns.outputs['Fac'], sr.inputs['Fac'])
    m1=_mix('MULTIPLY'); m1.location=(120,-60); m1.inputs[0].default_value=0.9
    nt.links.new(color, m1.inputs[6]); nt.links.new(sr.outputs['Color'], m1.inputs[7])
    # 2) POEIRA nas faces pra cima (normal Z alto) modulada por noise
    geo=nt.nodes.new('ShaderNodeNewGeometry'); geo.location=(-440,-520)
    sep=nt.nodes.new('ShaderNodeSeparateXYZ'); sep.location=(-260,-520)
    nt.links.new(geo.outputs['Normal'], sep.inputs['Vector'])
    mr=nt.nodes.new('ShaderNodeMapRange'); mr.location=(-80,-520)
    mr.inputs['From Min'].default_value=0.45; mr.inputs['From Max'].default_value=0.95
    nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
    nd=nt.nodes.new('ShaderNodeTexNoise'); nd.location=(-260,-700)
    nd.inputs['Scale'].default_value=max(3.0, scale*0.9)
    nt.links.new(mp.outputs['Vector'], nd.inputs['Vector'])
    dm=nt.nodes.new('ShaderNodeMath'); dm.location=(120,-560); dm.operation='MULTIPLY'
    nt.links.new(mr.outputs['Result'], dm.inputs[0]); nt.links.new(nd.outputs['Fac'], dm.inputs[1])
    dscale=nt.nodes.new('ShaderNodeMath'); dscale.location=(300,-560); dscale.operation='MULTIPLY'
    nt.links.new(dm.outputs['Value'], dscale.inputs[0]); dscale.inputs[1].default_value=0.7
    m2=_mix('MIX'); m2.location=(480,-60)
    m2.inputs[7].default_value=(0.20,0.175,0.14,1)         # cor da poeira (marrom-cinza)
    nt.links.new(m1.outputs[2], m2.inputs[6]); nt.links.new(dscale.outputs['Value'], m2.inputs[0])
    return m2.outputs[2]

def _pmat(m, kind, c1, c2, rough, metal, scale, bump=0.25, grime=True):
    """Reconstroi o material com textura procedural: var de cor (ColorRamp) + bump. Coord Object."""
    m.use_nodes=True; nt=m.node_tree; nt.nodes.clear()
    out=nt.nodes.new('ShaderNodeOutputMaterial'); out.location=(700,0)
    b=nt.nodes.new('ShaderNodeBsdfPrincipled'); b.location=(380,0)
    nt.links.new(b.outputs[0], out.inputs['Surface'])
    b.inputs['Metallic'].default_value=metal; b.inputs['Roughness'].default_value=rough
    tc=nt.nodes.new('ShaderNodeTexCoord'); tc.location=(-1000,0)
    mp=nt.nodes.new('ShaderNodeMapping'); mp.location=(-820,0)
    sx=scale*0.22 if kind=='wood' else scale
    mp.inputs['Scale'].default_value=(sx,scale,scale)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    height=None
    if kind=='wood':
        w=nt.nodes.new('ShaderNodeTexWave'); w.location=(-560,80); w.wave_type='BANDS'
        try:
            w.inputs['Scale'].default_value=2.2; w.inputs['Distortion'].default_value=7.0
            w.inputs['Detail'].default_value=3.0
        except Exception: pass
        nt.links.new(mp.outputs['Vector'], w.inputs['Vector'])
        fac=w.outputs['Fac']; height=w.outputs['Fac']
    elif kind=='ceramic':
        v=nt.nodes.new('ShaderNodeTexVoronoi'); v.location=(-560,80)
        v.feature='DISTANCE_TO_EDGE'; v.inputs['Scale'].default_value=scale
        nt.links.new(mp.outputs['Vector'], v.inputs['Vector'])
        fac=v.outputs['Distance']; height=v.outputs['Distance']
    elif kind=='stone':
        v=nt.nodes.new('ShaderNodeTexVoronoi'); v.location=(-560,150); v.inputs['Scale'].default_value=scale
        nt.links.new(mp.outputs['Vector'], v.inputs['Vector'])
        n=nt.nodes.new('ShaderNodeTexNoise'); n.location=(-560,-120); n.inputs['Scale'].default_value=scale*2.0
        try: n.inputs['Detail'].default_value=8
        except Exception: pass
        nt.links.new(mp.outputs['Vector'], n.inputs['Vector'])
        fac=n.outputs['Fac']; height=v.outputs['Distance']
    else:                                   # cloth / metal / vine / generic
        n=nt.nodes.new('ShaderNodeTexNoise'); n.location=(-560,0); n.inputs['Scale'].default_value=scale
        try: n.inputs['Detail'].default_value=6
        except Exception: pass
        nt.links.new(mp.outputs['Vector'], n.inputs['Vector'])
        fac=n.outputs['Fac']; height=n.outputs['Fac']
    ramp=nt.nodes.new('ShaderNodeValToRGB'); ramp.location=(0,0)
    ramp.color_ramp.elements[0].color=(c1[0],c1[1],c1[2],1)
    ramp.color_ramp.elements[1].color=(c2[0],c2[1],c2[2],1)
    nt.links.new(fac, ramp.inputs['Fac'])
    colsock = ramp.outputs['Color']
    if grime:
        colsock = _grime(nt, colsock, mp, scale)
    nt.links.new(colsock, b.inputs['Base Color'])
    if bump>0 and height is not None:
        bp=nt.nodes.new('ShaderNodeBump'); bp.location=(120,-320); bp.inputs['Strength'].default_value=bump
        nt.links.new(height, bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m

def apply_textures(M=None):
    """Textura procedural em TUDO (pedra/madeira/tecido/porcelana/ceramica/metal/trepadeira)."""
    M=M or materials()
    _pmat(M['stone'],'stone', (0.090,0.080,0.068),(0.032,0.028,0.024),0.95,0.0, 7.0,0.40)
    _pmat(M['floor'],'stone', (0.080,0.072,0.060),(0.026,0.023,0.019),0.93,0.0, 5.0,0.45)
    _pmat(M['rubble'],'stone',(0.105,0.098,0.088),(0.042,0.038,0.032),0.95,0.0,12.0,0.55)
    _pmat(M['rubble2'],'stone',(0.130,0.085,0.052),(0.055,0.034,0.020),0.95,0.0,13.0,0.55)
    _pmat(M['rubble3'],'stone',(0.075,0.082,0.060),(0.030,0.036,0.026),0.95,0.0,14.0,0.55)
    _pmat(M['wood'],'wood',   (0.080,0.048,0.024),(0.032,0.018,0.009),0.60,0.0, 7.0,0.28)
    _pmat(M['wood_d'],'wood', (0.048,0.028,0.013),(0.020,0.011,0.006),0.70,0.0, 7.0,0.32)
    _pmat(M['cloth'],'cloth', (0.340,0.300,0.220),(0.225,0.185,0.125),0.95,0.0,32.0,0.15)
    _pmat(M['stain'],'cloth', (0.150,0.110,0.065),(0.070,0.050,0.030),0.95,0.0,26.0,0.18)
    _pmat(M['porc'],'ceramic',(0.640,0.615,0.560),(0.430,0.405,0.360),0.28,0.0,16.0,0.08)
    _pmat(M['glaze'],'ceramic',(0.095,0.115,0.135),(0.040,0.050,0.060),0.30,0.15,11.0,0.06)
    _pmat(M['wax'],'cloth',   (0.820,0.760,0.620),(0.700,0.640,0.500),0.55,0.0,12.0,0.05)
    _pmat(M['brass'],'metal', (0.520,0.380,0.150),(0.300,0.210,0.080),0.38,1.0,10.0,0.06)
    _pmat(M['steel'],'metal', (0.620,0.620,0.640),(0.450,0.450,0.480),0.22,1.0,14.0,0.05)
    _pmat(M['vine'],'cloth',  (0.055,0.105,0.038),(0.022,0.050,0.016),0.80,0.0, 9.0,0.20)
    return "textures ok"

# ---------------- shell ----------------
IX, IY, IZ = 9.50, 7.30, 4.20   # PLANTA OFICIAL cena4: interna 9.50(X) x 7.30(Y), teto 4.20
WT = 0.40                        # wall thickness (planta: parede 0.40)

def build_shell(M=None):
    M = M or materials()
    parts = []
    # floor + ceiling
    parts.append(box('Floor', (IX+2*WT, IY+2*WT, 0.30), (0,0,-0.15), M['floor']))
    parts.append(box('Ceiling', (IX+2*WT, IY+2*WT, 0.30), (0,0,IZ+0.15), M['stone']))
    # walls (centered on interior edge + outward)
    box('Wall_Xp', (WT, IY+2*WT, IZ), ( IX/2+WT/2, 0, IZ/2), M['stone'])
    box('Wall_Xn', (WT, IY+2*WT, IZ), (-IX/2-WT/2, 0, IZ/2), M['stone'])
    box('Wall_Yp', (IX+2*WT, WT, IZ), (0,  IY/2+WT/2, IZ/2), M['stone'])
    # -Y wall = entrada ARRUINADA: muro BAIXO quebrado, vao largo, sem lintel
    dgap = 2.2
    seg = (IX+2*WT - dgap)/2
    hf = 1.9
    box('Wall_Yn_L', (seg, WT, hf), (-(dgap/2+seg/2), -IY/2-WT/2, hf/2), M['stone'])
    box('Wall_Yn_R', (seg, WT, hf), ( (dgap/2+seg/2), -IY/2-WT/2, hf/2), M['stone'])
    # ceiling beams (vigas)
    for x in (-2.4, 0.0, 2.4):
        box(f'Beam_{x}', (0.22, IY+2*WT, 0.28), (x, 0, IZ-0.18), M['wood_d'])
    return "shell ok"

def cut_windows(M=None):
    """CAD: fileira de 3 janelas altas arqueadas na parede do FUNDO (+Y) + rosacea na ESQUERDA (-X).
    Janela 1.80x2.20, peitoril 0.70 (bloqueio 3D)."""
    M = M or materials()
    wl, wh, sill = 1.70, 2.95, 0.75          # altas+arco, teto 4.20; dominam parede do fundo
    rect_h = wh - 0.75                       # parte reta; resto = arco
    yb = IY/2 + WT/2                          # centro da parede do fundo (norte)
    wall = bpy.data.objects.get('Wall_Yp')
    for xx in (-2.8, 0.0, 2.8):              # 3 janelas arqueadas no fundo (parede 9.5m)
        cz = sill + rect_h/2
        cut = box('cut', (wl, WT*2, rect_h), (xx, yb, cz))
        arc = cyl('arc', wl/2, WT*2, (xx, yb, sill+rect_h), rot=(math.radians(90),0,0))
        arc.scale = (1, 1, 0.62); bpy.ops.object.transform_apply(scale=True)
        boolean(wall, arc); boolean(wall, cut)
        # peitoril + montantes (mullions verticais) + vidro
        box('WinSill', (wl+0.20, 0.20, 0.10), (xx, yb, sill-0.05), M['stone'])
        for mx in (xx-0.45, xx, xx+0.45):
            box('Mullion', (0.05, 0.16, rect_h+0.45), (mx, yb, sill+(rect_h+0.45)/2), M['wood_d'])
        box('WinGlass', (wl-0.02, 0.02, wh-0.05), (xx, yb, sill+(wh-0.05)/2), M['glass'])
    # rosacea (janela redonda) na parede ESQUERDA (-X), area do fundo, alta
    wallL = bpy.data.objects.get('Wall_Xn'); xl = -IX/2-WT/2
    ry, rz, rr = 1.4, 2.95, 0.55
    disc = cyl('rcut', rr, WT*2, (xl, ry, rz), rot=(0, math.radians(90), 0))
    boolean(wallL, disc)
    bpy.ops.mesh.primitive_torus_add(location=(xl,ry,rz), major_radius=rr, minor_radius=0.06,
                                     major_segments=24, minor_segments=8,
                                     rotation=(0, math.radians(90), 0))
    rg=bpy.context.active_object; rg.name='RoseRing'; setmat(rg, M['wood_d'])
    for ang in (0, 45, 90, 135):             # tracery (raios)
        box('rbar', (0.05, rr*2, 0.05), (xl, ry, rz),
            rot=(math.radians(ang), math.radians(90), 0), m=M['wood_d'])
    cyl('RoseGlass', rr-0.03, 0.02, (xl, ry, rz), M['glass'], rot=(0, math.radians(90), 0))
    return "windows ok"

# ---------------- ruina: topos quebrados + contrafortes ----------------
def build_ruin(M=None):
    """CAD: paredes arruinadas — topos irregulares/quebrados + pilastras verticais."""
    M = M or materials(); rng = _rng()
    for wn in ['Wall_Xp','Wall_Xn','Wall_Yp','Wall_Yn_L','Wall_Yn_R']:
        w = bpy.data.objects.get(wn)
        if not w: continue
        bb=[w.matrix_world @ Vector(c) for c in w.bound_box]
        xs=[v.x for v in bb]; ys=[v.y for v in bb]; zs=[v.z for v in bb]
        x0,x1,y0,y1,ztop=min(xs),max(xs),min(ys),max(ys),max(zs)
        long_x=(x1-x0)>(y1-y0)
        for i in range(rng.randint(4,7)):           # notches irregulares no topo
            d=rng.uniform(0.15,0.55); cz=ztop-d+1.0; nw=rng.uniform(0.25,0.7)
            if long_x:
                cut=box('notch',(nw,(y1-y0)+0.4,2.0),(rng.uniform(x0+0.3,x1-0.3),(y0+y1)/2,cz))
            else:
                cut=box('notch',((x1-x0)+0.4,nw,2.0),((x0+x1)/2,rng.uniform(y0+0.3,y1-0.3),cz))
            boolean(w,cut)
    # contrafortes/pilastras nas paredes laterais (face interna, alturas quebradas)
    for sx in (IX/2-0.09, -IX/2+0.09):
        for yy in (-2.1,-0.5,1.1,2.3):
            h=rng.uniform(2.2,3.0)
            box('Buttress',(0.18,0.30,h),(sx,yy,h/2),M['stone'])
    return "ruin ok"

def add_masonry(M=None):
    """Blocos de pedra INDIVIDUAIS escalonados (junta de argamassa) nas paredes laterais."""
    M = M or materials(); rng=_rng(); blocks=[]
    bh=0.40                                       # altura da fiada
    for sx,inward in ((IX/2,-0.05),(-IX/2,0.05)):
        xc=sx+inward
        r=0
        z=bh/2
        while z < IZ-0.05:
            off=(bh*0.55) if r%2 else 0.0         # escalonado
            y=-IY/2+0.1+off
            while y < IY/2-0.12:
                bw=rng.uniform(0.45,0.66)
                if y+bw > IY/2-0.1: bw=IY/2-0.1-y
                if bw < 0.18: break
                cyo=y+bw/2
                skip = (sx<0 and abs(cyo-1.4)<0.75 and abs(z-2.95)<0.75)  # poupa rosacea
                if not skip:
                    blocks.append(box('blk',(0.11, bw-0.05, bh-0.06),
                                  (xc+rng.uniform(-0.015,0.015), cyo, z+rng.uniform(-0.02,0.02)),
                                  M['stone']))
                y += bw
            z += bh; r += 1
    if blocks: join(blocks,'Masonry')
    return f"masonry {len(blocks)} blocks"

def crack_floor():
    """Piso RACHADO: trincas em ARVORE (ramificadas) + ladrilhos quebrados rebaixados."""
    fl=bpy.data.objects.get('Floor')
    if not fl: return "no floor"
    rng=_rng()
    def crack(x,y,ang,ln,depth=0.09):
        mx=x+math.cos(ang)*ln/2; my=y+math.sin(ang)*ln/2
        cut=box('crack',(ln,0.05,depth),(mx,my,0.0),rot=(0,0,ang)); boolean(fl,cut)
        return x+math.cos(ang)*ln, y+math.sin(ang)*ln
    for i in range(4):                            # 4 trincas-arvore
        x=rng.uniform(-2.4,2.4); y=rng.uniform(-2.0,2.0); ang=rng.uniform(0,2*math.pi)
        ex,ey=crack(x,y,ang,rng.uniform(1.6,3.0))
        for b in range(2):                        # ramos
            crack(ex,ey,ang+rng.uniform(-1.0,1.0), rng.uniform(0.7,1.6))
    for i in range(6):                            # ladrilhos quebrados (rebaixados)
        cx=rng.uniform(-3.2,3.2); cy=rng.uniform(-2.4,2.4)
        if abs(cx)<1.45 and abs(cy)<0.75: continue
        cut=box('tile',(rng.uniform(0.4,0.85),rng.uniform(0.4,0.85),0.08),
                (cx,cy,-0.035), rot=(0,0,rng.uniform(0,1.2))); boolean(fl,cut)
    return "floor cracked"

def collapse_ceiling(M=None):
    """Teto parcialmente DESABADO: buracos + vigas quebradas + viga caida no chao."""
    M = M or materials(); rng=_rng()
    ce=bpy.data.objects.get('Ceiling')
    if ce:
        for i in range(3):
            cut=cyl('hole', rng.uniform(0.5,1.0), 1.2,
                    (rng.uniform(-2.5,2.5), rng.uniform(-1.8,1.8), IZ+0.15)); boolean(ce,cut)
    for b in [o for o in bpy.data.objects if o.name.startswith('Beam')]:
        if rng.random()<0.5: b.scale.y=rng.uniform(0.4,0.7)   # viga quebrada
    box('FallenBeam',(0.22,3.2,0.28),(rng.uniform(-1.2,1.2),rng.uniform(-1.0,1.0),0.15),
        M['wood_d'], rot=(0,0,rng.uniform(0,math.pi)))
    return "ceiling collapsed"

# ---------------- mesa longa + toalha ----------------
TLEN, TWID, TH = 1.10, 2.40, 0.75   # PLANTA: mesa 1.10(X larg) x 2.40(Y comp, LONGA) x 0.75 alt

def build_table(M=None):
    M = M or materials()
    p = []
    p.append(box('Table_Top', (TLEN, TWID, 0.06), (0,0,TH-0.03), M['wood']))
    # aventais
    p.append(box('Table_ApX', (TLEN-0.2, 0.08, 0.12), (0,  TWID/2-0.08, TH-0.16), M['wood_d']))
    p.append(box('Table_ApX2',(TLEN-0.2, 0.08, 0.12), (0, -TWID/2+0.08, TH-0.16), M['wood_d']))
    # pernas
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(box('Leg', (0.10,0.10,TH-0.06),
                         (sx*(TLEN/2-0.12), sy*(TWID/2-0.12), (TH-0.06)/2), M['wood_d']))
    t = join(p, 'Mesa_Cha'); bevel(t, 0.008, 2)
    # toalha manchada: grid plano no topo, bordas dobram p/ baixo sobre as laterais
    cw, cd, hang = TLEN+0.40, TWID+0.40, 0.28   # passa 0.20 de cada lado (cadeira nao penetra)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=28, y_subdivisions=18, size=1,
                                    location=(0,0,TH+0.013))
    cl = bpy.context.active_object; cl.name = 'Toalha'
    cl.scale = (cw, cd, 1); bpy.ops.object.transform_apply(scale=True)
    me = cl.data; rng = _rng()
    ex, ey = TLEN/2, TWID/2          # bordas do tampo
    for v in me.vertices:
        ox = max(0.0, abs(v.co.x) - ex)
        oy = max(0.0, abs(v.co.y) - ey)
        over = max(ox, oy)
        if over > 0:                  # overhang -> dobra reto p/ baixo
            v.co.z -= min(hang, over/0.20 * hang)
            v.co.x *= 0.985; v.co.y *= 0.985   # leve recolhimento
        else:
            v.co.z += rng.uniform(-0.006, 0.004)  # ondulacao sutil no topo
    sol = cl.modifiers.new('sol','SOLIDIFY'); sol.thickness = 0.010
    bpy.ops.object.modifier_apply(modifier='sol')
    setmat(cl, M['cloth']); cl.data.materials.append(M['stain'])
    rng2 = _rng()                     # manchas em BLOBS (nodoas reais, nao xadrez)
    blobs = [(rng2.uniform(-TLEN/2,TLEN/2), rng2.uniform(-TWID/2,TWID/2),
              rng2.uniform(0.10,0.40)) for _ in range(7)]
    for poly in cl.data.polygons:
        c = poly.center
        for bx,by,br in blobs:
            if ((c.x-bx)**2+(c.y-by)**2)**0.5 < br*(0.55+0.5*rng2.random()):
                poly.material_index = 1; break
    shade_smooth(cl)
    return "table ok"

# ---------------- cadeiras ----------------
def _chair(name, loc, rotz, M):
    seatz = 0.50
    p = []
    p.append(box(name+'_seat', (0.46,0.44,0.05), (0,0,seatz), M['wood']))
    p.append(box(name+'_back', (0.46,0.05,0.62), (0,-0.20,seatz+0.34), M['wood']))
    for sx in (-1,1):
        for sy in (-1,1):
            p.append(box(name+'_leg', (0.05,0.05,seatz),
                         (sx*0.19, sy*0.18, seatz/2), M['wood_d']))
    # ripas da costa
    for zz in (0.12, 0.30, 0.48):
        p.append(box(name+'_slat',(0.40,0.03,0.05),(0,-0.20,seatz+zz), M['wood']))
    c = join(p, name); bevel(c, 0.006, 1)
    c.location = Vector(loc); c.rotation_euler = (0,0,rotz)
    return c

def build_chairs(M=None):
    M = M or materials()
    rng = _rng()
    placed = []
    sidex = TLEN/2 + 0.50                      # afastado: toalha pende 0.20 + meia-cadeira + folga
    for i, y in enumerate((-0.82, 0.0, 0.82)):
        placed.append(_chair(f'Chair_W{i}', (-sidex, y, 0),  math.radians(90+rng.uniform(-7,7)), M))
        placed.append(_chair(f'Chair_E{i}', ( sidex, y, 0), math.radians(-90+rng.uniform(-7,7)), M))
    endy = TWID/2 + 0.52                        # cabeceiras (±Y) = 8 cadeiras total
    placed.append(_chair('Chair_S', (0, -endy, 0), math.radians(rng.uniform(-7,7)), M))
    placed.append(_chair('Chair_N', (0,  endy, 0), math.pi+math.radians(rng.uniform(-7,7)), M))
    c = placed[2]; c.rotation_euler = (math.radians(85), 0, c.rotation_euler.z); c.location.z = 0.22
    return "chairs ok"

# ---------------- candelabro ----------------
def _candelabra(name, loc, M):
    p = []
    p.append(cyl(name+'_base', 0.12, 0.04, (0,0,0.02), M['brass']))
    p.append(cyl(name+'_stem', 0.025, 0.9, (0,0,0.47), M['brass']))
    # 3 bracos
    for a in range(3):
        ang = a*2*math.pi/3
        dx, dy = 0.18*math.cos(ang), 0.18*math.sin(ang)
        arm = cyl(name+f'_arm{a}', 0.015, 0.36, (dx/2,dy/2,0.62), M['brass'],
                  rot=(math.radians(70)*0 + 0, math.radians(55), ang))
        p.append(arm)
        # vela + chama na ponta
        p.append(cyl(name+f'_cup{a}', 0.03, 0.03, (dx,dy,0.80), M['brass']))
        wax = cyl(name+f'_wax{a}', 0.018, 0.12, (dx,dy,0.88), M['wax'])
        p.append(wax)
        fl = cyl(name+f'_flame{a}', 0.012, 0.06, (dx,dy,0.97), M['flame'])
        fl.scale = (1,1,1.4); p.append(fl)
    # vela central
    p.append(cyl(name+'_cwax', 0.02, 0.14, (0,0,0.99), M['wax']))
    p.append(cyl(name+'_cfl', 0.013, 0.07, (0,0,1.09), M['flame']))
    c = join(p, name); shade_smooth(c)
    c.location = Vector(loc)
    return c

def build_candelabra(M=None):
    M = M or materials()
    _candelabra('Cand_S', (0,-0.85,TH), M)   # fileira de candelabros descendo a mesa longa (Y)
    _candelabra('Cand_C', (0, 0.00,TH), M)
    _candelabra('Cand_N', (0, 0.85,TH), M)
    return "candelabra ok"

# ---------------- porcelana + faca ----------------
def _teacup(name, x, y, z, M, rng):
    cup = cyl(name, 0.044, 0.056, (x,y,z+0.028), M['porc'], verts=24); shade_smooth(cup)
    if rng.random() < 0.28:                                   # tombada (caos)
        cup.rotation_euler=(math.radians(82),0,rng.uniform(0,6)); cup.location.z=z+0.02
    else:
        sc=cyl(name+'_saucer', 0.07, 0.012, (x,y,z+0.006), M['porc'], verts=28); shade_smooth(sc)
    return cup

def _teapot(name, x, y, z, M, s=1.0):
    b=sphere(name, 0.11*s, (x,y,z+0.09*s), M['porc'], seg=28, ring=16); b.scale=(1,1,0.82); shade_smooth(b)
    sp=cyl(name+'_sp', 0.018*s, 0.16*s, (x-0.15*s,y,z+0.10*s), M['porc'], rot=(0,math.radians(68),0)); shade_smooth(sp)
    hh=cyl(name+'_h',  0.014*s, 0.13*s, (x+0.13*s,y,z+0.10*s), M['porc'], rot=(math.radians(40),0,0)); shade_smooth(hh)
    ld=sphere(name+'_lid', 0.05*s, (x,y,z+0.17*s), M['porc'], seg=20, ring=12); ld.scale=(1,1,0.5); shade_smooth(ld)
    return b

def build_props(M=None):
    """Mesa LOTADA (arte cena4) SEM sobreposicao: sistema de ocupacao (occ) reserva
    candelabros/faca/bules; pratos+xicaras+talheres so caem em ponto LIVRE.
    Mesa top X[-0.55,0.55] Y[-1.20,1.20]; candelabros em x=0."""
    M = M or materials(); rng = _rng()
    z = TH + 0.012; n = 0
    occ = []
    def free(x, y, r, pad=0.015):
        for ox, oy, orr in occ:
            if (x-ox)**2 + (y-oy)**2 < (r+orr+pad)**2: return False
        return True
    # RESERVAS (nao colocar prato em cima): candelabros (x=0), faca, bules
    for cy in (-0.85, 0.0, 0.85): occ.append((0.0, cy, 0.17))
    KX, KY = 0.16, -1.05; occ.append((KX, KY, 0.21))          # faca em ponto limpo (sul)
    teapots = [('TeapotA', -0.22, -0.32, 1.1), ('TeapotB', 0.21, 0.42, 0.9),
               ('TeapotC', -0.05, 0.98, 1.0)]
    for _nm, tx, ty, s in teapots: occ.append((tx, ty, 0.16*s))
    # pratos em 2 fileiras, SO onde livre
    for rowx in (-0.30, 0.30):
        yy = -1.02
        while yy <= 1.04:
            jx = rowx+rng.uniform(-0.03,0.03); jy = yy+rng.uniform(-0.04,0.04)
            r = rng.uniform(0.095,0.12)
            if free(jx, jy, r):
                pl=cyl(f'Plate{n}', r, 0.018, (jx,jy,z), M['porc'], verts=40); shade_smooth(pl)
                occ.append((jx,jy,r))
                if rng.random() < 0.35:                       # pilha
                    p2=cyl(f'Plate{n}b', r*0.9, 0.018, (jx,jy,z+0.022), M['porc'], verts=40); shade_smooth(p2)
                    if rng.random() < 0.4:
                        p3=cyl(f'Plate{n}c', r*0.82, 0.018, (jx,jy,z+0.044), M['porc'], verts=40); shade_smooth(p3)
                cxp = jx+rng.uniform(-0.09,0.09); cyp = jy+(0.13 if jy < 0.9 else -0.13)
                if free(cxp, cyp, 0.075):                     # xicara+pires se livre
                    _teacup(f'Cup{n}', cxp, cyp, z, M, rng); occ.append((cxp,cyp,0.075))
                n += 1
            yy += rng.uniform(0.30,0.36)
    for nm, tx, ty, s in teapots: _teapot(nm, tx, ty, z, M, s)
    c = 0                                                     # talheres so em ponto livre
    for i in range(18):
        x = rng.uniform(-0.42,0.42); y = rng.uniform(-1.05,1.05)
        if free(x, y, 0.06):
            box(f'Cutlery{c}', (0.013, rng.uniform(0.10,0.15), 0.006),
                (x, y, z+0.004), M['steel'], rot=(0,0,rng.uniform(0,math.pi)))
            occ.append((x,y,0.06)); c += 1
    build_knife(M, loc=(KX, KY, z+0.001), angle=14)
    return f"props ok ({n} pratos, {c} talheres)"

def build_knife(M=None, loc=(0.30,0.22,TH+0.013), angle=26):
    M=M or materials()
    # --- lamina afilada com ponta (bmesh) ---
    bm=bmesh.new(); L=0.20; hw=0.020; th=0.0045
    prof=[(0.0,-hw),(0.0,hw),(L*0.70,hw*0.85),(L,0.0),(L*0.70,-hw)]
    top=[bm.verts.new((x,y, th)) for x,y in prof]
    bot=[bm.verts.new((x,y,-th)) for x,y in prof]
    bm.faces.new(top); bm.faces.new(list(reversed(bot)))
    n=len(prof)
    for i in range(n):
        bm.faces.new((top[i],top[(i+1)%n],bot[(i+1)%n],bot[i]))
    me=bpy.data.meshes.new('Knife_blade_m'); bm.to_mesh(me); bm.free()
    blade=bpy.data.objects.new('Knife_blade',me); bpy.context.collection.objects.link(blade)
    setmat(blade,M['steel'])
    hd =box('Knife_handle',(0.095,0.026,0.024),(-0.055,0,0),M['wood_d'])
    bol=box('Knife_bolster',(0.018,0.030,0.028),(-0.004,0,0),M['steel'])
    r1 =sphere('riv1',0.006,(-0.045,0.013,0),M['steel'],seg=8,ring=4)
    r2 =sphere('riv2',0.006,(-0.075,0.013,0),M['steel'],seg=8,ring=4)
    knife=join([blade,hd,bol,r1,r2],'Faca_Cozinha'); bevel(knife,0.0015,1); shade_smooth(knife)
    knife.location=Vector(loc); knife.rotation_euler=(0,0,math.radians(angle))
    # glint quente que pega a lamina (especular de destaque)
    bpy.ops.object.light_add(type='POINT', location=(loc[0]+0.12,loc[1]-0.06,TH+0.30))
    g=bpy.context.active_object; g.name='L_Knife'
    g.data.energy=2.6; g.data.color=(1.0,0.85,0.6); g.data.shadow_soft_size=0.04
    return knife

# ---------------- BULE-OLHO GIGANTE (o que observa) ----------------
def _lid_cap(name, R, upper, M, ylim=0.84):
    """Pálpebra = CASCA do bule (raio R, centro na origem). Cap frontal (+Y), metade sup/inf.
    Concentrica com o bule -> fica RENTE a curvatura e desliza sobre a superficie."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=R, segments=44, ring_count=30, location=(0,0,0))
    o=bpy.context.active_object; o.name=name
    bm=bmesh.new(); bm.from_mesh(o.data)
    yl=R*ylim
    for v in list(bm.verts):
        keep=(v.co.y > yl) and (v.co.z > -0.02*R if upper else v.co.z < 0.02*R)
        if not keep: bm.verts.remove(v)
    bm.to_mesh(o.data); bm.free(); o.data.update()
    o.modifiers.new('s','SOLIDIFY').thickness=0.035
    setmat(o,M['glaze']); shade_smooth(o)
    return o

def build_eye_assembly(C, gaze, Rb, M, fend=96):
    """Olho INSET no bule + PALPEBRAS concentricas (rente). Pisca em loop. Local: gaze=+Y, up=+Z.
    C=centro do bule, Rb=raio do bule. Pivot das palpebras = C (=origem do empty)."""
    g=Vector(gaze).normalized()
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,0,0)); E=bpy.context.active_object; E.name='Eye_root'
    re=Rb*0.36
    ball=sphere('Eye_ball', re, (0, Rb*0.58, 0), M['sclera'], seg=40, ring=24); shade_smooth(ball)  # globo
    iris=sphere('Eye_iris', re*0.62,(0, Rb*0.58+re*0.86, 0), M['iris'], seg=32, ring=18); iris.scale=(1,0.22,1); shade_smooth(iris)
    pup =sphere('Eye_pupil', re*0.32,(0, Rb*0.58+re*0.95, 0), M['pupil'], seg=24, ring=14); pup.scale=(0.30,0.18,1.7); shade_smooth(pup)
    up=_lid_cap('Eye_lidU', Rb*1.01, True, M); lo=_lid_cap('Eye_lidL', Rb*1.01, False, M)  # concentricas c/ bule
    for o in (ball,iris,pup,up,lo): o.parent=E
    E.location=Vector(C); E.rotation_euler=g.to_track_quat('Y','Z').to_euler()
    OU=math.radians(62); OL=math.radians(-62)             # aberto desliza sobre o bule; 0=fechado(rente)
    keys=[(1,OU,OL),(40,OU,OL),(45,0.0,0.0),(50,OU,OL),(fend,OU,OL)]
    for f,ua,la in keys:
        up.rotation_euler=(ua,0,0); up.keyframe_insert('rotation_euler', frame=f)
        lo.rotation_euler=(la,0,0); lo.keyframe_insert('rotation_euler', frame=f)
    try:                                                  # loop ciclico (API varia por versao)
        for ob in (up,lo):
            act=ob.animation_data.action; fcs=getattr(act,'fcurves',None)
            if fcs is None:
                cb=act.layers[0].strips[0].channelbag(ob.animation_data.action_slot); fcs=cb.fcurves
            for fc in fcs: fc.modifiers.new('CYCLES')
    except Exception as e:
        print('cycles skip:', e)
    sc=bpy.context.scene; sc.frame_start=1; sc.frame_end=fend
    return E

def build_eye_teapot(M=None):
    M = M or materials()
    Sb=1.143; Rb=0.70*Sb                     # PLANTA: Ø1.60 -> Rb=0.80
    C=Vector((IX/2-0.95, 0.0, 0.95))         # bule-olho na parede DIREITA (+X) ao meio (label 02)
    g=(Vector((0,0,C.z))-C); g.z=0; g=g.normalized()      # olhar horizontal p/ centro da sala
    right=Vector((-g.y,g.x,0)).normalized()
    # corpo (achatado em Z) -> aplica scale -> cava SOQUETE na frente (boolean)
    body=sphere('ET_body', Rb, C, M['glaze'], seg=44, ring=28); body.scale=(1,1,0.80)
    bpy.ops.object.transform_apply(scale=True)
    sock=sphere('sock', Rb*0.42, C+g*Rb*0.98, None, seg=24, ring=16)
    boolean(body, sock)
    p=[body]
    lid=sphere('ET_lid', 0.34*Sb, C+Vector((0,0,Rb*0.78)), M['glaze'], seg=24, ring=12); lid.scale=(1,1,0.5); p.append(lid)
    p.append(cyl('ET_knob',0.06*Sb,0.10*Sb, C+Vector((0,0,Rb*0.95)), M['glaze']))
    p.append(cyl('ET_spout',0.10*Sb,0.7*Sb, C-g*Rb*0.9+Vector((0,0,Rb*0.1)), M['glaze'], rot=(0,math.radians(60),0)))
    bpy.ops.mesh.primitive_torus_add(location=C+right*Rb*0.95+Vector((0,0,Rb*0.05)),
                                     major_radius=0.28*Sb,minor_radius=0.05*Sb,
                                     major_segments=20,minor_segments=10,rotation=(math.radians(90),0,0))
    h=bpy.context.active_object; h.name='ET_handle'; setmat(h,M['glaze']); p.append(h)
    grp=join(p,'BuleOlho_GIGANTE'); shade_smooth(grp)
    build_eye_assembly(C, g, Rb, M)          # olho inset + palpebras rente
    bpy.ops.object.light_add(type='POINT', location=C+g*Rb*1.2+Vector((0,0,0.3)))
    L=bpy.context.active_object; L.name='L_Eye'; L.data.energy=6; L.data.color=(0.55,0.78,1.0)
    L.data.shadow_soft_size=0.2
    return "eye_teapot ok (inset+pisca)"

# ---------------- paredes com olhos ----------------
def _small_eye(name, pos, dir_, M, r=0.10):
    scl=sphere(name+'_s', r, pos, M['sclera'], seg=16, ring=10); scl.scale=(1,1,0.78)
    iris=sphere(name+'_i', r*0.58, pos+dir_*r*0.70, M['iris_dim'], seg=14, ring=8)
    pup=sphere(name+'_p', r*0.26, pos+dir_*r*0.92, M['pupil'])
    e=join([scl,iris,pup],name); shade_smooth(e); return e

def build_wall_eyes(M=None):
    """'PAREDES COM OLHOS' — olhos pequenos embutidos, olhar frio p/ a sala."""
    M=M or materials(); rng=_rng()
    spots=[ (Vector(( IX/2-0.04,  0.9, 2.35)), Vector((-1,-0.15,-0.25))),
            (Vector((-IX/2+0.04, -1.3, 1.55)), Vector(( 1, 0.30,-0.05))),
            (Vector(( 1.6,  IY/2-0.04, 2.55)), Vector((-0.2,-1,-0.35))),
            (Vector((-2.3,  IY/2-0.04, 1.15)), Vector(( 0.25,-1, 0.20))),
            (Vector(( IX/2-0.04, -2.0, 2.05)), Vector((-1, 0.25,-0.10))) ]
    for i,(p,d) in enumerate(spots):
        _small_eye(f'WallEye{i}', p, d.normalized(), M, r=rng.uniform(0.075,0.125))
    return "wall eyes ok"

# ---------------- entulho ANGULAR (rocha facetada, cor variada) ----------------
def _rock(name, loc, r, M, rng, mats, flat_sq=(0.45,0.95)):
    """Pedra/escombro ANGULAR: ico subdiv1 com verts deslocados (nao esfera lisa).
    Cor sorteada entre cinza/marrom/musgo (arte = escombro variado, nao bolha cinza)."""
    bpy.ops.mesh.primitive_ico_sphere_add(radius=r, subdivisions=2, location=loc)
    o=bpy.context.active_object; o.name=name; me=o.data
    for v in me.vertices:
        v.co += Vector((rng.uniform(-0.22,0.22),rng.uniform(-0.22,0.22),rng.uniform(-0.22,0.22)))*r
    o.scale=(rng.uniform(0.7,1.5),rng.uniform(0.7,1.4),rng.uniform(*flat_sq))
    o.rotation_euler=(rng.uniform(0,0.5),rng.uniform(0,0.5),rng.uniform(0,3.14))
    setmat(o, rng.choice(mats))               # flat shade (default) = facetas duras
    return o

# ---------------- teias de aranha ----------------
def _web_tri(name, p0, p1, p2, M, sag=0.12):
    """Membrana de teia triangular (p0=canto, p1/p2=bracos) com leve afundamento no meio."""
    bm=bmesh.new()
    v0=bm.verts.new(p0); v1=bm.verts.new(p1); v2=bm.verts.new(p2)
    mid=(Vector(p0)+Vector(p1)+Vector(p2))/3.0; mid.z-=sag
    vm=bm.verts.new(mid)
    bm.faces.new((v0,v1,vm)); bm.faces.new((v1,v2,vm)); bm.faces.new((v2,v0,vm))
    me=bpy.data.meshes.new(name+'_m'); bm.to_mesh(me); bm.free()
    o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o)
    setmat(o,M['web']); return o

def build_cobwebs(M=None):
    """Teias: cantos teto-parede, topo das janelas, e fios pendendo das vigas (arte: sala tomada)."""
    M=M or materials(); rng=_rng(); n=0
    hx,hy,hz=IX/2-0.05, IY/2-0.05, IZ-0.05
    s=1.05
    for sx in (-1,1):
        for sy in (-1,1):                      # 4 cantos teto-parede
            p0=(sx*hx, sy*hy, hz)
            _web_tri(f'Web_C{n}', p0, (sx*(hx-s), sy*hy, hz), (sx*hx, sy*(hy-s), hz), M, sag=0.22); n+=1
            # segunda teia descendo o canto vertical (parede-parede)
            _web_tri(f'Web_V{n}', p0, (sx*(hx-0.8), sy*hy, hz-0.9), (sx*hx, sy*(hy-0.8), hz-0.9), M, sag=0.15); n+=1
    yb=IY/2-0.02
    for xx in (-2.8,0.0,2.8):                   # topo das janelas do fundo
        _web_tri(f'Web_W{n}', (xx-0.85,yb,3.55), (xx+0.85,yb,3.55), (xx,yb,2.7), M, sag=0.10); n+=1
    # fios finos pendendo das vigas
    for i in range(7):
        x=rng.uniform(-3.5,3.5); y=rng.uniform(-2.6,2.6); ln=rng.uniform(0.5,1.3)
        cyl(f'WebStrand{i}', 0.004, ln, (x,y,IZ-0.2-ln/2), M['web'])
        n+=1
    return f"cobwebs ok ({n})"

# ---------------- decadencia: entulho, trepadeiras ----------------
def build_decay(M=None):
    """CAD arruinado: entulho denso nas paredes laterais + detritos no piso + trepadeiras fartas."""
    M = M or materials(); rng = _rng()
    RMATS = [M['rubble'], M['rubble2'], M['rubble3']]
    piles = []
    for sx in (-(IX/2-0.35), IX/2-0.35):       # pilhas grandes ao longo de -X e +X
        for cy in (-3.0,-1.5,0.0,1.5,3.0):
            piles.append((sx+rng.uniform(-0.22,0.22), cy))
    for cx in (-3.2,-1.1,1.1,3.2):           # junto ao fundo (sob janelas)
        piles.append((cx, IY/2-0.55))
    allrocks=[]
    for (cx,cy) in piles:
        for i in range(rng.randint(5,9)):
            r=rng.uniform(0.10,0.30)
            o=_rock('rub', (cx+rng.uniform(-0.45,0.45), cy+rng.uniform(-0.35,0.35), r*0.6),
                    r, M, rng, RMATS)
            allrocks.append(o)
    # detritos espalhados pelo piso (pedras/cacos), evita sobre a mesa
    for i in range(55):
        x=rng.uniform(-4.3,4.3); y=rng.uniform(-3.2,3.2)
        if abs(x)<0.75 and abs(y)<1.35: continue
        r=rng.uniform(0.04,0.15)
        o=_rock('debris', (x,y,r*0.5), r, M, rng, RMATS, flat_sq=(0.35,0.7))
        allrocks.append(o)
    # BANCOS de entulho subindo as paredes laterais (desmoronamento)
    for sx in (-(IX/2-0.5), IX/2-0.5):
        for cy in (-2.6,-1.1,0.4,2.0):
            for k in range(rng.randint(4,7)):
                r=rng.uniform(0.18,0.42); zz=rng.uniform(0.1,1.35)
                o=_rock('bank', (sx+rng.uniform(-0.30,0.20), cy+rng.uniform(-0.35,0.35), zz),
                        r, M, rng, RMATS, flat_sq=(0.6,1.0))
                allrocks.append(o)
    if allrocks: join(allrocks,'Entulho')
    # trepadeiras FARTAS sobre janelas do FUNDO + cantos
    yb = IY/2+WT/2-0.10
    for xx in (-2.8,0.0,2.8):
        for k in range(9):
            xo=xx+rng.uniform(-0.95,0.95)
            cyl('vine', rng.uniform(0.012,0.03), rng.uniform(1.2,2.8), (xo,yb,1.95),
                M['vine'], rot=(0, rng.uniform(-0.18,0.18), 0))
    for cx,cy in ((-IX/2+0.12,1.5),(-IX/2+0.12,-1.0),(IX/2-0.12,1.8)):  # trepa cantos
        for k in range(4):
            cyl('vine', rng.uniform(0.012,0.025), rng.uniform(1.4,2.6),
                (cx,cy+rng.uniform(-0.4,0.4),1.9), M['vine'], rot=(rng.uniform(-0.15,0.15),0,0))
    return "decay ok"

# ---------------- iluminacao ----------------
def build_lighting(M=None):
    sc = bpy.context.scene
    # mundo bem escuro
    w = bpy.data.worlds.get('World') or bpy.data.worlds.new('World')
    sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes.get('Background')
    if bg: bg.inputs[0].default_value=(0.010,0.013,0.020,1); bg.inputs[1].default_value=0.14
    # neblina volumetrica -> feixes de luz (lua/vela). EEVEE Next.
    nt=w.node_tree; out=nt.nodes.get('World Output')
    for n in list(nt.nodes):
        if n.type=='VOLUME_SCATTER': nt.nodes.remove(n)
    vs=nt.nodes.new('ShaderNodeVolumeScatter')
    vs.inputs['Density'].default_value=0.028
    vs.inputs['Color'].default_value=(0.55,0.68,0.92,1)
    if out: nt.links.new(vs.outputs['Volume'], out.inputs['Volume'])
    try:
        ev=sc.eevee
        if hasattr(ev,'volumetric_start'): ev.volumetric_start=0.1; ev.volumetric_end=20.0
        if hasattr(ev,'use_volumetric_shadows'): ev.use_volumetric_shadows=True
    except Exception: pass
    # luz da lua: SUN frio vindo do NORTE-alto pelas janelas do FUNDO
    bpy.ops.object.light_add(type='SUN', location=(0,8,7))
    s=bpy.context.active_object; s.name='L_Moon'
    s.data.energy=2.0; s.data.color=(0.72,0.80,1.0); s.data.angle=math.radians(2)
    s.rotation_euler=(math.radians(122), 0, 0)        # desce do +Y p/ -Y
    # area fill atras de cada janela do FUNDO (lua entrando)
    for xx in (-2.8,0.0,2.8):
        bpy.ops.object.light_add(type='AREA', location=(xx, IY/2+WT+0.3, 1.95))
        a=bpy.context.active_object; a.name='L_Win'
        a.data.shape='RECTANGLE'; a.data.size=1.5; a.data.size_y=2.4
        a.data.energy=90; a.data.color=(0.70,0.80,1.0)
        a.rotation_euler=(math.radians(-90),0,0)
    # rosacea esquerda
    bpy.ops.object.light_add(type='AREA', location=(-IX/2-WT-0.3, 1.4, 2.95))
    a=bpy.context.active_object; a.name='L_Rose'; a.data.size=1.1
    a.data.energy=45; a.data.color=(0.70,0.80,1.0); a.rotation_euler=(0,math.radians(-90),0)
    # velas: point quente em cada candelabro
    for cx in (-0.7,0.7):
        for dx,dy in ((0,0),(0.18,0),(-0.09,0.15),(-0.09,-0.15)):
            bpy.ops.object.light_add(type='POINT', location=(cx+dx,dy,TH+0.95))
            pl=bpy.context.active_object; pl.name='L_Candle'
            pl.data.energy=8; pl.data.color=(1.0,0.6,0.30); pl.data.shadow_soft_size=0.05
    return "lighting ok"

# ---------------- cameras ----------------
def _cam(name, loc, target, lens=35):
    bpy.ops.object.camera_add(location=loc)
    c=bpy.context.active_object; c.name=name; c.data.lens=lens
    d=(Vector(target)-Vector(loc)); c.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
    return c

def build_cameras():
    _cam('Cam_Estab', (-1.15,-3.05,1.40), (1.35,0.55,0.95), 20)  # hero cena4: mesa recua + olho a direita
    _cam('Cam_Eye',   (2.10,0.0,1.05), (IX/2-0.95,0.0,0.95), 50)  # frente do bule-olho (direita)
    _cam('Cam_Knife', (0.52,-1.58,1.02),(0.16,-1.05,0.78), 50)  # 04.2 faca (ponto limpo, sul da mesa)
    a=_cam('Cam_Aerial',(0,0,12),(0,0,0.5), 40); a.data.type='ORTHO'; a.data.ortho_scale=11.0
    iso=_cam('Cam_Iso',(7,-9,7),(0,0,0.5), 30); iso.data.type='ORTHO'; iso.data.ortho_scale=11.5
    return "cameras ok"

# ---------------- shot helper ----------------
def look(cam_name='Cam_Estab', rendered=True):
    sc=bpy.context.scene
    cam=bpy.data.objects.get(cam_name)
    if cam: sc.camera=cam
    # aerial/iso: esconde teto+vigas pra ver o layout (relevo = topo aberto)
    aerial = ('Aerial' in cam_name) or ('Iso' in cam_name)
    for o in bpy.data.objects:
        if o.name=='Ceiling' or o.name.startswith('Beam'):
            o.hide_viewport=aerial; o.hide_render=aerial
    # engine EEVEE
    for eng in ('BLENDER_EEVEE_NEXT','BLENDER_EEVEE'):
        try: sc.render.engine=eng; break
        except Exception: pass
    sc.render.resolution_x=1280; sc.render.resolution_y=800; sc.render.resolution_percentage=100
    # viewport -> camera + rendered
    for scr in bpy.data.screens:
        for ar in scr.areas:
            if ar.type=='VIEW_3D':
                sp=ar.spaces.active
                try: sp.region_3d.view_perspective='CAMERA'
                except Exception: pass
                try:
                    if rendered=='clay':
                        sp.shading.type='SOLID'; sp.shading.light='STUDIO'
                        sp.shading.color_type='SINGLE'; sp.shading.single_color=(0.62,0.62,0.62)
                        sp.shading.show_shadows=True; sp.shading.show_cavity=True
                    else:
                        sp.shading.type='RENDERED' if rendered else 'MATERIAL'
                except Exception: pass
                try: sp.overlay.show_overlays=False
                except Exception: pass
    return f"look {cam_name}"

# ---------------- dispatcher ----------------
def build_geometry():
    purge(); M=materials()
    build_shell(M); cut_windows(M); build_ruin(M); add_masonry(M); crack_floor()
    collapse_ceiling(M); build_table(M); build_chairs(M)
    return "GEOMETRY DONE"

def build_dressing():
    M=materials()
    build_candelabra(M); build_props(M); build_eye_teapot(M); build_wall_eyes(M); build_decay(M)
    build_cobwebs(M)
    return "DRESSING DONE"

def build_lights_cams():
    build_lighting(); build_cameras(); look('Cam_Estab')
    return "LIGHTS+CAMS DONE"
