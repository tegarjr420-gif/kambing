# Stok & autopost: video di Drive "2. Video Jadi" diambil satu per satu oleh n8n (Buffer -> TikTok, Instagram, Facebook).
# Catatan kecil disimpan di volume: caption.json (caption per video), terposting.json (video yang sudah diposting).
import os, json, hmac, hashlib, datetime, threading, re
import jembatan

DATA = os.environ.get('DATA', '/data')
WIB = datetime.timezone(datetime.timedelta(hours=7))
_kunci = threading.Lock()
VIDEO = re.compile(r'\.(mp4|mov|m4v)$', re.I)

def _baca(n, awal):
    try: return json.load(open(f'{DATA}/{n}'))
    except Exception: return awal

def _tulis(n, isi):
    os.makedirs(DATA, exist_ok=True); tmp = f'{DATA}/{n}.tmp'
    json.dump(isi, open(tmp, 'w'), ensure_ascii=False, indent=1); os.replace(tmp, f'{DATA}/{n}')

def simpan_caption(drive_id, data):
    with _kunci:
        C = _baca('caption.json', {}); C[drive_id] = data; _tulis('caption.json', C)

def token(fid): return hmac.new(os.environ.get('ENGINE_KEY', 'x').encode(), fid.encode(), hashlib.sha256).hexdigest()[:24]

def url_media(fid):
    dom = os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'mesin-video-production.up.railway.app')
    return f'https://{dom}/media/{fid}.mp4?t={token(fid)}'

def daftar_stok():
    """video di folder Video Jadi yang belum diposting, terlama dulu"""
    T = _baca('terposting.json', {})
    fs = jembatan.panggil('daftar', folder=jembatan.JADI())['file']
    habis = {k for k, v in T.items() if v.get('berhasil') or v.get('percobaan', 0) >= 3}  # gagal total 3x: dilewati
    fs = [f for f in fs if (VIDEO.search(f['nama']) or str(f.get('mime', '')).startswith('video/')) and f['id'] not in habis]
    return sorted(fs, key=lambda f: (f.get('dibuat') or '', f['nama']))

def stok_aman():
    try: return len(daftar_stok())
    except Exception: return None

def judul_dari_nama(nama):
    t = re.sub(r'^BarokahFarm-[\d-]+?-\d{2}-', '', os.path.splitext(nama)[0])
    return re.sub(r'[-_]+', ' ', t).strip() or 'Barokah Farm'

def caption_cadangan(nama):
    j = judul_dari_nama(nama)
    teks = (f"{j} dari kandang Barokah Farm 🐐\n"
            "Kambing & domba dirawat setiap hari di peternakan kami di Curug, Tangerang.")
    return dict(judul=f'{j} | Barokah Farm'[:80], caption=teks, hashtag=['#barokahfarm', '#peternakankambing', '#aqiqah', '#tangerang'])

# Ajakan per platform (sesuai aturan): TikTok melarang kontak/arahan transaksi di luar aplikasi untuk hewan hidup,
# Instagram maks 5 tagar, Facebook membatasi postingan bertautan (tautan ditaruh di komentar pertama).
CTA = {'tiktok': 'Info lengkap ada di link bio ya 🙏',
       'instagram': 'Info & konsultasi: link di bio 🙏',
       'facebook': 'Katalog & kontak ada di komentar pertama 🙏'}
KOMENTAR_FB = 'Katalog lengkap & kontak WhatsApp Barokah Farm: https://barokahfarm.pages.dev'
LARANG = re.compile(r'(\b(jual|beli|harga|dp|transfer|rekening|termurah|terbaik|termurah|halal)\b|rp\s?\d|\b08\d{7,}|\+?62\d{8,}|https?://|\w+\.pages\.dev)', re.I)

def bersihkan(teks):
    """buang kalimat yang memuat kata/angka terlarang (cadangan bila AI lalai)"""
    kal = re.split(r'(?<=[.!?\n])\s+', teks or '')
    return ' '.join(k for k in kal if k.strip() and not LARANG.search(k)).strip()

