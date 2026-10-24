"""Synthesize the game's sound effects (no recordings needed): writes 16-bit mono WAVs.

usage: python3 -I make_sfx.py <out_dir>

  swing       the club whooshing through
  hit_driver  the crack of a driver
  hit_iron    the click of an iron or wedge
  putt        a soft putter tock
  land_grass  the ball thumping down on grass
  land_sand   a puff of sand
  splash      the ball dropping into water, with bubbles
  cup         rattling in and dropping to the bottom
  perfect     a bright two-note chime for a perfect strike
  holed       a spooky celesta run when the ball drops
  thunder     a crack and a long rumble, for the lightning
  hit_wood, hit_stone, hit_soft, hit_leaves   the ball off a trunk, a tombstone, a pumpkin, through leaves
  click       a tiny tick as the pull settles on the mark
  stretch     a short rubbery creak as the slingshot's band stretches
  twang       the band snapping back when it's let go
  chalk       a stick of chalk writing a line on the board (scratchy taps)
  erase       a felt eraser swished across the board
"""
import os
import sys
import wave

import numpy as np
from scipy import signal

RATE = 22050
rng = np.random.default_rng(7)


def t_of(seconds):
    return np.arange(int(seconds * RATE)) / RATE


def env(n, attack, decay):
    """Attack (s) then exponential decay with time constant `decay` (s)."""
    t = np.arange(n) / RATE
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-np.maximum(t - attack, 0) / decay)


def band(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype="band", fs=RATE, output="sos")
    return signal.sosfilt(sos, x)


def low(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="low", fs=RATE, output="sos"), x)


def high(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="high", fs=RATE, output="sos"), x)


def sweep_band(x, f0, f1, width=0.6, block=256):
    """Band-pass with a centre gliding from f0 to f1 over the sound."""
    out = np.zeros_like(x)
    n = len(x)
    for start in range(0, n, block):
        u = start / n
        fc = f0 * (f1 / f0) ** u
        seg = x[max(0, start - 1024):start + block]
        y = band(seg, fc * (1 - width / 2), fc * (1 + width / 2))
        out[start:start + block] = y[-len(x[start:start + block]):]
    return out


def bell(freq, seconds, decay, partials=((1, 1.0), (2.76, 0.35), (5.4, 0.15))):
    t = t_of(seconds)
    y = sum(a * np.sin(2 * np.pi * freq * k * t) * np.exp(-t / (decay / k ** 0.5)) for k, a in partials)
    return y * env(len(t), 0.003, 10.0)


def recorded_thunder(path):
    """The recording, mono at RATE, its quiet lead-in trimmed to a breath before the clap (the game
    already plays thunder a second or two after the flash), faded out over its last half second."""
    import subprocess
    raw = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(RATE),
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    y = np.frombuffer(raw, "<i2").astype(float) / 32768.0
    loud = np.nonzero(np.abs(y) > 0.15 * np.max(np.abs(y)))[0]
    start = max(0, loud[0] - int(0.12 * RATE))
    end = min(len(y), np.nonzero(np.abs(y) > 0.01)[0][-1] + int(0.2 * RATE))
    y = y[start:end]
    fade = int(0.5 * RATE)
    y[-fade:] *= np.linspace(1, 0, fade)
    y[:int(0.02 * RATE)] *= np.linspace(0, 1, int(0.02 * RATE))
    return y


def recorded(path, tail=0.05):
    """A short recording, mono at RATE, from just before its first loud sample to where it dies away."""
    import subprocess
    raw = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(RATE),
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    y = np.frombuffer(raw, "<i2").astype(float) / 32768.0
    peak = np.max(np.abs(y))
    start = max(0, np.nonzero(np.abs(y) > 0.05 * peak)[0][0] - int(0.003 * RATE))
    end = min(len(y), np.nonzero(np.abs(y) > 0.01 * peak)[0][-1] + int(tail * RATE))
    return y[start:end]


