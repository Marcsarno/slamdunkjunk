"""Split a painted atlas into individual trimmed RGBA cutouts by alpha islands."""
import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage

src, out, names = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
os.makedirs(out, exist_ok=True)
im = Image.open(src).convert("RGBA")
a = np.array(im)[..., 3]
mask = ndimage.binary_opening(a > 200, iterations=2)
mask = ndimage.binary_dilation(mask, iterations=5)
lab, n = ndimage.label(mask)
boxes = [s for s in ndimage.find_objects(lab) if (s[0].stop - s[0].start) * (s[1].stop - s[1].start) > 20000]
boxes.sort(key=lambda s: (round((s[0].start + s[0].stop) / 2 / 300), s[1].start))
for i, s in enumerate(boxes):
    crop = im.crop((s[1].start, s[0].start, s[1].stop, s[0].stop))
    ca = np.array(crop)
    ca[..., 3] = np.where(ca[..., 3] < 24, 0, ca[..., 3])   # drop the faint glow haze
    crop = Image.fromarray(ca).crop(Image.fromarray(ca[..., 3]).getbbox())
    name = names[i] if i < len(names) else f"piece_{i}"
    crop.save(os.path.join(out, name + ".png"))
    print(name, crop.size)
