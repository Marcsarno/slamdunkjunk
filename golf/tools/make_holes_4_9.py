"""Write the hole layouts 4-9 to courses/holes (usage: python3 -I make_holes_4_9.py golf/courses/holes).

Course coords in meters: x right, y down-range, z up; tee at the origin. Edit a hole here, run this,
then rebuild it with build_hole.py.
"""
import json
import math
import sys

OUT = sys.argv[1]
NOTE_TAIL = " Course coords in meters: x right, y down-range, z up."
TEE_PUMPKINS = [{"center": [4.9, 3.4], "carved": 2, "plain": 1, "radius": 1.1},
                {"center": [-5.2, 6.2], "carved": 1, "plain": 2, "radius": 1.0}]


def painted(hole, yaw=0, span=95, horizon_v=0.8, variant="a"):
    return {"hole": hole, "variant": variant, "span": span, "yaw": yaw, "horizon_v": horizon_v}


def ravine(points, half_width=5.0, depth=4.2):
    """A rocky ravine with a creek at its bottom, along a polyline: one deep, narrow water piece per
    segment (their banks fall away steeply under the waterline, and steep ground draws as rock)."""
    out = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        dx, dy = x1 - x0, y1 - y0
        ln = (dx * dx + dy * dy) ** 0.5
        out.append({"center": [round((x0 + x1) / 2, 2), round((y0 + y1) / 2, 2)],
                    "radius": [round(ln / 2 + 4.0, 2), half_width],
                    "rotation": round(math.atan2(dy, dx), 4), "level_offset": -depth})
    return out


def pines(radius=420, haze=0.5):
    return [{"image": "horizon_pines", "radius": radius, "height": 44, "base": -6, "repeats": 9, "haze": haze}]


