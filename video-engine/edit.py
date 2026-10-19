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
ANA = os.environ.get('ANA', f'{S}/ana')
W, H, FPS, SR = 1080, 1920, 30, 48000
LAND = False  # True = keluaran landscape 1920x1080
def Y(y): return int(y * H / 1920)               # posisi vertikal dirancang untuk 1920, diskalakan
def FS(z): return int(z * (0.85 if LAND else 1))  # ukuran huruf
CACHE = os.environ.get('CACHE', f'{E}/cache'); os.makedirs(CACHE, exist_ok=True)
OUT = os.environ.get('OUT', f'{E}/out')
TH = os.environ.get('FF_THREADS', '2')
VF_VERSI = 3  # naikkan bila filter video berubah agar cache shot dibuat ulang
FONTS = f'{E}/fonts'

def sh(cmd, quiet=True, timeout=3600):
    try: r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print('PERINTAH MACET (timeout):', ' '.join(cmd)[:300], flush=True); sys.exit(1)
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

def face_y(src, a, b):
    global _faces
    face_track(src)
    rows = [r for r in (_faces or {}).get(src, []) if a - 0.3 <= r[0] <= b + 0.3 and r[3] > 0.04]
    return float(np.median([r[2] for r in rows])) if rows else 0.33

def face_cx(src, a, b):
    tr = [x for t, x in face_track(src) if a - 0.3 <= t <= b + 0.3]
    if not tr: return None
    return float(np.median(tr))

_klip = None
def perlu_stab(src):
    """stabilisasi bila klip terdeteksi goyang (analisa.py -> klip.json); klip lama tanpa data: pakai pola nama HP"""
    global _klip
    if _klip is None:
        try: _klip = json.load(open(f'{ANA}/klip.json'))
        except Exception: _klip = {}
    k = _klip.get(src)
    if k and 'goyang' in k: return k['goyang'] >= 0.5
    return src.startswith('VID_')

# ---------------------------------------------------------------- koreksi warna otomatis
_cc = None
def cc_shot(src, a, b):
    """statistik warna 3 frame -> gain RGB (white balance) + gamma (exposure), disamakan antar-shot"""
    global _cc
    if _cc is None:
        try: _cc = json.load(open(f'{CACHE}/cc.json'))
        except Exception: _cc = {}
    key = f'{src}|{a:.2f}|{b:.2f}'
    if key not in _cc:
        ms = []
        for t in (a + 0.1, (a + b) / 2, max(a + 0.1, b - 0.15)):
            raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-ss', f'{t:.2f}', '-i', meta(src)['path'], '-frames:v', '1',
                                  '-vf', 'scale=160:-2', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
            if raw: ms.append(np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(np.float32) / 255)
        px = np.concatenate(ms) if ms else np.full((10, 3), 0.45, np.float32)
        lum = px @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        mid = px[(lum > 0.12) & (lum < 0.88)]  # abaikan langit putih & bayangan pekat
        if len(mid) < 50: mid = px
        mean = mid.mean(0); y = float(np.median(lum))
        _cc[key] = [float(x) for x in mean] + [y]
        json.dump(_cc, open(f'{CACHE}/cc.json', 'w'))
    r, g, b_, y = _cc[key]
    gray = (r + g + b_) / 3
    gains = [min(1.08, max(0.93, (gray / max(c, 1e-3)) ** 0.5)) for c in (r, g, b_)]
    target = 0.44
    gamma = min(1.22, max(0.85, math.log(max(y, 0.05)) / math.log(target)))
    return dict(rr=round(gains[0], 3), gg=round(gains[1], 3), bb=round(gains[2], 3), gamma=round(gamma, 3))

def ease_expr(keys, var='t'):
    """keyframe [(t, v), ...] -> ekspresi ffmpeg dengan easing smoothstep"""
    if len(keys) == 1: return f'{keys[0][1]}'
    e = f'{keys[-1][1]}'
    for (ta, va), (tb, vb) in reversed(list(zip(keys, keys[1:]))):
        u = f'(({var}-{ta:.3f})/{max(tb - ta, 1e-3):.3f})'
        e = f'if(lt({var},{tb:.3f}),{va}+({vb - va:.4f})*{u}*{u}*(3-2*{u}),{e})'
    return f'if(lt({var},{keys[0][0]:.3f}),{keys[0][1]},{e})'

# ---------------------------------------------------------------- timeline
class TL:
    def __init__(s):
        s.shots = []; s.voice = []; s.amb = []; s.words = []; s.texts = []; s.sfx = []; s.t = 0.0; s.bounds = []; s.peringatan = []

SUNYI = set()  # titik potong yang dipilih dari analisa audio (kata menempel)
AKHIR_KALIMAT = re.compile(r'[.!?]["\')]*$')
ABA_ = re.compile(r'^(\d+|satu|dua|tiga|empat|lima|oke|ok|action)[,.!]?$', re.I)

def aba_semu(w):
    """kata hitungan aba-aba ("1, 2, 3") yang waktunya dijepit penyelaras (< 0.2 dtk) atau direntang (> 0.9 dtk): waktunya tidak bisa dipercaya"""
    return bool(ABA_.match(w['w'].strip())) and not (0.2 <= w['t1'] - w['t0'] <= 0.9)

def titik_sunyi(src, lo, hi):
    """detik paling sunyi (RMS 30 ms) di rentang [lo, hi] audio klip; dipakai bila dua kata hampir menempel"""
    lo = max(0.0, lo)
    if hi - lo < 0.04: return None
    try:
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{lo:.3f}', '-t', f'{hi - lo:.3f}', '-i', f'{RAW}/{src}.mp4', '-vn', '-ac', '1', '-ar', '16000',
                              '-f', 's16le', '-'], capture_output=True, timeout=60).stdout
        a = np.frombuffer(raw, np.int16).astype(np.float32)
        n = len(a) // 160
        if n < 3: return None
        e = np.sqrt((a[:n * 160].reshape(n, 160) ** 2).mean(1))
        e = np.convolve(e, np.ones(3) / 3, 'same')
        return round(lo + (int(np.argmin(e)) + 0.5) * 0.01, 3)
    except Exception:
        return None

