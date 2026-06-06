# claude-blender-designer

Pipeline image -> 3D -> Blender (rig, multilayer skirt, facial shape keys).

## Components

- `pipeline_orquestrador.py` — orchestrates image -> TripoSR -> Blender bridge.
- `live/game_builder.py` — Blender-side: mesh ingest, full skeleton, skirt layers, facial shape keys, hand limits, secondary dynamics.
- `claude_bridge.py` — socket bridge running inside Blender (port 9877..9881).
- `bridge_cmd.py` — CLI client to send Python code to the running Blender bridge.

## Usage

```bash
python pipeline_orquestrador.py <front-image.png> [character_name]
```

Example:
```bash
python pipeline_orquestrador.py D:/Alice/tools/dress/regen/in_front.png Alice_v1
```

## Requirements

- Blender 4.x running with `claude_bridge.py` loaded.
- TripoSR at `D:/Alice/tools/TripoSR`.
- Python with torch+CUDA (ComfyUI portable works).

## Output

Generated GLB lands in `work/generated/`; Blender scene is replaced with the rigged character.