def teks_platform(c, judul):
    cap = bersihkan(c.get('caption', '')) or bersihkan(caption_cadangan(judul)['caption'])
    tag = [t for t in (c.get('hashtag') or []) if t.startswith('#')][:5] or ['#barokahfarm']
    return {k: f"{cap}\n\n{CTA[k]}\n\n{' '.join(tag[:4] if k == 'tiktok' else tag)}" for k in CTA}

def pilih_berikut(st, C):
    """AI memilih video yang paling pas diposting sekarang (variasi tema, kekuatan hook, musim). Cadangan: aturan."""
    T = _baca('terposting.json', {})
    riwayat = sorted([v for v in T.values() if v.get('berhasil')], key=lambda v: v.get('waktu', ''))[-6:]
    tema_akhir = [(C.get(k, {}).get('tema') or '') for k, v in T.items() if v.get('berhasil') and v.get('waktu') == (riwayat[-1]['waktu'] if riwayat else None)]
    def aturan():
        cal = sorted(st, key=lambda f: ((C.get(f['id'], {}).get('tema') or '') in tema_akhir, C.get(f['id'], {}).get('tugas') or '', C.get(f['id'], {}).get('prioritas') or 9, f['nama']))
        return cal[0], 'aturan: tema berbeda dari posting terakhir, prioritas sutradara'
    if len(st) == 1: return st[0], 'satu-satunya stok'
    try:
        import sutradara
        calon = [dict(id=f['id'], judul=C.get(f['id'], {}).get('judul') or judul_dari_nama(f['nama']), tema=C.get(f['id'], {}).get('tema', ''),
                      gaya=C.get(f['id'], {}).get('gaya', ''), durasi=C.get(f['id'], {}).get('durasi'), prioritas=C.get(f['id'], {}).get('prioritas'),
                      batch=C.get(f['id'], {}).get('tugas', ''), caption=(C.get(f['id'], {}).get('caption') or '')[:160]) for f in st[:25]]
        lalu = [dict(judul=judul_dari_nama(v.get('nama', '')), tanggal=v.get('waktu', '')[:10], tema=next((C.get(k, {}).get('tema') for k, x in T.items() if x is v), '')) for v in riwayat]
        teks = ("Kamu manajer media sosial Barokah Farm (peternakan kambing & domba, aqiqah, qurban). Pilih SATU video yang paling tepat diposting HARI INI "
                f"({datetime.datetime.now(WIB).strftime('%d %B %Y')}; Iduladha 1448 H sekitar pertengahan Mei 2027; aqiqah sepanjang tahun) ke TikTok, Instagram, dan Facebook.\n"
                "Pertimbangkan: (1) tema jangan sama dengan 1–2 posting terakhir, (2) hook/judul paling kuat, (3) relevansi musim, (4) prioritas saran sutradara di batch yang sama, "
                "(5) video yang lebih lama menunggu sedikit didahulukan.\n"
                f"Posting terakhir: {json.dumps(lalu, ensure_ascii=False)}\nKandidat: {json.dumps(calon, ensure_ascii=False)}\n"
                'Jawab JSON: {"id": "<id kandidat>", "alasan": "<1 kalimat>"}')
        out, use = sutradara.panggil_claude(teks, [], timeout=120)
        J = sutradara.baca_json(out)
        f = next((x for x in st if x['id'] == J.get('id')), None)
        if f: return f, 'AI: ' + str(J.get('alasan', ''))[:200]
    except Exception as e:
        print('pilih posting AI gagal:', str(e)[:200], flush=True)
    return aturan()

def terakhir_posting():
    T = _baca('terposting.json', {})
    w = [v.get('waktu') for v in T.values() if v.get('waktu') and v.get('berhasil')]
    return max(w) if w else None