def rapikan_batas(ws, a0, a1, dur, src=None):
    """pastikan potongan bicara berupa kalimat utuh dan tidak memotong kata:
    'out' di tengah kalimat -> diperpanjang ke akhir kalimat (maks +5 dtk); 'in' di tengah kalimat -> dimundurkan ke awal kalimat (maks 4 dtk);
    batas tidak boleh jatuh di dalam kata."""
    if not ws: return a0, a1
    # akhir: kata terakhir yang mulai sebelum out
    j = max([i for i, w in enumerate(ws) if w['t0'] < a1 - 0.05] or [-1])
    if j >= 0 and not AKHIR_KALIMAT.search(ws[j]['w'].strip()):
        k = next((i for i in range(j, len(ws)) if AKHIR_KALIMAT.search(ws[i]['w'].strip())), len(ws) - 1)
        if ws[k]['t1'] - a1 <= 5.0: a1 = ws[k]['t1'] + 0.25
    if j >= 0:
        j2 = max([i for i, w in enumerate(ws) if w['t0'] < a1 - 0.05] or [j])
        nxt = ws[j2 + 1]['t0'] if j2 + 1 < len(ws) else dur
        a1 = min(max(a1, ws[j2]['t1'] + 0.2), nxt - 0.03, dur - 0.02)
        if src and j2 + 1 < len(ws) and nxt - ws[j2]['t1'] < 0.15:  # kata berikut menempel: potong di titik tersunyi di antaranya
            n = ws[j2 + 1]
            t = titik_sunyi(src, ws[j2]['t1'] - 0.03, min(n['t0'] + 0.4 * (n['t1'] - n['t0']), n['t0'] + 0.2))
            if t: a1 = t; SUNYI.add((src, round(t, 2)))
    # awal: kata pertama yang berakhir setelah in
    i = next((i for i, w in enumerate(ws) if w['t1'] > a0 + 0.05), None)
    if i is not None:
        s = i
        while s > 0 and not AKHIR_KALIMAT.search(ws[s - 1]['w'].strip()) and not ABA_.match(ws[s - 1]['w'].strip()) and ws[i]['t0'] - ws[s - 1]['t0'] <= 4.0:
            s -= 1
        if s > 0 and not AKHIR_KALIMAT.search(ws[s - 1]['w'].strip()) and not ABA_.match(ws[s - 1]['w'].strip()):
            s = i  # awal kalimat terlalu jauh: biarkan, tapi jangan memotong kata
        while s < len(ws) - 1 and ABA_.match(ws[s]['w'].strip()): s += 1  # lewati hitungan aba-aba "1, 2, 3"
        prev = ws[s - 1]['t1'] if s > 0 else 0.0
        if s > 0 and aba_semu(ws[s - 1]): prev = ws[s - 1]['t0']  # aba-aba dengan waktu ASR terjepit: waktunya tidak bisa dipercaya
        # mulai sedikit sebelum kata pertama; jangan masuk ke kata sebelumnya, tapi juga jangan sampai memotong awal kata pertama
        a0 = max(min(a0, ws[s]['t0'] - 0.1), min(prev + 0.03, ws[s]['t0'] - 0.08), 0.0)
        if src and s > 0 and not aba_semu(ws[s - 1]) and ws[s]['t0'] - prev < 0.15:  # kata sebelumnya menempel (mis. aba-aba "3" lalu "Yuk"): cari titik tersunyi
            p = ws[s - 1]
            t = titik_sunyi(src, max(p['t0'] + 0.6 * (p['t1'] - p['t0']), ws[s]['t0'] - 0.35), ws[s]['t0'] + 0.02)
            if t: a0 = t; SUNYI.add((src, round(t, 2)))
    return round(a0, 3), round(a1, 3)

