# -*- coding: utf-8 -*-
"""Pipeline garment builder via bridge_cmd.

Modos:
  # blueprint completo de uma vez
  python pipeline_garment_builder.py --blueprint examples/alice_chapeleiro_blueprint.json \
      --character Alice_Base_Body --outfit Alice_Chapeleiro --validate-render

  # chapeleiro preset direto (le manifest 22 pecas)
  python pipeline_garment_builder.py --chapeleiro --character Alice_Base_Body

  # listar peca por peca (build_order)
  python pipeline_garment_builder.py --chapeleiro --list-pieces

  # construir UMA peca apenas (workflow piece-by-piece + snapshot apos cada)
  python pipeline_garment_builder.py --chapeleiro --piece bloomer_interno --character Alice_Base_Body

  # remover uma peca (rollback antes de reconstruir)
  python pipeline_garment_builder.py --chapeleiro --remove-piece bloomer_interno
"""
import argparse, os, subprocess, sys, tempfile
BRIDGE_CMD = os.environ.get('BRIDGE_CMD', r'D:/Alice/tools/auto-rig-fix/bridge_cmd.py')
LIVE_DIR   = os.environ.get('LIVE_DIR',   r'D:/Alice/tools/auto-rig-fix/live')

def run_bridge(script):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script); p=f.name
    try:
        r=subprocess.run([sys.executable, BRIDGE_CMD, '--file', p], text=True, capture_output=True, timeout=900)
        sys.stdout.write(r.stdout)
        if r.returncode != 0:
            sys.stderr.write(r.stderr); raise SystemExit(r.returncode)
    finally:
        try: os.unlink(p)
        except Exception: pass

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--blueprint', default=None, help='caminho JSON blueprint (alt: --chapeleiro)')
    ap.add_argument('--chapeleiro', action='store_true', help='usa preset Alice Chapeleiro 22 pecas')
    ap.add_argument('--character', default='Alice_Base_Body')
    ap.add_argument('--outfit', default='Alice_Chapeleiro')
    ap.add_argument('--piece', default=None, help='build apenas esta peca (piece_id ou accessory_id)')
    ap.add_argument('--remove-piece', default=None, help='remove objetos PA_<id>*')
    ap.add_argument('--list-pieces', action='store_true', help='lista build_order do blueprint')
    ap.add_argument('--validate-render', action='store_true')
    args=ap.parse_args()

    # Carrega blueprint: prioridade --blueprint, depois --chapeleiro
    if args.chapeleiro:
        bp_load = "import garment_alice_chapeleiro\nbp = garment_alice_chapeleiro.build_blueprint()\n"
    elif args.blueprint:
        bp_path=os.path.abspath(args.blueprint)
        bp_load = f"bp = garment_schema.load_blueprint(r'{bp_path}')\n"
    else:
        ap.error('precisa de --blueprint <path> ou --chapeleiro')

    header = f"""
import sys, importlib
sys.path.insert(0, r'{LIVE_DIR}')
import garment_schema, garment_builder, garment_fit_to_body, garment_alice_chapeleiro
importlib.reload(garment_schema); importlib.reload(garment_builder)
importlib.reload(garment_fit_to_body); importlib.reload(garment_alice_chapeleiro)
{bp_load}
"""

    if args.list_pieces:
        body = """
rows = garment_builder.list_pieces_in_order(bp)
print('BUILD ORDER:')
for kind, pid, layer, shape in rows:
    print(f'  [{layer:02d}] {kind:9s} {pid:36s} {shape}')
"""
        run_bridge(header + body); return

    if args.remove_piece:
        body = f"print('REMOVED:', garment_builder.remove_piece('{args.remove_piece}'))\n"
        run_bridge(header + body); return

    if args.piece:
        body = f"""
print('COLLISION:', garment_fit_to_body.add_collision_to_body(r'{args.character}'))
print('SINGLE:', garment_builder.build_single_piece(bp, '{args.piece}', character_name=r'{args.character}', collection_name=r'{args.outfit}'))
print('PIN:', garment_fit_to_body.pin_all_garment_tops())
"""
        if args.validate_render:
            body += "\nimport garment_validation_render; importlib.reload(garment_validation_render)\nprint('VALIDATION:', garment_validation_render.render_validation_set())\n"
        run_bridge(header + body); return

    # full build
    body = f"""
print('COLLISION:', garment_fit_to_body.add_collision_to_body(r'{args.character}'))
print('BUILD:', garment_builder.build_garment_from_blueprint(bp, character_name=r'{args.character}', collection_name=r'{args.outfit}'))
print('PIN:', garment_fit_to_body.pin_all_garment_tops())
"""
    if args.validate_render:
        body += "\nimport garment_validation_render; importlib.reload(garment_validation_render)\nprint('VALIDATION:', garment_validation_render.render_validation_set())\n"
    run_bridge(header + body)

if __name__ == '__main__': main()
