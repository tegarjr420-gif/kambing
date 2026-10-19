# Alur otomatis: Drive "1. Video Mentah" -> unduh -> hapus mentahan di Drive -> analisa -> sutradara -> render -> cek
#               -> unggah ke "2. Video Jadi/<tanggal>" -> lapor WhatsApp admin (minta mentahan baru).
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

def lapor_wa(teks, log=print):
    url = os.environ.get('LAPOR_URL')
    if not url: log('(lapor WA dilewati: LAPOR_URL kosong)'); return
    try:
        r = requests.post(url, json={'kunci': os.environ.get('GEMINI_PROXY_KEY', ''), 'teks': teks}, timeout=60)
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
    info = dict(tanggal=now().strftime('%Y%m%d'), ana=f'{T.dir}/ana', kerja=T.dir)
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
            r = subprocess.run([sys.executable, f'{E}/edit.py', p], capture_output=True, text=True, env=env_mesin(T))
            with open(f'{T.dir}/render_{sp["id"]}.log', 'w') as f: f.write(r.stdout + '\n' + r.stderr)
            if r.returncode != 0 or not os.path.exists(out):
                T.log(f"  GAGAL render {sp['id']}: {(r.stdout + r.stderr)[-400:]}"); continue
            teks = re.findall(r'^\s+teks (.*)$', r.stdout, re.M)
            T.log(f"  selesai {time.time() - t0:.0f} dtk; teks: {teks[0][:300] if teks else '-'}")
            shutil.rmtree(f"{T.dir}/cache/{sp['id']}", ignore_errors=True)
            for f in glob.glob(f'{T.dir}/cache/shot_*.mp4') + glob.glob(f'{T.dir}/cache/stab_*.trf'): os.remove(f)
        hasil.append(dict(id=sp['id'], gaya=sp['gaya'], file=out))
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
    T.tahap('unggah')
    if not jembatan.ada():
        T.log('jembatan Drive belum dipasang: video jadi disimpan di server saja'); return None
    nama = now().strftime('%Y-%m-%d %H.%M') + f' ({len(hasil)} video)'
    if not T.st.get('folder_jadi'):
        fj = jembatan.folder(nama, bagikan=True); T.st['folder_jadi'] = fj; T.simpan()
    fj = T.st['folder_jadi']
    for v in hasil:
        if v.get('url'): continue
        for coba in range(3):
            try:
                r = jembatan.unggah(v['file'], fj['id']); v['url'] = r['url']; T.log(f"unggah {os.path.basename(v['file'])} ok"); break
            except Exception as e:
                T.log(f'  unggah gagal ({coba + 1}): {e}'); time.sleep(10)
        T.st['video'] = hasil; T.simpan()
    return fj

def judul_dari(file): return re.sub(r'^BarokahFarm-\d+-\d+-', '', os.path.basename(file)[:-4]).replace('-', ' ')

