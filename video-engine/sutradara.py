# Sutradara: menulis naskah edit (spec JSON) dari hasil analisa.
# Utama: Gemini (lewat proxy n8n, kredensial Gemini tersimpan di n8n). Cadangan: aturan tetap (aturan.py) bila AI gagal.
import os, json, re, base64, subprocess, sys, time, random
import requests

E = os.path.dirname(os.path.abspath(__file__))
from gaya import GAYA
from kata import kata_klip

MUSIK = ['akustik', 'lofi', 'sinematik', 'pop', 'inspirasi', 'tropis', 'folk', 'funk', 'religi', 'hiphop']
TRANSISI = ['cut', 'fade', 'whip', 'zoomin', 'slideleft', 'slideup', 'wipeleft', 'smoothleft', 'hblur', 'fadewhite', 'dissolve']
PENUTUP = {'edukasi': 'terang', 'sinematik': 'gelap', 'hook': 'kuning', 'vlog': 'terang', 'promo': 'hijau', 'komersial': 'hijau'}

def kalimat(nama):
    """ucapan per kalimat dengan waktu sumber: [(t0, t1, teks)]"""
    try: ws = kata_klip(nama)
    except Exception: return []
    out = []; cur = []
    for w in ws:
        cur.append(w)
        if re.search(r'[.!?]$', w['w']) or (len(cur) >= 14 and re.search(r',$', w['w'])):
            out.append(cur); cur = []
    if cur: out.append(cur)
    return [(round(c[0]['t0'], 2), round(c[-1]['t1'], 2), ' '.join(w['w'] for w in c)) for c in out]

def inventaris(K):
    baris = []
    for n, k in K.items():
        if not k or k.get('rusak'): continue
        wj = k.get('wajah') or []
        pos = ''
        if wj:
            import numpy as np
            cx = float(np.median([r[1] for r in wj])); pos = f", wajah terlihat {100 * len(wj) / max(1, k['dur'] * 2):.0f}% waktu (posisi x≈{cx:.2f})"
        b = [f"## {n}: {k['dur']:.1f} dtk, {k['orientasi']} {k['w']}x{k['h']}, {k['fps']} fps, terang={k['terang']}, goyang={k['goyang']}"
             f"{pos}{', CATATAN: ' + ', '.join(k['catatan']) if k.get('catatan') else ''}"]
        ks = kalimat(n) if k.get('detik_ucapan', 0) > 0.5 else []
        if ks:
            b.append('ucapan (detik sumber):')
            b += [f'  [{a:.2f}–{c:.2f}] {t}' for a, c, t in ks]
        else:
            b.append('tanpa ucapan (B-roll / suasana)')
        baris.append('\n'.join(b))
    return '\n\n'.join(baris)

def contoh_spec():
    try: return open(f'{E}/sutradara/contoh_spec.json').read()
    except Exception: return ''

def prompt(K, info):
    tugas = open(f'{E}/sutradara/TUGAS_SUTRADARA.md').read()
    master = open(f'{E}/sutradara/MASTER_PROMPT.txt').read()
    gaya = '\n'.join(f"- {g}: {v['nama']}; transisi antar bagian {v['transisi']['antar_bagian']}; musik cocok {v['musik']}" for g, v in GAYA.items())
    return f"""{master}

=====================================================================
{tugas}

## Gaya yang tersedia (pakai gaya BERBEDA untuk tiap video)
{gaya}
Musik (dibuat mesin, aman hak cipta): {', '.join(MUSIK)}. Transisi: {', '.join(TRANSISI)}.

## Aturan teknis naskah (WAJIB, mesin akan menolak yang salah)
- Semua waktu dalam DETIK SUMBER klip ('in', 'out', 'in' klip B-roll). Jangan melebihi durasi klip.
- Bagian "bicara": ambil rentang kalimat utuh dari daftar ucapan (in sedikit sebelum kata pertama, out sedikit setelah kata terakhir). Kalimat yang salah ucap/terpotong/menyebut fakta keliru dibuang dengan "buang": [[x,y]].
- Untuk "sisip", "kata", dan "teks" di bagian bicara, JANGAN hitung detik; pakai "pada": "<kata yang diucapkan>" (mesin mencari kata itu), boleh ditambah "geser" (detik).
- Teks di bagian "broll" memakai "at" = detik dari awal bagian itu.
- Jangan isi koordinat "y" kecuali perlu; mesin otomatis menaruh tulisan di area kosong yang tidak menutupi wajah.
- Durasi tiap video 20–50 detik. Tiap video diakhiri bagian "penutup" (1 klip B-roll tenang, dur 3–3.6).
- Klip yang CATATAN-nya "sangat goyang", "gelap", atau "buram" hanya boleh dipakai sebentar (≤1.2 dtk) atau tidak dipakai.
- Satu momen sumber (rentang waktu yang sama dari klip yang sama) hanya boleh muncul di satu video.
- Teks layar singkat (≤ 4 kata per baris), bahasa Indonesia santai, tidak alay, tanpa emoji.
- "file": "BarokahFarm-{info['tanggal']}-<no>-<Judul-Singkat>" tanpa spasi. "id": "A1", "A2", dst.
- Keluaran video POTRAIT 1080x1920 untuk TikTok, Instagram, dan Facebook.

## Contoh naskah yang sudah benar
{contoh_spec()}

## Bahan mentah ({len(K)} klip). Contact sheet tiap klip terlampir sebagai gambar (judul gambar = nama klip, label waktu di pojok).
{inventaris(K)}

## Yang harus kamu keluarkan
JSON saja: {{"video": [<naskah 1>, <naskah 2>, ...], "catatan": "<ringkasan pilihan editing, klip yang tidak dipakai beserta alasannya, risiko>"}}
Buat sebanyak mungkin video BAGUS dari bahan ini (1–6 video), tiap video punya tujuan berbeda (promo, edukasi, kenalan, testimoni suasana, dll.). Maksimalkan pemakaian momen yang bagus, tapi kualitas lebih penting dari jumlah."""

