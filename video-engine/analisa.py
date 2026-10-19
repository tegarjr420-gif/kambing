# Analisa otomatis mentahan: transkrip per kata, posisi wajah, guncangan, ketajaman, contact sheet.
# python3 analisa.py <folder_raw> <folder_ana>   -> ana/asr/<id>.json, ana/wajah.json, ana/klip.json, ana/sheet/<id>.jpg
import os, sys, json, subprocess, re, math
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

E = os.path.dirname(os.path.abspath(__file__))
MODELS = os.environ.get('MODELS', '/tmp/claude-0/-home-claude/8530fe1f-175c-5546-b869-127bbb89636c/scratchpad/video-kit/asr')
THREADS = int(os.environ.get('ASR_THREADS', str(max(2, (os.cpu_count() or 2) - 1))))
SR = 16000

def run(cmd):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0: raise RuntimeError(' '.join(cmd)[:300] + '\n' + r.stderr.decode(errors='ignore')[-1500:])
    return r.stdout

def probe(p):
    o = json.loads(run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,width,height,r_frame_rate:stream_side_data=rotation:format=duration', '-of', 'json', p]))
    v = next((s for s in o['streams'] if s.get('codec_type') == 'video'), None)
    if not v: return None
    w, h = v['width'], v['height']; rot = 0
    for sd in v.get('side_data_list', []) or []:
        if 'rotation' in sd: rot = int(sd['rotation'])
    if abs(rot) == 90: w, h = h, w
    a, b = v['r_frame_rate'].split('/')
    return dict(w=w, h=h, fps=round(float(a) / max(float(b), 1), 2), dur=float(o['format'].get('duration', 0)),
                audio=any(s.get('codec_type') == 'audio' for s in o['streams']), orientasi='potrait' if h > w else 'landscape')

# ------------------------------------------------------------------ ASR
_asr = None
def asr_models():
    global _asr
    if _asr is None:
        import sherpa_onnx
        t = f'{MODELS}/sherpa-onnx-whisper-turbo/'
        wh = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=t + 'turbo-encoder.int8.onnx', decoder=t + 'turbo-decoder.int8.onnx',
                                                        tokens=t + 'turbo-tokens.txt', language='id', task='transcribe', num_threads=THREADS)
        d = f'{MODELS}/sherpa-onnx-dolphin-base-ctc-multi-lang-int8-2025-04-02/'
        dol = sherpa_onnx.OfflineRecognizer.from_dolphin_ctc(model=d + 'model.int8.onnx', tokens=d + 'tokens.txt', num_threads=THREADS)
        _asr = (wh, dol)
    return _asr

