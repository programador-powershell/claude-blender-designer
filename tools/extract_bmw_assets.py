# -*- coding: utf-8 -*-
"""Extract Black Myth Wukong UE5 assets pra reference library Qwen.
Requer FModel (https://fmodel.app) ou umodel + AES key BMW.

Setup (manual usuario):
  1. Baixar FModel https://github.com/4sval/FModel/releases
  2. Settings: Directory = D:/SteamLibrary/steamapps/common/BlackMythWukong/b1/Content/Paks
  3. AES key BMW publica: pesquisar comunidade modding
  4. Export: Textures (.png), Skeletal Meshes (.fbx)
  5. Output dir: D:/Alice/tools/auto-rig-fix/refs/bmw/

Apos extract, este script indexa:
  - characters/  (Sun Wukong, bosses, NPCs)
  - clothing/    (capes, armors, robes)
  - materials/   (PBR textures: albedo+normal+roughness)
  - hair/        (hair cards examples)
"""
import os, sys, json, glob

BMW_ROOT = r"D:/SteamLibrary/steamapps/common/BlackMythWukong"
REFS_DIR = r"D:/Alice/tools/auto-rig-fix/refs/bmw"
INDEX = os.path.join(REFS_DIR, "_index.json")

CATEGORIES = {
    "characters":   ["*hero*", "*wukong*", "*boss*", "*npc*", "Character*"],
    "clothing":     ["*cloth*", "*robe*", "*armor*", "*cape*", "*outfit*"],
    "materials":    ["*Mat*", "*MI_*", "*T_*alb*", "*T_*nrm*", "*T_*rgh*"],
    "hair":         ["*hair*", "*Hair*", "*hairc*"],
    "weapons":      ["*weapon*", "*staff*", "*sword*", "*spear*"],
    "environments": ["*landscape*", "*environment*", "*temple*"],
}

def scan():
    os.makedirs(REFS_DIR, exist_ok=True)
    idx = {"_doc":"BMW UE5 refs extraidos via FModel/umodel",
           "_source": BMW_ROOT, "_categories": {}}
    if not os.path.exists(REFS_DIR):
        print(f"REFS_DIR vazio: {REFS_DIR}")
        print(f"Rode FModel primeiro pra extrair de {BMW_ROOT}/b1/Content/Paks")
        return idx
    for cat, patterns in CATEGORIES.items():
        files = []
        for pat in patterns:
            files += glob.glob(os.path.join(REFS_DIR, cat, '**', pat), recursive=True)
        idx["_categories"][cat] = sorted(set(files))
        print(f"{cat}: {len(idx['_categories'][cat])} arquivos")
    json.dump(idx, open(INDEX,'w',encoding='utf-8'), indent=2, ensure_ascii=False)
    print(f"INDEX: {INDEX}")
    return idx

if __name__ == '__main__':
    scan()
