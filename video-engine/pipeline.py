# Alur otomatis: Drive "1. Video Mentah" -> unduh -> analisa -> sutradara (Claude) -> render -> cek
#   -> unggah ke "2. Video Jadi" -> pastikan semua video ada di Drive -> baru hapus mentahan di Drive
#   + semua data tugas di server (mentahan, analisa, cache, salinan QC) -> lapor WhatsApp admin.
# Video di "2. Video Jadi" diambil satu per satu oleh autopost (n8n + Buffer), lihat posting.py.
import os, sys, json, time, re, shutil, subprocess, threading, traceback, datetime, glob
import requests

E = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, E)
import jembatan

DATA = os.environ.get('DATA', '/data')
WIB = datetime.timezone(datetime.timedelta(hours=7))
KUNCI = threading.Lock()
SEKARANG = {'tugas': None}

def now(): return datetime.datetime.now(WIB)

def sudah_diproses():
    try: return set(json.load(open(f'{DATA}/sudah.json')))
    except Exception: return set()

def tandai(fid):
    s = sudah_diproses(); s.add(fid); os.makedirs(DATA, exist_ok=True); json.dump(sorted(s), open(f'{DATA}/sudah.json', 'w'))

def lapor_wa(teks, log=print, **ekstra):
    """kirim ke WA admin lewat n8n; ekstra: chat_id (satu nomor saja), berkas_url + berkas_nama (kirim file)"""
    url = os.environ.get('LAPOR_URL')
    if not url: log('(lapor WA dilewati: LAPOR_URL kosong)'); return
    try:
        r = requests.post(url, json=dict(kunci=os.environ.get('GEMINI_PROXY_KEY', ''), teks=teks, **ekstra), timeout=60)
        log(f'lapor WA: {r.status_code}')
    except Exception as e:
        log(f'lapor WA gagal: {e}')

class Tugas:
    def __init__(s, jid=None):
        s.id = jid or now().strftime('%Y%m%d-%H%M')
        s.dir = f'{DATA}/tugas/{s.id}'
        for d in ('raw', 'ana', 'cache', 'out'): os.makedirs(f'{s.dir}/{d}', exist_ok=True)
        s.st_path = f'{s.dir}/status.json'
        s.st = json.load(open(s.st_path)) if os.path.exists(s.st_path) else dict(id=s.id, tahap='mulai', file={}, video=[], mulai=now().isoformat())
    def simpan(s): json.dump(s.st, open(s.st_path, 'w'), ensure_ascii=False, indent=1)
    def log(s, *a):
        line = now().strftime('%H:%M:%S ') + ' '.join(str(x) for x in a)
        print(f'[{s.id}] {line}', flush=True)
        with open(f'{s.dir}/log.txt', 'a') as f: f.write(line + '\n')
    def tahap(s, t): s.st['tahap'] = t; s.simpan(); s.log('== tahap:', t)

def nama_aman(n, ada):
    b = re.sub(r'[^A-Za-z0-9]+', '_', os.path.splitext(n)[0]).strip('_')[:40] or 'klip'
    x = b; i = 2
    while x in ada: x = f'{b}_{i}'; i += 1
    return x

def env_mesin(T):
    e = dict(os.environ, RAW=f'{T.dir}/raw', ANA=f'{T.dir}/ana', CACHE=f'{T.dir}/cache', OUT=f'{T.dir}/out')
    return e

# ------------------------------------------------------------------ tahap-tahap
def t_unduh(T, files):
    T.tahap('unduh')
    sudah = {v['drive_id']: k for k, v in T.st['file'].items()}
    for f in files:
        if f['id'] in sudah: continue
        n = nama_aman(f['nama'], set(T.st['file']))
        T.log(f"unduh {f['nama']} -> {n}")
        try:
            size = jembatan.unduh(f['id'], f'{T.dir}/raw/{n}.mp4', T.log)
            T.st['file'][n] = dict(drive_id=f['id'], asli=f['nama'], ukuran=size, dihapus=False); T.simpan(); tandai(f['id'])
        except Exception as e:
            T.log(f"  gagal unduh {f['nama']}: {e}")
            T.st.setdefault('gagal_unduh', []).append(f['nama']); T.simpan()