def ambil(jeda_hari=3, paksa=False, uji_id='', uji_nama=''):
    """video berikutnya untuk diposting; 'jadwal' False bila belum waktunya (jeda dihitung per tanggal WIB)"""
    if uji_id:  # uji: video tertentu (mis. dari arsip), tidak mengubah antrean
        c = caption_cadangan(uji_nama or 'Uji'); tp = teks_platform(c, uji_nama or 'Uji')
        st = stok_aman()
        return dict(jadwal=True, ada=True, id=uji_id, nama=uji_nama, media_url=url_media(uji_id), judul=c['judul'],
                    teks=tp['instagram'], teks_tiktok=tp['tiktok'], teks_instagram=tp['instagram'], teks_facebook=tp['facebook'],
                    komentar_facebook=KOMENTAR_FB, stok=st, stok_setelah=st, uji=True, alasan='uji')
    akhir = terakhir_posting()
    hari_ini = datetime.datetime.now(WIB).date()
    if akhir and not paksa:
        sejak = (hari_ini - datetime.datetime.fromisoformat(akhir).astimezone(WIB).date()).days
        if sejak < jeda_hari: return dict(jadwal=False, ada=False, sejak_hari=sejak, terakhir=akhir)
    st = daftar_stok()
    if not st: return dict(jadwal=True, ada=False, stok=0, terakhir=akhir)
    C = _baca('caption.json', {})
    f, alasan = pilih_berikut(st, C)
    c = C.get(f['id']) or {}
    if not c.get('caption'): c = dict(c, **caption_cadangan(f['nama']))
    judul = (c.get('judul') or judul_dari_nama(f['nama']))
    judul = bersihkan(judul) or judul_dari_nama(f['nama'])
    tp = teks_platform(c, f['nama'])
    return dict(jadwal=True, ada=True, id=f['id'], nama=f['nama'], ukuran=f.get('ukuran'), media_url=url_media(f['id']),
                judul=judul[:90], teks=tp['instagram'], teks_tiktok=tp['tiktok'], teks_instagram=tp['instagram'], teks_facebook=tp['facebook'],
                komentar_facebook=KOMENTAR_FB, alasan=alasan, stok=len(st), stok_setelah=len(st) - 1, terakhir=akhir)

def selesai(fid, nama, hasil, uji=False):
    """hasil: [{layanan, ok, post_id, pesan}] dari Buffer. Dianggap terposting bila minimal satu kanal berhasil."""
    berhasil = any(h.get('ok') for h in hasil)
    if uji: return dict(ok=True, berhasil=berhasil, stok=stok_aman(), uji=True)
    with _kunci:
        T = _baca('terposting.json', {})
        lama = T.get(fid, {})
        T[fid] = dict(nama=nama, waktu=datetime.datetime.now(WIB).isoformat(), berhasil=berhasil or lama.get('berhasil', False),
                      hasil=hasil, percobaan=lama.get('percobaan', 0) + 1)
        _tulis('terposting.json', T)
    return dict(ok=True, berhasil=berhasil, stok=stok_aman())

def perlu_cek_status():
    """post Buffer yang belum dipastikan tayang (untuk dicek n8n beberapa jam kemudian)"""
    T = _baca('terposting.json', {}); out = []
    for fid, v in T.items():
        for h in v.get('hasil', []):
            if h.get('ok') and h.get('post_id') and not h.get('status_akhir'):
                out.append(dict(id=fid, nama=v.get('nama'), layanan=h.get('layanan'), post_id=h['post_id']))
    return out

def catat_status(fid, post_id, status, tautan='', pesan=''):
    with _kunci:
        T = _baca('terposting.json', {})
        for h in T.get(fid, {}).get('hasil', []):
            if h.get('post_id') == post_id:
                if status in ('sent', 'error'): h['status_akhir'] = status
                h['status'] = status; h['tautan'] = tautan; h['pesan_status'] = pesan
        _tulis('terposting.json', T)
