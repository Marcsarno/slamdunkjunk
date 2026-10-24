PUMPKIN GOLF STAND BAG - THREE-PASS CRAFTSMANSHIP EDITION
Graveyard Shift: Midnight Golf

An actual Blender-built game prop. The approved dark plum / burnt-orange
palette is retained. This is not an AI-generated image pretending to be a model.
The hero and angle images are renders of the enclosed Blender asset.

THREE CHECKPOINTS
1. Construction: smoother padded carry handle, broader contoured rubber base
   with protective ribs, slightly fuller front pocket, more compact club display.
2. Materials/detail: subtly varied woven plum texture, zipper track and pull,
   restrained pocket stitches and handle wrap seams. No baked lighting or glow.
3. Critical QA: front/back/side inspection identified floating collar fasteners,
   pocket piping and a side seam. Rivets were seated against the collar; pocket
   piping was rebuilt by projecting onto its curved surface; the side seam was
   aligned with the pocket. Added protective stand-entry sleeves and a tiny
   reference-style driver crown accent. Static detail consolidated for export.

CONTENTS
- Pumpkin_Bag_Overnight_Final.blend: editable Blender 4.3.2 scene, packed textures.
- Pumpkin_Bag_Overnight_Final.glb: game asset with embedded textures, no studio.
- Pumpkin_Bag_Overnight_Hero.png: neutral studio hero render.
- Pumpkin_Bag_Multiangle.png: front, handle side and rear inspection views.
- Pumpkin_Bag_Before_After.png: approved earlier final vs new version, identical
  hero camera, lighting and exposure.
- textures/: new woven plum fabric and unchanged pumpkin graphic.
- asset_stats.json and glb_validation.json: actual export statistics/checks.

SPECIFICATIONS
6,000 triangles; 10 mesh objects; 9 materials; 2 embedded textures.
Bounds approximately 0.632 x 0.747 x 1.172 metres including stand and clubs.
Bag body height approximately 0.87 m. Root and base ground contact at z=0.
Club_DRIVER, Club_IRON and Club_PUTTER remain separate removable objects.
Both stand legs, feet and hinge assemblies remain separate.

A fresh Blender scene successfully reimported the GLB; clubs, both legs,
embedded images and triangle count were verified. All three ground contacts
are retained. Earlier versions/checkpoints were preserved outside this package.

IMPLEMENTATION
Static deployed prop only. No folding animation, armature, collision, LOD,
or game integration is included. The editable .blend has STUDIO camera,
floor and lights for preview; GLB excludes them. Use the GLB in the game.

The dark materials use KHR_materials_specular. If your engine ignores this
extension, lower specular manually to avoid pale reflection washout. The dark
base colors and fabric textures are independently embedded. Render appearance
will vary with the game's lighting and tone mapping.
