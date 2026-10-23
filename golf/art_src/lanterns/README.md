# Pumpkin Lanterns — Night Finish v2

A separate darker-texture edition of the approved Graveyard Shift Midnight Golf lanterns. Original files remain unchanged.

## Changes
- Painted wood base-color PNG pixels multiplied by 0.76 in sRGB (24% darker).
- Pumpkin rind base-color PNG pixels multiplied by 0.78 in sRGB (22% darker).
- Warm emissive interior material remains unchanged.
- No geometry, scale, pivot, component, face-opening, or triangle-count changes.
- Cooler, dimmer studio illumination for the actual Blender preview. The darker exported textures are real material changes, not just different preview lighting.

## Contents
- `Pumpkin_Lanterns_Night_v2.blend`: editable source, packed textures and night-preview studio.
- `01_Post_Top_Pumpkin.glb`: complete post-top marker.
- `02_Braced_L_Arm.glb`: complete rigid-bracket hanging lantern.
- `01_Bridge_Mount.glb`: pumpkin and wooden cap, without the post.
- `00_Night_v2_Both_Lanterns.png`: actual Blender render.
- `textures/`: darker albedo PNGs, also embedded in GLBs and packed in Blender.
- `validation_report.json`: independent import checks and triangle counts.
- `geometry_comparison.json`: exact raw geometry-buffer comparison against the original GLBs.
- `material_changes.json`: darkening factors.
- `rebuild_assets.py`, `validate_exports.py`: standalone construction/export/render and validation scripts. The rebuild reads the v2 textures supplied in this folder.

## Geometry and performance
Post-top: 16,188 triangles, approximately 2.79m tall.
Braced arm: 17,484 triangles, approximately 2.65m tall.
Bridge mount: 15,756 triangles, approximately 1.07m tall.

These are mid-poly first passes, not mobile-optimized low-LOD models. Use instancing for repeated path markers, create reduced LODs for dense/mobile placement, and avoid one shadow-casting light per repeated prop. No collision meshes, LODs, lightmap UV2, rigs or animation have been added.

## Placement and lighting
Units are meters. GLB root pivots sit at ground level; the bridge variant pivot sits at the underside of its cap. Individual components have geometry-centered pivots. Source models are offset side-by-side for presentation, but each GLB exports at its own origin. Faces point toward Blender -Y, with Z up; glTF automatically converts to Y up.

The hollow pumpkin shells have genuine carved openings and separate emissive interiors. Use bloom for a halo and add warm point lights in your engine if needed for nearby surface lighting. Emission does not automatically illuminate surrounding objects in every engine. No engine lighting, game integration or catalog edits were performed. Studio lights and ground are excluded from GLBs.

Rebuild with Blender 4.3.2 or compatible:

    blender -b -t 8 --python rebuild_assets.py
    blender -b -t 4 --python validate_exports.py
