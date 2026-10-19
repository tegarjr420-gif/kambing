# Cek sinkron subtitle: tiap kata harus jatuh di bagian yang benar-benar ada suara orang
import json, sys, numpy as np
sys.path.insert(0, '.'); sys.argv += [] 
import edit
spec = json.load(open(sys.argv[1])); tl, G = edit.build(spec)
n = int((tl.t + 0.1) * edit.SR); V = np.zeros((n, 2), np.float32)
for v in tl.voice:
    y = edit.wav_src(v['src'], 'voice'); edit.place(V, y[int(v['a']*edit.SR):int(v['b']*edit.SR)], v['start'], 0.012)
hop = int(0.02 * edit.SR); e = np.sqrt((V[:len(V)//hop*hop, 0].reshape(-1, hop)**2).mean(1)); db = 20*np.log10(e + 1e-9)
thr = np.percentile(db[db > -80], 90) - 22
bad = []
for w in tl.words:
    a, b = int(w['t0']/0.02), max(int(w['t1']/0.02), int(w['t0']/0.02) + 1)
    if db[a:b].max() < thr: bad.append(f"{w['w']}@{w['t0']:.2f}")
print(f"{spec['id']}: {len(tl.words) - len(bad)}/{len(tl.words)} kata jatuh di suara", 'MELESET:', bad[:10])
