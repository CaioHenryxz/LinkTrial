"""Soundtrack for the LinkTrial brag video: D major at 100 BPM, effects in key, one shared reverb."""
import sys, wave
import numpy as np

LINK, LDUR = 11.0, 2.6  # the patient–trial link card; everything after it runs LDUR later
SR, DUR = 48000, 23.8 + LDUR
def sh(t): return t + LDUR if t >= LINK else t
N = int(SR * DUR)
rng = np.random.default_rng(7)
BEAT = 0.6
t_all = np.arange(N) / SR

def hz(m): return 440 * 2 ** ((m - 69) / 12)
def env(n, a, r):
    e = np.ones(n); ai, ri = int(a * SR), int(r * SR)
    if ai: e[:ai] = np.linspace(0, 1, ai)
    if ri: e[-ri:] *= np.linspace(1, 0, ri)
    return e
def add(buf, start, sig, gain=1.0):
    i = int(start * SR); j = min(N, i + len(sig))
    if i < N: buf[i:j] += sig[:j - i] * gain
def lowpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); acc = 0.0
    for k in range(len(x)): acc = (1 - a) * x[k] + a * acc; y[k] = acc
    return y
def tone(m, dur, harm=(1, .5, .25, .12), decay=None):
    t = np.arange(int(dur * SR)) / SR
    s = sum(a * np.sin(2 * np.pi * hz(m) * (h + 1) * t) for h, a in enumerate(harm))
    return s * (np.exp(-t / decay) if decay else 1)

music, sfx = np.zeros(N), np.zeros(N)
CHORDS = [[50, 54, 57], [47, 50, 54], [43, 47, 50], [45, 49, 52]]  # D Bm G A
BAR = 4 * BEAT

# Pad: soft additive chords, slow attack, a bar each.
for b in range(int(DUR / BAR) + 1):
    ch = CHORDS[b % 4]
    for m in ch + [ch[0] + 12]:
        s = sum(tone(m + d, BAR + .6, harm=(1, .3, .12)) for d in (-.04, .04)) * env(int((BAR + .6) * SR), .5, .7)
        add(music, b * BAR, s, .05)
music[: int(.4 * SR)] *= np.linspace(0, 1, int(.4 * SR))

# Pluck arpeggio (8ths) and soft kick once the app appears; out before the outro.
for k in range(int(3.0 / (BEAT / 2)), int(sh(21.0) / (BEAT / 2))):
    t0 = k * BEAT / 2; ch = CHORDS[int(t0 / BAR) % 4]
    m = (ch + [ch[0] + 12])[k % 4] + 12
    add(music, t0, tone(m, .5, decay=.12) * env(int(.5 * SR), .004, .05), .07)
for k in range(int(3.0 / BEAT), int(sh(21.0) / BEAT)):
    if k % 2 or LINK <= k * BEAT < LINK + 1.1: continue  # kick drops out until the rings lock
    t = np.arange(int(.32 * SR)) / SR
    f = 48 + 70 * np.exp(-t / .04)
    add(music, k * BEAT, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .1), .22)
# Shaker on off-beats from the review scene on.
for k in range(int(8.4 / BEAT), int(sh(21.0) / BEAT)):
    n = rng.standard_normal(int(.06 * SR)); n = n - lowpass(n, 6000)
    add(music, k * BEAT + BEAT / 2, n * np.exp(-np.arange(len(n)) / SR / .015), .03)

# Effects.
def bell(m, dur=1.4): return tone(m, dur, harm=(1, .0, .35, .0, .12), decay=.45) * env(int(dur * SR), .003, .2)
def tock():
    t = np.arange(int(.12 * SR)) / SR
    return (np.sin(2 * np.pi * 1180 * t) * np.exp(-t / .012) + .6 * np.sin(2 * np.pi * 180 * t) * np.exp(-t / .03))
for t0 in (12.25, 15.6, 19.6): add(sfx, sh(t0), tock(), .16)
add(sfx, 7.65, bell(81), .06); add(sfx, 7.75, bell(86), .05)          # pseudonym assigned: A5, D6
add(sfx, sh(16.3), tone(47, .7, harm=(1, .3), decay=.22), .07)            # blocking criterion: soft low B
for i, m in enumerate((74, 78, 81, 86)): add(sfx, sh(19.68) + i * .07, bell(m), .055)  # referral
def whoosh(dur=.45):
    n = rng.standard_normal(int(dur * SR)); w = np.sin(np.linspace(0, np.pi, len(n))) ** 2
    return lowpass(n, 1800) * w
for t0 in (2.75, 8.2, 10.65, 14.6, 18.2): add(sfx, sh(t0), whoosh(), .1)
add(sfx, LINK + LDUR - .35, whoosh(), .1)  # link card leaves
add(sfx, sh(20.95), whoosh(.6), .12)
# The link: rings fly in, shimmer rises, the lock rings out, the head pops.
add(sfx, LINK + .1, whoosh(1.0), .13)
for i in range(10): add(sfx, LINK + .75 + i * .04, bell(86 + i % 5 * 2, .5), .012 + i * .002)
for m in (74, 78, 81, 86): add(sfx, LINK + 1.15, bell(m, 2.2), .05)
add(sfx, LINK + 1.15, tone(38, 1.2, harm=(1, .4), decay=.35), .16)
add(sfx, LINK + 1.47, bell(93, .8), .05)
add(sfx, .1, bell(62, 2.2), .07); add(sfx, .95, bell(69, 2.2), .06)    # hook lines: D4, A4
for m in (50, 57, 62, 66, 69, 74):                                    # outro chord
    add(music, sh(21.3), tone(m, 2.5, harm=(1, .4, .15), decay=1.1) * env(int(2.5 * SR), .01, .6), .06)
add(sfx, sh(21.35), bell(86, 2.4), .05)

# One shared room for music and effects.
ir_t = np.arange(int(1.6 * SR)) / SR
ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t / .35); ir = lowpass(ir, 5000); ir /= np.sqrt((ir ** 2).sum())
def verb(x):
    L = 1 << int(np.ceil(np.log2(len(x) + len(ir))))
    return np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[: len(x)]
mix = music + sfx
mix = mix + .35 * verb(mix)
fade = int(.9 * SR); mix[-fade:] *= np.linspace(1, 0, fade) ** 2
mix = np.tanh(mix / np.abs(mix).max() * 1.4) / np.tanh(1.4) * .89    # gentle soft-clip, peak ≈ -1 dBFS

left = mix + .15 * np.roll(verb(sfx), 240); right = mix + .15 * np.roll(verb(sfx), 480)
st = np.stack([left, right], 1); st = st / np.abs(st).max() * .89
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype("<i2").tobytes())