def save(out, name, y, gain=0.9):
    y = np.asarray(y, float)
    peak = np.max(np.abs(y)) or 1.0
    y = y / peak * gain
    fade = min(len(y), int(0.01 * RATE))
    y[-fade:] *= np.linspace(1, 0, fade)
    data = (np.clip(y, -1, 1) * 32767).astype("<i2")
    with wave.open(os.path.join(out, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)

    # swing: breathy noise rising in pitch and loudness to the strike, then gone
    n = int(0.42 * RATE)
    t = np.arange(n) / RATE
    shape = np.sin(np.pi * np.clip(t / 0.42, 0, 1)) ** 2.2
    save(out, "swing", sweep_band(rng.standard_normal(n), 350, 2400, 0.9) * shape, 0.55)

    # driver: a crack (bright noise burst and ringing partials) over a short low thump
    n = int(0.35 * RATE)
    t = np.arange(n) / RATE
    crack = high(rng.standard_normal(n), 1800) * env(n, 0.0005, 0.012)
    ring = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((2300, 1.0), (3550, 0.6), (5200, 0.35))) * env(n, 0.0005, 0.05)
    thump = np.sin(2 * np.pi * 110 * t) * env(n, 0.001, 0.035)
    save(out, "hit_driver", crack * 1.2 + ring * 0.45 + thump * 0.6)

    # iron: a tighter, more metallic click
    ring = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((3100, 1.0), (4700, 0.5), (6900, 0.25))) * env(n, 0.0004, 0.03)
    crack = high(rng.standard_normal(n), 2500) * env(n, 0.0004, 0.008)
    save(out, "hit_iron", crack + ring * 0.5 + thump * 0.25)

    # putt: a soft wooden tock
    n = int(0.18 * RATE)
    t = np.arange(n) / RATE
    save(out, "putt", (np.sin(2 * np.pi * 820 * t) + 0.5 * np.sin(2 * np.pi * 1350 * t)) * env(n, 0.001, 0.025)
         + low(rng.standard_normal(n), 1500) * env(n, 0.0005, 0.006) * 0.4, 0.6)

    # landing on grass: a soft, round thump. The body is pitched where a phone speaker can play it
    # (a note dropping 190 -> 105 Hz, with a quieter octave above it), with a soft attack rather than
    # a click, and only a whisper of dull rustle on top: a sharp noise front reads as a snap
    n = int(0.32 * RATE)
    t = np.arange(n) / RATE
    rng.standard_normal(int(0.3 * RATE))                     # (keeps the later sounds' dice as they were)
    lr = np.random.default_rng(21)
    f = 105 + 85 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / RATE
    body = (np.sin(ph) + 0.35 * np.sin(2 * ph)) * env(n, 0.006, 0.075)
    rustle = low(lr.standard_normal(n), 420, 4) * env(n, 0.008, 0.04) * 0.5
    save(out, "land_grass", low(body + rustle, 1200), 0.8)

    # sand: a muffled puff
    n = int(0.45 * RATE)
    save(out, "land_sand", band(rng.standard_normal(n), 300, 2200) * env(n, 0.004, 0.11)
         + np.sin(2 * np.pi * 70 * t_of(0.45)) * env(n, 0.002, 0.05) * 0.5, 0.7)

    # splash: a burst of water noise, then bubbles popping
    n = int(1.1 * RATE)
    t = np.arange(n) / RATE
    burst = band(rng.standard_normal(n), 250, 3500) * env(n, 0.008, 0.16)
    plop = np.sin(2 * np.pi * (180 + 300 * np.exp(-t / 0.05)) * t) * env(n, 0.002, 0.08)
    bubbles = np.zeros(n)
    for k in range(9):
        s = int(rng.uniform(0.12, 0.9) * RATE)
        m = int(0.05 * RATE)
        if s + m < n:
            tt = np.arange(m) / RATE
            f = rng.uniform(500, 1100)
            bubbles[s:s + m] += np.sin(2 * np.pi * f * (1 + 2.5 * tt) * tt) * env(m, 0.002, 0.012) * rng.uniform(0.2, 0.5)
    save(out, "splash", burst + plop * 0.7 + bubbles * 0.6)

    # cup: three rattles round the rim, then the drop to the bottom
    n = int(0.75 * RATE)
    t = np.arange(n) / RATE
    y = np.zeros(n)
    for k, at in enumerate((0.0, 0.07, 0.13)):
        s = int(at * RATE)
        m = int(0.05 * RATE)
        tt = np.arange(m) / RATE
        y[s:s + m] += (np.sin(2 * np.pi * (1700 - 200 * k) * tt) + high(rng.standard_normal(m), 2000) * 0.5) * env(m, 0.0005, 0.01) * (0.6 - 0.12 * k)
    s = int(0.26 * RATE)
    tt = np.arange(n - s) / RATE
    y[s:] += (np.sin(2 * np.pi * 190 * tt) * 0.9 + np.sin(2 * np.pi * 640 * tt) * 0.4) * env(n - s, 0.001, 0.07)
    save(out, "cup", y)

    # perfect: a bright two-note chime
    a = bell(1318.5, 0.9, 0.35)
    b = bell(1975.5, 0.9, 0.35)
    y = np.zeros(int(1.0 * RATE))
    y[:len(a)] += a
    s = int(0.09 * RATE)
    y[s:s + len(b)] += b[:len(y) - s]
    save(out, "perfect", y, 0.5)

    # holed: a spooky celesta run (A minor, rising), with a soft shimmer
    notes = (440.0, 523.25, 659.25, 880.0, 1046.5, 1318.5)
    y = np.zeros(int(1.8 * RATE))
    for k, f in enumerate(notes):
        s = int(k * 0.11 * RATE)
        b = bell(f, 1.2, 0.5)
        y[s:s + len(b)] += b[:len(y) - s] * (0.7 + 0.06 * k)
    shimmer = band(rng.standard_normal(len(y)), 5000, 9000) * env(len(y), 0.3, 0.5) * 0.08
    save(out, "holed", y + shimmer, 0.6)

    # thunder: far off, a long, lumpy low rumble that swells in and rolls away (no crack: heard over
    # a shot it sounded like something hitting something)
    n = int(3.6 * RATE)
    t = np.arange(n) / RATE
    brown = np.cumsum(rng.standard_normal(n))
    brown = high(brown, 25)
    rumble = low(brown, 140, 4) * env(n, 0.6, 1.2) * (0.7 + 0.3 * np.sin(2 * np.pi * 1.3 * t) * np.sin(2 * np.pi * 0.47 * t))
    rng.standard_normal(n)                                   # (keeps the later sounds' dice as they were)
    # a real recording when we have one (art_src/sfx: a CC0 thunderclap and its roll), the rumble if not
    rec = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "art_src", "sfx", "thunder_rubberduck.ogg")
    if os.path.exists(rec):
        save(out, "thunder", recorded_thunder(rec), 0.85)
    else:
        save(out, "thunder", rumble / np.max(np.abs(rumble)), 0.6)

    # click: a tiny tick
    n = int(0.03 * RATE)
    save(out, "click", np.sin(2 * np.pi * 3200 * t_of(0.03)) * env(n, 0.0003, 0.004), 0.4)

    # stretch: rubber creaking, friction noise gliding up with a fast flutter
    n = int(0.16 * RATE)
    t = t_of(0.16)
    creak = sweep_band(rng.standard_normal(n), 380, 900, 0.5)
    creak *= (0.55 + 0.45 * np.sign(np.sin(2 * np.pi * 46 * t))) * env(n, 0.03, 0.06)
    save(out, "stretch", creak / np.max(np.abs(creak)), 0.35)

    # twang: a plucked band dropping in pitch, with the snap of it
    n = int(0.35 * RATE)
    t = t_of(0.35)
    f = 150 + 140 * np.exp(-t / 0.05)
    tone = np.sin(2 * np.pi * np.cumsum(f) / RATE) + 0.35 * np.sin(4 * np.pi * np.cumsum(f) / RATE)
    tone *= env(n, 0.002, 0.08)
    snap = high(rng.standard_normal(n), 1500) * env(n, 0.0005, 0.012)
    save(out, "twang", tone / np.max(np.abs(tone)) + snap * 0.5, 0.6)

    # (the menu's sounds, on their own dice so everything above stays as it was)
    mr = np.random.default_rng(31)
    # chalk: short scratchy strokes, bright noise in quick taps, the way chalk skips across a board
    n = int(0.55 * RATE)
    t = np.arange(n) / RATE
    strokes = np.zeros(n)
    at = 0.0
    while at < 0.5:
        ln = mr.uniform(0.03, 0.08)
        s0, s1 = int(at * RATE), int(min(at + ln, 0.55) * RATE)
        m = s1 - s0
        strokes[s0:s1] += np.sin(np.pi * np.arange(m) / m) ** 0.7 * mr.uniform(0.6, 1.0)
        at += ln + mr.uniform(0.01, 0.04)
    grit = band(mr.standard_normal(n), 1800, 7000) * (0.75 + 0.25 * np.sign(np.sin(2 * np.pi * 160 * t)))
    save(out, "chalk", grit * strokes, 0.35)
    # erase: a soft felt swish back and forth
    n = int(0.5 * RATE)
    t = np.arange(n) / RATE
    swish = np.abs(np.sin(2 * np.pi * 3.0 * t)) ** 1.5 * np.sin(np.pi * t / 0.5)
    save(out, "erase", sweep_band(mr.standard_normal(n), 500, 1400, 0.9) * swish, 0.4)
    # the ball off the props: CC0 recordings in art_src/sfx (see CREDITS.txt), skipped if they're missing
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "art_src", "sfx")
    for name, f, gain in [("hit_wood", "kenney_impactWood_light_000.ogg", 0.8),       # tree trunks
                          ("hit_stone", "kenney_impactGeneric_light_000.ogg", 0.8),   # tombstones
                          ("hit_soft", "kenney_impactSoft_heavy_000.ogg", 0.8),       # pumpkins, lanterns
                          ("hit_leaves", "tinyworlds_leaves01.ogg", 0.6)]:            # through a canopy
        if os.path.exists(os.path.join(src, f)):
            save(out, name, recorded(os.path.join(src, f)), gain)
    print("wrote", sorted(os.listdir(out)))


if __name__ == "__main__":
    main()
