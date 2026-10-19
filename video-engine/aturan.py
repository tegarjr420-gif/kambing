# Sutradara cadangan tanpa AI: menyusun naskah dari aturan tetap bila Gemini tidak tersedia.
import random
from sutradara import kalimat

URUT_GAYA = ['promo', 'edukasi', 'hook', 'komersial', 'vlog', 'sinematik']
KARTU = [('Gratis ongkir', 'se-Jabodetabek'), ('DP mulai Rp100rb', 'per ekor'), ('Pilih di katalog', 'barokahfarm.pages.dev')]
JUDUL = {'promo': 'Promo', 'edukasi': 'Info', 'hook': 'Kualitas', 'komersial': 'Commercial', 'vlog': 'Kandang', 'sinematik': 'Kenalan'}

class Broll:
    """pembagi potongan B-roll agar tiap momen dipakai sekali"""
    def __init__(s, K):
        s.k = [(n, k) for n, k in K.items() if k and not k.get('rusak') and k.get('detik_ucapan', 0) < 0.5 and k['terang'] > 0.2]
        s.k.sort(key=lambda x: x[1]['goyang'])
        s.pos = {n: 0.4 for n, _ in s.k}; s.i = 0
    def ambil(s, dur, tenang=False):
        for _ in range(len(s.k) * 2):
            if not s.k: return None
            n, k = s.k[s.i % len(s.k)]; s.i += 1
            if tenang and k['goyang'] >= 2.0: continue
            if s.pos[n] + dur + 0.3 < k['dur']:
                c = {'src': n, 'in': round(s.pos[n], 2), 'dur': dur}; s.pos[n] += dur + 0.6; return c
        return None

def susun(K, info):
    R = random.Random(len(K))
    br = Broll(K)
    momen = []  # (klip, in, out, teks)
    for n, k in K.items():
        if not k or k.get('rusak') or k.get('detik_ucapan', 0) < 2: continue
        cur = None
        for a, b, t in kalimat(n):
            if cur and b - cur[1] <= 14: cur = (cur[0], b, cur[2] + ' ' + t)
            else:
                if cur and cur[1] - cur[0] >= 3: momen.append((n, cur[0], cur[1], cur[2]))
                cur = (a, b, t)
        if cur and cur[1] - cur[0] >= 3: momen.append((n, cur[0], cur[1], cur[2]))
    n_video = max(1, min(6, round(sum(b - a for _, a, b, _ in momen) / 18) if momen else (2 if len(br.k) >= 6 else 1)))
    specs = []
    for vi in range(n_video):
        g = URUT_GAYA[vi % len(URUT_GAYA)]
        bag = []
        c1, c2 = br.ambil(1.6), br.ambil(1.4)
        intro = {'jenis': 'broll', 'klip': [c for c in (c1, c2) if c], 'suara': -6,
                 'teks': [{'kind': 'judul', 'at': 0.2, 'dur': 2.6, 'teks': 'Barokah Farm', 'sub2': 'Kambing & domba · Curug, Tangerang'}]}
        if intro['klip']: bag.append(intro)
        mine = momen[vi::n_video][:2]
        for (n, a, b, t) in mine:
            s = br.ambil(1.2)
            kata = t.split()
            bagian = {'jenis': 'bicara', 'src': n, 'in': max(0, a - 0.1), 'out': b + 0.15, 'rapat': 0.4}
            if s and len(kata) > 8: bagian['sisip'] = [dict(s, pada=kata[len(kata) // 2])]
            bag.append(bagian)
        kartu = [c for c in (br.ambil(1.7), br.ambil(1.7), br.ambil(1.7)) if c]
        if kartu:
            bag.append({'jenis': 'broll', 'klip': kartu, 'suara': -8,
                        'teks': [{'kind': 'kunci', 'at': 0.15 + i * 1.7, 'dur': 1.5, 'teks': a, 'sub2': b} for i, (a, b) in enumerate(KARTU[:len(kartu)])]})
        p = br.ambil(3.4, tenang=True)
        if p: bag.append({'jenis': 'penutup', 'src': p['src'], 'in': p['in'], 'dur': 3.4})
        if len(bag) < 2: continue
        specs.append({'id': f'A{vi + 1}', 'file': f"BarokahFarm-{info['tanggal']}-{vi + 1:02d}-{JUDUL[g]}", 'gaya': g, 'seed': R.randint(1, 99),
                      'musik': {'gaya': None, 'seed': R.randint(1, 99)}, 'bagian': bag,
                      'penutup': {'judul': 'Barokah Farm', 'sub': 'Kambing · Domba · Aqiqah · Qurban'}})
    return specs
