# Mesin editing video vertikal Barokah Farm / Otomaya.
# python3 edit.py spec/V1.json            -> out/<id>.mp4
# python3 edit.py spec/V1.json --preview  -> hanya timeline + contact sheet cepat
import json, os, sys, subprocess, math, hashlib, re, random
import numpy as np
from scipy.io import wavfile
from gaya import GAYA
from kata import kata_klip

E = os.path.dirname(os.path.abspath(__file__))
S = os.path.dirname(E)
RAW = os.environ.get('RAW', f'{S}/raw')
ANA = f'{S}/ana'
W, H, FPS, SR = 1080, 1920, 30, 48000
CACHE = f'{E}/cache'; os.makedirs(CACHE, exist_ok=True)
FONTS = f'{E}/fonts'

def sh(cmd, quiet=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print('PERINTAH GAGAL:', ' '.join(cmd)[:600]); print(r.stderr[-3000:]); sys.exit(1)
    return r.stdout

_meta = {}
def meta(src):
    if src in _meta: return _meta[src]
    p = f'{RAW}/{src}.mp4'
    o = json.loads(sh(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate:stream_side_data=rotation:format=duration', '-of', 'json', p]))
    st = o['streams'][0]; w, h = st['width'], st['height']
    rot = 0
    for sd in st.get('side_data_list', []) or []:
        if 'rotation' in sd: rot = int(sd['rotation'])
    if abs(rot) == 90: w, h = h, w
    a, b = st['r_frame_rate'].split('/')
    m = dict(w=w, h=h, fps=float(a)/float(b), dur=float(o['format']['duration']), path=p)
    _meta[src] = m; return m

_faces = None
def face_track(src):
    global _faces
    if _faces is None:
        try: _faces = json.load(open(f'{ANA}/wajah.json'))
        except Exception: _faces = {}
    rows = sorted([r for r in _faces.get(src, []) if r[3] > 0.04])
    if not rows: return []
    t = np.array([r[0] for r in rows]); x = np.array([r[1] for r in rows])
    # median bergulir +-1.0 s, lalu buang pencilan
    sm = np.array([np.median(x[np.abs(t - ti) <= 1.0]) for ti in t])
    return list(zip(t, sm))

def cam_path(src, a, b, c_start, dz=0.05):
    """jalur kamera (t relatif, cx) yang mengikuti wajah dengan zona mati; None bila diam"""
    tr = [(t, x) for t, x in face_track(src) if a - 0.6 <= t <= b + 0.6]
    if len(tr) < 2: return None
    ts = np.arange(a, b + 0.25, 0.25)
    fx = np.interp(ts, [t for t, _ in tr], [x for _, x in tr])
    c = c_start; cs = []
    for x in fx:
        if x - c > dz: c = x - dz
        elif c - x > dz: c = x + dz
        cs.append(c)
    cs = np.convolve(np.pad(cs, 4, mode='edge'), np.ones(9)/9, 'valid')
    if cs.max() - cs.min() < 0.03: return None
    return [[round(float(t - a), 2), round(float(x), 4)] for t, x in zip(ts, cs)]

def face_cx(src, a, b):
    tr = [x for t, x in face_track(src) if a - 0.3 <= t <= b + 0.3]
    if not tr: return None
    return float(np.median(tr))

# ---------------------------------------------------------------- timeline
class TL:
    def __init__(s):
        s.shots = []; s.voice = []; s.amb = []; s.words = []; s.texts = []; s.sfx = []; s.t = 0.0; s.bounds = []

def build(spec):
    G = GAYA[spec['gaya']]; tl = TL(); R = random.Random(spec.get('seed', 1))
    za, zb = G['zoom_alt']; alt = 0
    lambat_def = G.get('lambat', 1.0)
    for bi, b in enumerate(spec['bagian']):
        j = b['jenis']
        if bi > 0:
            tr = b.get('transisi') or (G['transisi']['broll'] if j in ('broll', 'penutup') else G['transisi']['antar_bagian'])
            tl.bounds.append((tl.t, tr))
        if j == 'bicara':
            src = b['src']; a0, a1 = b['in'], b['out']
            words = [w for w in kata_klip(src) if w['t0'] >= a0 - 0.05 and w['t1'] <= a1 + 0.3]
            # potong jeda: pecah jadi potongan bila jeda > rapat detik
            pieces = [[a0, a1]]
            gap = b.get('rapat', 0.45)
            if gap and words:
                pieces = []; cur = [max(a0, words[0]['t0'] - 0.12), None]
                for w1, w2 in zip(words, words[1:]):
                    g = w2['t0'] - w1['t1']
                    if g > gap:
                        cur[1] = w1['t1'] + 0.12; pieces.append(cur); cur = [w2['t0'] - 0.12, None]
                    elif b.get('potong_kalimat', True) and re.search(r'[.,!?]$', w1['w']) and w2['t0'] - cur[0] > 2.4:
                        mid = (w1['t1'] + w2['t0']) / 2  # jump cut di akhir kalimat tanpa membuang suara
                        cur[1] = mid; pieces.append(cur); cur = [mid, None]
                cur[1] = min(a1, words[-1]['t1'] + 0.18); pieces.append(cur)
            for k in b.get('buang', []):  # rentang sumber yang dibuang [x,y]
                np2 = []
                for p0, p1 in pieces:
                    if k[1] <= p0 or k[0] >= p1: np2.append([p0, p1]); continue
                    if k[0] > p0: np2.append([p0, k[0]])
                    if k[1] < p1: np2.append([k[1], p1])
                pieces = np2
            seg_start = tl.t; dipakai = set()
            cx = b.get('cx') or face_cx(src, a0, a1) or 0.5
            for pi, (p0, p1) in enumerate(pieces):
                d = round((p1 - p0) * FPS) / FPS; p1 = p0 + d  # durasi pas kelipatan frame
                if d < 0.15: continue
                z = (za, zb)[alt % 2] if b.get('zoom', True) else za; alt += 1
                if pi > 0: tl.bounds.append((tl.t, G['transisi']['bicara']))
                c0 = c1 = b.get('cx') or face_cx(src, p0, p1) or cx
                path = None if b.get('cx') else cam_path(src, p0, p1, c0)
                tl.shots.append(dict(kind='A', src=src, a=p0, dur=d, z0=z, z1=z + 0.02, cx=c0, cx1=c1, path=path, cy=b.get('cy', 0.42), start=tl.t, fit=b.get('fit', 'crop')))
                tl.voice.append(dict(src=src, a=p0, b=p1, start=tl.t))
                for wi_, w in enumerate(words):
                    if wi_ in dipakai: continue
                    if w['t0'] >= p0 - 0.02 and w['t0'] < p1:
                        dipakai.add(wi_)
                        tl.words.append(dict(w=w['w'], t0=tl.t + w['t0'] - p0, t1=tl.t + min(w['t1'], p1) - p0))
                tl.t += d
            seg_dur = tl.t - seg_start
            # sisipan B-roll di atas suara (cutaway). at: detik dari awal bagian ini (setelah dirapatkan)
            for c in b.get('sisip', []):
                t0 = seg_start + c['at']; t1 = min(seg_start + seg_dur, t0 + c['dur'])
                tl.shots.append(dict(kind='B', src=c['src'], a=c['in'], dur=t1 - t0, z0=1.0, z1=1.0 + G['gerak_broll'][1], cx=c.get('cx', 0.5), cy=0.5,
                                     start=t0, overlay=True, lambat=c.get('lambat', 1.0), fit=c.get('fit', 'crop')))
            for kk in b.get('kata', []):
                tl.texts.append(dict(kind='kunci', t0=seg_start + kk['at'], t1=seg_start + kk['at'] + kk.get('dur', 1.6), teks=kk['teks'], y=kk.get('y')))
                if G['sfx']['kunci']: tl.sfx.append((seg_start + kk['at'], G['sfx']['kunci']))
            for tt in b.get('teks', []):
                tl.texts.append(dict(kind=tt.get('kind', 'kunci'), t0=seg_start + tt['at'], t1=seg_start + tt['at'] + tt.get('dur', 2.0), teks=tt['teks'], y=tt.get('y'), sub2=tt.get('sub2')))
        elif j in ('broll', 'penutup'):
            items = b['klip'] if 'klip' in b else [b]
            lam = b.get('lambat', lambat_def)
            seg_start = tl.t
            for ci, c in enumerate(items):
                d = round(c.get('dur', b.get('dur', 2.5)) * FPS) / FPS
                if ci > 0: tl.bounds.append((tl.t, c.get('transisi') or G['transisi']['broll']))
                mv = c.get('gerak', G['gerak_broll'][0])
                zz = G['gerak_broll'][1]
                z0, z1 = (1.0, 1.0 + zz) if R.random() < 0.6 else (1.0 + zz, 1.0)
                if mv == 'punch': z0, z1 = 1.0 + zz, 1.0
                tl.shots.append(dict(kind='B', src=c['src'], a=c['in'], dur=d, z0=c.get('z0', z0), z1=c.get('z1', z1), cx=c.get('cx', 0.5), cy=c.get('cy', 0.5),
                                     start=tl.t, lambat=c.get('lambat', lam), fit=c.get('fit', b.get('fit', 'crop')), gerak=mv, blur=(j == 'penutup')))
                if c.get('suara', b.get('suara', 0)):
                    tl.amb.append(dict(src=c['src'], a=c['in'], dur=d, start=tl.t, gain=c.get('suara', b.get('suara')), lambat=c.get('lambat', lam)))
                tl.t += d
            for tt in b.get('teks', []):
                tl.texts.append(dict(kind=tt.get('kind', 'kunci'), t0=seg_start + tt.get('at', 0), t1=seg_start + tt.get('at', 0) + tt.get('dur', tl.t - seg_start - tt.get('at', 0)), teks=tt['teks'], y=tt.get('y'), sub2=tt.get('sub2')))
                if G['sfx']['kunci'] and tt.get('kind', 'kunci') == 'kunci': tl.sfx.append((seg_start + tt.get('at', 0), G['sfx']['kunci']))
            if j == 'penutup':
                tl.texts.append(dict(kind='penutup', t0=seg_start + 0.15, t1=tl.t, teks=b.get('cta', '')))
    for t, tr in tl.bounds:
        if tr != 'cut' and tr[0] and G['sfx']['transisi']: tl.sfx.append((t - 0.12, G['sfx']['transisi']))
    return tl, G

# ---------------------------------------------------------------- video per shot
def vf_shot(sh_, G, dur_out, m):
    """filter: sumber -> 1080x1920, gerak zoom, grade"""
    lam = sh_.get('lambat', 1.0)
    f = []
    if lam != 1.0: f.append(f'setpts={lam}*PTS')
    f.append(f'fps={FPS}')
    sw, sh2 = m['w'], m['h']
    z0, z1 = sh_['z0'], sh_['z1']
    D = max(dur_out, 0.04)
    zt = f'({z0}+({z1}-{z0})*min(t/{D:.3f},1))'
    if sh_.get('fit') == 'blur' and sw > sh2:
        # video mendatar utuh di tengah + latar blur
        f.append('split=2[bg][fg];[bg]scale=-2:1920,crop=1080:1920,boxblur=30:3,eq=brightness=-0.08[bgb];'
                 f"[fg]scale=1080:-2:eval=frame[fgs];[bgb][fgs]overlay=(W-w)/2:(H-h)/2-60")
    else:
        # crop 9:16 di sekitar cx, lalu zoom halus (scale per-frame + crop tengah)
        if sw / sh2 > W / H:
            cw = sh2 * W / H; ch = sh2
        else:
            cw = sw; ch = sw * H / W
        cl = lambda c: min(max(c * sw, cw/2), sw - cw/2)
        cx = cl(sh_.get('cx', 0.5)); cx1 = cl(sh_.get('cx1', sh_.get('cx', 0.5)))
        cy = min(max(sh_.get('cy', 0.5) * sh2, ch/2), sh2 - ch/2)
        x0 = int(cx - cw/2); x1 = int(cx1 - cw/2); y0 = int(cy - ch/2)
        if sh_.get('path'):
            P = [(t, cl(x) - cw/2) for t, x in sh_['path']]
            e = f'{P[-1][1]:.1f}'
            for (ta, xa), (tb, xb) in reversed(list(zip(P, P[1:]))):
                e = f'if(lt(t,{tb:.2f}),{xa:.1f}+({xb - xa:.1f})*(t-{ta:.2f})/{tb - ta:.2f},{e})'
            f.append(f"crop={int(cw)//2*2}:{int(ch)//2*2}:'max(0,min({sw - int(cw)//2*2},{e}))':{y0}")
        elif abs(x1 - x0) < 8:
            f.append(f'crop={int(cw)//2*2}:{int(ch)//2*2}:{x0}:{y0}')
        else:  # geser halus mengikuti wajah (ease in-out)
            f.append(f"crop={int(cw)//2*2}:{int(ch)//2*2}:'{x0}+({x1 - x0})*(0.5-0.5*cos(PI*min(t/{D:.3f},1)))':{y0}")
        if z0 == z1 == 1.0:
            f.append(f'scale={W}:{H}:flags=lanczos')
        else:
            mz = max(z0, z1)
            f.append(f"scale=w='trunc({W}*{zt}/2)*2':h='trunc({H}*{zt}/2)*2':eval=frame:flags=bicubic")
            ox = '(iw-ow)/2'; oy = f"(ih-oh)*{sh_.get('fy', 0.40)}"
            if sh_.get('gerak') == 'handheld':
                ox = '(iw-ow)/2+6*sin(t*1.7)'; oy = '(ih-oh)/2+5*sin(t*1.3+1)'
            f.append(f"crop={W}:{H}:'{ox}':'{oy}'")
    if sh_.get('blur'): f.append('boxblur=14:2,eq=brightness=-0.12')
    f.append(G['grade'])
    if G.get('letterbox') and sh_['kind'] == 'B':
        f.append('drawbox=0:0:1080:150:black:t=fill,drawbox=0:1770:1080:150:black:t=fill')
    f.append('format=yuv420p')
    return ','.join(f)

def render_shot(i, s, G, handle, key):
    m = meta(s['src'])
    dur = s['dur'] + handle
    lam = s.get('lambat', 1.0)
    need = dur / lam
    a = s['a']
    if a + need > m['dur'] - 0.05:  # mundurkan awal bila kurang
        a = max(0, m['dur'] - 0.05 - need)
    h = hashlib.md5(json.dumps([s, handle, G['grade'], G.get('letterbox'), a], sort_keys=True).encode()).hexdigest()[:12]
    out = f'{CACHE}/shot_{h}.mp4'
    if not os.path.exists(out):
        vf = vf_shot(s, G, dur, m)
        sh(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-ss', f'{a:.3f}', '-t', f'{need + 0.2:.3f}', '-i', m['path'], '-an',
            '-filter_complex', f'[0:v]{vf}[v]', '-map', '[v]', '-t', f'{dur:.3f}', '-r', str(FPS),
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-threads', '2', out + '.tmp.mp4'])
        os.rename(out + '.tmp.mp4', out)
    return out

def assemble(tl, G, out):
    # lapisan utama (tidak overlay) berurutan; overlay (cutaway) ditumpuk setelahnya
    main = [s for s in tl.shots if not s.get('overlay')]
    trans = {round(t, 3): tr for t, tr in tl.bounds}
    files = []; Ts = []
    for k, s in enumerate(main):
        nxt = main[k+1] if k+1 < len(main) else None
        tr = trans.get(round(nxt['start'], 3), 'cut') if nxt else 'cut'
        T = 0 if tr == 'cut' else tr[1]
        files.append(render_shot(k, s, G, T if T else 2/FPS, 'm'))
        Ts.append((tr, T))
    ov = [s for s in tl.shots if s.get('overlay')]
    ovf = [render_shot(100+k, s, G, 0.0, 'o') for k, s in enumerate(ov)]
    args = ['ffmpeg', '-nostdin', '-y', '-loglevel', 'error']
    for f in files + ovf: args += ['-i', f]
    fc = []; cur = '[0:v]'; acc = main[0]['dur']
    for k in range(1, len(main)):
        tr, T = Ts[k-1]
        name = 'fade' if tr == 'cut' else tr[0]
        dd = 1/FPS if tr == 'cut' else T
        o = f'[x{k}]'
        fc.append(f'{cur}[{k}:v]xfade=transition={name}:duration={dd:.4f}:offset={acc:.4f}{o}')
        cur = o; acc += main[k]['dur']
    for k, s in enumerate(ov):
        idx = len(files) + k
        o = f'[o{k}]'
        fc.append(f"[{idx}:v]setpts=PTS-STARTPTS+{s['start']:.4f}/TB,fade=t=in:st={s['start']:.3f}:d=0.12:alpha=1,format=yuva420p[ov{k}]")
        fc.append(f"{cur}[ov{k}]overlay=eof_action=pass:enable='between(t,{s['start']:.3f},{s['start']+s['dur']:.3f})'{o}")
        cur = o
    fc.append(f'{cur}trim=0:{tl.t:.4f},setpts=PTS-STARTPTS,format=yuv420p[vout]')
    args += ['-filter_complex', ';'.join(fc), '-map', '[vout]', '-r', str(FPS), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-threads', '2', out]
    sh(args)

# ---------------------------------------------------------------- audio
VOICE_CHAIN = ('highpass=f=85,lowpass=f=13000,afftdn=nr=12:nf=-42:tn=1,'
               'equalizer=f=220:t=q:w=1.0:g=-2.5,equalizer=f=3200:t=q:w=1.3:g=3,equalizer=f=7500:t=q:w=1.5:g=1.5,'
               'acompressor=threshold=-22dB:ratio=3.5:attack=4:release=140:makeup=5,'
               'loudnorm=I=-16:TP=-1.5:LRA=6')

def wav_src(src, kind):
    out = f'{CACHE}/aud_{src}_{kind}.wav'
    if not os.path.exists(out):
        af = VOICE_CHAIN if kind == 'voice' else 'highpass=f=60,loudnorm=I=-24:TP=-3'
        sh(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-i', meta(src)['path'], '-vn', '-ac', '2', '-ar', str(SR), '-af', af, out])
    sr, y = wavfile.read(out); return y.astype(np.float32) / 32768

def place(buf, y, t, fade=0.01):
    i = int(t * SR); n = min(len(y), len(buf) - i)
    if n <= 0: return
    y = y[:n].copy(); f = max(1, int(fade * SR))
    if n > 2*f:
        y[:f] *= np.linspace(0, 1, f)[:, None]; y[-f:] *= np.linspace(1, 0, f)[:, None]
    buf[i:i+n] += y

def sfx(kind):
    n = int(0.6 * SR); t = np.arange(n) / SR; rng = np.random.default_rng(len(kind))
    if kind == 'whoosh':
        nz = rng.standard_normal(n); env = np.exp(-((t - 0.22) / 0.11) ** 2)
        from scipy.signal import butter, sosfilt
        lo = sosfilt(butter(2, [400, 5000], 'band', fs=SR, output='sos'), nz)
        y = lo * env * 0.25
    elif kind == 'pop':
        y = np.sin(2*np.pi*(900 - 500*t) * t) * np.exp(-t * 40) * 0.3
    elif kind == 'impact':
        y = (np.sin(2*np.pi*55*t) * np.exp(-t*7) * 0.6 + rng.standard_normal(n) * np.exp(-t*25) * 0.15)
    else:
        y = np.zeros(n)
    return np.stack([y, y], 1).astype(np.float32)

def lufs(path):
    o = subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-i', path, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    m = re.findall(r'I:\s+(-?[\d.]+) LUFS', o)
    return float(m[-1]) if m else -70.0

def mix_audio(tl, G, spec, out):
    n = int((tl.t + 0.05) * SR)
    V = np.zeros((n, 2), np.float32); A = np.zeros((n, 2), np.float32); X = np.zeros((n, 2), np.float32)
    for v in tl.voice:
        y = wav_src(v['src'], 'voice'); place(V, y[int(v['a']*SR):int(v['b']*SR)], v['start'], 0.012)
    for a in tl.amb:
        y = wav_src(a['src'], 'amb'); lam = a.get('lambat', 1.0)
        seg = y[int(a['a']*SR):int((a['a'] + a['dur']/lam)*SR)]
        if lam != 1.0 and len(seg) > 10:  # perlambat dengan resample sederhana (nada turun, cocok untuk suasana)
            idx = np.linspace(0, len(seg)-1, int(len(seg)*lam)); seg = np.stack([np.interp(idx, np.arange(len(seg)), seg[:, k]) for k in range(2)], 1).astype(np.float32)
        place(A, seg * (10 ** (a['gain'] / 20)), a['start'], 0.15)
    for t, k in tl.sfx:
        if k: place(X, sfx(k) * 0.7, max(0, t), 0.002)
    # musik
    mz = spec.get('musik', {})
    gy = mz.get('gaya') or G['musik'][0]
    mfile = f"{CACHE}/musik_{spec['id']}_{gy}_{mz.get('seed', 1)}_{tl.t:.2f}.wav"
    drop = mz.get('drop', 0)
    if not os.path.exists(mfile):
        sh([sys.executable, f'{E}/musik.py', gy, f'{tl.t + 0.3:.2f}', mfile, '--seed', str(mz.get('seed', 1)), '--drop', str(drop)])
    sr, m = wavfile.read(mfile); m = m.astype(np.float32) / 32768
    if sr != SR:
        idx = np.linspace(0, len(m)-1, int(len(m)*SR/sr)); m = np.stack([np.interp(idx, np.arange(len(m)), m[:, k]) for k in range(2)], 1).astype(np.float32)
    M = np.zeros((n, 2), np.float32); M[:min(n, len(m))] = m[:n]
    # level musik ke target LUFS (ukur cepat via RMS berbobot sederhana -> pakai ffmpeg di file)
    ml = lufs(mfile); M *= 10 ** ((G['musik_db'] + mz.get('db', 0) - ml) / 20)
    # ducking dari amplop suara
    env = np.sqrt(np.convolve((V**2).mean(1), np.ones(int(0.05*SR))/int(0.05*SR), 'same'))
    act = (env > 10 ** (-38/20)).astype(np.float32)
    # tahan 250 ms, attack 80 ms, release 400 ms
    hold = int(0.25*SR); act = np.convolve(act, np.ones(hold), 'same') > 0
    g = np.where(act, 10 ** (G['duck_db'] / 20), 1.0).astype(np.float32)
    a_, r_ = 1 - math.exp(-1/(0.08*SR)), 1 - math.exp(-1/(0.4*SR))
    sm = np.empty_like(g); s0 = 1.0
    for i in range(0, len(g), 64):  # blok 64 sampel agar cepat
        tgt = g[i]; c = a_ if tgt < s0 else r_; s0 += (tgt - s0) * (1 - (1-c)**64); sm[i:i+64] = s0
    M *= sm[:, None]
    mix = V + A + X * 0.8 + M
    tmp = out + '.pre.wav'; wavfile.write(tmp, SR, np.clip(mix, -1, 1))
    L = lufs(tmp); gain = -14.0 - L
    sh(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-i', tmp, '-af', f'volume={gain:.2f}dB,alimiter=limit=0.84:attack=3:release=60', '-ar', str(SR), out])
    os.remove(tmp)
    return dict(lufs_awal=L, musik=gy)

# ---------------------------------------------------------------- teks (ASS)
def ass_time(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f'{h}:{m:02d}:{s:05.2f}'

def esc(s): return s.replace('{', '(').replace('}', ')').replace('\\n', '\\N').replace('\n', '\\N')

def make_ass(tl, G, spec, out):
    sb = G['sub']; k = G['kunci']
    bold = -1 if sb['bold'] else 0
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{G['font']},{sb['size']},{sb['warna']},&H000000FF,&H00101010,{'&H8C000000' if sb['box'] else '&H64000000'},{bold},0,0,0,100,100,0,0,{3 if sb['box'] else 1},{12 if sb['box'] else sb['outline']},{sb['shadow']},2,70,70,0,1
Style: Kunci,{k['font']},{k['size']},{k['warna']},&H000000FF,&H00101010,&H64000000,-1,0,0,0,100,100,0,0,1,{k['outline']},{3 if k['outline']==0 else 0},5,60,60,0,1
Style: Kartu,{k['font']},{int(k['size']*0.9)},&H00FFFFFF,&H000000FF,&H00256E2C,&H00256E2C,-1,0,0,0,100,100,0,0,3,30,0,5,60,60,0,1
Style: Kecil,{G['font']},54,&H00FFFFFF,&H000000FF,&H00101010,&H64000000,-1,0,0,0,100,100,0,0,1,4,0,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    # subtitle per potongan kata
    ws = tl.words; per = sb['kata_per']; chunks = []; cur = []
    for w in ws:
        cur.append(w)
        end_sent = re.search(r'[.,!?]$', w['w'])
        if len(cur) >= per or end_sent: chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    for ci, c in enumerate(chunks):
        t0 = c[0]['t0']; t1 = c[-1]['t1']
        if ci + 1 < len(chunks): t1 = min(max(t1, t0 + 0.35), chunks[ci+1][0]['t0'])
        # jangan tampil di atas kartu penutup
        txts = []
        for wi, w in enumerate(c):
            word = w['w'].strip()
            word = re.sub(r'[,.]$', '', word) if per <= 3 else word
            if sb['upper']: word = word.upper()
            txts.append((w['t0'], w['t1'], esc(word)))
        y = sb['y']
        if sb['sorot'] != sb['warna']:
            # sorot kata yang sedang diucapkan: satu event per kata aktif
            for wi, (a, b, _) in enumerate(txts):
                b2 = txts[wi+1][0] if wi + 1 < len(txts) else t1
                line = ' '.join((('{\\c' + sb['sorot'] + '&\\fscx108\\fscy108}' + tx + '{\\c' + sb['warna'] + '&\\fscx100\\fscy100}') if j == wi else tx) for j, (_, _, tx) in enumerate(txts))
                pop = '{\\fad(60,0)}' if wi == 0 else ''
                ev.append(f"Dialogue: 2,{ass_time(a if wi else t0)},{ass_time(b2)},Sub,,0,0,0,,{{\\an2\\pos({W//2},{y})}}{pop}{line}")
        else:
            ev.append(f"Dialogue: 2,{ass_time(t0)},{ass_time(t1)},Sub,,0,0,0,,{{\\an2\\pos({W//2},{y})\\fad(120,80)}}{' '.join(t for _, _, t in txts)}")
    for t in tl.texts:
        a, b = t['t0'], t['t1']; tx = esc(t['teks']); y = t.get('y') or k['y']
        if t['kind'] == 'kunci':
            an = k['anim']
            if an == 'pop':
                fx = f"{{\\an5\\pos({W//2},{y})\\fscx40\\fscy40\\t(0,140,\\fscx112\\fscy112)\\t(140,240,\\fscx100\\fscy100)\\fad(0,150)}}"
            elif an == 'slam':
                fx = f"{{\\an5\\pos({W//2},{y})\\fscx180\\fscy180\\alpha&HFF&\\t(0,110,\\fscx100\\fscy100\\alpha&H00&)\\fad(0,120)}}"
            elif an == 'tulis':
                fx = f"{{\\an5\\pos({W//2},{y})\\frz-4\\fad(200,200)\\clip(0,0,0,{H})\\t(0,500,\\clip(0,0,{W},{H}))}}"
            elif an == 'kartu':
                fx = f"{{\\an5\\move({W//2},{y+60},{W//2},{y},0,180)\\fad(150,150)}}"
            else:
                fx = f"{{\\an5\\pos({W//2},{y})\\fad(400,400)}}"
            st = 'Kartu' if an == 'kartu' else 'Kunci'
            ev.append(f"Dialogue: 5,{ass_time(a)},{ass_time(b)},{st},,0,0,0,,{fx}{tx}")
            if t.get('sub2'):
                ev.append(f"Dialogue: 5,{ass_time(a+0.15)},{ass_time(b)},Kecil,,0,0,0,,{{\\an5\\pos({W//2},{y + int(k['size']*(1.15 if k['anim']=='kartu' else 0.8))})\\fad(200,150)}}{esc(t['sub2'])}")
        elif t['kind'] == 'judul':
            ev.append(f"Dialogue: 6,{ass_time(a)},{ass_time(b)},Kunci,,0,0,0,,{{\\an5\\pos({W//2},{y})\\fscx60\\fscy60\\t(0,200,\\fscx100\\fscy100)\\fad(0,200)}}{tx}")
            if t.get('sub2'):
                ev.append(f"Dialogue: 6,{ass_time(a+0.2)},{ass_time(b)},Kecil,,0,0,0,,{{\\an5\\pos({W//2},{y + int(k['size']*0.85)})\\fad(200,200)}}{esc(t['sub2'])}")
    open(out, 'w').write(head + '\n'.join(ev) + '\n')

# ---------------------------------------------------------------- kartu penutup (HTML -> PNG)
def penutup_png(G, spec, out):
    gaya = G['penutup']
    js = f'{E}/penutup.js'
    sh(['node', js, out, gaya, json.dumps(spec.get('penutup', {}))])

def final(tl, G, spec, vid, aud, ass, out):
    logo = f'{E}/aset/logo.png'
    pen = [t for t in tl.texts if t['kind'] == 'penutup']
    args = ['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-i', vid, '-i', aud, '-i', logo]
    fc = [f"[0:v]ass={ass}:fontsdir={FONTS}[v1]"]
    pos = {'kanan_atas': f'W-w-44:96', 'kiri_atas': '44:96', 'tengah_bawah': '(W-w)/2:H-h-170'}[G['logo']]
    pt0 = pen[0]['t0'] if pen else tl.t
    fc.append(f"[2:v]scale=150:-1,format=rgba,colorchannelmixer=aa=0.92[lg]")
    fc.append(f"[v1][lg]overlay={pos}:enable='lt(t,{pt0:.2f})'[v2]")
    cur = '[v2]'
    if pen:
        png = f"{CACHE}/penutup_{spec['id']}.png"; penutup_png(G, spec, png)
        args += ['-loop', '1', '-t', f'{tl.t:.2f}', '-i', png]
        fc.append(f"[3:v]format=rgba,fade=t=in:st={pt0:.2f}:d=0.35:alpha=1[pn]")
        fc.append(f"{cur}[pn]overlay=0:0:enable='gte(t,{pt0:.2f})'[v3]"); cur = '[v3]'
    fc.append(f"{cur}fade=t=out:st={tl.t-0.35:.2f}:d=0.35,format=yuv420p[vo]")
    args += ['-filter_complex', ';'.join(fc), '-map', '[vo]', '-map', '1:a', '-t', f'{tl.t:.3f}',
             '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-maxrate', '10M', '-bufsize', '20M', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-threads', '2',
             '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out]
    sh(args)

def main():
    spec = json.load(open(sys.argv[1]))
    tl, G = build(spec)
    os.makedirs(f'{E}/out', exist_ok=True); wd = f"{CACHE}/{spec['id']}"; os.makedirs(wd, exist_ok=True)
    print(f"[{spec['id']}] gaya={spec['gaya']} durasi={tl.t:.1f}s shot={len(tl.shots)} kata={len(tl.words)}", flush=True)
    json.dump(dict(shots=tl.shots, voice=tl.voice, words=tl.words, texts=tl.texts, bounds=tl.bounds, dur=tl.t), open(f'{wd}/timeline.json', 'w'), indent=1)
    if '--timeline' in sys.argv: return
    make_ass(tl, G, spec, f'{wd}/teks.ass')
    info = mix_audio(tl, G, spec, f'{wd}/mix.wav'); print('  audio', info, flush=True)
    assemble(tl, G, f'{wd}/video.mp4'); print('  video ok', flush=True)
    out = f"{E}/out/{spec.get('file', spec['id'])}.mp4"
    final(tl, G, spec, f'{wd}/video.mp4', f'{wd}/mix.wav', f'{wd}/teks.ass', out)
    print('  SELESAI', out, f'{tl.t:.1f}s', flush=True)

if __name__ == '__main__': main()