def panggil_gemini(teks, gambar, model=None, timeout=600):
    url = os.environ.get('GEMINI_PROXY_URL'); kunci = os.environ.get('GEMINI_PROXY_KEY', '')
    if not url: raise RuntimeError('GEMINI_PROXY_URL belum diisi')
    parts = [{'text': teks}]
    for nama, p in gambar:
        parts.append({'text': f'Contact sheet klip {nama}:'})
        parts.append({'inline_data': {'mime_type': 'image/jpeg', 'data': base64.b64encode(open(p, 'rb').read()).decode()}})
    body = {'contents': [{'role': 'user', 'parts': parts}],
            'generationConfig': {'temperature': 0.6, 'maxOutputTokens': 60000, 'responseMimeType': 'application/json'}}
    r = requests.post(url, json={'kunci': kunci, 'model': model or os.environ.get('GEMINI_MODEL', 'gemini-3.8-flash'), 'body': body}, timeout=timeout)
    r.raise_for_status(); j = r.json()
    if isinstance(j, list): j = j[0]
    if j.get('error'): raise RuntimeError('Gemini: ' + json.dumps(j['error'])[:400])
    try:
        out = ''.join(p.get('text', '') for p in j['candidates'][0]['content']['parts'])
    except Exception:
        raise RuntimeError('Jawaban Gemini tidak terbaca: ' + json.dumps(j)[:400])
    return out, j.get('usageMetadata', {})

def baca_json(s):
    s = s.strip(); s = re.sub(r'^```[a-z]*\s*', '', s); s = re.sub(r'```\s*$', '', s)
    try: return json.loads(s)
    except Exception:
        a, b = s.find('{'), s.rfind('}')
        return json.loads(s[a:b + 1])