def potong_segmen(y):
    """bagi audio jadi segmen ucapan <= 25 dtk, dipotong di titik paling sunyi"""
    hop = 320; n = len(y) // hop
    if n < 10: return []
    from scipy.signal import butter, sosfilt
    b = sosfilt(butter(4, [150, 4000], btype='band', fs=SR, output='sos'), y)
    db = 20 * np.log10(np.sqrt((b[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
    thr = max(np.percentile(db, 20) + 8, db.max() - 35)
    act = db > thr
    # tutup celah < 0.6 dtk, buang aktivitas < 0.25 dtk
    k = int(0.6 * SR / hop); idx = np.where(act)[0]
    if not len(idx): return []
    segs = []; s0 = idx[0]; prev = idx[0]
    for i in idx[1:]:
        if i - prev > k: segs.append([s0, prev]); s0 = i
        prev = i
    segs.append([s0, prev])
    segs = [s for s in segs if (s[1] - s[0]) * hop / SR >= 0.25]
    out = []
    for a, b2 in segs:  # pecah yang terlalu panjang di titik sunyi
        while (b2 - a) * hop / SR > 25:
            lo, hi = a + int(15 * SR / hop), a + int(25 * SR / hop)
            cut = lo + int(np.argmin(db[lo:hi])); out.append([a, cut]); a = cut
        out.append([a, b2])
    return [(max(0, a * hop / SR - 0.25), min(len(y) / SR, b2 * hop / SR + 0.35)) for a, b2 in out]

def norm(w): return re.sub(r'[^0-9a-z]', '', w.lower())

def transkrip(wav):
    import difflib
    wh, dol = asr_models()
    from scipy.io import wavfile
    sr, y = wavfile.read(wav); y = y.astype(np.float32) / 32768
    pk = np.abs(y).max() + 1e-9; y = y * min(0.5 / pk, 30)
    segs = []
    for t0, t1 in potong_segmen(y):
        seg = y[int(t0 * SR):int(t1 * SR)]
        d = dol.create_stream(); d.accept_waveform(SR, seg); dol.decode_stream(d)
        toks = [[t, round(float(ts) + t0, 2)] for t, ts in zip(d.result.tokens, d.result.timestamps)]
        dtxt = ' '.join(''.join(t for t, _ in toks).replace('▁', ' ').split())
        if len(norm(dtxt)) < 4: continue  # tidak ada ucapan (suara kandang / musik)
        best = ('', 0.0)
        for lead, tail in ((0.2, 0.6), (0.0, 0.0), (0.4, 1.2)):  # Whisper butuh jeda di ujung; coba ulang bila hasilnya aneh
            pad = np.concatenate([np.zeros(int(SR * lead), np.float32), seg, np.zeros(int(SR * tail), np.float32)])
            s = wh.create_stream(); s.accept_waveform(SR, pad); wh.decode_stream(s); txt = s.result.text.strip()
            cocok = difflib.SequenceMatcher(None, [norm(w) for w in txt.split()], [norm(w) for w in dtxt.split()]).ratio()
            if cocok > best[1]: best = (txt, cocok)
            if cocok >= 0.5: break
        txt, cocok = best
        if cocok < 0.3:  # Whisper berhalusinasi: pakai teks Dolphin bila cukup panjang
            if len(dtxt.split()) < 3: continue
            txt, cocok = dtxt, 0.3
        segs.append(dict(t0=round(t0, 2), t1=round(t1, 2), whisper=txt, tok=toks, cocok=round(cocok, 2)))
    return segs

# ------------------------------------------------------------------ gambar
def frames(p, fps, lebar):
    m = probe(p); w = lebar if m['w'] >= m['h'] else int(lebar * m['w'] / m['h']) // 2 * 2
    h = int(round(w * m['h'] / m['w'])) // 2 * 2
    raw = run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-i', p, '-vf', f'fps={fps},scale={w}:{h}', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'])
    n = len(raw) // (w * h * 3)
    return [np.frombuffer(raw, np.uint8, w * h * 3, i * w * h * 3).reshape(h, w, 3) for i in range(n)], w, h

_yn = None
def wajah_klip(fr, w, h, fps):
    global _yn
    if _yn is None: _yn = cv2.FaceDetectorYN.create(f'{E}/aset/model/yunet.onnx', '', (w, h), score_threshold=0.6)
    _yn.setInputSize((w, h)); rows = []
    for i, f in enumerate(fr):
        _, fs = _yn.detect(f)
        if fs is None or not len(fs): continue
        x, y, bw, bh = max(fs, key=lambda r: r[2] * r[3])[:4]
        rows.append([round(i / fps, 2), round(float(x + bw / 2) / w, 3), round(float(y + bh / 2) / h, 3), round(float(bw) / w, 3)])
    return rows

def goyang(fr):
    """rata-rata pergeseran kamera antar-frame (px pada lebar 320) setelah dibuang gerakan pelan yang disengaja"""
    if len(fr) < 4: return 0.0
    g = [cv2.cvtColor(cv2.resize(f, (320, int(320 * f.shape[0] / f.shape[1]))), cv2.COLOR_BGR2GRAY).astype(np.float32) for f in fr]
    win = cv2.createHanningWindow(g[0].shape[::-1], cv2.CV_32F)
    d = np.array([cv2.phaseCorrelate(a, b, win)[0] for a, b in zip(g, g[1:])])
    # jitter = selisih gerak terhadap rata-rata bergeraknya (pan pelan tidak dihitung)
    k = np.ones(5) / 5
    sm = np.stack([np.convolve(d[:, j], k, 'same') for j in range(2)], 1)
    return float(np.median(np.linalg.norm(d - sm, axis=1)))

def sheet(fr, ts, nama, out, kol=6):
    th = 300 if fr[0].shape[0] > fr[0].shape[1] else 170
    tiles = []
    for f, t in zip(fr, ts):
        im = Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)); im = im.resize((int(th * im.width / im.height), th))
        d = ImageDraw.Draw(im); d.rectangle([0, 0, 58, 20], fill=(0, 0, 0)); d.text((4, 4), f'{t:.1f}s', fill=(255, 230, 0))
        tiles.append(im)
    tw = tiles[0].width; rows = math.ceil(len(tiles) / kol)
    S = Image.new('RGB', (tw * kol, th * rows + 26), (20, 20, 20)); d = ImageDraw.Draw(S)
    d.text((6, 6), nama, fill=(255, 255, 255))
    for i, im in enumerate(tiles): S.paste(im, ((i % kol) * tw, 26 + (i // kol) * th))
    S.save(out, quality=70)

def analisa_klip(p, ana, nama):
    m = probe(p)
    if not m or m['dur'] < 0.8: return None
    info = dict(m, nama=nama)
    # suara -> transkrip
    asr_p = f'{ana}/asr/{nama}.json'
    if not os.path.exists(asr_p):
        segs = []
        if m['audio']:
            wav = f'{ana}/wav/{nama}.wav'
            run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-i', p, '-vn', '-ac', '1', '-ar', str(SR), '-af', 'highpass=f=80', wav])
            segs = transkrip(wav)
        json.dump(dict(dur=m['dur'], segs=segs), open(asr_p, 'w'), ensure_ascii=False)
    J = json.load(open(asr_p))
    info['ucapan'] = ' '.join(s['whisper'] for s in J['segs'])
    info['detik_ucapan'] = round(sum(s['t1'] - s['t0'] for s in J['segs']), 1)
    # gambar: wajah (2 fps), guncangan (10 fps, 6 dtk pertama+tengah), kecerahan, ketajaman
    fr, w, h = frames(p, 2, 640)
    info['wajah'] = wajah_klip(fr, w, h, 2)
    gray = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in fr]
    info['terang'] = round(float(np.mean([g.mean() for g in gray])) / 255, 2)
    info['tajam'] = round(float(np.median([cv2.Laplacian(g, cv2.CV_64F).var() for g in gray])), 1)
    fr10, _, _ = frames(p, 10, 320)
    info['goyang'] = round(goyang(fr10[:120]), 2)
    # contact sheet: maks 24 gambar
    step = max(0.5, m['dur'] / 24); ts = [i * step for i in range(int(m['dur'] / step) + 1) if i * step < m['dur'] - 0.1][:24]
    fs = [fr[min(len(fr) - 1, int(round(t * 2)))] for t in ts]
    sheet(fs, ts, f"{nama}  ({m['dur']:.1f} dtk, {m['orientasi']}, {m['fps']} fps)", f'{ana}/sheet/{nama}.jpg')
    catatan = []
    if info['terang'] < 0.22: catatan.append('gelap')
    if info['tajam'] < 25: catatan.append('kurang tajam/buram')
    if info['goyang'] >= 4.0: catatan.append('sangat goyang')
    elif info['goyang'] >= 0.5: catatan.append('agak goyang (distabilkan)')
    info['catatan'] = catatan
    return info

def main(raw, ana):
    for d in ('asr', 'wav', 'sheet'): os.makedirs(f'{ana}/{d}', exist_ok=True)
    kp = f'{ana}/klip.json'
    K = json.load(open(kp)) if os.path.exists(kp) else {}
    for f in sorted(os.listdir(raw)):
        if not f.endswith('.mp4'): continue
        nama = f[:-4]
        if nama in K: continue
        print('analisa', nama, flush=True)
        try:
            info = analisa_klip(f'{raw}/{f}', ana, nama)
        except Exception as e:
            print('  gagal:', str(e)[:300], flush=True); info = None
        K[nama] = info or dict(nama=nama, rusak=True)
        json.dump(K, open(kp, 'w'), ensure_ascii=False, indent=1)
        if info: print(f"  {info['dur']:.1f}s {info['orientasi']} ucapan={info['detik_ucapan']}s goyang={info['goyang']} wajah={len(info['wajah'])} | {info['ucapan'][:90]}", flush=True)
    json.dump({n: k.get('wajah', []) for n, k in K.items() if k}, open(f'{ana}/wajah.json', 'w'))
    return K

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
