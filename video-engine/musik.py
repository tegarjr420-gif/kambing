# Pembuat musik latar (aman hak cipta) dengan soundfont GeneralUser GS.
# python3 musik.py <gaya> <durasi_detik> <out.wav> [--seed N] [--drop DETIK]
# Gaya: akustik, lofi, sinematik, pop, inspirasi, tropis, folk, funk, religi, hiphop
import tinysoundfont, numpy as np, sys, json, random, argparse, os
from scipy.signal import fftconvolve, butter, sosfilt

SF = os.environ.get('SF2', '/home/claude/mrbumpy409/generaluser-gs/GeneralUser-GS.sf2')
SR = 44100

# ---------------- teori musik ----------------
MAJ = [0, 2, 4, 5, 7, 9, 11]
MIN = [0, 2, 3, 5, 7, 8, 10]
def chord(root_deg, scale, key, octave=4, ext=False):
    """akor dari derajat skala (0-based)"""
    ns = []
    for k in (0, 2, 4) + ((6,) if ext else ()):
        d = root_deg + k
        ns.append(12*octave + key + scale[d % 7] + 12*(d // 7))
    return ns

PROG = {
    'maj': [[0, 4, 5, 3], [0, 5, 3, 4], [3, 4, 0, 5], [0, 3, 4, 4], [5, 3, 0, 4], [0, 4, 3, 4]],
    'min': [[0, 5, 2, 6], [0, 3, 6, 2], [5, 6, 0, 0], [0, 6, 5, 6], [0, 3, 4, 0]],
}

# ---------------- gaya ----------------
# prog: kanal -> (bank, preset, drums?)  vol 0-127, pan 0-127, wet = ikut reverb
STYLES = {
    'akustik':   dict(bpm=(98, 108), mode='maj', swing=0.0, kit=0, inst={'gtr': 25, 'bass': 32, 'lead': 73, 'pad': 48}, feel='strum'),
    'lofi':      dict(bpm=(78, 86), mode='maj', swing=0.18, kit=8, inst={'keys': 4, 'bass': 33, 'lead': 11, 'pad': 89}, feel='lofi', ext=True),
    'sinematik': dict(bpm=(80, 92), mode='min', swing=0.0, kit=48, inst={'keys': 0, 'bass': 48, 'lead': 48, 'pad': 49, 'perc': 47}, feel='cine'),
    'pop':       dict(bpm=(116, 124), mode='maj', swing=0.0, kit=24, inst={'keys': 0, 'bass': 38, 'lead': 80, 'pad': 89, 'pluck': 45}, feel='pop'),
    'inspirasi': dict(bpm=(94, 104), mode='maj', swing=0.0, kit=0, inst={'keys': 0, 'bass': 33, 'lead': 48, 'pad': 49}, feel='corp'),
    'tropis':    dict(bpm=(104, 112), mode='maj', swing=0.0, kit=24, inst={'keys': 12, 'bass': 38, 'lead': 114, 'pad': 89}, feel='trop'),
    'folk':      dict(bpm=(96, 106), mode='maj', swing=0.12, kit=0, inst={'gtr': 24, 'bass': 32, 'lead': 78, 'pad': 48, 'banjo': 105}, feel='folk'),
    'funk':      dict(bpm=(100, 108), mode='min', swing=0.1, kit=0, inst={'gtr': 28, 'bass': 36, 'lead': 61, 'keys': 4}, feel='funk', ext=True),
    'religi':    dict(bpm=(84, 94), mode='min', swing=0.0, kit=8, inst={'keys': 0, 'bass': 32, 'lead': 104, 'pad': 49, 'perc': 116}, feel='religi'),
    'hiphop':    dict(bpm=(86, 94), mode='min', swing=0.14, kit=8, inst={'keys': 0, 'bass': 33, 'lead': 4, 'pad': 89}, feel='boom', ext=True),
}
CH = {'keys': 0, 'gtr': 1, 'bass': 2, 'lead': 3, 'pad': 4, 'pluck': 5, 'banjo': 6, 'perc': 7}
WET = {'keys': 0.35, 'gtr': 0.3, 'bass': 0.05, 'lead': 0.45, 'pad': 0.6, 'pluck': 0.35, 'banjo': 0.25, 'perc': 0.5, 'drum': 0.15}
VOL = {'keys': 92, 'gtr': 96, 'bass': 100, 'lead': 84, 'pad': 70, 'pluck': 80, 'banjo': 78, 'perc': 96}
PAN = {'keys': 54, 'gtr': 44, 'bass': 64, 'lead': 76, 'pad': 64, 'pluck': 88, 'banjo': 36, 'perc': 64}

class Song:
    def __init__(s): s.ev = []  # (t, part, note, vel, dur)
    def n(s, part, t, note, vel, dur):
        if t >= 0: s.ev.append((t, part, int(note), int(max(1, min(127, vel))), dur))

def compose(style, dur, seed, drop, bpm_paksa=0):
    st = STYLES[style]; R = random.Random(seed)
    bpm = R.randint(*st['bpm'])
    if bpm_paksa: bpm = bpm_paksa
    beat = 60 / bpm; bar = 4 * beat; six = beat / 4
    key = R.choice([0, 2, 3, 5, 7, 8, 9, 10]) - (12 if R.random() < 0.3 else 0)
    scale = MAJ if st['mode'] == 'maj' else MIN
    prog = R.choice(PROG[st['mode']]); ext = st.get('ext', False)
    nbars = int(np.ceil((dur + 0.5) / bar))
    # intensitas per bar: intro tipis, isi, (drop) penuh, outro
    dbar = int(drop / bar) if drop else max(2, nbars // 3)
    def lvl(b):
        if b < 1: return 0
        if b < dbar: return 1
        if b >= nbars - 1: return 3  # bar terakhir: akor panjang + pukulan akhir
        return 2
    sw = st['swing']
    def T(b, s16): return b*bar + s16*six + (sw*six if s16 % 2 else 0)
    S = Song(); feel = st['feel']
    motif = [R.choice([0, 2, 4, 2, 4, 7, 9, 7]) for _ in range(6)]
    rhythm = sorted(R.sample(range(0, 16, 2), 5))
    for b in range(nbars):
        L = lvl(b); deg = prog[b % 4]
        c = chord(deg, scale, key, 4, ext); root = chord(deg, scale, key, 2)[0]
        last = L == 3
        # ---------- harmoni ----------
        if 'pad' in st['inst'] and (L >= 1 or feel in ('cine', 'religi', 'corp')):
            for x in c[:3]: S.n('pad', T(b, 0), x, 58 if L < 2 else 70, bar*0.98 if not last else bar*1.6)
        if 'gtr' in st['inst']:
            if last: [S.n('gtr', T(b, 0) + i*0.02, x, 84, bar*1.5) for i, x in enumerate([root+12] + c)]
            elif feel == 'strum':
                pat = [0, 3, 6, 8, 10, 12, 14] if L >= 2 else [0, 6, 8, 12]
                for s16 in pat:
                    dn = s16 % 4 == 0
                    for i, x in enumerate(([root+12] + c) if dn else (c[::-1])):
                        S.n('gtr', T(b, s16) + i*0.012, x, (88 if dn else 66) + R.randint(-6, 6), six*2.2)
            elif feel == 'folk':
                arp = [root+12, c[0], c[1], c[2], c[1], c[0], c[2], c[1]]
                for i in range(8): S.n('gtr', T(b, i*2), arp[i] + (12 if i == 3 else 0), 70 + R.randint(-5, 8), beat*0.9)
            elif feel == 'funk':
                for s16 in range(16):
                    if s16 in (2, 6, 10, 14) or (L >= 2 and s16 in (3, 11)):
                        for x in c[1:]: S.n('gtr', T(b, s16), x + 12, 92, six*0.6)
        if 'keys' in st['inst']:
            if last: [S.n('keys', T(b, 0), x, 80, bar*1.6) for x in [root+12] + c]
            elif feel in ('lofi', 'boom'):
                for s16, d in ((0, 2.6), (7, 1.2), (10, 1.6)):
                    for i, x in enumerate(c): S.n('keys', T(b, s16) + i*0.018, x, 66 + R.randint(-8, 6), beat*d)
            elif feel in ('corp', 'cine', 'religi'):
                arp = [c[0], c[1], c[2], c[1] + 12 if feel == 'corp' else c[1]]
                step = 2 if (feel == 'corp' and L >= 1) else 4
                for i, s16 in enumerate(range(0, 16, step)): S.n('keys', T(b, s16), arp[i % 4] + 12, 60 + 10*(L >= 2) + R.randint(-5, 5), six*step*1.4)
            elif feel == 'pop':
                for s16 in (0, 3, 6, 10, 12) if L >= 2 else (0, 8):
                    for x in c: S.n('keys', T(b, s16), x, 72, six*2.5)
            elif feel == 'trop':
                for s16 in (0, 3, 6, 8, 11, 14):
                    S.n('keys', T(b, s16), R.choice(c) + 12, 78 + R.randint(-6, 6), six*2)
            elif feel == 'funk' and L >= 2:
                for x in c: S.n('keys', T(b, 0), x, 60, bar*0.9)
        if 'pluck' in st['inst'] and L >= 2 and not last:
            for s16 in range(0, 16, 2): S.n('pluck', T(b, s16), c[(s16//2) % 3] + 12, 60, six*1.5)
        if 'banjo' in st['inst'] and L >= 2 and not last:
            for s16 in range(0, 16, 2): S.n('banjo', T(b, s16), c[(s16 // 2) % 3] + 12, 56, six*1.8)
        # ---------- bass ----------
        if L >= 1 or feel in ('cine',):
            if last: S.n('bass', T(b, 0), root, 100, bar*1.5)
            elif feel in ('pop', 'trop'):
                for s16 in range(0, 16, 2 if L >= 2 else 4): S.n('bass', T(b, s16), root + (12 if s16 % 8 == 6 and L >= 2 else 0), 96, six*1.6)
            elif feel == 'funk':
                for s16, o, d in ((0, 0, 2), (3, 12, 1), (6, 0, 1), (8, 7, 2), (11, 10, 1), (14, 12, 1)):
                    S.n('bass', T(b, s16), root + o, 104, six*d)
            elif feel == 'cine':
                S.n('bass', T(b, 0), root, 70 + 20*(L >= 2), bar)
            else:
                for s16, o in ((0, 0), (6, 0), (8, 7), (12, 0)) if L >= 2 else ((0, 0), (8, 7)):
                    S.n('bass', T(b, s16), root + o, 96, six*3)
        # ---------- melodi ----------
        if L >= 2 and not last and 'lead' in st['inst'] and (b % 2 == 0 or feel in ('pop', 'trop')):
            for i, s16 in enumerate(rhythm):
                d = (deg + motif[i % len(motif)])
                note = 12*5 + key + scale[d % 7] + 12*(d // 7)
                if b % 4 == 2: note += R.choice([0, 2, -1]) if False else 0
                S.n('lead', T(b, s16), note, 74 + R.randint(-6, 6), six*(3 if feel != 'cine' else 6))
        if feel in ('cine', 'religi') and 'perc' in st['inst'] and L >= 1 and not last:
            for s16 in ((0, 8) if L == 1 else (0, 6, 8, 12, 14)): S.n('perc', T(b, s16), 45 if feel == 'cine' else 48, 90 if s16 == 0 else 70, beat)
        # ---------- drum ----------
        if last:
            S.n('drum', T(b, 0), 49, 100, bar); S.n('drum', T(b, 0), 36, 110, beat)
            continue
        if L == 0: continue
        if feel in ('cine',):
            if L >= 2:
                for s16 in (0, 10): S.n('drum', T(b, s16), 36, 90, six)
                S.n('drum', T(b, 8), 38, 70, six)
            continue
        if feel == 'religi':
            for s16 in (0, 6, 10): S.n('drum', T(b, s16), 36, 78, six)
            for s16 in (4, 12): S.n('drum', T(b, s16), 37 if L == 1 else 39, 70, six)
            for s16 in range(0, 16, 2): S.n('drum', T(b, s16), 70, 45, six)
            continue
        full = L >= 2
        if feel in ('pop', 'trop') and full: kicks = (0, 4, 8, 12)
        elif feel in ('pop', 'trop'): kicks = (0, 8)
        elif feel == 'funk': kicks = (0, 7, 10)
        elif feel in ('boom', 'lofi'): kicks = (0, 7, 10) if full else (0, 10)
        else: kicks = (0, 8, 10) if full else (0, 8)
        for s16 in kicks: S.n('drum', T(b, s16), 36, 104 if s16 == 0 else 92, six)
        snr = 39 if feel in ('pop', 'trop', 'strum', 'folk') else (37 if not full and feel in ('corp', 'lofi') else 38)
        for s16 in (4, 12): S.n('drum', T(b, s16), snr, 96 if full else 74, six)
        hh = 82 if feel in ('strum', 'folk', 'trop') else 42
        step = 2 if feel not in ('funk', 'pop') else 1
        for s16 in range(0, 16, step):
            v = (70 if s16 % 4 == 0 else 52) + R.randint(-6, 6)
            S.n('drum', T(b, s16), hh, v if full else v - 14, six)
        if feel in ('pop', 'trop') and full:
            for s16 in (2, 6, 10, 14): S.n('drum', T(b, s16), 46, 60, six)
        if feel in ('strum', 'folk', 'trop'):
            for s16 in (2, 6, 10, 14): S.n('drum', T(b, s16), 54, 48, six)
        if b == dbar - 1:  # fill + crash menjelang drop
            for i, s16 in enumerate((8, 10, 12, 13, 14, 15)): S.n('drum', T(b, s16), [50, 48, 47, 45, 43, 41][i], 80 + i*4, six)
        if b == dbar or (full and b % 8 == 0): S.n('drum', T(b, 0), 49, 92, bar)
    return S, dict(bpm=bpm, key=key, beat=beat, bar=bar, drop_bar=dbar, drop_t=dbar*bar, nbars=nbars)

def render(S, st, dur):
    def mk():
        sy = tinysoundfont.Synth(samplerate=SR, gain=-6)
        sid = sy.sfload(SF); return sy, sid
    total = int((dur + 3) * SR)
    stems = {}
    for group in ('dry', 'wet'):
        sy, sid = mk(); buf = np.zeros((total, 2), np.float32)
        parts = [p for p in list(st['inst']) + ['drum'] if (WET.get(p, 0) >= 0.3) == (group == 'wet')]
        for p in parts:
            if p == 'drum':
                sy.program_select(9, sid, 128, st['kit'], True); sy.control_change(9, 7, 100)
            else:
                ch = CH[p]; sy.program_select(ch, sid, 0, st['inst'][p]); sy.control_change(ch, 7, VOL[p]); sy.control_change(ch, 10, PAN[p])
        evs = []
        for t, p, n, v, d in S.ev:
            if p not in parts: continue
            ch = 9 if p == 'drum' else CH[p]
            evs.append((t, 1, ch, n, v)); evs.append((t + d, 0, ch, n, 0))
        evs.sort(key=lambda e: (e[0], e[1]))
        pos = 0
        for t, on, ch, n, v in evs:
            i = min(total, int(t * SR))
            if i > pos:
                buf[pos:i] = np.frombuffer(bytes(sy.generate(i - pos)), np.float32).reshape(-1, 2); pos = i
            if on: sy.noteon(ch, n, v)
            else: sy.noteoff(ch, n)
        if pos < total: buf[pos:] = np.frombuffer(bytes(sy.generate(total - pos)), np.float32).reshape(-1, 2)
        stems[group] = buf
    # reverb: IR sintetis (noise meluruh) stereo
    rng = np.random.default_rng(7); n = int(1.8 * SR); tt = np.arange(n) / SR
    ir = np.stack([rng.standard_normal(n) * np.exp(-tt * 3.2) for _ in range(2)], 1).astype(np.float32)
    ir[:int(0.012*SR)] = 0; ir /= np.sqrt((ir**2).sum(0))
    sos = butter(2, [250, 7000], 'band', fs=SR, output='sos')
    wet = stems['wet']
    rv = np.stack([fftconvolve(sosfilt(sos, wet[:, k]), ir[:, k])[:total] for k in range(2)], 1)
    mix = stems['dry'] + wet * 0.8 + rv * 0.35
    return mix

def master(x, dur, fade=1.5):
    n = int(dur * SR); x = x[:n].copy()
    # kompresi bus sederhana + limiter
    env = np.abs(x).max(1); w = int(0.01 * SR)
    env = np.convolve(env, np.ones(w)/w, 'same')
    thr = np.percentile(env, 95) * 0.6 + 1e-6
    g = np.where(env > thr, (thr / env) ** 0.35, 1.0)
    x = x * g[:, None]
    x /= (np.abs(x).max() + 1e-9); x *= 0.89
    fl = int(fade * SR); x[-fl:] *= np.linspace(1, 0, fl)[:, None] ** 1.5
    x[:int(0.02*SR)] *= np.linspace(0, 1, int(0.02*SR))[:, None]
    return x

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('gaya'); ap.add_argument('durasi', type=float); ap.add_argument('out')
    ap.add_argument('--seed', type=int, default=1); ap.add_argument('--drop', type=float, default=0); ap.add_argument('--bpm', type=int, default=0)
    a = ap.parse_args()
    st = STYLES[a.gaya]
    S, info = compose(a.gaya, a.durasi, a.seed, a.drop, a.bpm)
    x = master(render(S, st, a.durasi), a.durasi)
    from scipy.io import wavfile
    wavfile.write(a.out, SR, (x * 32767).astype(np.int16))
    info.update(gaya=a.gaya, seed=a.seed, durasi=a.durasi)
    json.dump(info, open(a.out[:-4] + '.json', 'w'))
    print(json.dumps(info))

if __name__ == '__main__': main()