# ------------------------------------------------------------------ pemeriksa naskah
def periksa(spec, K, no, info):
    """perbaiki yang bisa diperbaiki, kembalikan (spec, daftar_masalah_fatal)"""
    m = []
    g = spec.get('gaya')
    if g not in GAYA: spec['gaya'] = g = 'edukasi'
    spec['id'] = f'A{no}'
    judul = re.sub(r'[^A-Za-z0-9-]', '', str(spec.get('file', '')).split('-')[-1])[:30] or g.capitalize()
    spec['file'] = f"BarokahFarm-{info['tanggal']}-{no:02d}-{judul}"
    mz = spec.setdefault('musik', {})
    if mz.get('gaya') not in MUSIK: mz['gaya'] = GAYA[g]['musik'][0]
    mz['seed'] = int(mz.get('seed') or random.randint(1, 99))
    if mz.get('bpm') and not (70 <= float(mz['bpm']) <= 140): mz.pop('bpm')
    bag = []
    for b in spec.get('bagian', []):
        j = b.get('jenis')
        if 'transisi' in b and b['transisi'] != 'cut':
            t = b['transisi']
            if not (isinstance(t, list) and len(t) == 2 and t[0] in TRANSISI): b.pop('transisi')
            else: b['transisi'] = [t[0], min(0.8, max(0.12, float(t[1])))]
        if j == 'bicara':
            k = K.get(b.get('src'))
            if not k or k.get('rusak'): m.append(f"bicara: klip {b.get('src')} tidak ada"); continue
            b['in'] = max(0.0, float(b.get('in', 0))); b['out'] = min(k['dur'] - 0.02, float(b.get('out', k['dur'])))
            if b['out'] - b['in'] < 1.0: m.append(f"bicara {b['src']}: rentang terlalu pendek"); continue
            if k.get('detik_ucapan', 0) < 0.5: m.append(f"bicara {b['src']}: klip ini tidak berisi ucapan"); continue
            b['sisip'] = [c for c in b.get('sisip', []) if c.get('src') in K and not K[c['src']].get('rusak') and
                          0 <= float(c.get('in', 0)) < K[c['src']]['dur'] - 0.5]
            for c in b['sisip']: c['dur'] = min(4.0, max(0.5, float(c.get('dur', 1.2))))
        elif j in ('broll', 'penutup'):
            items = b.get('klip') if j == 'broll' else [b]
            ok = []
            for c in items or []:
                k = K.get(c.get('src'))
                if not k or k.get('rusak'): m.append(f"{j}: klip {c.get('src')} tidak ada"); continue
                c['dur'] = min(6.0, max(0.4, float(c.get('dur', 2.0))))
                lam = float(c.get('lambat', b.get('lambat', 1.0)) or 1.0)
                c['in'] = max(0.0, min(float(c.get('in', 0)), k['dur'] - c['dur'] / lam - 0.1))
                ok.append(c)
            if not ok: continue
            if j == 'broll': b['klip'] = ok
        else:
            m.append(f'jenis bagian tidak dikenal: {j}'); continue
        bag.append(b)
    if not bag: return spec, m + ['tidak ada bagian yang valid']
    if bag[-1].get('jenis') != 'penutup':
        br = [n for n, k in K.items() if k and not k.get('rusak') and k.get('detik_ucapan', 0) < 0.5 and k['goyang'] < 3.0]
        if br: bag.append({'jenis': 'penutup', 'src': br[no % len(br)], 'in': 1.0, 'dur': 3.4})
    spec['bagian'] = bag
    spec.setdefault('penutup', {'judul': 'Barokah Farm', 'sub': 'Kambing · Domba · Aqiqah · Qurban'})
    # uji cepat: susun timeline (tanpa render)
    p = f"{info['kerja']}/spec_{spec['id']}.json"; json.dump(spec, open(p, 'w'), ensure_ascii=False, indent=1)
    r = subprocess.run([sys.executable, f'{E}/edit.py', p, '--timeline'], capture_output=True, text=True, env=dict(os.environ))
    if r.returncode != 0: return spec, m + ['mesin menolak naskah: ' + (r.stderr or r.stdout)[-300:]]
    d = re.search(r'durasi=([\d.]+)s', r.stdout)
    dur = float(d.group(1)) if d else 0
    if dur < 12 or dur > 75: return spec, m + [f'durasi {dur:.1f} dtk di luar 12–75']
    spec['_durasi'] = dur
    return spec, []

def tulis(K, info, log=print):
    """-> (daftar spec, catatan, sumber)"""
    gambar = [(n, f"{info['ana']}/sheet/{n}.jpg") for n, k in K.items() if k and not k.get('rusak') and os.path.exists(f"{info['ana']}/sheet/{n}.jpg")]
    teks = prompt(K, info)
    masalah_lalu = ''
    for coba in range(2):
        try:
            t0 = time.time()
            out, use = panggil_gemini(teks + masalah_lalu, gambar)
            J = baca_json(out)
            log(f"sutradara Gemini: {len(J.get('video', []))} naskah ({time.time() - t0:.0f} dtk, token {use.get('totalTokenCount', '?')})")
            hasil = []; masalah = []
            for i, sp in enumerate(J.get('video', [])[:6], 1):
                sp2, mm = periksa(sp, K, len(hasil) + 1, info)
                if mm and any(x.startswith(('mesin', 'durasi', 'tidak ada')) for x in mm):
                    masalah.append(f"video {i}: " + '; '.join(mm))
                else:
                    hasil.append(sp2)
                    if mm: log(f'  naskah {i} diperbaiki otomatis: ' + '; '.join(mm))
            if hasil and (not masalah or coba == 1):
                return hasil, J.get('catatan', ''), 'gemini'
            masalah_lalu = ('\n\n## PERBAIKI: percobaan sebelumnya ditolak mesin karena:\n- ' + '\n- '.join(masalah) +
                            '\nTulis ulang SELURUH jawaban dengan memperbaiki masalah itu.')
            log('  naskah ditolak, minta perbaikan: ' + '; '.join(masalah)[:400])
        except Exception as e:
            log(f'sutradara Gemini gagal (percobaan {coba + 1}): {str(e)[:300]}')
            if coba == 0: time.sleep(20)
    import aturan
    hasil = []
    for sp in aturan.susun(K, info):
        sp2, mm = periksa(sp, K, len(hasil) + 1, info)
        if not any(x.startswith(('mesin', 'durasi', 'tidak ada')) for x in mm): hasil.append(sp2)
    return hasil, 'Disusun dengan aturan cadangan (AI tidak tersedia).', 'aturan'
