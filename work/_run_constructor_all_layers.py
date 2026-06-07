# -*- coding: utf-8 -*-
"""Loop autonomo: chama build_next_layer() ate todas as 18 camadas."""
import os, sys, importlib
os.chdir(r"D:/Alice/tools/auto-rig-fix")
sys.path.insert(0, r"D:/Alice/tools/auto-rig-fix")

import project_alice_autonomous_constructor as pac
importlib.reload(pac)

# Reset state
state_path = r"D:/Alice/tools/auto-rig-fix/work/constructor_state.json"
if os.path.exists(state_path): os.remove(state_path)

c = pac.ProjectAliceAutonomousConstructor(spec_path=r"D:/Alice/tools/auto-rig-fix/specs/chapeleiro_dress_spec.json")
total = len(c.spec["layer_order"])
print(f"\n[LOOP AUTONOMO] total={total} camadas")
for i in range(total):
    print(f"\n========== ITER {i+1}/{total} ==========")
    c.build_next_layer()
print("\n[DONE] todas camadas configuradas")