def jeda_terdekat(ws, t, arah):
    """geser titik t keluar dari dalam kata: 'kiri' -> sebelum kata itu, 'kanan' -> sesudahnya"""
    for i, w in enumerate(ws):
        if w['t0'] - 0.02 < t < w['t1'] + 0.02:
            if arah == 'kiri':
                prev = ws[i - 1]['t1'] if i > 0 else 0.0
                return max(w['t0'] - 0.04, prev + 0.02, prev)
            nxt = ws[i + 1]['t0'] if i + 1 < len(ws) else w['t1'] + 1.0
            return max(w['t1'], min(w['t1'] + 0.06, nxt - 0.02))
    return t

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
            semua = kata_klip(src)
            a0, a1 = rapikan_batas(semua, a0, a1, meta(src)['dur'], src)
            b['in'], b['out'] = a0, a1
            words = [w for w in semua if w['t0'] >= a0 - 0.05 and w['t1'] <= a1 + 0.3]
            # potong jeda: pecah jadi potongan bila jeda > rapat detik
            pieces = [[a0, a1]]
            gap = b.get('rapat', 0.45)
            if gap and words:
                pieces = []; cur = [a0 if (src, round(a0, 2)) in SUNYI else max(a0, words[0]['t0'] - 0.12), None]
                for w1, w2 in zip(words, words[1:]):
                    g = w2['t0'] - w1['t1']
                    if g > gap:
                        cur[1] = min(w1['t1'] + 0.18, w2['t0'] - 0.03); pieces.append(cur); cur = [max(w2['t0'] - 0.12, cur[1]), None]
                    elif b.get('potong_kalimat', True) and re.search(r'[.,!?]$', w1['w']) and w2['t0'] - cur[0] > 2.4:
                        mid = (w1['t1'] + w2['t0']) / 2  # jump cut di akhir kalimat tanpa membuang suara
                        cur[1] = mid; pieces.append(cur); cur = [mid, None]
                cur[1] = a1 if (src, round(a1, 2)) in SUNYI else min(a1, words[-1]['t1'] + 0.25); pieces.append(cur)
            for k in b.get('buang', []):  # rentang sumber yang dibuang [x,y], tepinya digeser ke jeda antar-kata
                k[0], k[1] = jeda_terdekat(semua, k[0], 'kiri'), jeda_terdekat(semua, k[1], 'kanan')
                np2 = []
                for p0, p1 in pieces:
                    if k[1] <= p0 or k[0] >= p1: np2.append([p0, p1]); continue
                    if k[0] > p0: np2.append([p0, k[0]])
                    if k[1] < p1: np2.append([k[1], p1])
                pieces = np2
            for p0, p1 in pieces:  # pemeriksa: tidak ada kata yang terbelah di titik potong
                for w in semua:
                    if aba_semu(w) and abs(p0 - w['t1']) < 0.3: continue
                    if (src, round(p0, 2)) in SUNYI and w['t0'] < p0 < w['t1']: continue  # dipotong di titik tersunyi (batas kata ASR menempel)
                    if (src, round(p1, 2)) in SUNYI and w['t0'] < p1 < w['t1']: continue
                    if (w['t0'] < p1 - 0.04 < w['t1'] - 0.06) or (w['t0'] + 0.06 < p0 + 0.04 < w['t1']):
                        tl.peringatan.append(f"kata '{w['w']}' terbelah di {src}@{p1 if w['t0'] < p1 - 0.04 < w['t1'] - 0.06 else p0:.2f}")
            if pieces:
                akhir = [w for w in semua if w['t0'] < pieces[-1][1] - 0.04]
                lanjut = [w for w in semua if w['t0'] >= pieces[-1][1] - 0.04]
                if akhir and lanjut and not AKHIR_KALIMAT.search(akhir[-1]['w'].strip()) and lanjut[0]['t0'] - akhir[-1]['t1'] < 1.0:
                    tl.peringatan.append(f"kalimat belum selesai di {src}@{pieces[-1][1]:.2f} ('{akhir[-1]['w']}' → '{lanjut[0]['w']}')")
            seg_start = tl.t; dipakai = set()
            cx = b.get('cx') or face_cx(src, a0, a1) or 0.5
            for pi, (p0, p1) in enumerate(pieces):
                d = math.ceil((p1 - p0) * FPS - 1e-6) / FPS; p1 = p0 + d  # durasi kelipatan frame (dibulatkan ke atas: ujung kata tidak terpotong)
                if d < 0.15: continue
                z = (za, zb)[alt % 2] if b.get('zoom', True) else za; alt += 1
                if pi > 0: tl.bounds.append((tl.t, G['transisi']['bicara']))
                c0 = c1 = b.get('cx') or face_cx(src, p0, p1) or cx
                path = None if b.get('cx') else cam_path(src, p0, p1, c0)
                tl.shots.append(dict(kind='A', src=src, a=p0, dur=d, z0=z, z1=z + 0.02, cx=c0, cx1=c1, path=path, cy=b.get('cy', 0.42), start=tl.t, fit=b.get('fit', 'crop'),
                                     cc=cc_shot(src, p0, p1) if G.get('cc') else None, sorot=G.get('sorot', False), fy_wajah=face_y(src, p0, p1)))
                tl.voice.append(dict(src=src, a=p0, b=p1, start=tl.t))
                for wi_, w in enumerate(words):
                    if wi_ in dipakai: continue
                    if w['t0'] >= p0 - 0.02 and w['t0'] < p1:
                        dipakai.add(wi_)
                        tl.words.append(dict(w=w['w'], t0=tl.t + w['t0'] - p0, t1=tl.t + min(w['t1'], p1) - p0))
                tl.t += d
            seg_dur = tl.t - seg_start
            jc = b.get('jcut', G.get('jcut', 0))
            mains = [x for x in tl.shots if not x.get('overlay')]
            firstA = next((x for x in mains if x['kind'] == 'A' and abs(x['start'] - seg_start) < 1e-6), None)
            prev = [x for x in mains if x['start'] < seg_start - 1e-6]
            if jc and firstA and prev and prev[-1]['kind'] == 'B' and firstA['dur'] > jc + 0.6:
                # J-cut: suara mulai duluan, gambar B-roll sebelumnya masih tampil sebentar
                prev[-1]['dur'] += jc; firstA['a'] += jc; firstA['dur'] -= jc; firstA['start'] += jc
                if firstA.get('path'): firstA['path'] = [[round(t - jc, 2), x] for t, x in firstA['path'] if t - jc >= -0.25]
                tl.bounds = [(t + jc if abs(t - seg_start) < 1e-6 else t, tr) for t, tr in tl.bounds]
            # 'pada': jangkar ke kata yang diucapkan (lebih aman daripada detik, karena jeda sudah dipotong)
            seg_words = [w for w in tl.words if w['t0'] >= seg_start - 1e-6]
            def jangkar(item, dflt=0.0):
                if item.get('pada'):
                    kunci_ = [re.sub(r'[^0-9a-z]', '', x.lower()) for x in str(item['pada']).split()]
                    nw = [re.sub(r'[^0-9a-z]', '', w['w'].lower()) for w in seg_words]
                    for i in range(len(nw)):
                        if nw[i:i + len(kunci_)] == kunci_:
                            return max(0.0, seg_words[i]['t0'] - seg_start + item.get('geser', 0.0))
                return item.get('at', dflt)
            for c in b.get('sisip', []): c['at'] = jangkar(c)
            for kk in b.get('kata', []) + b.get('teks', []): kk['at'] = jangkar(kk)
            # sisipan B-roll di atas suara (cutaway). at: detik dari awal bagian ini (setelah dirapatkan)
            for c in b.get('sisip', []):
                if c['at'] >= seg_dur - 0.3: continue
                t0 = seg_start + c['at']; t1 = min(seg_start + seg_dur, t0 + c['dur'])
                tl.shots.append(dict(kind='B', src=c['src'], a=c['in'], dur=t1 - t0, z0=1.0, z1=1.0 + G['gerak_broll'][1], cx=c.get('cx', 0.5), cy=0.5,
                                     start=t0, overlay=True, lambat=c.get('lambat', 1.0), fit=c.get('fit', 'crop'),
                                     cc=cc_shot(c['src'], c['in'], c['in'] + c['dur']) if G.get('cc') else None,
                                     stab=bool(G.get('stab') and perlu_stab(c['src']) and c.get('stab', True))))
            for kk in b.get('kata', []):
                tl.texts.append(dict(kind='kunci', t0=seg_start + kk['at'], t1=seg_start + kk['at'] + kk.get('dur', 1.6), teks=kk['teks'], y=kk.get('y')))
                if G['sfx']['kunci']: tl.sfx.append((seg_start + kk['at'], G['sfx']['kunci'], G.get('sfx_db', {}).get('kunci', -8)))
            for tt in b.get('teks', []):
                tl.texts.append(dict(kind=tt.get('kind', 'kunci'), t0=seg_start + tt['at'], t1=seg_start + tt['at'] + tt.get('dur', 2.0), teks=tt['teks'], y=tt.get('y'), sub2=tt.get('sub2')))
        elif j in ('broll', 'penutup'):
            items = b['klip'] if 'klip' in b else [b]
            lam = b.get('lambat', lambat_def)
            seg_start = tl.t
            bpm = spec.get('musik', {}).get('bpm') if G.get('ketukan') else None
            for ci, c in enumerate(items):
                d = round(c.get('dur', b.get('dur', 2.5)) * FPS) / FPS
                if bpm and j == 'broll' and not c.get('bebas'):  # potongan jatuh tepat di ketukan musik (setengah ketukan)
                    half = 30 / bpm
                    end = max(tl.t + 0.5, round((tl.t + d) / half) * half)
                    d = round((end - tl.t) * FPS) / FPS
                if ci > 0: tl.bounds.append((tl.t, c.get('transisi') or G['transisi']['broll']))
                mv = c.get('gerak', G['gerak_broll'][0])
                zz = G['gerak_broll'][1]
                z0, z1 = (1.0, 1.0 + zz) if R.random() < 0.6 else (1.0 + zz, 1.0)
                if mv == 'punch': z0, z1 = 1.0 + zz, 1.0
                lm = c.get('lambat', lam)
                tl.shots.append(dict(kind='B', src=c['src'], a=c['in'], dur=d, z0=c.get('z0', z0), z1=c.get('z1', z1), cx=c.get('cx', 0.5), cy=c.get('cy', 0.5),
                                     start=tl.t, lambat=lm, fit=c.get('fit', b.get('fit', 'crop')), gerak=mv, blur=(j == 'penutup'),
                                     ramp=c.get('ramp'), kf=c.get('kf'),
                                     cc=cc_shot(c['src'], c['in'], c['in'] + d / lm) if G.get('cc') else None,
                                     stab=bool(G.get('stab') and perlu_stab(c['src']) and c.get('stab', True) and j != 'penutup')))
                if c.get('suara', b.get('suara')) is not None:
                    tl.amb.append(dict(src=c['src'], a=c['in'], dur=d, start=tl.t, gain=c.get('suara', b.get('suara')), lambat=c.get('lambat', lam)))
                tl.t += d
            for tt in b.get('teks', []):
                tl.texts.append(dict(kind=tt.get('kind', 'kunci'), t0=seg_start + tt.get('at', 0), t1=seg_start + tt.get('at', 0) + tt.get('dur', tl.t - seg_start - tt.get('at', 0)), teks=tt['teks'], y=tt.get('y'), sub2=tt.get('sub2')))
                kd = tt.get('kind', 'kunci')
                if kd in ('kunci', 'kartu') and G['sfx']['kunci']: tl.sfx.append((seg_start + tt.get('at', 0), G['sfx']['kunci'], G.get('sfx_db', {}).get('kunci', -8)))
                if kd == 'judul' and G['sfx'].get('judul'): tl.sfx.append((seg_start + tt.get('at', 0), G['sfx']['judul'], G.get('sfx_db', {}).get('judul', -6)))
            if j == 'penutup':
                tl.texts.append(dict(kind='penutup', t0=seg_start + 0.15, t1=tl.t, teks=b.get('cta', '')))
    for t, tr in tl.bounds:  # whoosh dimulai sedikit sebelum potongan agar terdengar alami
        if tr != 'cut' and tr[0] and G['sfx']['transisi']: tl.sfx.append((t - 0.2, G['sfx']['transisi'], G.get('sfx_db', {}).get('transisi', -6)))
    drop = spec.get('musik', {}).get('drop', 0)
    if drop and G['sfx'].get('riser'): tl.sfx.append((max(0, drop - 1.35), G['sfx']['riser'], G.get('sfx_db', {}).get('riser', -10)))
    return tl, G

