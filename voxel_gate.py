"""Gate volumetrico via charlies_voxel_octree (SVO mesh voxelization).

Voxeliza 2 STLs com mesma cell-size e compara a assinatura de edge-voxels
por nivel de octree (forma global -> detalhe fino). Desvio <15% nos niveis
grossos (>=4) = forma global compativel.

Uso: python voxel_gate.py a.stl b.stl [cell_size]
Requer: D:/charlies_voxel_octree/voxelize_stl.exe (MSYS2 ucrt64 runtime).
"""
import subprocess, sys, re

VOX = r'D:/charlies_voxel_octree'
MSYS = r'C:/msys64/usr/bin/bash.exe'

def voxelize(stl, cell=0.012):
    cmd = (f"export PATH=/ucrt64/bin:$PATH; cd {VOX}; "
           f"./voxelize_stl.exe '{stl}' -o _gate_tmp --cell-size {cell} --cpu 2>&1")
    r = subprocess.run([MSYS, '-lc', cmd], capture_output=True, text=True, timeout=1800)
    levels = {}
    for m in re.finditer(r'Edge voxels at level (\d+): (\d+)', r.stdout):
        levels[int(m.group(1))] = int(m.group(2))
    return levels

def gate(stl_a, stl_b, cell=0.012, coarse_tol=0.15):
    la = voxelize(stl_a, cell)
    lb = voxelize(stl_b, cell)
    print(f'{"nivel":<7}{"A":>10}{"B":>10}{"razao":>8}  zona')
    ok = True
    for lv in sorted(set(la) | set(lb), reverse=True):
        a, b = la.get(lv, 0), lb.get(lv, 0)
        ratio = a / b if b else float('inf')
        zona = 'forma global' if lv >= 4 else 'detalhe fino'
        flag = ''
        if lv >= 4 and abs(ratio - 1) > coarse_tol:
            flag = ' <<< DIVERGE'
            ok = False
        print(f'{lv:<7}{a:>10}{b:>10}{ratio:>8.2f}  {zona}{flag}')
    print('GATE:', 'PASS (forma global compativel)' if ok else 'FAIL')
    return ok

if __name__ == '__main__':
    a, b = sys.argv[1], sys.argv[2]
    cell = float(sys.argv[3]) if len(sys.argv) > 3 else 0.012
    gate(a, b, cell)
