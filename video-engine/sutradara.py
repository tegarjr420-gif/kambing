# Sutradara: menulis naskah edit (spec JSON) dari hasil analisa.
# Utama: Gemini (lewat proxy n8n, kredensial Gemini tersimpan di n8n). Cadangan: aturan tetap (aturan.py) bila AI gagal.
import os, json, re, base64, subprocess, sys, time, random, datetime
import requests

E = os.path.dirname(os.path.abspath(__file__))
from gaya import GAYA
from kata import kata_klip

MUSIK = ['akustik', 'lofi', 'sinematik', 'pop', 'inspirasi', 'tropis', 'folk', 'funk', 'religi', 'hiphop']
TRANSISI = ['cut', 'fade', 'whip', 'zoomin', 'slideleft', 'slideup', 'wipeleft', 'smoothleft', 'hblur', 'fadewhite', 'dissolve']
PENUTUP = {'edukasi': 'terang', 'sinematik': 'gelap', 'hook': 'kuning', 'vlog': 'terang', 'promo': 'hijau', 'komersial': 'hijau'}

ABA = re.compile(r'^(\d+|satu|dua|tiga|empat|lima|oke|ok|action)[,.!]?$', re.I)

def kalimat(nama):
    """ucapan per kalimat dengan waktu sumber: [(t0, t1, teks)]; hitungan aba-aba di awal klip dibuang"""
    try: ws = kata_klip(nama)
    except Exception: return []
    while ws and ABA.match(ws[0]['w'].strip()): ws = ws[1:]
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
- Bagian "bicara" WAJIB berisi kalimat UTUH: "in" tepat sebelum kata pertama sebuah kalimat, "out" setelah kata terakhir yang diakhiri tanda titik/tanya/seru. JANGAN berhenti di koma atau di tengah kalimat (orang terdengar terpotong). Mesin akan memperpanjang otomatis sampai akhir kalimat bila kamu salah.
- Untuk "sisip", "kata", dan "teks" di bagian bicara, JANGAN hitung detik; pakai "pada": "<kata yang diucapkan>" (mesin mencari kata itu), boleh ditambah "geser" (detik).
- Teks di bagian "broll" memakai "at" = detik dari awal bagian itu.
- Jangan isi koordinat "y" kecuali perlu; mesin otomatis menaruh tulisan di area kosong yang tidak menutupi wajah.
- Durasi tiap video 20–50 detik. Tiap video diakhiri bagian "penutup" (1 klip B-roll tenang, dur 3–3.6).
- Klip yang CATATAN-nya "sangat goyang", "gelap", atau "buram" hanya boleh dipakai sebentar (≤1.2 dtk) atau tidak dipakai.
- Momen sumber BOLEH dipakai ulang di video lain (maksimal 2 video per momen), asal tiap video tampil berbeda: hook pembuka, urutan, potongan, gaya, teks, dan sudut cerita berbeda. Jangan ada dua video yang terasa sama.
- Abaikan hitungan aba-aba (\"1, 2, 3\", \"oke\", \"action\") dan bagian sebelum orang mulai bicara; 'in' dimulai tepat sebelum kata pertama kalimat.
- Teks layar singkat (≤ 4 kata per baris), bahasa Indonesia santai, tidak alay, tanpa emoji.
- Teks layar TIDAK BOLEH memuat harga, DP, nomor WA/rekening, alamat web, atau kata jual/beli/harga/DP/transfer/termurah/terbaik (aturan TikTok & Meta).
- Kalimat ucapan yang menyebut harga, nominal, nomor WA, atau klaim superlatif ("termurah", "terbaik", "paling") sebaiknya tidak dipakai bila ada kalimat lain yang setara; bila tetap dipakai, buang bagian klaimnya dengan "buang" kalau bisa dipotong rapi.
- "file": "BarokahFarm-{info['tanggal']}-<no>-<Judul-Singkat>" tanpa spasi. "id": "A1", "A2", dst.
- Keluaran video POTRAIT 1080x1920 untuk TikTok, Instagram, dan Facebook.

## Contoh BENTUK naskah (nama klip di contoh ini hanya penanda <...>; di naskahmu "src" WAJIB persis sama dengan nama klip pada judul "## nama:" di daftar bahan)
{contoh_spec()}

## Bahan mentah ({len(K)} klip). Contact sheet tiap klip terlampir sebagai gambar (judul gambar = nama klip, label waktu di pojok).
{inventaris(K)}

## Yang harus kamu keluarkan
Tanggal hari ini: {datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).strftime('%d %B %Y')} (Iduladha 1448 H diperkirakan sekitar pertengahan Mei 2027; aqiqah sepanjang tahun).
JSON saja: {{"video": [<naskah 1>, <naskah 2>, ...], "catatan": "<ringkasan pilihan editing, klip yang tidak dipakai beserta alasannya, risiko>"}}
MAKSIMALKAN bahan: video ini dipakai untuk autopost berkala, jadi buat sebanyak mungkin video yang layak posting.
Target sekitar {target_video(K)} video (boleh sedikit lebih atau kurang sesuai kualitas bahan, maksimal 12). Tiap video punya tujuan/sudut berbeda
(promo, edukasi, kenalan, suasana kandang, reseller, aqiqah, qurban, tips memilih hewan, dll.). Kualitas tetap nomor satu: jangan isi video dengan klip jelek.