# ---------------------------------------------------------------- video per shot
def vf_shot(sh_, G, dur_out, m, trf=None):
    """filter: sumber -> stabilisasi -> speed/ramp -> 1080x1920 (crop/keyframe zoom) -> koreksi warna -> LUT -> grade"""
    lam = sh_.get('lambat', 1.0); D = max(dur_out, 0.04)
    f = []
    if trf: f.append(f"vidstabtransform=input={trf}:smoothing=14:zoom=4:optzoom=0:interpol=bicubic")
    rp = sh_.get('ramp')
    if rp:  # speed ramp: cepat (motion blur) lalu lambat (slow motion)
        d1 = rp['titik'] * D; i1 = d1 * rp['cepat']
        f.append(f"setpts='(if(lt(T-STARTT,{i1:.4f}),(T-STARTT)/{rp['cepat']},{d1:.4f}+(T-STARTT-{i1:.4f})/{rp['lambat']}))/TB'")
        f.append(f"tmix=frames=4:enable='lt(t,{d1 - 0.02:.3f})'")
    elif lam != 1.0:
        f.append(f'setpts={lam}*PTS')
    f.append(f'fps={FPS}')
    sw, sh2 = m['w'], m['h']
    z0, z1 = sh_['z0'], sh_['z1']
    kz = sh_.get('kf') or [[0, z0], [D, z1]]
    zt = '(' + ease_expr([(float(t), float(z)) for t, z in kz]) + ')'
    static = all(abs(z - 1.0) < 1e-6 for _, z in kz)
    if (sh_.get('fit') == 'blur' and sw > sh2 and H > W):
        f.append(f'split=2[bg][fg];[bg]scale=-2:{H},crop={W}:{H},boxblur=30:3,eq=brightness=-0.08[bgb];'
                 f"[fg]scale={W}:-2:eval=frame[fgs];[bgb][fgs]overlay=(W-w)/2:(H-h)/2-60")
    elif W > H and sh2 > sw:  # sumber potrait di keluaran landscape: video utuh di tengah + latar blur
        f.append(f'split=2[bg][fg];[bg]scale={W}:-2,crop={W}:{H},boxblur=40:3,eq=brightness=-0.1:saturation=0.9[bgb];'
                 f"[fg]scale=-2:{H}[fgs];[bgb][fgs]overlay=(W-w)/2:0")
    else:
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
        else:
            f.append(f"crop={int(cw)//2*2}:{int(ch)//2*2}:'{x0}+({x1 - x0})*(0.5-0.5*cos(PI*min(t/{D:.3f},1)))':{y0}")
        if static:
            f.append(f'scale={W}:{H}:flags=lanczos')
        else:
            f.append(f"scale=w='trunc({W}*{zt}/2)*2':h='trunc({H}*{zt}/2)*2':eval=frame:flags=bicubic")
            ox = '(iw-ow)/2'; oy = f"(ih-oh)*{sh_.get('fy', 0.40)}"
            if sh_.get('gerak') == 'handheld':
                ox = '(iw-ow)/2+6*sin(t*1.7)'; oy = '(ih-oh)/2+5*sin(t*1.3+1)'
            f.append(f"crop={W}:{H}:'{ox}':'{oy}'")
    if sh_.get('blur'): f.append('boxblur=14:2,eq=brightness=-0.12')
    cc = sh_.get('cc')
    if cc:  # koreksi warna: white balance + exposure, disamakan antar-shot
        f.append(f"colorchannelmixer=rr={cc['rr']}:gg={cc['gg']}:bb={cc['bb']},eq=gamma={cc['gamma']}")
    if G.get('lut'):
        f.append(f"lut3d=file={E}/aset/lut/{G['lut']}.cube:interp=tetrahedral")
    f.append(G['grade'])
    if sh_.get('sorot'):  # mask vignette lembut yang berpusat di subjek (ikut posisi wajah)
        f.append(f"vignette=angle=PI/4:aspect=9/16:x0=w/2:y0=h*{min(0.5, sh_.get('fy_wajah', 0.33) + 0.1):.2f}")
    if sh_.get('mb_awal'):
        f.append(f"dblur=angle=0:radius=28:enable='lt(t,{sh_['mb_awal']:.3f})'")
    if sh_.get('mb_akhir'):
        f.append(f"dblur=angle=0:radius=28:enable='gte(t,{D - sh_['mb_akhir']:.3f})'")
    if G.get('letterbox') and sh_['kind'] == 'B':
        f.append('drawbox=0:0:1080:150:black:t=fill,drawbox=0:1770:1080:150:black:t=fill')
    f.append('format=yuv420p')
    return ','.join(f)

