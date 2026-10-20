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
            "Kambing & domba sehat dirawat langsung di Curug, Tangerang. Siap untuk aqiqah, qurban, dan kebutuhan lainnya.\n"
            "Cek katalog di barokahfarm.pages.dev atau chat WA 0878-9014-0532.")
    return dict(judul=f'{j} | Barokah Farm'[:80], caption=teks, hashtag=['#barokahfarm', '#kambing', '#domba', '#aqiqah', '#qurban', '#tangerang'])

def terakhir_posting():
    T = _baca('terposting.json', {})
    w = [v.get('waktu') for v in T.values() if v.get('waktu') and v.get('berhasil')]
    return max(w) if w else None

def ambil(jeda_hari=3, paksa=False, uji_id='', uji_nama=''):
    """video berikutnya untuk diposting; 'jadwal' False bila belum waktunya (jeda dihitung per tanggal WIB)"""
    if uji_id:  # uji: video tertentu (mis. dari arsip), tidak mengubah antrean
        c = caption_cadangan(uji_nama or 'Uji')
        st = stok_aman()
        return dict(jadwal=True, ada=True, id=uji_id, nama=uji_nama, media_url=url_media(uji_id), judul=c['judul'],
                    teks=c['caption'] + '\n\n' + ' '.join(c['hashtag']), stok=st, stok_setelah=st, uji=True)
    akhir = terakhir_posting()
    hari_ini = datetime.datetime.now(WIB).date()
    if akhir and not paksa:
        sejak = (hari_ini - datetime.datetime.fromisoformat(akhir).astimezone(WIB).date()).days
        if sejak < jeda_hari: return dict(jadwal=False, ada=False, sejak_hari=sejak, terakhir=akhir)
    st = daftar_stok()
    if not st: return dict(jadwal=True, ada=False, stok=0, terakhir=akhir)
    f = st[0]; C = _baca('caption.json', {})
    c = C.get(f['id']) or {}
    if not c.get('caption'): c = dict(c, **caption_cadangan(f['nama']))
    tag = ' '.join(c.get('hashtag') or [])
    return dict(jadwal=True, ada=True, id=f['id'], nama=f['nama'], ukuran=f.get('ukuran'), media_url=url_media(f['id']),
                judul=(c.get('judul') or judul_dari_nama(f['nama']))[:90], teks=(c.get('caption', '') + ('\n\n' + tag if tag else '')).strip(),
                stok=len(st), stok_setelah=len(st) - 1, terakhir=akhir)

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
