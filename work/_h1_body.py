import bpy, math, json

# ===== CENA NOVA ZERO ABSOLUTO =====
bpy.ops.wm.save_as_mainfile(filepath=r'D:\Alice\tools\auto-rig-fix\work\alice_HUMAN.blend')
for o in list(bpy.data.objects):
    if o.type not in ('CAMERA', 'LIGHT'):
        bpy.data.objects.remove(o, do_unlink=True)
for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.images):
    for d in list(coll):
        if d.users == 0:
            coll.remove(d)

prof = json.load(open(r'D:\Alice\tools\auto-rig-fix\work\alice_profile_v2.json'))
H = 1.70
def z_of(t): return H * (1.0 - t)

def torso_hw(t):
    """half-width do torso pelo perfil real; faixa contaminada por bracos (0.17-0.27) suavizada."""
    pts = [(r['t'], r['torso_hw']) for r in prof if r.get('torso_hw')]
    if t <= 0.17 or t >= 0.27:
        best = min(pts, key=lambda p: abs(p[0]-t))
        # interp linear entre vizinhos
        lo = max((p for p in pts if p[0] <= t), key=lambda p: p[0], default=best)
        hi = min((p for p in pts if p[0] >= t), key=lambda p: p[0], default=best)
        if lo[0] == hi[0]: return lo[1]
        f = (t - lo[0]) / (hi[0] - lo[0])
        return lo[1] + f * (hi[1] - lo[1])
    # zona contaminada: blend ombro(0.17)->busto(0.27)
    a = torso_hw(0.169)
    b = torso_hw(0.271)
    f = (t - 0.17) / 0.10
    # ombros largos: pico suave no inicio
    shoulder_boost = 0.022 * math.exp(-((t - 0.185) / 0.025) ** 2)
    return a + f * (b - a) + shoulder_boost

def leg_data(t):
    pts = [(r['t'], r['leg_hw'], r['leg_cx']) for r in prof if r.get('leg_hw') and r['t'] > 0.50]
    best = min(pts, key=lambda p: abs(p[0]-t))
    lo = max((p for p in pts if p[0] <= t), key=lambda p: p[0], default=best)
    hi = min((p for p in pts if p[0] >= t), key=lambda p: p[0], default=best)
    if lo[0] == hi[0]: return lo[1], lo[2]
    f = (t - lo[0]) / (hi[0] - lo[0])
    return lo[1] + f*(hi[1]-lo[1]), lo[2] + f*(hi[2]-lo[2])

verts = []
faces = []

def ring(idx_base, n):
    fs = []
    for i in range(n):
        j = (i + 1) % n
        fs.append((idx_base + i, idx_base + j, idx_base + n + j, idx_base + n + i))
    return fs

# ===== TORSO+CABECA+PESCOCO: tubo continuo 84 aneis x 32 (t 0.005 -> 0.495) =====
NSEG = 32
NRING = 84
ratio_y = [  # (t, ry/rx) razao profundidade/largura por regiao anatomica
    (0.005, 0.95), (0.06, 1.12), (0.10, 1.05),  # cranio: mais fundo que largo
    (0.135, 0.85), (0.155, 0.80),               # pescoco
    (0.19, 0.62), (0.24, 0.72),                 # ombros/peito alto: achatado
    (0.28, 0.80), (0.32, 0.76),                 # busto/cintura
    (0.40, 0.82), (0.46, 0.95), (0.495, 0.98),  # quadril: fundo (gluteo)
]
def ry_ratio(t):
    lo = max((p for p in ratio_y if p[0] <= t), default=ratio_y[0])
    hi = min((p for p in ratio_y if p[0] >= t), default=ratio_y[-1])
    if lo[0] == hi[0]: return lo[1]
    f = (t - lo[0]) / (hi[0] - lo[0])
    return lo[1] + f * (hi[1] - lo[1])

base = 0
for k in range(NRING):
    t = 0.005 + (0.495 - 0.005) * k / (NRING - 1)
    z = z_of(t)
    rx = torso_hw(t) * H
    ry = rx * ry_ratio(t)
    # centro y: cabeca pra frente leve, gluteo puxa centro pra tras
    cy = 0.0
    if t < 0.13: cy = -0.012  # cabeca
    if t > 0.42: cy = 0.012   # pelvis
    for i in range(NSEG):
        a = 2 * math.pi * i / NSEG
        x = rx * math.sin(a)
        y = cy - ry * math.cos(a)  # a=0 -> frente (-y)
        # PEITO: 2 lobos gaussianos frente (t 0.245-0.315)
        if -math.pi/2 < a < math.pi/2:
            lobe = math.exp(-((t - 0.275) / 0.030) ** 2)
            side = math.exp(-((abs(x) - rx * 0.42) / (rx * 0.30)) ** 2)
            y -= 0.030 * lobe * side * math.cos(a)
        # GLUTEO: protrusao posterior (t 0.44-0.50)
        if abs(a) > math.pi * 0.55:
            gl = math.exp(-((t - 0.475) / 0.030) ** 2)
            gs = math.exp(-((abs(x) - rx * 0.45) / (rx * 0.35)) ** 2)
            y += 0.030 * gl * gs
        # BARRIGA leve (t 0.36-0.42 frente)
        if -math.pi/3 < a < math.pi/3:
            y -= 0.006 * math.exp(-((t - 0.39) / 0.025) ** 2)
        verts.append((x, y, z))
