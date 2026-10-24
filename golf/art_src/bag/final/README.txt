PUMPKIN GOLF STAND BAG - FINAL POLISH
Graveyard Shift: Midnight Golf

This is the approved dark Night v3 palette with a final club-shape polish.
All 8 material definitions and both embedded texture byte streams were
verified identical to v3. Lighting, camera and exposure are unchanged.

Changes:
- Iron has a rounded, sloped blade, tapered back, score lines and shaped hosel.
- Driver has a flattened striking plate and subtle score lines.
- Existing handle attachments, piping, stand legs, feet and bag shape preserved.

Files:
Pumpkin_Golf_Stand_Bag_Final.blend: editable Blender 4.3.2 scene, packed textures.
Pumpkin_Golf_Stand_Bag_Final.glb: game asset, textures embedded, no studio objects.
Pumpkin_Golf_Bag_Final_Preview.png: neutral studio render of the actual model.
textures/: source PNG files, unchanged from Night v3.
asset_stats.json / glb_validation.json / palette_validation.json: validation.

3,868 triangles, 10 mesh objects, 8 materials, 2 embedded textures.
Dimensions: 0.632 x 0.749 x 1.199 metres, including clubs and deployed stand.
Bag body height approximately 0.87 metres. Root is at ground level.
Club_DRIVER, Club_IRON and Club_PUTTER remain separate objects.
Both stand legs, rubber feet and hinge assemblies remain separate.
The base and both feet contact z=0; preview floor is at z=-0.003.

GLB was reimported successfully into a fresh Blender scene and checked.
Specular properties use KHR_materials_specular. If an engine ignores that
extension, reduce specular manually to preserve the dark matte appearance.
The approved dark base colors are independently embedded in the GLB.

Static deployed prop, no armature, folding animation, collision or game setup.
The .blend includes named STUDIO preview objects; those are excluded from GLB.
Earlier versions remain unchanged and are not included in this final package.
