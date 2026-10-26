"""The ground of each hole (its Terrain and Skirt meshes) imports without far-detail copies (LODs) or a
shadow copy: the camera always stands on the ground, so the far-detail copies are never drawn, and the
game never lets the ground cast a shadow (hole_view.gd), so the shadow copy is never used. Together they
were ~60% of every hole's model download. Everything else in a hole keeps both.

Writes that into each assets/holes/hNN/hole.glb.import (Godot keeps a hole's import settings when the
hole is rebuilt; this puts them back if the file was ever made fresh). Run by tools/build_web.sh.
usage: python3 -I golf/tools/ground_import.py
"""
import glob
import os
import re

GROUND = ("hole_Terrain", "hole_Skirt")      # Godot's names for them: the file's name, then the mesh's
game = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game")
changed = 0
for p in sorted(glob.glob(os.path.join(game, "assets", "holes", "h*", "hole.glb.import"))):
    s = open(p).read()
    meshes = ",\n".join('"%s": {\n"generate/lods": 2,\n"generate/shadow_meshes": 2\n}' % m for m in GROUND)
    want = '_subresources={\n"meshes": {\n%s\n}\n}' % meshes
    new = re.sub(r"_subresources=\{.*?\n\}(?=\n[a-z]|\n*$)", want, s, count=1, flags=re.S) \
        if "_subresources={\n" in s else s.replace("_subresources={}", want)
    if new != s:
        open(p, "w").write(new)
        changed += 1
print("ground_import: %d hole imports updated" % changed)