def t_hapus_drive(T):
    T.tahap('hapus_mentahan')
    if not jembatan.ada():
        T.log('jembatan Drive belum dipasang: mentahan TIDAK bisa dihapus otomatis'); T.st['hapus_catatan'] = 'jembatan belum dipasang'; T.simpan(); return
    for n, f in T.st['file'].items():
        if f.get('dihapus'): continue
        try:
            r = jembatan.hapus(f['drive_id']); f['dihapus'] = r.get('cara', True); T.simpan()
            T.log(f"mentahan {f['asli']} dihapus dari Drive ({r.get('cara')})")
        except Exception as e:
            T.log(f"  gagal hapus {f['asli']}: {e}")

def t_analisa(T):
    T.tahap('analisa')
    import analisa
    return analisa.main(f'{T.dir}/raw', f'{T.dir}/ana')

def t_sutradara(T, K):
    T.tahap('sutradara')
    import kata; kata.ANA = f'{T.dir}/ana'
    os.environ.update(env_mesin(T))
    import sutradara
    p = f'{T.dir}/naskah.json'
    if os.path.exists(p):
        J = json.load(open(p)); return J['video'], J.get('catatan', ''), J.get('sumber', '?')
    info = dict(tanggal=T.id, ana=f'{T.dir}/ana', kerja=T.dir)
    specs, catatan, sumber = sutradara.tulis(K, info, log=T.log)
    json.dump(dict(video=specs, catatan=catatan, sumber=sumber), open(p, 'w'), ensure_ascii=False, indent=1)
    T.log(f'{len(specs)} naskah dari {sumber}. Catatan: {str(catatan)[:500]}')
    return specs, catatan, sumber

def t_render(T, specs):
    T.tahap('render')
    hasil = []
    for sp in specs:
        out = f"{T.dir}/out/{sp['file']}.mp4"
        if not os.path.exists(out):
            p = f"{T.dir}/spec_{sp['id']}.json"; json.dump(sp, open(p, 'w'), ensure_ascii=False, indent=1)
            T.log(f"render {sp['id']} ({sp['gaya']}, ±{sp.get('_durasi', 0):.0f} dtk)")
            t0 = time.time()
            import signal
            lp = f'{T.dir}/render_{sp["id"]}.log'
            with open(lp, 'w') as lf:
                pr = subprocess.Popen([sys.executable, f'{E}/edit.py', p], stdout=lf, stderr=lf, stdin=subprocess.DEVNULL,
                                      env=env_mesin(T), start_new_session=True)
                try: pr.wait(timeout=int(os.environ.get('RENDER_BATAS_DTK', '2700')))
                except subprocess.TimeoutExpired: T.log(f"  render {sp['id']} melebihi batas waktu, dihentikan")
                finally:
                    try: os.killpg(pr.pid, signal.SIGKILL)
                    except Exception: pass
            keluaran = open(lp).read()
            if pr.returncode != 0 or not os.path.exists(out):
                T.log(f"  GAGAL render {sp['id']}: {keluaran[-400:]}"); continue
            teks = re.findall(r'^\s+teks (.*)$', keluaran, re.M)
            sp['_peringatan'] = re.findall(r'^\s+peringatan: (.*)$', keluaran, re.M)
            if sp['_peringatan']: T.log('  ' + '; '.join(sp['_peringatan']))
            T.log(f"  selesai {time.time() - t0:.0f} dtk; teks: {teks[0][:300] if teks else '-'}")
            shutil.rmtree(f"{T.dir}/cache/{sp['id']}", ignore_errors=True)
            for f in glob.glob(f'{T.dir}/cache/shot_*.mp4') + glob.glob(f'{T.dir}/cache/stab_*.trf'): os.remove(f)
        hasil.append(dict(id=sp['id'], gaya=sp['gaya'], file=out, peringatan=sp.get('_peringatan', [])))
    return hasil