def jalankan(files, jid=None):
    if not KUNCI.acquire(blocking=False): return None
    T = Tugas(jid); SEKARANG['tugas'] = T.id
    try:
        baru = not T.st['file']
        t_unduh(T, files)
        if not T.st['file']: T.log('tidak ada mentahan yang bisa dipakai'); T.tahap('gagal'); return T
        if baru:
            menit = 20 + 6 * len(T.st['file'])
            lapor_wa(f"🎬 *Mentahan diterima*: {len(T.st['file'])} video. Mesin sedang mengedit, perkiraan selesai ±{menit} menit. Hasilnya nanti dikirim ke sini.", T.log)
        t_hapus_drive(T)
        K = t_analisa(T)
        specs, catatan, sumber = t_sutradara(T, K)
        if not specs: T.tahap('gagal'); lapor_wa('⚠️ Mesin video tidak bisa menyusun video dari mentahan terakhir (bahan kurang/rusak). Mohon kirim mentahan lain.', T.log); return T
        hasil = [cek_video(T, v) for v in t_render(T, specs)]
        T.st['video'] = hasil; T.simpan()
        for v in hasil: salin_qc(T, v['file'], os.path.basename(v['file']))
        for p in [f'{T.dir}/naskah.json', f'{T.dir}/log.txt', f'{T.dir}/ana/klip.json']:
            if os.path.exists(p): salin_qc(T, p, os.path.basename(p) + '.txt')
        fj = t_unggah(T, hasil)
        baris = []
        for i, v in enumerate(hasil, 1):
            b = f"{i}. *{judul_dari(v['file'])}* ({v['gaya']}, {v['durasi']:.0f} dtk)"
            if v.get('url'): b += f"\n   {v['url']}"
            if v['masalah']: b += f"\n   ⚠️ {', '.join(v['masalah'])}"
            baris.append(b)
        dihapus = sum(1 for f in T.st['file'].values() if f.get('dihapus'))
        teks = (f"✅ *{len(hasil)} video Barokah Farm siap dicek*\n\n" + '\n'.join(baris) +
                (f"\n\n📁 Semua video: {fj['url']}" if fj else '') +
                (f"\n\n🗑️ {dihapus} mentahan sudah dihapus dari Drive." if dihapus else '') +
                "\n📥 Silakan kirim *mentahan baru* ke folder *1. Video Mentah* di Drive (rekam potrait, stabil, suara dekat).")
        if sumber != 'gemini': teks += '\n\nℹ️ Video kali ini disusun tanpa AI (Gemini belum aktif/gagal).'
        lapor_wa(teks, T.log)
        T.tahap('selesai'); T.st['selesai'] = now().isoformat(); T.simpan()
        shutil.rmtree(f'{T.dir}/raw', ignore_errors=True); shutil.rmtree(f'{T.dir}/cache', ignore_errors=True)
        shutil.rmtree(f'{T.dir}/ana/wav', ignore_errors=True)
        return T
    except Exception:
        T.log('ERROR\n' + traceback.format_exc()); T.st['tahap_error'] = T.st.get('tahap'); T.tahap('error'); return T
    finally:
        SEKARANG['tugas'] = None; KUNCI.release()

def bersih_lama(hari=4):
    for d in glob.glob(f'{DATA}/tugas/*'):
        try:
            st = json.load(open(f'{d}/status.json'))
            if st.get('tahap') == 'selesai' and time.time() - os.path.getmtime(f'{d}/status.json') > hari * 86400: shutil.rmtree(d)
        except Exception: pass

def belum_tuntas():
    for d in sorted(glob.glob(f'{DATA}/tugas/*')):
        try:
            st = json.load(open(f'{d}/status.json'))
            if st.get('tahap') not in ('selesai', 'gagal') and st.get('file') and st.get('ulang', 0) < 2:
                return os.path.basename(d), st
        except Exception: pass
    return None, None

def cek(log=print, tenang_menit=None):
    """dipanggil berkala: lanjutkan tugas yang terputus, atau mulai tugas baru bila ada mentahan yang sudah selesai diunggah"""
    if KUNCI.locked(): return 'sibuk'
    jid, st = belum_tuntas()
    if jid:
        st['ulang'] = st.get('ulang', 0) + 1; json.dump(st, open(f'{DATA}/tugas/{jid}/status.json', 'w'))
        threading.Thread(target=jalankan, args=([], jid), daemon=True).start(); return f'lanjut {jid}'
    lama = sudah_diproses()
    files = [f for f in jembatan.daftar_mentah() if f['id'] not in lama]
    if not files: return 'kosong'
    tenang = float(os.environ.get('TENANG_MENIT', '15') if tenang_menit is None else tenang_menit)
    tbaru = [f['dibuat'] for f in files if f.get('dibuat')]
    if tbaru and tenang > 0:
        umur = (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(max(tbaru).replace('Z', '+00:00'))).total_seconds() / 60
        if umur < tenang: return f'menunggu unggahan selesai ({umur:.0f}/{tenang:.0f} menit)'
    threading.Thread(target=jalankan, args=(files,), daemon=True).start()
    return f'mulai {len(files)} file'