def render_shot(i, s, G, handle, key):
    m = meta(s['src'])
    dur = s['dur'] + handle
    lam = s.get('lambat', 1.0)
    rp = s.get('ramp')
    need = (rp['titik'] * dur * rp['cepat'] + (1 - rp['titik']) * dur * rp['lambat']) if rp else dur / lam
    a = s['a']
    if a + need > m['dur'] - 0.05:  # mundurkan awal bila kurang
        a = max(0, m['dur'] - 0.05 - need)
    h = hashlib.md5(json.dumps([s, handle, G['grade'], G.get('letterbox'), G.get('lut'), a, VF_VERSI, W, H] + ([2] if s.get('sorot') else []), sort_keys=True).encode()).hexdigest()[:12]
    out = f'{CACHE}/shot_{h}.mp4'
    if not os.path.exists(out):
        trf = None
        if s.get('stab'):  # stabilisasi 2 tahap (vid.stab): analisa guncangan lalu koreksi
            trf = f'{CACHE}/stab_{h}.trf'
            sh(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-ss', f'{a:.3f}', '-t', f'{need + 0.2:.3f}', '-i', m['path'], '-an',
                '-vf', f'vidstabdetect=shakiness=6:accuracy=12:result={trf}', '-f', 'null', '-'])
        vf = vf_shot(s, G, dur, m, trf)
        sh(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-ss', f'{a:.3f}', '-t', f'{need + 0.2:.3f}', '-i', m['path'], '-an',
            '-filter_complex', f'[0:v]{vf}[v]', '-map', '[v]', '-t', f'{dur:.3f}', '-r', str(FPS),
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-threads', TH, out + '.tmp.mp4'])
        os.rename(out + '.tmp.mp4', out)
    return out

def assemble(tl, G, out):
    # lapisan utama (tidak overlay) berurutan; overlay (cutaway) ditumpuk setelahnya
    main = [s for s in tl.shots if not s.get('overlay')]
    trans = {round(t, 3): tr for t, tr in tl.bounds}
    files = []; Ts = []
    trs = []
    for k, s in enumerate(main):
        nxt = main[k+1] if k+1 < len(main) else None
        trs.append(trans.get(round(nxt['start'], 3), 'cut') if nxt else 'cut')
    for k, s in enumerate(main):  # motion blur di sekitar transisi whip
        if trs[k] != 'cut' and trs[k][0] == 'whip': s['mb_akhir'] = trs[k][1] + 0.06
        if k > 0 and trs[k-1] != 'cut' and trs[k-1][0] == 'whip': s['mb_awal'] = trs[k-1][1] * 0.7
    for k, s in enumerate(main):
        tr = trs[k]
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
        name = 'fade' if tr == 'cut' else {'whip': 'slideleft'}.get(tr[0], tr[0])
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
    args += ['-filter_complex', ';'.join(fc), '-map', '[vout]', '-r', str(FPS), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-threads', TH, out]
    sh(args)

# ---------------------------------------------------------------- audio
VOICE_CHAIN = ('highpass=f=80,bandreject=f=50:width_type=q:w=12,bandreject=f=100:width_type=q:w=12,adeclick,'
               f'arnndn=m={E}/aset/suara.rnnn:mix=0.8,afftdn=nr=6:nf=-45:tn=1,lowpass=f=13000,deesser=i=0.35:m=0.5:f=0.5,'
               'equalizer=f=220:t=q:w=1.0:g=-2.5,equalizer=f=3200:t=q:w=1.3:g=3,equalizer=f=7500:t=q:w=1.5:g=1.5,'
               'acompressor=threshold=-22dB:ratio=3.5:attack=4:release=140:makeup=5,'
               'loudnorm=I=-16:TP=-1.5:LRA=6')

def wav_src(src, kind):
    out = f'{CACHE}/aud_{src}_{kind}.wav'
    if not os.path.exists(out):
        af = VOICE_CHAIN if kind == 'voice' else 'highpass=f=80,afftdn=nr=8:nf=-40,loudnorm=I=-22:TP=-3'
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
    from scipy.signal import butter, sosfilt
    n = int(1.4 * SR); t = np.arange(n) / SR; rng = np.random.default_rng(len(kind))
    if kind == 'whoosh':  # udara lewat: noise disapu frekuensinya, puncak 0.22 dtk
        nz = rng.standard_normal(n); env = np.exp(-((t - 0.22) / 0.09) ** 2)
        lo = sosfilt(butter(2, [300, 2500], 'band', fs=SR, output='sos'), nz); hi = sosfilt(butter(2, [2500, 9000], 'band', fs=SR, output='sos'), nz)
        y = (lo * np.clip(1.6 - t*4, 0.3, 1) + hi * np.clip(t*4 - 0.2, 0, 1)) * env * 0.22
    elif kind == 'tick':  # klik lembut untuk teks/kartu
        y = (np.sin(2*np.pi*2400*t) * 0.5 + rng.standard_normal(n) * 0.2) * np.exp(-t * 90) * 0.18
    elif kind == 'riser':  # naik menjelang drop
        y = sosfilt(butter(2, [800, 6000], 'band', fs=SR, output='sos'), rng.standard_normal(n)) * (t / 1.4) ** 2 * 0.12
    elif kind == 'thump':  # pukulan bass halus untuk logo/judul
        y = np.sin(2*np.pi*(70 - 25*t) * t) * np.exp(-t*6) * 0.5
    elif kind == 'pop':
        y = np.sin(2*np.pi*(900 - 500*t) * t) * np.exp(-t * 40) * 0.3
    elif kind == 'impact':
        y = (np.sin(2*np.pi*55*t) * np.exp(-t*7) * 0.6 + rng.standard_normal(n) * np.exp(-t*25) * 0.15)
    else:
        y = np.zeros(n)
    return np.stack([y, y], 1).astype(np.float32)

def lufs_arr(x):
    p = f'{CACHE}/_lv.wav'; wavfile.write(p, SR, np.clip(x, -1, 1)); return lufs(p)

def lufs(path):
    o = subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-i', path, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    m = re.findall(r'I:\s+(-?[\d.]+) LUFS', o)
    return float(m[-1]) if m else -70.0

def rata(x, k):
    """rata-rata bergerak (sama seperti np.convolve(x, ones(k)/k, 'same')) tapi O(n) lewat cumsum"""
    x = np.asarray(x, np.float64); n = len(x); k = max(1, int(k))
    c = np.concatenate([[0.0], np.cumsum(x)])
    i = np.arange(n); a = np.clip(i - k // 2 + (1 if k % 2 == 0 else 0), 0, n); b = np.clip(a + k, 0, n)
    a = np.clip(i - (k - 1) // 2, 0, n); b = np.clip(i + k // 2 + 1, 0, n)
    return (c[b] - c[a]) / k

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
    for it in tl.sfx:
        t, k = it[0], it[1]; gdb = it[2] if len(it) > 2 else -6
        if k: place(X, sfx(k) * 10 ** (gdb / 20), max(0, t), 0.002)
    # musik
    mz = spec.get('musik', {})
    gy = mz.get('gaya') or G['musik'][0]
    mfile = f"{CACHE}/musik_{spec['id']}_{gy}_{mz.get('seed', 1)}_{tl.t:.2f}.wav"
    drop = mz.get('drop', 0)
    if not os.path.exists(mfile):
        sh([sys.executable, f'{E}/musik.py', gy, f'{tl.t + 0.3:.2f}', mfile, '--seed', str(mz.get('seed', 1)), '--drop', str(drop)] + (['--bpm', str(mz['bpm'])] if mz.get('bpm') else []))
    sr, m = wavfile.read(mfile); m = m.astype(np.float32) / 32768
    if sr != SR:
        idx = np.linspace(0, len(m)-1, int(len(m)*SR/sr)); m = np.stack([np.interp(idx, np.arange(len(m)), m[:, k]) for k in range(2)], 1).astype(np.float32)
    M = np.zeros((n, 2), np.float32); M[:min(n, len(m))] = m[:n]
    # level musik ke target LUFS (ukur cepat via RMS berbobot sederhana -> pakai ffmpeg di file)
    ml = lufs(mfile); M *= 10 ** ((G['musik_db'] + mz.get('db', 0) - ml) / 20)
    # ducking dari amplop suara
    env = np.sqrt(rata((V**2).mean(1), int(0.05*SR)))
    act = (env > 10 ** (-38/20)).astype(np.float32)
    # tahan 250 ms, attack 80 ms, release 400 ms
    hold = int(0.25*SR); act = rata(act, hold) > 0
    g = np.where(act, 10 ** (G['duck_db'] / 20), 1.0).astype(np.float32)
    a_, r_ = 1 - math.exp(-1/(0.08*SR)), 1 - math.exp(-1/(0.4*SR))
    sm = np.empty_like(g); s0 = 1.0
    for i in range(0, len(g), 64):  # blok 64 sampel agar cepat
        tgt = g[i]; c = a_ if tgt < s0 else r_; s0 += (tgt - s0) * (1 - (1-c)**64); sm[i:i+64] = s0
    M *= sm[:, None]
    # pastikan musik selalu di bawah suara asli (suara orang & suara kandang)
    asli = np.sqrt(rata((V**2).mean(1), int(0.4*SR)))  # patokan: suara orang
    mus = np.sqrt(rata((M**2).mean(1), int(0.4*SR)))
    over = np.where((asli > 10 ** (-40/20)) & (mus > asli * 10 ** (-9/20)), (asli * 10 ** (-9/20)) / np.maximum(mus, 1e-6), 1.0)
    over = rata(over, int(0.2*SR)).astype(np.float32)
    M *= np.clip(over, 0.25, 1.0)[:, None]
    mix = V + A + X + M
    tmp = out + '.pre.wav'; wavfile.write(tmp, SR, np.clip(mix, -1, 1))
    L = lufs(tmp); gain = -14.0 - L
    info_lv = dict(lv_suara=round(lufs_arr(V), 1), lv_musik=round(lufs_arr(M), 1), lv_kandang=round(lufs_arr(A), 1))
    sh(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-i', tmp, '-af', f'volume={gain:.2f}dB,alimiter=limit=0.84:attack=3:release=60', '-ar', str(SR), out])
    os.remove(tmp)
    return dict(lufs_awal=L, musik=gy, **info_lv)

# ---------------------------------------------------------------- teks (ASS)
def ass_time(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f'{h}:{m:02d}:{s:05.2f}'

def esc(s): return s.replace('{', '(').replace('}', ')').replace('\\n', '\\N').replace('\n', '\\N')

FAKTOR_FONT = {'Anton': 0.46, 'Montserrat': 0.64, 'Bricolage Grotesque': 0.57, 'Playfair Display': 0.54, 'Caveat': 0.42,
               'Plus Jakarta Sans': 0.57, 'Poppins': 0.61}
PETA = []  # peta wajah video hasil: [(t, [[x0,y0,x1,y1]..])], diisi di main()
VIDEO_POLOS = None  # video tanpa teks, untuk menilai keramaian latar

def ukur(teks, size, font):
    lines = [re.sub(r'\{[^}]*\}', '', l) for l in teks.split('\\N')]
    f = FAKTOR_FONT.get(font, 0.58)
    lw = [len(l) * size * f * (1.1 if l.isupper() else 1.0) for l in lines]
    return max(lw + [size]), len(lines) * size * 1.2

def tumpang(a, b, kotak):
    from wajahtl import tabrakan
    return tabrakan(PETA, a, b, kotak) if PETA else 0.0

def pilih(a, b, w, h, x_def, y_def, ys, xs=None, batas=None, ambang=0.02, pad=24):
    """pilih titik tengah (x,y) teks yang tidak menutupi wajah; utamakan posisi asal"""
    y_lo, y_hi = batas or (60, H - 60)
    cands = []
    for x in (xs or [x_def]):
        for y in [y_def] + [v for v in ys if abs(v - y_def) > 20]:
            if y - h / 2 < y_lo or y + h / 2 > y_hi or x - w / 2 < 30 or x + w / 2 > W - 30: continue
            cands.append((x, y))
    if not cands: return x_def, y_def, 0.0
    def kot(x, y): return (x - w / 2 - pad, y - h / 2 - pad, x + w / 2 + pad, y + h / 2 + pad)
    s0 = tumpang(a, b, kot(x_def, y_def))
    if s0 <= ambang: return x_def, y_def, s0
    def ramai(c):
        if not VIDEO_POLOS: return 0.0
        from wajahtl import keramaian
        return sum(keramaian(VIDEO_POLOS, W, H, tt, kot(*c)) for tt in (a + 0.3, (a + b) / 2)) / 2
    aman = [c for c in cands if tumpang(a, b, kot(*c)) <= ambang]
    if aman:  # di antara posisi yang tidak menutupi wajah: pilih latar paling tenang, lalu yang paling dekat posisi asal
        best = min(aman, key=lambda c: ramai(c) * 1.0 + (abs(c[0] - x_def) / W + abs(c[1] - y_def) / H) * 0.35)
    else:
        best = min(cands, key=lambda c: (round(tumpang(a, b, kot(*c)), 3), abs(c[0] - x_def) / W + abs(c[1] - y_def) / H))
    return best[0], best[1], tumpang(a, b, kot(*best))

def anim(an, x, y, h, w=0):
    """tag animasi masuk (halus, tidak berlebihan)"""
    if an == 'slam':
        return f"\\an5\\pos({x},{y})\\fscx135\\fscy135\\blur6\\alpha&HFF&\\t(0,140,0.6,\\fscx100\\fscy100\\blur0\\alpha&H00&)\\fad(0,140)"
    if an == 'tulis':
        return f"\\an5\\pos({x},{y})\\frz-3\\fad(150,200)\\clip({int(x - w / 2)},0,{int(x - w / 2)},{H})\\t(0,520,0.7,\\clip(0,0,{W},{H}))"
    if an == 'kartu':
        return f"\\an5\\move({x},{y + 22},{x},{y},0,300)\\fscx94\\fscy94\\alpha&HFF&\\t(0,300,0.45,\\fscx100\\fscy100\\alpha&H00&)\\fad(0,180)"
    if an == 'garis':  # teks naik dari balik garis tipis
        gy = int(y + h / 2 + 6)
        return f"\\an5\\move({x},{int(y + h)},{x},{y},120,560)\\clip(0,0,{W},{gy})\\fad(0,250)"
    # 'naik' (bawaan): naik pelan + memudar masuk, kabur -> tajam
    return f"\\an5\\move({x},{y + 26},{x},{y},0,320)\\blur5\\alpha&HFF&\\t(0,320,0.5,\\blur0\\alpha&H00&)\\fad(0,160)"

def per_kata(tx, d0=0, step=70):
    """munculkan kata satu per satu (memudar + tajam)"""
    out = []; parts = tx.split('\\N')
    i = 0
    for pi, p in enumerate(parts):
        ws = []
        for w in p.split(' '):
            if not w: continue
            t0 = d0 + i * step; i += 1
            ws.append(f"{{\\alpha&HFF&\\blur4\\t({t0},{t0 + 260},0.6,\\alpha&H00&\\blur0)}}{w}")
        out.append(' '.join(ws))
    return '\\N'.join(out)

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
Style: Sub,{G['font']},{FS(sb['size'])},{sb['warna']},&H000000FF,&H00101010,{'&H8C000000' if sb['box'] else '&H64000000'},{bold},0,0,0,100,100,0,0,{3 if sb['box'] else 1},{12 if sb['box'] else sb['outline']},{sb['shadow']},2,70,70,0,1
Style: Kunci,{k['font']},{FS(k['size'])},{k['warna']},&H000000FF,&H00101010,&H64000000,-1,0,0,0,100,100,0,0,1,{k['outline']},{3 if k['outline']==0 else 0},5,60,60,0,1
Style: Kartu,{k['font']},{FS(int(k['size']*0.9))},&H00FFFFFF,&H000000FF,&H00256E2C,&H00256E2C,-1,0,0,0,100,100,0,0,3,30,0,5,60,60,0,1
Style: Kecil,{G['font']},{FS(G.get('kecil', 54))},&H00FFFFFF,&H000000FF,&H00101010,&H64000000,-1,0,0,0,100,100,0,0,1,{G.get('kecil_outline', 4)},0,5,60,60,0,1
Style: Garis,{G['font']},20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: LT1,{G.get('font_judul', G['font'])},50,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: LT2,{G['font']},34,&H00E6F0EA,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Kotak,{G['font']},20,&H002C6E25,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []; laporan = []
    pen = [t for t in tl.texts if t['kind'] == 'penutup']; t_pen = pen[0]['t0'] if pen else 1e9
    # batas aman: tulisan besar tidak masuk area tombol/caption TikTok-IG (potrait) dan area subtitle
    if LAND:
        bt = (40, int(H * 0.80)); ys = [int(H * f) for f in (0.17, 0.30, 0.50, 0.66)]; xs_side = True
    else:
        bt = (150, 1330); ys = [300, 460, 640, 820, 1000, 1180]; xs_side = False
    # ---- subtitle per potongan kata
    ws = tl.words; per = sb['kata_per']; chunks = []; cur = []
    for w in ws:
        if w['t0'] >= t_pen - 0.05: continue
        cur.append(w)
        end_sent = re.search(r'[.,!?]$', w['w'])
        if len(cur) >= per or end_sent: chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    redup = '&H00D2D2D2'
    for ci, c in enumerate(chunks):
        t0 = c[0]['t0']; t1 = c[-1]['t1']
        if ci + 1 < len(chunks): t1 = min(max(t1, t0 + 0.35), chunks[ci+1][0]['t0'])
        t1 = min(t1, t_pen)
        txts = []
        for w in c:
            word = w['w'].strip()
            word = re.sub(r'[,.]$', '', word) if per <= 3 else word
            if sb['upper']: word = word.upper()
            txts.append((w['t0'], w['t1'], esc(word)))
        full = ' '.join(t for _, _, t in txts)
        sw_, sh_ = ukur(full, FS(sb['size']), G['font']); baris = max(1, math.ceil(sw_ / (W - 160)))
        sw_ = min(sw_, W - 160); sh_ = baris * FS(sb['size']) * 1.25
        y_def = int(H * 0.88) if LAND else sb['y']
        alt = [int(H * 0.22)] if LAND else [400]
        cands = [y_def] + alt; skor = []
        for yy in cands:
            skor.append(tumpang(t0, t1, (W/2 - sw_/2 - 16, yy - sh_ - 12, W/2 + sw_/2 + 16, yy + 12)))
        y = y_def if skor[0] <= 0.12 else cands[int(np.argmin(skor))]
        if y != y_def: laporan.append(f'sub {t0:.1f}s pindah ke y={y}')
        aktif = sb['sorot'] if sb['sorot'] != sb['warna'] else sb['warna']
        dim = sb['warna'] if sb['sorot'] != sb['warna'] else redup
        for wi, (a, b, _) in enumerate(txts):  # kata yang sedang diucapkan sedikit lebih terang
            b2 = txts[wi+1][0] if wi + 1 < len(txts) else t1
            a2 = t0 if wi == 0 else a
            if b2 <= a2: continue
            line = ' '.join((('{\\c' + aktif + '&}' + tx + '{\\c' + dim + '&}') if j == wi else tx) for j, (_, _, tx) in enumerate(txts))
            masuk = f"\\move({W//2},{y + 12},{W//2},{y},0,160)\\fad(110,0)" if wi == 0 else f"\\pos({W//2},{y})"
            ev.append(f"Dialogue: 2,{ass_time(a2)},{ass_time(b2)},Sub,,0,0,0,,{{\\an2{masuk}\\c{dim}&}}{line}")
    # ---- teks besar, judul, lower third
    for t in tl.texts:
        a, b = t['t0'], t['t1']; tx = esc(t['teks']); y0 = Y(t.get('y') or k['y'])
        if t['kind'] in ('kunci', 'judul'):
            an = k['anim'] if t['kind'] == 'kunci' else ('garis' if k['anim'] in ('fade', 'garis') else 'naik')
            if an in ('pop', 'fade'): an = 'naik' if an == 'pop' else 'garis'
            st = 'Kartu' if (an == 'kartu' and t['kind'] == 'kunci') else 'Kunci'
            size = FS(int(k['size'] * (0.9 if st == 'Kartu' else 1)))
            w_, h_ = ukur(tx, size, k['font'])
            if st == 'Kartu': w_ += 60; h_ += 60
            off2 = FS(int(k['size'] * (1.15 if an == 'kartu' else 0.85))) if t.get('sub2') else 0
            h_tot = h_ + (off2 + FS(G.get('kecil', 54)) * 0.6 if off2 else 0)
            w_tot = max(w_, ukur(esc(t.get('sub2') or ''), FS(G.get('kecil', 54)), G['font'])[0])
            xs = [W // 2, int(W * 0.27), int(W * 0.73)] if (xs_side and w_tot < W * 0.42) else None
            # titik acuan = tengah blok (judul + keterangan)
            cy_def = int(y0 + (h_tot - h_) / 2)
            x, cy, sisa = pilih(a, b, w_tot, h_tot, W // 2, cy_def, [v + int((h_tot - h_) / 2) for v in ys], xs, bt)
            y = int(cy - (h_tot - h_) / 2)
            if (x, cy) != (W // 2, cy_def): laporan.append(f"{t['kind']} '{t['teks'][:18]}' {a:.1f}s pindah ke ({x},{y}) sisa={sisa:.2f}")
            body = per_kata(tx, 60) if an == 'naik' else tx
            lay = 5 if t['kind'] == 'kunci' else 6
            ev.append(f"Dialogue: {lay},{ass_time(a)},{ass_time(b)},{st},,0,0,0,,{{{anim(an, x, y, h_, w_)}}}{body}")
            if an == 'garis':  # garis tipis yang memanjang dari tengah
                gw = int(min(w_, W * 0.5)); gy = int(y + h_ / 2 + 6)
                ev.append(f"Dialogue: {lay},{ass_time(a)},{ass_time(b)},Garis,,0,0,0,,{{\\an5\\pos({x},{gy})\\fscx0\\t(0,380,0.4,\\fscx100)\\fad(0,250)\\p1}}m 0 0 l {gw} 0 {gw} 3 0 3")
            if t.get('sub2'):
                y2 = y + off2
                ev.append(f"Dialogue: {lay},{ass_time(a+0.18)},{ass_time(b)},Kecil,,0,0,0,,{{\\an5\\move({x},{y2 + 12},{x},{y2},0,260)\\fad(200,150)}}{esc(t['sub2'])}")
        elif t['kind'] == 'lower':  # lower third beranimasi (geser masuk dengan ease-out, aksen kuning)
            wbar = t.get('w', 640)
            if LAND:
                opsi = [(110, int(H*0.63)), (W - 110 - wbar, int(H*0.63)), (110, int(H*0.12))]
            else:
                opsi = [(64, t.get('y') or 1190), (64, 300)]
            sk = [tumpang(a, b, (x0 - 20, yb - 20, x0 + wbar + 20, yb + 138)) for x0, yb in opsi]
            x0, yb = opsi[0] if sk[0] <= 0.02 else opsi[int(np.argmin(sk))]
            if (x0, yb) != opsi[0]: laporan.append(f'lower third {a:.1f}s pindah ke ({x0},{yb})')
            box = f"m 0 0 l {wbar} 0 {wbar} 118 0 118"
            acc = "m 0 0 l 10 0 10 118 0 118"
            ev.append(f"Dialogue: 7,{ass_time(a)},{ass_time(b)},Kotak,,0,0,0,,{{\\an7\\pos({x0},{yb})\\1c&H2C6E25&\\1a&H18&\\clip(0,0,{x0},{H})\\t(0,380,0.4,\\clip(0,0,{x0+wbar},{H}))\\fad(0,200)\\p1}}{box}")
            ev.append(f"Dialogue: 8,{ass_time(a)},{ass_time(b)},Kotak,,0,0,0,,{{\\an7\\pos({x0},{yb})\\1c&H4EC1F2&\\fad(120,200)\\p1}}{acc}")
            l1, _, l2 = t['teks'].partition('|')
            ev.append(f"Dialogue: 9,{ass_time(a+0.18)},{ass_time(b)},LT1,,0,0,0,,{{\\an7\\move({x0+10},{yb+14},{x0+30},{yb+14},0,320)\\alpha&HFF&\\t(0,300,0.5,\\alpha&H00&)\\fad(0,200)}}{esc(l1.strip())}")
            if l2: ev.append(f"Dialogue: 9,{ass_time(a+0.3)},{ass_time(b)},LT2,,0,0,0,,{{\\an7\\move({x0+10},{yb+70},{x0+30},{yb+70},0,320)\\alpha&HFF&\\t(0,300,0.5,\\alpha&H00&)\\fad(0,200)}}{esc(l2.strip())}")
    open(out, 'w').write(head + '\n'.join(ev) + '\n')
    return laporan

# ---------------------------------------------------------------- kartu penutup (HTML -> PNG)
def penutup_png(G, spec, out):
    gaya = G['penutup']
    js = f'{E}/penutup.js'
    import signal
    logp = out + '.log'
    with open(logp, 'w') as lf:  # proses grup sendiri + log ke file: Chromium yang tertinggal tidak bisa menahan pipa
        pr = subprocess.Popen(['node', js, out, gaya, json.dumps(dict(spec.get('penutup', {}), w=W, h=H))],
                              stdout=lf, stderr=lf, stdin=subprocess.DEVNULL, start_new_session=True)
        try: pr.wait(timeout=120)
        except subprocess.TimeoutExpired: print('  kartu penutup macet (timeout 120 dtk)', flush=True)
        finally:
            try: os.killpg(pr.pid, signal.SIGKILL)
            except Exception: pass
    ok = pr.returncode == 0 and os.path.exists(out)
    if not ok: print('  kartu penutup gagal:', open(logp).read()[-500:], flush=True)
    return ok

def final(tl, G, spec, vid, aud, ass, out):
    logo = f'{E}/aset/logo.png'
    pen = [t for t in tl.texts if t['kind'] == 'penutup']
    args = ['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-i', vid, '-i', aud, '-i', logo]
    fc = [f"[0:v]ass={ass}:fontsdir={FONTS}[v1]"]
    pos = {'kanan_atas': f'W-w-44:{60 if LAND else 96}', 'kiri_atas': f'44:{60 if LAND else 96}', 'tengah_bawah': 'W-w-44:60' if LAND else '(W-w)/2:H-h-170'}[G['logo']]
    pt0 = pen[0]['t0'] if pen else tl.t
    il = spec.get('intro_logo'); t_in = float(il.get('dur', 1.6)) if il else 0.0
    fc.append(f"[2:v]scale={120 if LAND else 150}:-1,format=rgba,colorchannelmixer=aa=0.92[lg]")
    fc.append(f"[v1][lg]overlay={pos}:enable='between(t,{t_in:.2f},{pt0:.2f})'[v2]")
    cur = '[v2]'; nxt = 3
    if il:  # logo reveal: membesar halus (ease-out) + fade, lalu mengecil jadi logo pojok
        args += ['-loop', '1', '-t', f'{t_in:.2f}', '-i', logo]
        fc.append(f"[{nxt}:v]format=rgba,scale=w='trunc({260 if LAND else 340}*(0.8+0.2*(1-pow(1-min(t/0.6,1),3)))/2)*2':h=-2:eval=frame,"
                  f"fade=t=in:st=0:d=0.35:alpha=1,fade=t=out:st={t_in-0.3:.2f}:d=0.3:alpha=1[li]")
        fc.append(f"{cur}[li]overlay=(W-w)/2:(H-h)/2-{Y(il.get('naik', 260))}:eval=frame:enable='lt(t,{t_in:.2f})'[v2b]"); cur = '[v2b]'; nxt += 1
    if pen:
        png = f"{CACHE}/penutup_{spec['id']}.png"
        if not (os.path.exists(png) or penutup_png(G, spec, png)):  # cadangan: kartu sederhana dari logo
            from PIL import Image, ImageDraw
            im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); lg = Image.open(f'{E}/aset/logo.png').convert('RGBA').resize((min(W, H) // 3,) * 2)
            d = ImageDraw.Draw(im); cw, chh = int(min(W, H) * 0.8), int(min(W, H) * 0.62)
            d.rounded_rectangle([(W - cw) // 2, (H - chh) // 2, (W + cw) // 2, (H + chh) // 2], 48, fill=(30, 74, 44, 235))
            im.alpha_composite(lg, ((W - lg.width) // 2, (H - chh) // 2 + 40)); im.save(png)
        args += ['-loop', '1', '-t', f'{tl.t:.2f}', '-i', png]
        fc.append(f"[{nxt}:v]format=rgba,fade=t=in:st={pt0:.2f}:d=0.35:alpha=1[pn]")
        fc.append(f"{cur}[pn]overlay=0:0:enable='gte(t,{pt0:.2f})'[v3]"); cur = '[v3]'
    fc.append(f"{cur}fade=t=out:st={tl.t-0.35:.2f}:d=0.35,format=yuv420p[vo]")
    args += ['-filter_complex', ';'.join(fc), '-map', '[vo]', '-map', '1:a', '-t', f'{tl.t:.3f}',
             '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-maxrate', '10M', '-bufsize', '20M', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-threads', TH,
             '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out]
    sh(args)

def main():
    spec = json.load(open(sys.argv[1]))
    global W, H, LAND
    if '--landscape' in sys.argv or spec.get('format') == 'landscape':
        W, H, LAND = 1920, 1080, True
        spec['id'] = spec['id'] + 'L'; spec['file'] = spec.get('file', spec['id']) + '-Landscape'
    tl, G = build(spec)
    os.makedirs(OUT, exist_ok=True); wd = f"{CACHE}/{spec['id']}"; os.makedirs(wd, exist_ok=True)
    print(f"[{spec['id']}] gaya={spec['gaya']} durasi={tl.t:.1f}s shot={len(tl.shots)} kata={len(tl.words)}", flush=True)
    if tl.peringatan: print('  peringatan: ' + '; '.join(tl.peringatan), flush=True)
    json.dump(dict(shots=tl.shots, voice=tl.voice, words=tl.words, texts=tl.texts, bounds=tl.bounds, dur=tl.t), open(f'{wd}/timeline.json', 'w'), indent=1)
    if '--timeline' in sys.argv: return
    cepat = '--ulang-teks' in sys.argv and os.path.exists(f'{wd}/video.mp4') and os.path.exists(f'{wd}/mix.wav')
    if not cepat:
        info = mix_audio(tl, G, spec, f'{wd}/mix.wav'); print('  audio', info, flush=True)
        assemble(tl, G, f'{wd}/video.mp4'); print('  video ok', flush=True)
    global PETA, VIDEO_POLOS
    from wajahtl import peta_wajah
    VIDEO_POLOS = f'{wd}/video.mp4'
    if cepat and os.path.exists(f'{wd}/wajah.json'): PETA = json.load(open(f'{wd}/wajah.json'))
    else:
        PETA = peta_wajah(f'{wd}/video.mp4', W, H); json.dump(PETA, open(f'{wd}/wajah.json', 'w'))
    lap = make_ass(tl, G, spec, f'{wd}/teks.ass')
    print('  teks', '; '.join(lap) if lap else 'semua posisi aman', flush=True)
    out = f"{OUT}/{spec.get('file', spec['id'])}.mp4"
    final(tl, G, spec, f'{wd}/video.mp4', f'{wd}/mix.wav', f'{wd}/teks.ass', out)
    print('  SELESAI', out, f'{tl.t:.1f}s', flush=True)

if __name__ == '__main__': main()