def cek_video(T, v):
    """cek teknis: durasi, kenyaringan, subtitle didengar ulang"""
    o = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height', '-of', 'json', v['file']], capture_output=True, text=True)
    J = json.loads(o.stdout or '{}')
    v['durasi'] = round(float(J.get('format', {}).get('duration', 0)), 1)
    vs = [s for s in J.get('streams', []) if s.get('codec_type') == 'video']
    v['ukuran'] = f"{vs[0]['width']}x{vs[0]['height']}" if vs else '?'
    e = subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-i', v['file'], '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    m = re.findall(r'I:\s+(-?[\d.]+) LUFS', e); v['lufs'] = float(m[-1]) if m else None
    masalah = []
    if v['durasi'] < 10: masalah.append('terlalu pendek')
    if v['lufs'] is None or abs(v['lufs'] + 14) > 2: masalah.append(f"volume {v['lufs']}")
    if v.get('peringatan'): masalah.append('cek bagian bicara (mungkin terpotong)')
    v['masalah'] = masalah
    return v

def salin_qc(T, path, nama):
    """opsional: salinan untuk pemeriksaan kualitas jarak jauh (Supabase Storage)"""
    url, key = os.environ.get('QC_STORAGE_URL'), os.environ.get('QC_STORAGE_KEY')
    if not url or not key: return
    try:
        with open(path, 'rb') as f:
            r = requests.post(f'{url}/{T.id}/{nama}', data=f, timeout=600,
                              headers={'apikey': key, 'Authorization': f'Bearer {key}', 'x-upsert': 'true',
                                       'Content-Type': 'video/mp4' if nama.endswith('.mp4') else 'application/octet-stream'})
        T.log(f'salinan QC {nama}: {r.status_code}')
    except Exception as e:
        T.log(f'salinan QC gagal: {e}')

def t_unggah(T, hasil):
    """unggah langsung ke folder "2. Video Jadi" (tanpa sub-folder) agar autopost mudah mengambil satu per satu"""
    T.tahap('unggah')
    if not jembatan.ada():
        T.log('jembatan Drive belum dipasang: video jadi disimpan di server saja'); return False
    for v in hasil:
        if v.get('drive_id'): continue
        for coba in range(3):
            try:
                r = jembatan.unggah(v['file'], jembatan.JADI()); v['url'] = r['url']; v['drive_id'] = r['id']
                T.log(f"unggah {os.path.basename(v['file'])} ok"); break
            except Exception as e:
                T.log(f'  unggah gagal ({coba + 1}): {e}'); time.sleep(10)
        T.st['video'] = hasil; T.simpan()
    return True

def t_verifikasi(T, hasil):
    """pastikan SEMUA video benar-benar ada di Drive dengan ukuran yang sama sebelum apa pun dihapus"""
    T.tahap('verifikasi')
    try:
        ada = {f['id']: f for f in jembatan.panggil('daftar', folder=jembatan.JADI())['file']}
    except Exception as e:
        T.log(f'verifikasi gagal membaca Drive: {e}'); return False
    ok = True
    for v in hasil:
        f = ada.get(v.get('drive_id'))
        if not f or int(f.get('ukuran') or 0) != os.path.getsize(v['file']):
            T.log(f"  BELUM ADA di Drive: {os.path.basename(v['file'])}"); ok = False
    T.log('semua video terverifikasi di Drive' if ok else 'verifikasi GAGAL: data tidak dihapus')
    return ok

