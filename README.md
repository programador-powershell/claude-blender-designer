# claude-blender-designer

Image -> 3D -> Blender rigged character pipeline.

## Pipelines

| Script | Input | 3D engine | Status |
|---|---|---|---|
| `pipeline_hunyuan.py` | front/left/back images | Hunyuan3D-2mv | working |
| `pipeline_unique3d.py` | front image | Unique3D (multi-view + mesh recon) | install required |
| `pipeline_orquestrador.py` | front image | TripoSR | install required |

## Blender side

`live/game_builder.py` — invoked by the pipeline scripts via `bridge_cmd.py`:

- `auto_process_ai_generated_mesh()` — ingest GLB, normalize to 1.7m, base z=0
- `build_complete_skeleton()` — full Mixamo-named skeleton incl. fingers, jaw, eyes
- `apply_skirt_layers_and_weighting()` — 3 tiers x 8 rings x 3 segments, numpy-vectorized weights
- `inject_secondary_physics_bones()` — breast + butt physics bones with falloff
- `setup_advanced_finger_constraints()` — anatomical hinge limits per phalange
- `apply_facial_shape_keys()` — Mouth_Open + Blink_L + Blink_R via vert-coord proximity
- `apply_vision_details_to_mesh()` — VLM JSON curves -> bump map onto material
- `execute_ultimate_pipeline()` — dispatcher: SHD skinning -> all of the above

Legacy utilities preserved: `skin_auto`, `shd_launch/finalize`, `surgical_align`,
`extract_and_fit_clothing`, `snapshot/rollback`, etc.

## Vision (VLM)

`live/vision_ask.py` — single-image / multi-image query against llama.cpp server.
`live/vision_to_trace.py` — VLM -> JSON {curves:[{label,region,points}]} for bump.

Backend: llama-server (Qwen3-VL 30B GGUF + mmproj) on port 8080.

## Bridge

`claude_bridge.py` — socket bridge inside Blender (port 9877..9881).
`bridge_cmd.py` — CLI client that ships a Python file to the bridge.

## Usage

```bash
# Hunyuan path
python pipeline_hunyuan.py D:/path/to/front.png D:/path/to/left.png D:/path/to/back.png char_name

# Trace bump details via vision
python live/vision_to_trace.py D:/path/to/art.png D:/out/trace.json
# then inside Blender (via MCP or bridge):
# game_builder.apply_vision_details_to_mesh("char_name_Mesh", "D:/out/trace.json")
```

## Requirements

- Blender 4.x or 5.x running with `claude_bridge.py` loaded (or Blender MCP add-on).
- Python env per pipeline (Hunyuan portable; Unique3D conda env).
- llama-server with vision-capable GGUF for the VLM trace.
