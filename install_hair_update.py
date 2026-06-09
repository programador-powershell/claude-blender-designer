#!/usr/bin/env python3
from pathlib import Path
import shutil, sys

ROOT = Path(__file__).resolve().parent

def copy_tree(src: Path, dst: Path):
    for p in src.rglob("*"):
        if p.is_dir() or "__pycache__" in p.parts:
            continue
        rel = p.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)

def main():
    if len(sys.argv) < 2:
        print("Uso: python install_hair_update.py <PASTA_DO_CLAUDE_BLENDER_DESIGNER>")
        raise SystemExit(1)
    dst = Path(sys.argv[1])
    if not dst.exists():
        raise SystemExit(f"Pasta não encontrada: {dst}")
    copy_tree(ROOT, dst)
    print(f"Atualização Hair + Garment instalada em: {dst}")

if __name__ == "__main__":
    main()