def simpan_caption(T, specs, hasil):
    import posting
    by_file = {f"{T.dir}/out/{sp['file']}.mp4": sp for sp in specs}
    for v in hasil:
        sp = by_file.get(v['file'], {})
        if v.get('drive_id'):
            posting.simpan_caption(v['drive_id'], dict(nama=os.path.basename(v['file']), judul=sp.get('judul', ''), caption=sp.get('caption', ''),
                                                       hashtag=sp.get('hashtag', []), gaya=v.get('gaya'), durasi=v.get('durasi'), tugas=T.id,
                                                       tema=sp.get('tema', ''), prioritas=sp.get('prioritas', 9)))

def hapus_qc(T):
    url, key = os.environ.get('QC_STORAGE_URL'), os.environ.get('QC_STORAGE_KEY')
    if not url or not key: return
    try:
        base, ember_path = url.split('/object/', 1)
        ember, awal = ember_path.split('/', 1)
        h = {'apikey': key, 'Authorization': f'Bearer {key}'}
        r = requests.post(f'{base}/object/list/{ember}', json={'prefix': f'{awal}/{T.id}/', 'limit': 1000}, headers=h, timeout=60)
        nama = [f"{awal}/{T.id}/{o['name']}" for o in r.json()] if r.ok else []
        if nama: requests.delete(f'{base}/object/{ember}', json={'prefixes': nama}, headers=h, timeout=60)
        T.log(f'salinan QC dihapus: {len(nama)} file')
    except Exception as e:
        T.log(f'hapus salinan QC gagal: {e}')

def judul_dari(file): return re.sub(r'^BarokahFarm-[\d-]+?-\d{2}-', '', os.path.basename(file)[:-4]).replace('-', ' ')

