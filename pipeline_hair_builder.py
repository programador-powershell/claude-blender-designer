#!/usr/bin/env python3
"""
Project Alice — Hair Builder Pipeline

Gera ou aplica blueprint de cabelo no Blender via bridge_cmd.py.

Exemplos:
    python pipeline_hair_builder.py --preset alice --save examples/alice_liddell_hair_blueprint.json
    python pipeline_hair_builder.py --blueprint examples/alice_liddell_hair_blueprint.json --build
    python pipeline_hair_builder.py --blueprint examples/alice_liddell_hair_blueprint.json --build --shot
"""
from __future__ import annotations

import argparse, json, subprocess, sys
from pathlib import Path


def save_preset_alice(path: Path):
    sys.path.insert(0, str(Path(__file__).parent / "live"))
    from hair_alice_liddell import make_alice_liddell_hair
    bp = make_alice_liddell_hair()
    path.parent.mkdir(parents=True, exist_ok=True)
    bp.save(str(path))
    print(f"[hair] blueprint salvo: {path}")


def run_in_blender(blueprint: Path, shot: bool):
    code = f"""
import sys, importlib
sys.path.insert(0, r'{str((Path(__file__).parent / "live").resolve())}')
import hair_card_builder
importlib.reload(hair_card_builder)
print(hair_card_builder.build_hair_from_file(r'{str(blueprint.resolve())}'))
print(hair_card_builder.add_secondary_motion_rig())
"""
    bridge = Path(__file__).parent / "bridge_cmd.py"
    args = [sys.executable, str(bridge), code]
    if shot:
        args.insert(2, "--shot")
    subprocess.check_call(args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", choices=["alice"], help="gera blueprint preset")
    ap.add_argument("--save", default="examples/alice_liddell_hair_blueprint.json")
    ap.add_argument("--blueprint", default="examples/alice_liddell_hair_blueprint.json")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--shot", action="store_true")
    args = ap.parse_args()

    if args.preset == "alice":
        save_preset_alice(Path(args.save))
    if args.build:
        run_in_blender(Path(args.blueprint), args.shot)


if __name__ == "__main__":
    main()