holes = [
    {
        "id": "h04_spiderwood", "name": "Spiderwood", "number": 4, "par": 4, "seed": 404,
        "note": "The Web: the fairway runs up the left side, then turns hard right along the top to a green "
                "in the woods. The inside of the bend is a giant spider web: anything that comes down in it "
                "stays there, and comes out short. Play the L, or fly the web's corner from the tee to the top "
                "of the turn and pitch on." + NOTE_TAIL,
        "path": [[0, 0], [-2, 60], [-4, 120], [2, 170], [30, 192], [80, 200], [128, 202], [152, 206]],
        "fairway_start": 34,
        "fairway_width": [22, 26, 28, 28, 28, 26, 24, 22],
        "rough_width": 12, "deep_rough_width": 14,
        "tee": {"center": [0, 0], "size": [8, 10]},
        "green": {"center": [152, 206], "radius": [12, 10], "rotation": 0.2, "slope": [-0.012, 0.018]},
        "pin": [155, 207],
        "bunkers": [{"center": [134, 192], "radius": [4.6, 2.6], "rotation": 0.4, "depth": 0.5},
                    {"center": [167, 218], "radius": [4.4, 2.4], "rotation": -0.5, "depth": 0.45},
                    {"center": [-16, 162], "radius": [3, 6.5], "rotation": 0.2, "depth": 0.45}],
        "water": [],
        "webs": [{"center": [62, 100], "radius": [42, 54], "rotation": 0.35},
                 {"center": [34, 62], "radius": [18, 18], "rotation": -0.4},
                 {"center": [100, 142], "radius": [22, 15], "rotation": 0.6}],
        "web_art": [{"center": [62, 100], "radius": [48, 60], "rotation": 0.35},
                    {"center": [34, 62], "radius": [22, 22], "rotation": 2.1},
                    {"center": [100, 142], "radius": [26, 19], "rotation": -1.2}],
        "zones": [{"center": [66, 100], "radius": [56, 66], "rotation": 0.35, "surface": "deep_rough"}],
        "elevation": {"tee": 3.0, "green": 4.5, "cross_tilt": 0.006, "roll_height": 0.3, "bank_height": 2.5,
                      "mounds": [{"center": [-50, 120], "radius": 22, "height": 2.4},
                                 {"center": [90, 250], "radius": 24, "height": 2.6},
                                 {"center": [200, 160], "radius": 22, "height": 2.4}]},
        "wind": {"min": 0, "max": 3},
        "graveyards": [{"center": [-40, 230], "radius": 6, "count": 6, "fence": False}],
        "plan": {"safe": [[-2, 168], [155, 207]], "risk": [[46, 192], [155, 207]]},
        "lantern_spacing": 17, "trees_spacing": 7.0,
        "pumpkin_clusters": TEE_PUMPKINS,
        "cart_path": {"side": -1, "offset": 6.0},
        "theme": {
            "light_props_spacing": 20,
            "light_props": ["light_captured_spirit", "light_marsh_wisp", "light_moon_mushrooms", "light_lantern_ghost",
                            "light_skull_lantern", "light_haunted_lamppost"],
            "trees_near": ["tree_ghost_birch", "tree_moonlit_pine", "tree_twisted_cypress", "tree_windbent_fir",
                           "tree_hollow_sentinel", "birch", "tree_moonlit_pine"],
            "trees_far": ["tree_moonlit_pine", "tree_windbent_fir", "pine_blue", "tree_moonlit_pine", "tree_ghost_birch"],
            "backdrop": painted("04-spiderwood", yaw=10), "rings": pines(400, 0.6), "sky_style": "night",
            "sky_top": [0.004, 0.006, 0.025], "sky_horizon": [0.04, 0.05, 0.13], "fog": [0.1, 0.08, 0.19],
            "fog_density": 0.0048, "backdrop_haze": 0.2, "moon": "white", "moon_azimuth": -22, "moon_elevation": 14,
            "light_azimuth": 210, "light_elevation": 30, "water_deep": [0.02, 0.02, 0.06], "water_glow": [0.45, 0.35, 1.0],
            "wisp_color": [0.75, 0.6, 1.0], "ghosts": 4, "lightning": 0, "mist": 44, "mist_alpha": 0.42,
            "clouds": 0.7, "leaf_amount": 0.2,
        },
    },
    {
        "id": "h05_haunted_harvest", "name": "Haunted Harvest", "number": 5, "par": 5, "seed": 505,
        "note": "Haunted Harvest: a long S out to the right round a fenced cornfield, to a green under the old "
                "barn and its silo. Three shots round it, or two over the corn: lay up on the pad beside the "
                "field and fly its corner. Anything in the corn is lost in it, and comes out short." + NOTE_TAIL,
        "path": [[0, 0], [55, 70], [115, 125], [140, 190], [125, 260], [85, 315], [35, 345]],
        "fairway_start": 38,
        "fairway_width": [24, 28, 30, 30, 28, 26, 22],
        "rough_width": 13, "deep_rough_width": 14,
        "tee": {"center": [0, 0], "size": [8, 10]},
        "green": {"center": [35, 346], "radius": [13, 11], "rotation": -0.3, "slope": [-0.012, 0.018]},
        "pin": [32, 348],
        "bunkers": [{"center": [52, 352], "radius": [5, 3], "rotation": 1.0, "depth": 0.5},
                    {"center": [20, 334], "radius": [4.4, 2.6], "rotation": -0.5, "depth": 0.45},
                    {"center": [156, 205], "radius": [3, 7], "rotation": 0.2, "depth": 0.45}],
        "water": [],
        "pads": [{"center": [24, 178], "radius": [15, 13], "rotation": 0.2}],
        "cornfields": [{"center": [52, 262], "radius": [26, 44], "rotation": -0.35, "gap": 4.2}],
        "zones": [{"center": [52, 262], "radius": [34, 54], "rotation": -0.35, "surface": "deep_rough"},
                  {"center": [62, 190], "radius": [30, 40], "rotation": 0.4, "surface": "rough"},
                  {"center": [56, 380], "radius": [34, 26], "rotation": 0.6, "surface": "rough"}],
        "features": [{"model": "barn", "pos": [62, 392], "face": [35, 346], "clear": 18}],
        "elevation": {"tee": 2.0, "green": 4.5, "cross_tilt": 0.008, "roll_height": 0.35, "bank_height": 2.5,
                      "mounds": [{"center": [-40, 120], "radius": 24, "height": 2.4},
                                 {"center": [190, 260], "radius": 22, "height": 2.2},
                                 {"center": [-10, 380], "radius": 24, "height": 2.6}]},
        "wind": {"min": 1, "max": 5},
        "graveyards": [{"center": [180, 120], "radius": 6, "count": 6, "fence": True}],
        "plan": {"safe": [[98, 116], [140, 230], [32, 348]], "risk": [[24, 178], [32, 348]]},
        "lantern_spacing": 18, "trees_spacing": 8.5,
        "pumpkin_clusters": TEE_PUMPKINS + [
            {"center": [12, 34], "carved": 2, "plain": 3}, {"center": [10, 228], "carved": 1, "plain": 3},
            {"center": [22, 368], "carved": 2, "plain": 3}, {"center": [90, 372], "carved": 2, "plain": 2},
            {"center": [84, 236], "carved": 1, "plain": 3}],
        "cart_path": {"side": 1, "offset": 7.0},
        "theme": {
            "light_props_spacing": 26,
            "light_props": ["light_classic_jack", "light_pumpkin_totem", "light_hanging_harvest",
                            "light_pumpkin_path_lights", "light_skeleton_groundskeeper", "light_hollow_heart_tree"],
            "trees_near": ["tree_harvest_pear", "tree_crooked_plum", "tree_copper_oak", "apple_tree",
                           "tree_scarlet_maple", "tree_golden_aspen", "tree_harvest_pear"],
            "trees_far": ["tree_copper_oak", "tree_scarlet_maple", "maple_orange", "tree_golden_aspen", "tree_moonlit_pine"],
            "backdrop": painted("05-haunted-harvest", yaw=-8), "rings": pines(440, 0.5), "sky_style": "night",
            "sky_top": [0.004, 0.006, 0.025], "sky_horizon": [0.04, 0.05, 0.13], "fog": [0.14, 0.07, 0.12],
            "fog_density": 0.0034, "backdrop_haze": 0.16, "moon": "harvest", "moon_azimuth": 18, "moon_elevation": 12,
            "moon_size": 0.04, "light_azimuth": 160, "light_elevation": 28, "moon_light": [0.9, 0.7, 0.85],
            "water_deep": [0.04, 0.015, 0.03], "water_glow": [1.0, 0.45, 0.12],
            "wisp_color": [1.0, 0.6, 0.25], "ghosts": 2, "lightning": 0, "mist": 20, "clouds": 0.55,
            "cloud_tint": [0.65, 0.45, 0.6], "leaf_amount": 0.45,
        },
    },
    {
        "id": "h06_ghostlight_marsh", "name": "Ghostlight Marsh", "number": 6, "par": 3, "seed": 606,
        "note": "Will-o'-the-Wisp: a par 3 with a choice. The fairway bends left and round the glowing "
                "marsh to a green on its far shore: lay up and pitch on, or fly the marsh straight at the "
                "flag. Ghost-lights drift over the water." + NOTE_TAIL,
        "path": [[0, 0], [-12, 50], [-10, 95], [8, 125], [36, 135]],
        "fairway_start": 30,
        "fairway_width": [20, 24, 26, 24, 22],
        "rough_width": 13, "deep_rough_width": 14,
        "tee": {"center": [0, 0], "size": [8, 9]},
        "green": {"center": [36, 135], "radius": [12, 10], "rotation": 0.5, "slope": [-0.014, 0.018]},
        "pin": [38, 137],
        "bunkers": [{"center": [-30, 72], "radius": [3, 8], "rotation": 0.1, "depth": 0.5},
                    {"center": [20, 146], "radius": [5, 2.8], "rotation": -0.6, "depth": 0.5},
                    {"center": [50, 148], "radius": [4.2, 2.4], "rotation": 0.8, "depth": 0.45}],
        "water": [{"center": [28, 66], "radius": [21, 44], "rotation": -0.3, "level_offset": -0.5}],
        "zones": [{"center": [30, 66], "radius": [34, 60], "rotation": -0.3, "surface": "deep_rough"}],
        "elevation": {"tee": 2.4, "green": 2.4, "cross_tilt": 0.004, "roll_height": 0.2, "bank_height": 2.5,
                      "mounds": [{"center": [-50, 40], "radius": 18, "height": 1.8},
                                 {"center": [-36, 130], "radius": 20, "height": 2.0},
                                 {"center": [40, 180], "radius": 24, "height": 2.4}]},
        "wind": {"min": 1, "max": 6},
        "graveyards": [{"center": [-40, 112], "radius": 5, "count": 5, "fence": False}],
        "plan": {"safe": [[-10, 90], [38, 137]], "risk": [[38, 137]]},
        "lantern_spacing": 13, "trees_spacing": 8.0,
        "pumpkin_clusters": TEE_PUMPKINS,
        "cart_path": {"side": -1, "offset": 6.0},
        "theme": {
            "light_props_spacing": 14,
            "light_props": ["light_marsh_wisp", "light_captured_spirit", "light_moon_mushrooms", "light_marsh_wisp",
                            "light_skull_lantern", "light_lantern_ghost"],
            "trees_near": ["tree_bent_willow", "tree_twisted_cypress", "tree_ancient_yew", "tree_bent_willow",
                           "tree_raven_perch"],
            "trees_far": ["tree_moonlit_pine", "tree_twisted_cypress", "tree_windbent_fir", "tree_moonlit_pine"],
            "backdrop": painted("06-ghostlight-marsh", yaw=0), "rings": pines(380, 0.6), "sky_style": "night",
            "sky_top": [0.004, 0.006, 0.025], "sky_horizon": [0.04, 0.05, 0.13], "fog": [0.05, 0.1, 0.13],
            "fog_density": 0.0046, "backdrop_haze": 0.2, "moon": "white", "moon_azimuth": 26, "moon_elevation": 13,
            "light_azimuth": 195, "light_elevation": 30, "water_deep": [0.01, 0.03, 0.05], "water_glow": [0.15, 0.9, 1.0],
            "wisp_color": [0.35, 1.0, 0.95], "wisps": 110, "ghosts": 5, "lightning": 0, "mist": 46, "mist_alpha": 0.42,
            "clouds": 0.5, "leaf_amount": 0.12,
        },
    },
    {
        "id": "h07_vampires_garden", "name": "Vampire's Garden", "number": 7, "par": 4, "seed": 707,
        "note": "The Count's Lawn: the drive drifts right past a fenced crypt in the fairway, then the hole "
                "turns hard left round a blood-red pond. A moat crosses in front of the green, which is "
                "ringed with bunkers like a rose bed." + NOTE_TAIL,
        "path": [[0, 0], [2, 55], [18, 115], [22, 170], [6, 220], [-24, 262], [-50, 292], [-62, 318]],
        "fairway_start": 36,
        "fairway_width": [22, 26, 28, 28, 26, 24, 22, 20],
        "rough_width": 15, "deep_rough_width": 16,
        "rough_islands": [{"center": [20, 148], "radius": [6, 8], "rotation": 0.2}],
        "tee": {"center": [0, 0], "size": [8, 10]},
        "green": {"center": [-62, 318], "radius": [12, 10.5], "rotation": 0.8, "slope": [-0.014, 0.018]},
        "pin": [-64, 321],
        "bunkers": [{"center": [-49, 326], "radius": [5, 2.6], "rotation": 1.4, "depth": 0.5},
                    {"center": [-75, 310], "radius": [5, 2.6], "rotation": 0.2, "depth": 0.5},
                    {"center": [-68, 333], "radius": [4.6, 2.4], "rotation": -0.4, "depth": 0.5},
                    {"center": [-58, 304], "radius": [4.0, 2.2], "rotation": 0.8, "depth": 0.45},
                    {"center": [36, 132], "radius": [7, 3.4], "rotation": -0.3, "depth": 0.45}],
        "water": [{"center": [-22, 206], "radius": [11, 15], "rotation": 0.3},
                  {"center": [-43, 288], "radius": [24, 4.5], "rotation": 0.71, "level_offset": -0.7}],
        "elevation": {"tee": 4.0, "green": 6.0, "cross_tilt": 0.01, "roll_height": 0.4, "bank_height": 3.5,
                      "mounds": [{"center": [44, 80], "radius": 22, "height": 2.2},
                                 {"center": [-70, 240], "radius": 22, "height": 2.4},
                                 {"center": [-92, 336], "radius": 22, "height": 2.6}]},
        "carry": [296, 314],
        "wind": {"min": 0, "max": 4},
        "graveyards": [{"center": [20, 148], "radius": 5.5, "count": 7, "fence": True},
                       {"center": [60, 210], "radius": 8, "count": 9, "fence": True}],
        "lantern_spacing": 16, "trees_spacing": 8.0,
        "pumpkin_clusters": TEE_PUMPKINS,
        "cart_path": {"side": -1, "offset": 6.0},
        "theme": {
            "light_props_spacing": 20,
            "light_props": ["light_haunted_lamppost", "light_grave_candles", "light_skull_lantern",
                            "light_hollow_heart_tree", "light_lantern_ghost", "light_glowing_ghoul"],
            "trees_near": ["tree_scarlet_maple", "tree_twisted_cypress", "tree_crooked_plum", "tree_ancient_yew",
                           "tree_hollow_sentinel", "tree_twisted_cypress"],
            "trees_far": ["tree_twisted_cypress", "tree_moonlit_pine", "tree_scarlet_maple", "tree_windbent_fir"],
            "backdrop": painted("07-vampires-garden", yaw=-14), "rings": pines(420, 0.5), "sky_style": "night",
            "sky_top": [0.004, 0.006, 0.025], "sky_horizon": [0.04, 0.05, 0.13], "fog": [0.12, 0.05, 0.12],
            "fog_density": 0.0036, "backdrop_haze": 0.17, "moon": "harvest", "moon_azimuth": -30, "moon_elevation": 15,
            "moon_size": 0.03, "light_azimuth": 220, "light_elevation": 32, "moon_light": [0.95, 0.6, 0.8],
            "water_deep": [0.06, 0.005, 0.02], "water_glow": [1.0, 0.1, 0.25],
            "wisp_color": [1.0, 0.3, 0.45], "ghosts": 3, "lightning": 30, "mist": 28, "clouds": 0.6,
            "cloud_tint": [0.7, 0.4, 0.6], "leaf_amount": 0.3,
            "leaf_colors": [[0.6, 0.05, 0.1], [0.45, 0.02, 0.12], [0.75, 0.15, 0.1]],
        },
    },
    {
        "id": "h08_headless_trail", "name": "Headless Trail", "number": 8, "par": 4, "seed": 808,
        "note": "Headless Trail: up the valley and across a rocky ravine to a green under the crag. Lay up "
                "short of the ravine and fly it where it narrows, or drive the left pad by the old bridge and "
                "the Horseman's statue and go straight over. The ravine swallows anything that comes up short."
                + NOTE_TAIL,
        "path": [[0, 0], [6, 80], [14, 150], [12, 200], [4, 260], [-2, 318]],
        "fairway_start": 36,
        "fairway_width": [24, 28, 30, 28, 26, 22],
        "rough_width": 12, "deep_rough_width": 14,
        "tee": {"center": [0, 0], "size": [8, 10]},
        "green": {"center": [-2, 320], "radius": [13, 11], "rotation": 0.1, "slope": [0.01, 0.02]},
        "pin": [0, 322],
        "bunkers": [{"center": [-22, 140], "radius": [3, 7], "rotation": 0.1, "depth": 0.5},
                    {"center": [30, 176], "radius": [3, 6], "rotation": -0.3, "depth": 0.45},
                    {"center": [-18, 286], "radius": [3, 6], "rotation": 0.2, "depth": 0.5},
                    {"center": [14, 330], "radius": [4.6, 2.6], "rotation": 0.4, "depth": 0.5},
                    {"center": [-20, 326], "radius": [4.2, 2.4], "rotation": -0.4, "depth": 0.45}],
        "water": ravine([[-110, 262], [-60, 240], [-10, 224], [40, 204], [90, 186], [140, 176]]),
        "carry": [204, 236],
        "pads": [{"center": [-34, 178], "radius": [14, 11], "rotation": 0.2}],
        "zones": [{"center": [-30, 175], "radius": [26, 44], "rotation": 0.1, "surface": "rough"},
                  {"center": [-36, 262], "radius": [20, 14], "rotation": 0.0, "surface": "rough"}],
        "features": [{"image": "statue_horseman", "pos": [-36, 256], "scale": 1.4, "clear": 9}],
        "elevation": {"tee": 3.0, "green": 6.5, "cross_tilt": 0.008, "roll_height": 0.35, "bank_height": 3.0,
                      "profile": [[0, 3.0], [150, 3.6], [200, 4.0], [240, 4.6], [330, 6.5]],
                      "mounds": [{"center": [60, 100], "radius": 24, "height": 2.4},
                                 {"center": [-70, 120], "radius": 22, "height": 2.2},
                                 {"center": [40, 300], "radius": 24, "height": 3.0}]},
        "wind": {"min": 1, "max": 6},
        "graveyards": [{"center": [44, 260], "radius": 6, "count": 6, "fence": False}],
        "plan": {"safe": [[12, 168], [0, 322]], "risk": [[-34, 178], [0, 322]]},
        "lantern_spacing": 17, "trees_spacing": 7.0,
        "pumpkin_clusters": TEE_PUMPKINS,
        "cart_path": {"side": -1, "offset": 6.0},
        "theme": {
            "ravine": True,
            "light_props_spacing": 22,
            "light_props": ["light_classic_jack", "light_skull_lantern", "light_haunted_lamppost",
                            "light_glowing_ghoul", "light_lantern_ghost", "light_pumpkin_totem"],
            "trees_near": ["tree_lightning_oak", "tree_raven_perch", "tree_windbent_fir", "dead_tree",
                           "tree_silver_snag", "tree_lightning_oak"],
            "trees_far": ["tree_windbent_fir", "tree_moonlit_pine", "tree_silver_snag", "pine_blue"],
            "backdrop": painted("08-headless-trail", yaw=6), "rings": pines(420, 0.55), "sky_style": "night",
            "sky_top": [0.004, 0.006, 0.025], "sky_horizon": [0.04, 0.05, 0.13], "fog": [0.08, 0.08, 0.15],
            "fog_density": 0.0042, "backdrop_haze": 0.18, "moon": "white", "moon_azimuth": 30, "moon_elevation": 16,
            "light_azimuth": 150, "light_elevation": 34,
            "water_deep": [0.01, 0.02, 0.05], "water_glow": [0.35, 0.55, 1.0],
            "wisp_color": [1.0, 0.55, 0.2], "ghosts": 4, "lightning": 12, "mist": 30, "clouds": 0.95,
            "leaf_amount": 0.4,
        },
    },
    {
        "id": "h09_midnight_homecoming", "name": "Midnight Homecoming", "number": 9, "par": 4, "seed": 909,
        "note": "The Walk Home: the finale curls right and back round a fenced pumpkin patch to the lit "
                "clubhouse. Play round the long way, or carry the patch to a landing pad on the left and "
                "leave a short pitch home." + NOTE_TAIL,
        "path": [[0, 0], [30, 60], [70, 120], [82, 185], [65, 245], [25, 285], [0, 300]],
        "fairway_start": 34,
        "fairway_width": [24, 28, 30, 30, 28, 26, 24],
        "rough_width": 13, "deep_rough_width": 14,
        "tee": {"center": [0, 0], "size": [8, 10]},
        "green": {"center": [0, 300], "radius": [14, 12], "rotation": -0.3, "slope": [0.01, 0.022]},
        "pin": [2, 303],
        "bunkers": [{"center": [-17, 300], "radius": [5, 3], "rotation": 1.1, "depth": 0.5},
                    {"center": [16, 313], "radius": [4.4, 2.4], "rotation": -0.5, "depth": 0.45},
                    {"center": [66, 196], "radius": [3, 7], "rotation": 0.1, "depth": 0.45},
                    {"center": [64, 84], "radius": [6, 3], "rotation": 0.7, "depth": 0.45}],
        "water": [],
        "pads": [{"center": [-10, 178], "radius": [17, 14], "rotation": 0.0}],
        "zones": [{"center": [16, 135], "radius": [27, 58], "rotation": 0.1, "surface": "deep_rough"},
                  {"center": [-6, 100], "radius": [16, 82], "rotation": 0.0, "surface": "deep_rough"},
                  {"center": [-6, 240], "radius": [14, 50], "rotation": 0.0, "surface": "rough"}],
        "fences": [{"points": [[-6, 82], [-11, 110], [-11, 150], [-4, 182], [14, 194], [34, 186], [43, 160],
                               [44, 120], [38, 92], [24, 78]]}],
        "elevation": {"tee": 2.0, "green": 6.0, "cross_tilt": 0.008, "roll_height": 0.3, "bank_height": 2.5,
                      "mounds": [{"center": [120, 110], "radius": 24, "height": 2.4},
                                 {"center": [-70, 160], "radius": 22, "height": 2.2},
                                 {"center": [60, 330], "radius": 22, "height": 2.4}]},
        "wind": {"min": 1, "max": 3},
        "graveyards": [{"center": [-60, 240], "radius": 7, "count": 8, "fence": True}],
        "lantern_spacing": 11, "trees_spacing": 8.5,
        "pumpkin_clusters": TEE_PUMPKINS + [
            {"center": [x, y], "carved": 1 + (i % 2), "plain": 2, "radius": 2.2}
            for i, (x, y) in enumerate([(0, 100), (12, 96), (26, 104), (-2, 122), (14, 120), (30, 124),
                                        (2, 142), (18, 140), (34, 146), (-2, 162), (12, 162), (28, 166),
                                        (10, 182), (24, 182), (36, 104)])] + [
            {"center": [8, 330], "carved": 3, "plain": 2}, {"center": [-22, 318], "carved": 2, "plain": 1}],
        "plan": {"safe": [[72, 160], [2, 303]], "risk": [[-10, 178], [2, 303]]},
        "cart_path": {"side": 1, "offset": 6.0},
        "theme": {
            "light_props_spacing": 13,
            "light_props": ["light_haunted_lamppost", "light_pumpkin_path_lights", "light_hanging_harvest",
                            "light_classic_jack", "light_lantern_ghost", "light_skeleton_groundskeeper",
                            "light_grave_candles", "light_pumpkin_totem"],
            "trees_near": ["maple_orange", "tree_copper_oak", "tree_golden_aspen", "tree_scarlet_maple",
                           "lantern_tree", "tree_harvest_pear"],
            "trees_far": ["tree_moonlit_pine", "pine_blue", "tree_copper_oak", "tree_golden_aspen"],
            "backdrop": painted("09-midnight-homecoming", yaw=4), "rings": pines(420, 0.45), "sky_style": "night",
            "sky_top": [0.004, 0.006, 0.025], "sky_horizon": [0.04, 0.05, 0.13], "fog": [0.11, 0.08, 0.16],
            "fog_density": 0.0032, "backdrop_haze": 0.15, "moon": "harvest", "moon_azimuth": -10, "moon_elevation": 14,
            "moon_size": 0.045, "light_azimuth": 200, "light_elevation": 34,
            "water_deep": [0.03, 0.015, 0.04], "water_glow": [1.0, 0.6, 0.22],
            "wisp_color": [1.0, 0.7, 0.3], "wisps": 80, "ghosts": 3, "lightning": 0, "mist": 22, "clouds": 0.45,
            "leaf_amount": 0.35,
        },
    },
]

for h in holes:
    path = f"{OUT}/{h['id']}.json"
    with open(path, "w") as f:
        json.dump(h, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(path)
