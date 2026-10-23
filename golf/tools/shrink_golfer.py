"""Fit the golfer's video-cut frames to the size the game draws them at, and thin out the pull frames.

usage: python3 -I shrink_golfer.py <assets/golfer dir>

The frames are cut at the videos' full size (prep_video_swing.py, prep_video_putt.py), but the game
draws her far smaller: in the swing close-up she's under half the screen high, and while pulling
she's a small figure in the high aiming view. Loaded at full size every frame took ~280 MB of a
phone's graphics memory, and loading them mid-pull made the first pull with each club stutter.

Per set (SETS): every pixel quantity in golfer.json (frame sizes, anchors, club heads, body_px) is
scaled by the same factor, so she stands the same height in the game; `keep_every` keeps every nth
frame of the backswing that follows the pull (the first and the top always stay) and the files of
dropped frames are deleted. Run once on freshly cut frames; it refuses frames already shrunk.
"""
import json
import os
import sys

from PIL import Image

# set: (scale, keep every nth backswing frame)
SETS = {
    "video_driver": (0.8, 1),
    "video_iron": (0.8, 1),
    "video_back_driver": (0.6, 4),
    "video_back_iron": (0.6, 4),
    "video_back_putter": (0.7, 2),
}
FULL_BODY_PX = 561          # body height the videos were cut at (the smaller of the face and back sets)


def main():
    d = sys.argv[1]
    path = os.path.join(d, "golfer.json")
    meta = json.load(open(path))
    for name, (k, every) in SETS.items():
        s = meta[name]
        if s["body_px"] < FULL_BODY_PX:
            print(name, "already shrunk, skipped")
            continue
        back = s["back"]
        keep = [f for i, f in enumerate(back) if i % every == 0 or i == len(back) - 1]
        used = set(str(f) for f in keep) | set(str(f) for f in s["down"])
        for key in list(s["frames"]):
            f = s["frames"][key]
            file = os.path.join(d, f["file"])
            if key not in used:
                os.remove(file)
                if os.path.exists(file + ".import"):
                    os.remove(file + ".import")
                del s["frames"][key]
                continue
            img = Image.open(file)
            w, h = max(1, round(img.width * k)), max(1, round(img.height * k))
            img.resize((w, h), Image.LANCZOS).save(file, optimize=True)
            f["size"] = [w, h]
            f["anchor"] = [round(v * k, 1) for v in f["anchor"]]
            if f.get("club_head") is not None:
                f["club_head"] = [round(v * k, 1) for v in f["club_head"]]
            if "height" in f:
                f["height"] = round(f["height"] * k, 1)
        s["back"] = keep
        s["body_px"] = round(s["body_px"] * k, 1)
        print("%s: %d frames, body %.0f px" % (name, len(s["frames"]), s["body_px"]))
    with open(path, "w") as f:
        json.dump(meta, f, indent=1)


if __name__ == "__main__":
    main()
