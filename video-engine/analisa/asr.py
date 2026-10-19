# Transkrip tiap file: Whisper (teks per segmen) + Dolphin CTC (waktu token) → ana/asr/<nama>.json
import sherpa_onnx, numpy as np, json, sys, os
from scipy.io import wavfile
from scipy.signal import butter, sosfilt
K = '/tmp/claude-0/-home-claude/8530fe1f-175c-5546-b869-127bbb89636c/scratchpad/video-kit/asr/'
A = os.path.dirname(os.path.abspath(__file__))
W = os.environ.get('WMODEL', 'small')
wd = K + f'sherpa-onnx-whisper-{W}/'
wh = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=wd+f'{W}-encoder.int8.onnx', decoder=wd+f'{W}-decoder.int8.onnx', tokens=wd+f'{W}-tokens.txt', language='id', task='transcribe', num_threads=2)
dm = K + 'sherpa-onnx-dolphin-base-ctc-multi-lang-int8-2025-04-02/'
dol = sherpa_onnx.OfflineRecognizer.from_dolphin_ctc(model=dm+'model.int8.onnx', tokens=dm+'tokens.txt', num_threads=2)
SR = 16000
os.makedirs(A+'/asr', exist_ok=True)
sos = butter(4, [150, 4000], btype='band', fs=SR, output='sos')
for f in dict.fromkeys(sys.argv[1:]):
    if os.path.exists(f'{A}/asr/' + os.path.basename(f)[:-4] + '.json'): continue
    name = os.path.basename(f)[:-4]
    sr, y = wavfile.read(f); y = y.astype(np.float32) / 32768
    pk = np.abs(y).max() + 1e-9
    g = min(0.5 / pk, 30); yn = y * g  # normalisasi agar suara pelan terbaca
    b = sosfilt(sos, yn); hop = 320; n = len(b)//hop
    db = 20*np.log10(np.sqrt((b[:n*hop].reshape(n, hop)**2).mean(1)) + 1e-9)
    thr = max(np.percentile(db, 20) + 8, db.max() - 35)
    act = db > thr
    # gabungkan aktivitas, toleransi jeda 0.6 s, buang < 0.3 s
    segs = []; i = 0
    while i < n:
        if act[i]:
            j = i
            while j < n and (act[j] or (j+30 < n and act[j:j+30].any())): j += 1
            if (j-i)*hop/SR >= 0.3: segs.append([i*hop/SR, j*hop/SR])
            i = j
        else: i += 1
    # pecah segmen > 20 s
    out = []
    for s0, s1 in segs:
        while s1 - s0 > 20: out.append([s0, s0+18]); s0 += 18
        out.append([s0, s1])
    res = []
    for s0, s1 in out:
        a = max(0, int((s0-0.2)*SR)); z = min(len(yn), int((s1+0.2)*SR))
        st = wh.create_stream(); st.accept_waveform(SR, yn[a:z]); wh.decode_stream(st); t = st.result.text.strip()
        sd = dol.create_stream(); sd.accept_waveform(SR, yn[a:z]); dol.decode_stream(sd)
        toks = [[tk, round(float(a/SR + ts), 2)] for tk, ts in zip(sd.result.tokens, sd.result.timestamps)]
        res.append({'t0': round(float(s0), 2), 't1': round(float(s1), 2), 'whisper': t, 'dolphin': ''.join(x for x, _ in toks).replace('▁', ' ').strip(), 'tok': toks})
    json.dump({'dur': len(y)/SR, 'gain_db': round(float(20*np.log10(g)), 1), 'segs': res}, open(f'{A}/asr/{name}.json', 'w'), ensure_ascii=False)
    print('##', name, f'{len(y)/SR:.1f}s')
    for r in res: print(f"  {r['t0']:6.1f}-{r['t1']:6.1f} | {r['whisper']}")
    sys.stdout.flush()