def jalankan(files, jid=None, uji=False):
    if not KUNCI.acquire(blocking=False): return None
    if not jid:  # tugas baru: bersihkan mentahan & cache tugas lama agar disk cukup
        for d in glob.glob(f'{DATA}/tugas/*'):
            shutil.rmtree(f'{d}/raw', ignore_errors=True); shutil.rmtree(f'{d}/cache', ignore_errors=True)
    T = Tugas(jid); SEKARANG['tugas'] = T.id
    if uji: T.st['uji'] = True; T.simpan()
    awal = '🧪 *UJI COBA MESIN* (mentahan lama, abaikan bila bukan Anda)\n' if T.st.get('uji') else ''
    try:
        baru = not T.st['file']
        t_unduh(T, files)
        if not T.st['file']: T.log('tidak ada mentahan yang bisa dipakai'); T.tahap('gagal'); return T
        if baru:
            menit = 20 + 6 * len(T.st['file'])
            lapor_wa(awal + f"🎬 *Mentahan diterima*: {len(T.st['file'])} video. Mesin sedang mengedit, perkiraan selesai ±{menit} menit. Hasilnya nanti dikirim ke sini.", T.log)
        K = t_analisa(T)
        import sutradara
        try:
            specs, catatan, sumber = t_sutradara(T, K)
        except sutradara.TundaAI:
            T.st['tunda_ke'] = T.st.get('tunda_ke', 0) + 1
            T.st['tunda_sampai'] = (now() + datetime.timedelta(minutes=30)).isoformat()
            if T.st['tunda_ke'] == 1:
                lapor_wa(awal + '⏳ AI sutradara (Claude) sedang gangguan atau batas biaya harian tercapai. Mentahan aman tersimpan; editing ditunda dan mesin mencoba lagi otomatis tiap 30 menit.', T.log)
            if T.st['tunda_ke'] >= 48:
                lapor_wa(awal + '⚠️ AI sutradara (Claude) tidak bisa dipakai lebih dari 24 jam, editing belum bisa dibuat. Cek saldo & batas di platform.claude.com.', T.log)
                T.tahap('gagal'); return T
            T.tahap('tunggu_ai'); T.log('ditunda: menunggu AI sutradara, dicoba lagi', T.st['tunda_sampai']); return T
        if not specs: T.tahap('gagal'); lapor_wa('⚠️ Mesin video tidak bisa menyusun video dari mentahan terakhir (bahan kurang/rusak). Mentahan TIDAK dihapus dari Drive. Mohon cek atau kirim mentahan lain.', T.log); return T
        if not T.st.get('video'):
            hasil = [cek_video(T, v) for v in t_render(T, specs)]
            if not hasil: T.tahap('gagal'); lapor_wa('⚠️ Semua video gagal dirender. Mentahan TIDAK dihapus dari Drive; mesin akan dicek.', T.log); return T
            T.st['video'] = hasil; T.simpan()
            for v in hasil: salin_qc(T, v['file'], os.path.basename(v['file']))
        hasil = T.st['video']
        if not t_unggah(T, hasil) or not t_verifikasi(T, hasil):
            T.st['gagal_unggah'] = T.st.get('gagal_unggah', 0) + 1; T.tahap('unggah_gagal')
            if T.st['gagal_unggah'] in (1, 3):
                lapor_wa(awal + '⚠️ Video sudah jadi tetapi BELUM berhasil masuk ke Drive. Mentahan dan data TIDAK dihapus; mesin mencoba unggah lagi otomatis.', T.log)
            return T
        simpan_caption(T, specs, hasil)
        t_hapus_drive(T)
        import posting
        stok = posting.stok_aman()
        baris = []
        for i, v in enumerate(hasil, 1):
            b = f"{i}. *{judul_dari(v['file'])}* ({v['gaya']}, {v['durasi']:.0f} dtk)"
            if v.get('url'): b += f"\n   {v['url']}"
            if v['masalah']: b += f"\n   ⚠️ {', '.join(v['masalah'])}"
            baris.append(b)
        dihapus = sum(1 for f in T.st['file'].values() if f.get('dihapus'))
        teks = awal + (f"✅ *{len(hasil)} video baru masuk folder 2. Video Jadi*\n\n" + '\n'.join(baris) +
                (f"\n\n📦 Stok video siap posting sekarang: *{stok}* (autopost 1 video tiap 3 hari)." if stok is not None else '') +
                (f"\n🗑️ {dihapus} mentahan sudah dihapus dari Drive, data di server dibersihkan." if dihapus else '') +
                "\n\nTonton dulu; video yang tidak layak cukup dipindah keluar dari folder 2. Video Jadi agar tidak ikut diposting.")
        if sumber not in ('gemini', 'claude', 'manual'): teks += '\n\nℹ️ Video kali ini disusun TANPA AI, jadi isinya belum disaring. Mohon tonton dulu sebelum diposting.'
        lapor_wa(teks, T.log)
        T.tahap('selesai'); T.st['selesai'] = now().isoformat(); T.simpan()
        bersihkan_tugas(T)
        return T
    except Exception:
        T.log('ERROR\n' + traceback.format_exc()); T.st['tahap_error'] = T.st.get('tahap'); T.tahap('error'); return T
    finally:
        SEKARANG['tugas'] = None; KUNCI.release()

def bersihkan_tugas(T):
    """hapus SEMUA data tugas di server (mentahan, analisa, cache, video) + salinan QC; sisakan ringkasan kecil"""
    if not all(f.get('dihapus') for f in T.st['file'].values()):
        T.log('sebagian mentahan belum terhapus dari Drive; data server tetap dibersihkan (mentahan di Drive tidak akan diambil ulang)')
    hapus_qc(T)
    ringkas = dict(id=T.id, selesai=T.st.get('selesai'), file=len(T.st['file']),
                   video=[dict(nama=os.path.basename(v['file']), drive_id=v.get('drive_id'), durasi=v.get('durasi')) for v in T.st.get('video', [])])
    os.makedirs(f'{DATA}/riwayat', exist_ok=True)
    json.dump(ringkas, open(f'{DATA}/riwayat/{T.id}.json', 'w'), ensure_ascii=False)
    log = open(f'{T.dir}/log.txt').read() if os.path.exists(f'{T.dir}/log.txt') else ''
    open(f'{DATA}/riwayat/{T.id}.log', 'w').write(log[-20000:])
    shutil.rmtree(T.dir, ignore_errors=True)
    print(f'[{T.id}] data tugas di server dihapus', flush=True)