for k in range(NRING - 1):
    faces += ring(base + k * NSEG, NSEG)
# tampar topo da cabeca
top_c = len(verts)
verts.append((0, -0.012, z_of(0.005) + 0.012))
for i in range(NSEG):
    faces.append((base + i, base + (i + 1) % NSEG, top_c))

# ===== PERNAS: 2 tubos 48 aneis x 20 (t 0.49 -> 0.985) perfil real =====
NL = 20
for g in (1, -1):
    lb = len(verts)
    for k in range(48):
        t = 0.49 + (0.985 - 0.49) * k / 47
        z = z_of(t)
        hw, cx = leg_data(max(t, 0.505))
        r = hw * H
        cxx = g * cx * H
        # coxa interna mais cheia / panturrilha posterior
        for i in range(NL):
            a = 2 * math.pi * i / NL
            rr = r
            x = cxx + rr * math.sin(a)
            y = -rr * 0.95 * math.cos(a)
            # panturrilha: bulge posterior t 0.66-0.78
            if abs(a) > math.pi * 0.5:
                y += 0.012 * math.exp(-((t - 0.72) / 0.035) ** 2)
            # coxa frontal cheia t 0.52-0.62
            else:
                y -= 0.008 * math.exp(-((t - 0.56) / 0.04) ** 2)
            verts.append((x, y, z))
    for k in range(47):
        faces += ring(lb + k * NL, NL)
    # PE: caixa do tornozelo pra frente
    fb = len(verts)
    ank_z = z_of(0.985)
    hw, cx = leg_data(0.95)
    cxx = g * cx * H
    fw = 0.042
    for (dy, dz) in [(0.05, ank_z), (-0.045, ank_z), (-0.125, 0.030), (-0.135, 0.012), (0.05, 0.010)]:
        for sx in (-1, 1):
            verts.append((cxx + sx * fw, dy, dz))
    # faces do pe (strip simples)
    for q in range(4):
        i0 = fb + q * 2
        faces.append((i0, i0 + 1, i0 + 3, i0 + 2))
    # sola
    faces.append((fb, fb + 2, fb + 4, fb + 6))

# ===== BRACOS: 2 tubos A-pose 20graus, 36 aneis x 14 =====
NA = 14
arm_prof = [(0.0, 0.052), (0.12, 0.047), (0.30, 0.040), (0.48, 0.034),
            (0.52, 0.036), (0.70, 0.030), (0.88, 0.0235), (1.0, 0.022)]
def arm_r(s):
    lo = max((p for p in arm_prof if p[0] <= s), default=arm_prof[0])
    hi = min((p for p in arm_prof if p[0] >= s), default=arm_prof[-1])
    if lo[0] == hi[0]: return lo[1]
    f = (s - lo[0]) / (hi[0] - lo[0])
    return lo[1] + f * (hi[1] - lo[1])
SHO = (0.155, 0.005, 1.405)
WRI_OFF = (0.345, 0.012, -0.125)  # A-pose ~20 graus
for g in (1, -1):
    ab = len(verts)
    for k in range(36):
        s = k / 35
        cx = g * (SHO[0] + WRI_OFF[0] * s)
        cy = SHO[1] + WRI_OFF[1] * s
        cz = SHO[2] + WRI_OFF[2] * s
        r = arm_r(s)
        for i in range(NA):
            a = 2 * math.pi * i / NA
            verts.append((cx, cy + r * math.cos(a), cz + r * math.sin(a)))
    for k in range(35):
        faces += ring(ab + k * NA, NA)
    # MAO: palma + 5 dedos simples
    hb = len(verts)
    px = g * (SHO[0] + WRI_OFF[0])
    pz = SHO[2] + WRI_OFF[2]
    # palma: caixa achatada
    for (du, dv) in [(0, 0), (0.075, -0.012)]:
        for (sy, sz) in [(-0.012, 0.038), (0.012, 0.038), (0.012, -0.038), (-0.012, -0.038)]:
            verts.append((px + g * du, SHO[1] + WRI_OFF[1] + sy, pz + sz * 0.9 + dv))
    for q in range(4):
        faces.append((hb + q, hb + (q + 1) % 4, hb + 4 + (q + 1) % 4, hb + 4 + q))

me = bpy.data.meshes.new('HumanBody_Me')
me.from_pydata(verts, [], faces)
me.update()
body = bpy.data.objects.new('HumanBody', me)
bpy.context.scene.collection.objects.link(body)
skin = bpy.data.materials.new('MAT_HSkin')
skin.use_nodes = True
b = skin.node_tree.nodes.get('Principled BSDF')
b.inputs['Base Color'].default_value = (0.78, 0.65, 0.59, 1)
b.inputs['Roughness'].default_value = 0.48
try:
    b.inputs['Subsurface Weight'].default_value = 0.10
except KeyError:
    pass
body.data.materials.append(skin)
bpy.context.view_layer.objects.active = body
for o in bpy.data.objects: o.select_set(False)
body.select_set(True)
bpy.ops.object.shade_smooth()
sub = body.modifiers.new('Subd', 'SUBSURF')
sub.levels = 1
sub.render_levels = 2
bpy.ops.wm.save_mainfile()
print('HUMAN BODY v1:', len(verts), 'verts construidos do zero')
