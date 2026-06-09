# -*- coding: utf-8 -*-
"""Gemma diz ROUPA vs PESSOA por BOUNDING BOXES (VLM faz isso melhor que grid denso).
Rasteriza p/ grade -> seg_grid.npy (1=dress,2=skin,3=hair,4=hat). python gemma_segment.py [view]"""
import sys, os, json, re, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vision_ask as VA
from PIL import Image
ROWS, COLS = 48, 40
W_ = r"D:/Alice/tools/auto-rig-fix/work/loop"
view = sys.argv[1] if len(sys.argv) > 1 else "front"
src = f"{W_}/seg_{view}.png"
prompt = ("3D character, full body front view. Normalized coords 0..1, origin TOP-LEFT (x right, y down). "
  "Give TIGHT bounding boxes [x0,y0,x1,y1] for EACH separate item: "
  "DRESS (gown bodice+skirt; the box MUST STOP at the skirt hem ~mid-shin, do NOT cover feet), "
  "STOCKINGS (striped leg socks/meias visible below the skirt), BOOTS (the shoes/botas at the feet, bottom of image), "
  "GLOVES (gauntlets on forearms/hands), SKIN (face/neck; left bare arm; right bare arm), HAT, HAIR. "
  "All items are visible; legs and feet are at the BOTTOM of the image. Reply ONLY JSON: "
  '{"dress":[[..]],"stockings":[[..]],"boots":[[..]],"gloves":[[..]],"skin":[[..]],"hat":[[..]],"hair":[[..]]}')
IW, IH = Image.open(src).size
ans = VA.ask_multi([src], prompt, num_predict=500)
print("GEMMA_BOXES:", ans)
t = ans[ans.find("{"):ans.rfind("}")+1]
try:
    data = json.loads(t)
except Exception as e:
    print("parse fail", e); data = {}
grid = np.zeros((ROWS, COLS), dtype=np.int8)
def fill(boxes, val):
    for b in boxes or []:
        try: x0,y0,x1,y1 = [float(v) for v in b[:4]]
        except Exception: continue
        if max(x0,y0,x1,y1) > 1.5:        # gemma deu PIXELS -> normaliza
            x0/=IW; x1/=IW; y0/=IH; y1/=IH
        c0,c1 = sorted((int(x0*COLS), int(x1*COLS))); r0,r1 = sorted((int(y0*ROWS), int(y1*ROWS)))
        grid[max(0,r0):min(ROWS,r1+1), max(0,c0):min(COLS,c1+1)] = val
# ordem: dress base; peças específicas sobrescrevem onde estão; skin por último corta o que sobra exposto
fill(data.get("dress"), 1)
fill(data.get("hair"), 3); fill(data.get("hat"), 4)
fill(data.get("stockings"), 5); fill(data.get("boots"), 6); fill(data.get("gloves"), 7)
fill(data.get("skin"), 2)
np.save(f"{W_}/seg_grid.npy", grid)
LBL = {1:"dress",2:"skin",3:"hair",4:"hat",5:"meias",6:"botas",7:"luvas"}
print(" ".join(f"{n}={int((grid==v).sum())}" for v,n in LBL.items()))