def bersih_lama(hari=3):
    for d in glob.glob(f'{DATA}/tugas/*'):
        try:
            st = json.load(open(f'{d}/status.json'))
            if st.get('tahap') in ('selesai', 'gagal', 'error') and time.time() - os.path.getmtime(f'{d}/status.json') > hari * 86400: shutil.rmtree(d)
        except Exception: pass

def belum_tuntas():
    for d in sorted(glob.glob(f'{DATA}/tugas/*')):
        try:
            st = json.load(open(f'{d}/status.json'))
            if st.get('tahap') == 'tunggu_ai':
                if now().isoformat() >= st.get('tunda_sampai', ''): return os.path.basename(d), st
                continue
            if st.get('tahap') == 'unggah_gagal' and st.get('gagal_unggah', 0) < 6: return os.path.basename(d), st
            if st.get('tahap') not in ('selesai', 'gagal') and st.get('file') and st.get('ulang', 0) < 2:
                return os.path.basename(d), st
        except Exception: pass
    return None, None

def cek(log=print, tenang_menit=None, uji=False):
    """dipanggil berkala: lanjutkan tugas yang terputus, atau mulai tugas baru bila ada mentahan yang sudah selesai diunggah"""
    if KUNCI.locked(): return 'sibuk'
    jid, st = belum_tuntas()
    if jid:
        if st.get('tahap') not in ('tunggu_ai', 'unggah_gagal'): st['ulang'] = st.get('ulang', 0) + 1
        json.dump(st, open(f'{DATA}/tugas/{jid}/status.json', 'w'))
        threading.Thread(target=jalankan, args=([], jid), daemon=True).start(); return f'lanjut {jid}'
    lama = sudah_diproses()
    files = [f for f in jembatan.daftar_mentah() if f['id'] not in lama]
    if not files: return 'kosong'
    tenang = float(os.environ.get('TENANG_MENIT', '15') if tenang_menit is None else tenang_menit)
    tbaru = [f['dibuat'] for f in files if f.get('dibuat')]
    if tbaru and tenang > 0:
        umur = (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(max(tbaru).replace('Z', '+00:00'))).total_seconds() / 60
        if umur < tenang: return f'menunggu unggahan selesai ({umur:.0f}/{tenang:.0f} menit)'
    threading.Thread(target=jalankan, args=(files, None, uji), daemon=True).start()
    return f'mulai {len(files)} file'

def ulang(jid, dari='sutradara'):
    """jalankan ulang tugas lama mulai dari tahap tertentu (mentahan masih tersimpan di server)"""
    d = f'{DATA}/tugas/{jid}'
    if not os.path.isdir(f'{d}/raw') or not os.listdir(f'{d}/raw'): return 'mentahan tugas itu sudah tidak ada'
    if KUNCI.locked(): return 'sibuk'
    st = json.load(open(f'{d}/status.json'))
    if dari == 'analisa':  # transkrip & analisa diulang; naskah lama tetap dipakai (titik potong dirapikan ulang dari kata yang baru)
        for f in glob.glob(f'{d}/ana/asr/*.json') + [f'{d}/ana/klip.json']:
            if os.path.exists(f): os.remove(f)
    if dari in ('analisa', 'sutradara', 'render'):
        if dari == 'sutradara' and os.path.exists(f'{d}/naskah.json'): os.rename(f'{d}/naskah.json', f'{d}/naskah_lama_{int(time.time())}.json')
        for f in glob.glob(f'{d}/out/*.mp4'): os.remove(f)
        st['video'] = []; st.pop('folder_jadi', None)
    st['tahap'] = 'ulang'; st['ulang'] = 0; json.dump(st, open(f'{d}/status.json', 'w'))
    threading.Thread(target=jalankan, args=([], jid), daemon=True).start()
    return f'ulang {jid} dari {dari}'
