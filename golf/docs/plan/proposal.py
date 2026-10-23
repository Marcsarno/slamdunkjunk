"""The proposed nine: build-ready hole specs (overrides on the current ones) plus the plan's notes."""
import copy, json, os

HOLES_DIR = "/home/user/slamdunkjunk/golf/courses/holes"
FILES = ["h01_pumpkin_patch", "h02_witchs_hollow", "h03_forgotten_cemetery", "h04_spiderwood", "h05_haunted_harvest",
         "h06_ghostlight_marsh", "h07_vampires_garden", "h08_headless_trail", "h09_midnight_homecoming"]


def base(i):
    return json.load(open(os.path.join(HOLES_DIR, FILES[i] + ".json")))


def proposal():
    P = []
    # 1 -------------------------------------------------------------------------------------------
    h = base(0)
    P.append(dict(spec=h, par=4, changed=False,
        title="The Welcome", shape="Gentle dogleg left", elevation="Flat, slight rise", green="Large, open front",
        hazard="Farm pond inside the corner", landmark="Pumpkin patch and cornfield",
        question="An easy opener: how much of the pond corner do you dare cut?",
        safe=[[0, 0], [3, 200], [-49, 295]], hero=[[0, 0], [-24, 205], [-49, 295]],
        notes=[[-33, 118, "Farm pond"], [32, 120, "Cornfield (lost ball)"]],
        today="Stays as built: a wide, friendly first hole."))
    # 2 -------------------------------------------------------------------------------------------
    h = base(1)
    P.append(dict(spec=h, par=3, changed=False,
        title="The Cauldron", shape="Straight, downhill", elevation="Tee on a ridge, 10 m drop", green="Island",
        hazard="Forced carry to an island green", landmark="The witch's cottage",
        question="All or nothing: carry the swamp, or lay up on the strip and pitch over.",
        safe=[[0, 0], [3, 92], [12, 151]], hero=[[0, 0], [12, 151]],
        notes=[[-26, 128, "Glowing swamp"], [-14, 104, "Boardwalk to the island"]],
        today="Stays as built."))
    # 3 -------------------------------------------------------------------------------------------
    h = base(2)
    h["fairway_width"] = [22, 26, 30, 44, 46, 30, 22, 20]
    h["rough_islands"] = [{"center": [6, 232], "radius": [26, 9], "rotation": 1.3}]
    h["bunkers"] = h["bunkers"] + [{"center": [-14, 262], "radius": [5, 2.6], "rotation": 0.6, "depth": 0.5}]
    P.append(dict(spec=h, par=5, changed=True,
        title="Two Roads", shape="S-bend with a split fairway", elevation="Climbs 9 m to the abbey", green="Long, two tiers",
        hazard="A fenced graveyard splits the fairway", landmark="The ruined abbey",
        question="High road or low road? Left is shorter but squeezed by a bunker; right is wide and safe.",
        safe=[[0, 0], [22, 215], [-14, 322], [-26, 414]], hero=[[0, 0], [-9, 215], [-30, 335], [-26, 414]],
        notes=[[6, 232, "Graveyard island"], [-14, 262, "Bunker on the short road"]],
        today="The graveyard in the fairway becomes a real split: two fairways round it."))
    # 4 -------------------------------------------------------------------------------------------
    h = base(3)
    h.update({
        "path": [[0, 0], [-2, 60], [-4, 120], [6, 172], [24, 218], [36, 248]],
        "fairway_width": [20, 24, 26, 24, 22, 20], "fairway_start": 40,
        "green": {"center": [36, 248], "radius": [11, 9], "rotation": 0.9, "slope": [-0.012, 0.02]},
        "pin": [38, 250],
        "bunkers": [{"center": [48, 240], "radius": [4.5, 2.6], "rotation": 0.6, "depth": 0.5},
                    {"center": [26, 262], "radius": [4.4, 2.4], "rotation": -0.3, "depth": 0.45},
                    {"center": [-14, 150], "radius": [6, 3], "rotation": 0.2, "depth": 0.45}],
        "water": [{"center": [10, 206], "radius": [22, 5], "rotation": -0.75, "level_offset": -0.7},
                  {"center": [-12, 226], "radius": [14, 4.5], "rotation": -0.4, "level_offset": -0.7},
                  {"center": [30, 188], "radius": [14, 4.5], "rotation": -1.0, "level_offset": -0.7}],
        "carry": [196, 216], "rough_islands": [],
        "elevation": {"tee": 8.0, "green": 5.0, "cross_tilt": 0.01, "roll_height": 0.3, "bank_height": 5.0, "mounds": []},
    })
    P.append(dict(spec=h, par=4, changed=True,
        title="The Web", shape="Short dogleg right", elevation="Tee above the woods", green="Small, shelf above the creek",
        hazard="Ravine creek guarding a drivable green", landmark="Giant spider webs strung between the pines",
        question="A short par 4: lay up short of the creek and wedge on, or drive over the woods for an eagle putt.",
        safe=[[0, 0], [-4, 165], [38, 250]], hero=[[0, 0], [38, 250]],
        notes=[[10, 206, "Ravine creek"], [-14, 150, "Lay-up bunker"], [16, 120, "Web-strung pines"]],
        today="Shortened from 365 to about 270 yards: the course's drivable par 4."))
    # 5 -------------------------------------------------------------------------------------------
    h = base(4)
    h.update({
        "path": [[0, 0], [4, 60], [18, 120], [42, 175], [66, 220], [84, 262], [90, 300]],
        "fairway_width": [24, 30, 32, 30, 28, 24, 22], "fairway_start": 36,
        "green": {"center": [90, 300], "radius": [13, 11], "rotation": 0.5, "slope": [0.012, 0.02]},
        "pin": [92, 303],
        "bunkers": [{"center": [104, 292], "radius": [5, 2.8], "rotation": 1.0, "depth": 0.45},
                    {"center": [78, 312], "radius": [5, 2.8], "rotation": -0.6, "depth": 0.45},
                    {"center": [12, 190], "radius": [8, 3.6], "rotation": 0.8, "depth": 0.45}],
        "water": [{"center": [62, 132], "radius": [16, 42], "rotation": -0.55}],
        "rough_islands": [{"center": [70, 262], "radius": [3.5, 3.5], "rotation": 0}],
        "carry": None,
    })
    h.pop("carry")
    P.append(dict(spec=h, par=4, changed=True,
        title="The Cape", shape="Dogleg right round a diagonal pond", elevation="Flat farmland", green="Raised, by the windmill",
        hazard="Diagonal pond: carry as much as you dare", landmark="The windmill and a lone apple tree in the fairway",
        question="Bite off more of the pond for a shorter approach, or play out left and leave a long iron.",
        safe=[[0, 0], [10, 200], [92, 303]], hero=[[0, 0], [52, 190], [92, 303]],
        notes=[[62, 132, "Farm pond"], [70, 262, "Lone apple tree"], [-40, 150, "Corn maze (lost ball)"]],
        today="Becomes a par 4 cape hole (it was the course's second par 5)."))
    # 6 -------------------------------------------------------------------------------------------
    h = base(5)
    h.update({
        "path": [[0, 0], [6, 60], [14, 120]], "fairway_width": [16, 18, 18], "fairway_start": 104,
        "green": {"center": [14, 124], "radius": [10, 8], "rotation": 0.4, "slope": [-0.014, 0.018]},
        "pin": [16, 126],
        "bunkers": [{"center": [2, 132], "radius": [4, 2.3], "rotation": -0.5, "depth": 0.5}],
        "water": [{"center": [2, 58], "radius": [30, 30], "rotation": 0.0, "level_offset": -0.5},
                  {"center": [38, 124], "radius": [14, 22], "rotation": 0.2, "level_offset": -0.5},
                  {"center": [8, 150], "radius": [24, 9], "rotation": 0.1, "level_offset": -0.5}],
        "carry": [10, 104],
    })
    P.append(dict(spec=h, par=3, changed=True,
        title="Will-o'-the-Wisp", shape="Straight, short", elevation="Flat marsh", green="Peninsula, water on three sides",
        hazard="Water front, right and behind", landmark="The drowned chapel and floating wisps",
        question="Just a wedge, but the green is small and the wisps drift across the line.",
        safe=[[0, 0], [12, 120]], hero=[[0, 0], [16, 126]],
        notes=[[2, 58, "Glowing lagoon"], [-22, 70, "Boardwalk"], [38, 124, "Marsh"]],
        today="Shortened to a 135-yard wedge, so the two par 3s feel different (hole 2 is a 165-yard iron)."))
    # 7 -------------------------------------------------------------------------------------------
    h = base(6)
    h["rough_islands"] = h.get("rough_islands", []) + [
        {"center": [4, 208], "radius": [8, 3.5], "rotation": 0.3}, {"center": [18, 226], "radius": [7, 3.5], "rotation": -0.4},
        {"center": [-4, 236], "radius": [7, 3.5], "rotation": 0.8}]
    P.append(dict(spec=h, par=4, changed=True,
        title="The Count's Lawn", shape="Dogleg left", elevation="Gentle climb to the castle", green="Ringed by four bunkers",
        hazard="Hedge maze in the landing area, moat before the green", landmark="The castle and a drawbridge",
        question="Thread the hedges off the tee, then carry the moat to the rose-bed green.",
        safe=[[0, 0], [22, 190], [-64, 321]], hero=[[0, 0], [8, 200], [-64, 321]],
        notes=[[-22, 206, "Blood pond"], [-43, 288, "Moat and drawbridge"], [8, 226, "Hedge maze"], [20, 148, "Crypt"]],
        today="Adds a hedge maze where drives land; the moat crossing becomes a drawbridge."))
    # 8 -------------------------------------------------------------------------------------------
    h = base(7)
    h["fairway_width"] = [22, 26, 34, 44, 40, 26, 22, 20]
    h["rough_islands"] = [{"center": [-25, 200], "radius": [34, 8], "rotation": 1.19}]
    P.append(dict(spec=h, par=4, changed=True,
        title="The Horseman's Ride", shape="S along a ridge, two routes", elevation="Sidehill, falls right then left", green="Crowned, under the crag",
        hazard="High road on the ridge or low road by the ravine", landmark="A covered bridge over the ravine",
        question="The longest par 4 in a gale: the safe ridge, or the shorter low road over the ravine.",
        safe=[[0, 0], [-40, 190], [10, 300], [36, 373]], hero=[[0, 0], [-8, 195], [36, 373]],
        notes=[[-24, 196, "Ridge spine"], [-1, 250, "Ravine creek"], [22, 262, "Covered bridge"]],
        today="A long ridge splits the fairway into a high road and a low road."))
    # 9 -------------------------------------------------------------------------------------------
    h = base(8)
    h.update({
        "path": [[0, 0], [-4, 60], [-20, 125], [-16, 190], [8, 250], [30, 300], [40, 350], [38, 410]],
        "fairway_width": [26, 30, 32, 32, 30, 28, 26, 24], "fairway_start": 36,
        "green": {"center": [38, 410], "radius": [14, 12], "rotation": 0.1, "slope": [0.01, 0.022]},
        "pin": [40, 413],
        "bunkers": [{"center": [54, 402], "radius": [6, 3.2], "rotation": 0.6, "depth": 0.5},
                    {"center": [24, 424], "radius": [4.4, 2.4], "rotation": -0.5, "depth": 0.45},
                    {"center": [-30, 165], "radius": [7, 3.4], "rotation": -0.2, "depth": 0.45}],
        "water": [{"center": [-46, 96], "radius": [26, 4.5], "rotation": 1.75, "level_offset": -0.7},
                  {"center": [-42, 146], "radius": [26, 4.5], "rotation": 1.5, "level_offset": -0.7},
                  {"center": [10, 372], "radius": [30, 5], "rotation": -0.2, "level_offset": -0.7},
                  {"center": [-14, 372], "radius": [12, 4.5], "rotation": 0.5, "level_offset": -0.7}],
        "carry": [360, 384],
    })
    P.append(dict(spec=h, par=5, changed=True,
        title="The Walk Home", shape="Long S, risk-reward finish", elevation="Climbs to the village", green="Punchbowl, ringed by lanterns",
        hazard="A stream in front of the green: go for it in two?", landmark="The village square, lit for the homecoming",
        question="The finale: lay up short of the stream, or go for the green in two and finish with a roar.",
        safe=[[0, 0], [-14, 210], [34, 350], [40, 413]], hero=[[0, 0], [-14, 210], [40, 413]],
        notes=[[-44, 120, "Stream"], [10, 372, "Stream in front of the green"], [60, 440, "Village square"]],
        today="Becomes a par 5 finale you can reach in two."))
    return P
