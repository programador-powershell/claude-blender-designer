# -*- coding: utf-8 -*-
from pathlib import Path
import shutil, sys
src = Path(__file__).resolve().parent
dst = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
for folder in ['live','tools','examples','docs','patches']:
    for p in (src/folder).rglob('*'):
        if p.is_file():
            rel = p.relative_to(src); out = dst/rel; out.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p,out); print('copied', rel)
for p in ['pipeline_garment_builder.py']:
    shutil.copy2(src/p, dst/p); print('copied', p)
print('OK: garment update instalado em', dst)