Tiap naskah video WAJIB punya 3 kunci tambahan untuk posting media sosial:
- "caption": 2–3 kalimat bahasa Indonesia santai: kalimat pembuka yang memancing rasa ingin tahu, lalu isi singkat sesuai video. Boleh 1–2 emoji.
  JANGAN tulis harga, DP, nomor WA, rekening, link, atau kata jual/beli/harga/DP/transfer/termurah/terbaik/halal (ajakan & link ditambahkan otomatis per platform).
- "hashtag": TEPAT 4–5 tagar relevan dan spesifik (Instagram membatasi 5), contoh ["#barokahfarm", "#peternakankambing", "#aqiqah", "#tangerang"]. Jangan tagar umum yang spam (#fyp #viral).
- "judul": judul pendek ≤ 70 karakter (dipakai sebagai judul TikTok), tanpa harga/kontak.
- "tema": 1–3 kata topik video (mis. "aqiqah", "tips qurban", "suasana kandang", "kenalan", "reseller").
- "prioritas": angka 1..n urutan posting yang kamu sarankan untuk naskah-naskah ini (1 = paling kuat untuk diposting duluan: hook paling kuat, paling relevan dengan musim/tanggal sekarang)."""

def target_video(K):
    layak = [k for k in K.values() if k and not k.get('rusak')]
    bicara = sum(1 for k in layak if k.get('detik_ucapan', 0) >= 2)
    return max(2, min(12, round(len(layak) / 2), bicara * 2 + 2))

def panggil_gemini(teks, gambar, model=None, timeout=600):
    url = os.environ.get('GEMINI_PROXY_URL'); kunci = os.environ.get('GEMINI_PROXY_KEY', '')
    if not url and not os.environ.get('GEMINI_API_KEY'): raise RuntimeError('GEMINI_PROXY_URL / GEMINI_API_KEY belum diisi')
    parts = [{'text': teks}]
    for nama, p in gambar:
        parts.append({'text': f'Contact sheet klip {nama}:'})
        parts.append({'inline_data': {'mime_type': 'image/jpeg', 'data': base64.b64encode(open(p, 'rb').read()).decode()}})
    body = {'contents': [{'role': 'user', 'parts': parts}],
            'generationConfig': {'temperature': 0.6, 'maxOutputTokens': 60000, 'responseMimeType': 'application/json'}}
    mdl = model or os.environ.get('GEMINI_MODEL', 'gemini-3.8-flash')
    if os.environ.get('GEMINI_API_KEY'):  # langsung ke Gemini (tidak menahan antrean n8n)
        r = requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{mdl}:generateContent',
                          params={'key': os.environ['GEMINI_API_KEY']}, json=body, timeout=timeout)
    else:  # lewat n8n (kredensial Gemini tersimpan di n8n)
        r = requests.post(url, json={'kunci': kunci, 'model': mdl, 'body': body}, timeout=timeout)
    if r.status_code >= 500: r.raise_for_status()
    j = r.json()
    if isinstance(j, list): j = j[0]
    if j.get('error'): raise RuntimeError('Gemini: ' + json.dumps(j['error'])[:400])
    try:
        out = ''.join(p.get('text', '') for p in j['candidates'][0]['content']['parts'])
    except Exception:
        raise RuntimeError('Jawaban Gemini tidak terbaca: ' + json.dumps(j)[:400])
    return out, j.get('usageMetadata', {})

# ------------------------------------------------------------------ Claude (sutradara utama bila ANTHROPIC_API_KEY ada)
class BatasHarian(Exception): pass

def _biaya_path(): return os.path.join(os.environ.get('DATA', '/tmp'), 'biaya_claude.json')

def biaya_hari_ini():
    import datetime
    hari = (datetime.datetime.utcnow() + datetime.timedelta(hours=7)).strftime('%Y-%m-%d')
    try: B = json.load(open(_biaya_path()))
    except Exception: B = {}
    return hari, B

def catat_biaya(usd):
    hari, B = biaya_hari_ini(); B[hari] = round(B.get(hari, 0) + usd, 4)
    try: json.dump(B, open(_biaya_path(), 'w'))
    except Exception: pass
    return B[hari]

def _kecilkan(p, maks=1568):
    from PIL import Image
    import io
    im = Image.open(p).convert('RGB'); s = maks / max(im.size)
    if s < 1: im = im.resize((int(im.width * s), int(im.height * s)))
    b = io.BytesIO(); im.save(b, 'JPEG', quality=80); return base64.b64encode(b.getvalue()).decode()

def panggil_claude(teks, gambar, timeout=900):
    key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if not key: raise RuntimeError('ANTHROPIC_API_KEY belum diisi')
    batas = float(os.environ.get('CLAUDE_BATAS_HARIAN_USD', '1.0'))
    hari, B = biaya_hari_ini()
    if B.get(hari, 0) >= batas:
        raise BatasHarian(f'batas harian Claude ${batas:.2f} sudah tercapai hari ini (${B.get(hari, 0):.2f})')
    content = []
    for nama, p in gambar:
        content.append({'type': 'text', 'text': f'Contact sheet klip {nama}:'})
        content.append({'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': _kecilkan(p)}})
    content.append({'type': 'text', 'text': teks + '\n\nKeluarkan HANYA objek JSON valid, tanpa teks lain, tanpa ```.'})
    body = {'model': os.environ.get('CLAUDE_MODEL', 'claude-sonnet-5-5'), 'max_tokens': int(os.environ.get('CLAUDE_MAX_TOKENS', '40000')),
            'messages': [{'role': 'user', 'content': content}]}
    r = requests.post('https://api.anthropic.com/v1/messages', json=body, timeout=timeout,
                      headers={'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'})
    j = r.json()
    if r.status_code != 200 or j.get('type') == 'error':
        raise RuntimeError(f"Claude {r.status_code}: {json.dumps(j.get('error', j))[:400]}")
    u = j.get('usage', {})
    hin = float(os.environ.get('CLAUDE_HARGA_INPUT', '2.0')); hout = float(os.environ.get('CLAUDE_HARGA_OUTPUT', '10.0'))
    usd = (u.get('input_tokens', 0) * hin + u.get('output_tokens', 0) * hout + u.get('cache_creation_input_tokens', 0) * hin * 1.25
           + u.get('cache_read_input_tokens', 0) * hin * 0.1) / 1e6
    total = catat_biaya(usd)
    out = ''.join(c.get('text', '') for c in j.get('content', []) if c.get('type') == 'text')
    if j.get('stop_reason') == 'max_tokens': raise RuntimeError('jawaban Claude terpotong (max_tokens)')
    return out, dict(totalTokenCount=u.get('input_tokens', 0) + u.get('output_tokens', 0), biaya_usd=round(usd, 4), biaya_hari_ini=total)

def panggil_ai(teks, gambar, log=print):
    """urutan: Claude (bila ada kunci & belum lewat batas harian) -> Gemini"""
    galat = []
    if os.environ.get('ANTHROPIC_API_KEY'):
        try:
            out, use = panggil_claude(teks, gambar); return out, use, 'claude'
        except BatasHarian as e:
            log(f'  {e}'); galat.append(str(e))
        except Exception as e:
            log(f'  Claude gagal: {str(e)[:300]}'); galat.append('Claude: ' + str(e)[:200])
    else:
        galat.append('ANTHROPIC_API_KEY belum diisi')
    if os.environ.get('GEMINI_CADANGAN', '0') == '1':  # nonaktif: pemilik memutuskan tidak memakai Gemini
        try:
            out, use = panggil_gemini(teks, gambar); return out, use, 'gemini'
        except Exception as e:
            galat.append(str(e)[:300])
    raise RuntimeError(' | '.join(galat))

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
    spec['caption'] = str(spec.get('caption') or '').strip()[:1500]
    tg = spec.get('hashtag') or []
    if isinstance(tg, str): tg = tg.split()
    tg = ['#' + re.sub(r'[^0-9A-Za-z_]', '', str(t).lstrip('#')) for t in tg][:8]
    spec['hashtag'] = [t for t in tg if len(t) > 1] or ['#barokahfarm', '#kambing', '#domba', '#aqiqah', '#qurban']
    spec['judul'] = str(spec.get('judul') or judul.replace('-', ' ')).strip()[:80]
    spec['hashtag'] = spec['hashtag'][:5]
    spec['tema'] = str(spec.get('tema') or g).strip()[:40]
    try: spec['prioritas'] = int(spec.get('prioritas') or no)
    except Exception: spec['prioritas'] = no
    # uji cepat: susun timeline (tanpa render)
    p = f"{info['kerja']}/spec_{spec['id']}.json"; json.dump(spec, open(p, 'w'), ensure_ascii=False, indent=1)
    r = subprocess.run([sys.executable, f'{E}/edit.py', p, '--timeline'], capture_output=True, text=True, env=dict(os.environ))
    if r.returncode != 0: return spec, m + ['mesin menolak naskah: ' + (r.stderr or r.stdout)[-300:]]
    d = re.search(r'durasi=([\d.]+)s', r.stdout)
    dur = float(d.group(1)) if d else 0
    if dur < 12 or dur > 75: return spec, m + [f'durasi {dur:.1f} dtk di luar 12–75']
    spec['_durasi'] = dur
    return spec, []

class TundaAI(Exception): pass

def tulis(K, info, log=print):
    """-> (daftar spec, catatan, sumber)"""
    gambar = [(n, f"{info['ana']}/sheet/{n}.jpg") for n, k in K.items() if k and not k.get('rusak') and os.path.exists(f"{info['ana']}/sheet/{n}.jpg")]
    teks = prompt(K, info)
    masalah_lalu = ''
    tunggu_maks = float(os.environ.get('AI_TUNGGU_MENIT', '30')) * 60; t_mulai = time.time()
    jeda = [60, 120, 240, 480, 900]; gagal_beruntun = 0; ditolak = 0
    while True:
        try:
            t0 = time.time()
            out, use, penyedia = panggil_ai(teks + masalah_lalu, gambar, log)
            J = baca_json(out)
            log(f"sutradara {penyedia}: {len(J.get('video', []))} naskah ({time.time() - t0:.0f} dtk, token {use.get('totalTokenCount', '?')}"
                + (f", biaya ${use['biaya_usd']}, hari ini ${use['biaya_hari_ini']}" if 'biaya_usd' in use else '') + ')')
            hasil = []; masalah = []
            semua = J.get('video', [])[:14]
            for i, sp in enumerate(semua, 1):
                sp2, mm = periksa(sp, K, len(hasil) + 1, info)
                if mm and any(x.startswith(('mesin', 'durasi', 'tidak ada')) for x in mm):
                    masalah.append(f"video {i}: " + '; '.join(mm))
                else:
                    hasil.append(sp2)
                    if mm: log(f'  naskah {i} diperbaiki otomatis: ' + '; '.join(mm))
            if hasil and (not masalah or ditolak >= 1 or len(hasil) >= max(2, 0.7 * len(semua))):
                if masalah: log('  sebagian naskah dibuang: ' + '; '.join(masalah)[:400])
                return hasil, J.get('catatan', ''), penyedia
            ditolak += 1
            if ditolak > 2: raise RuntimeError('naskah Gemini terus ditolak mesin')
            masalah_lalu = ('\n\n## PERBAIKI: percobaan sebelumnya ditolak mesin karena:\n- ' + '\n- '.join(masalah) +
                            '\nTulis ulang SELURUH jawaban dengan memperbaiki masalah itu.')
            log('  naskah ditolak, minta perbaikan: ' + '; '.join(masalah)[:400])
            continue
        except Exception as e:
            gagal_beruntun += 1
            log(f'sutradara AI gagal (percobaan {gagal_beruntun}): {str(e)[:300]}')
            if time.time() - t_mulai > tunggu_maks: break
            d = jeda[min(gagal_beruntun - 1, len(jeda) - 1)]
            log(f'  coba lagi dalam {d // 60} menit')
            time.sleep(d)
    if os.environ.get('ATURAN_CADANGAN', '0') != '1':
        raise TundaAI('AI sutradara belum bisa dipakai, editing ditunda')
    import aturan
    hasil = []
    for sp in aturan.susun(K, info):
        sp2, mm = periksa(sp, K, len(hasil) + 1, info)
        if not any(x.startswith(('mesin', 'durasi', 'tidak ada')) for x in mm): hasil.append(sp2)
    return hasil, 'Disusun dengan aturan cadangan (AI tidak tersedia).', 'aturan'
