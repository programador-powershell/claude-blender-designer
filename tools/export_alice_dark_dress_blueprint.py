# -*- coding: utf-8 -*-
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'live'))
import garment_alice_dark_dress
bp = garment_alice_dark_dress.build_blueprint()
out = ROOT / 'examples' / 'alice_dark_dress_blueprint.json'
out.write_text(bp.to_json(), encoding='utf-8')
print(out)
