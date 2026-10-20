# Server mesin video Barokah Farm (Railway). Cek folder mentahan berkala, jalankan alur otomatis, sediakan status & unduhan.
import os, re, json, threading, time, glob, shutil, urllib.parse, traceback
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import pipeline

VERSI = '2026-10-20.5'
KEY = os.environ.get('ENGINE_KEY', '')
MENIT = float(os.environ.get('CEK_MENIT', '20'))
TERAKHIR = {'cek': None, 'hasil': None}

def loop():
    time.sleep(30)
    while True:
        try:
            TERAKHIR['hasil'] = pipeline.cek(); TERAKHIR['cek'] = pipeline.now().isoformat()
            print('cek berkala:', TERAKHIR['hasil'], flush=True)
            pipeline.bersih_lama()
        except Exception as e:
            TERAKHIR['hasil'] = 'error: ' + str(e)[:300]; print('cek gagal:', traceback.format_exc(), flush=True)
        time.sleep(MENIT * 60)

def tugas_list():
    out = []
    for d in sorted(glob.glob(f'{pipeline.DATA}/tugas/*'))[-10:]:
        try:
            st = json.load(open(f'{d}/status.json'))
            out.append(dict(id=st['id'], tahap=st.get('tahap'), file=len(st.get('file', {})),
                            video=[dict(file=os.path.basename(v['file']), durasi=v.get('durasi'), url=v.get('url'), masalah=v.get('masalah')) for v in st.get('video', [])]))
        except Exception: pass
    return out

class H(BaseHTTPRequestHandler):
    def kirim(s, code, obj, ctype='application/json'):
        b = obj if isinstance(obj, bytes) else json.dumps(obj, ensure_ascii=False, indent=1).encode()
        s.send_response(code); s.send_header('Content-Type', ctype); s.send_header('Content-Length', str(len(b))); s.end_headers(); s.wfile.write(b)
    def boleh(s, q): return KEY and (q.get('k', [''])[0] == KEY or s.headers.get('X-Kunci') == KEY)
    def log_message(s, *a): pass
    def media(s, kepala_saja=False):
        # video Drive untuk diambil Buffer (dialirkan langsung, tidak disimpan di server); dilindungi token per file
        import posting, requests as rq, hmac
        u = urllib.parse.urlparse(s.path); q = urllib.parse.parse_qs(u.query)
        fid = os.path.basename(u.path)[:-4]
        if not hmac.compare_digest(q.get('t', [''])[0], posting.token(fid)): return s.kirim(403, dict(ok=False))
        h = {'Range': s.headers['Range']} if s.headers.get('Range') else {}
        r = rq.get(f'https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t', headers=h, stream=True, timeout=120)
        if r.status_code >= 400 or 'text/html' in r.headers.get('Content-Type', ''): r.close(); return s.kirim(404, dict(ok=False))
        s.send_response(r.status_code); s.send_header('Content-Type', 'video/mp4'); s.send_header('Accept-Ranges', 'bytes')
        for k in ('Content-Length', 'Content-Range'):
            if r.headers.get(k): s.send_header(k, r.headers[k])
        s.end_headers()
        if kepala_saja: r.close(); return
        try:
            for ch in r.iter_content(1 << 20): s.wfile.write(ch)
        except (BrokenPipeError, ConnectionResetError): pass
        finally: r.close()
    def do_HEAD(s):
        u = urllib.parse.urlparse(s.path)
        if u.path.startswith('/media/') and u.path.endswith('.mp4'): return s.media(True)
        s.send_response(404); s.end_headers()
    def do_GET(s):
        u = urllib.parse.urlparse(s.path); q = urllib.parse.parse_qs(u.query)
        if u.path.startswith('/media/') and u.path.endswith('.mp4'): return s.media()
        if u.path.startswith('/berkas/') and u.path.endswith('.pdf'):
            import skrip
            p = f'{skrip.BERKAS}/{os.path.basename(u.path)}'
            if not re.fullmatch(r'[\w-]{20,40}\.pdf', os.path.basename(u.path)) or not os.path.exists(p): return s.kirim(404, dict(ok=False))
            return s.kirim(200, open(p, 'rb').read(), 'application/pdf')
        if u.path in ('/cek', '/uji-ai', '/uji-wa', '/uji-drive', '/ulang', '/skrip', '/posting/selesai', '/posting/status', '/hapus-tugas', '/skrip-status', '/dokumen-status', '/dokumen-uji'): return s.do_POST()
        if u.path in ('/', '/sehat'):
            return s.kirim(200, dict(ok=True, versi=VERSI, sibuk=pipeline.SEKARANG['tugas'], cek_terakhir=TERAKHIR))
        if not s.boleh(q): return s.kirim(403, dict(ok=False, galat='kunci'))
        if u.path == '/status':
            jid = q.get('tugas', [None])[0] or pipeline.SEKARANG['tugas'] or (tugas_list()[-1]['id'] if tugas_list() else None)
            log = ''
            if jid and os.path.exists(f'{pipeline.DATA}/tugas/{jid}/log.txt'): log = open(f'{pipeline.DATA}/tugas/{jid}/log.txt').read()[-6000:]
            return s.kirim(200, dict(tugas=tugas_list(), sibuk=pipeline.SEKARANG['tugas'], log=log))
        if u.path.startswith('/hasil/'):
            _, _, jid, nama = u.path.split('/', 3); p = f'{pipeline.DATA}/tugas/{os.path.basename(jid)}/out/{os.path.basename(urllib.parse.unquote(nama))}'
            if not os.path.exists(p): return s.kirim(404, dict(ok=False))
            s.send_response(200); s.send_header('Content-Type', 'video/mp4'); s.send_header('Content-Length', str(os.path.getsize(p))); s.end_headers()
            with open(p, 'rb') as f:
                while True:
                    ch = f.read(1 << 20)
                    if not ch: break
                    s.wfile.write(ch)
            return
        if u.path == '/pakai-spec':  # uji: pakai naskah contoh dari folder spec/ untuk tugas yang mentahannya masih ada
            jid = os.path.basename(q.get('tugas', [''])[0]); d = f'{pipeline.DATA}/tugas/{jid}'
            if not os.path.isdir(f'{d}/raw'): return s.kirim(404, dict(ok=False, galat='tugas/mentahan tidak ada'))
            specs = []
            for i, n in enumerate(q.get('spec', [''])[0].split(','), 1):
                sp = json.load(open(f'{os.path.dirname(os.path.abspath(__file__))}/spec/{os.path.basename(n)}.json'))
                sp['id'] = f'A{i}'; sp['file'] = f"BarokahFarm-{jid[:8]}-{i:02d}-" + sp.get('file', n).split('-')[-1]
                specs.append(sp)
            if os.path.exists(f'{d}/naskah.json'): os.rename(f'{d}/naskah.json', f'{d}/naskah_lama_{int(time.time())}.json')
            json.dump(dict(video=specs, catatan='naskah contoh (uji render)', sumber='manual'), open(f'{d}/naskah.json', 'w'), ensure_ascii=False)
            return s.kirim(200, dict(ok=True, hasil=pipeline.ulang(jid, 'render')))
        if u.path == '/arsip':  # pindahkan file dari Supabase Storage (…/arsip/) ke folder Drive lewat jembatan
            import jembatan, requests as rq
            folder = q.get('folder', [''])[0]; berkas = [b for b in q.get('berkas', [''])[0].split(',') if b]
            base = os.environ.get('QC_STORAGE_URL', '').replace('/object/', '/object/authenticated/').rsplit('/qc', 1)[0] + '/arsip/'
            key = os.environ.get('QC_STORAGE_KEY', '')
            def kerja():
                for b in berkas:
                    try:
                        p = f'{pipeline.DATA}/arsip_{os.path.basename(b)}'
                        with rq.get(base + b, headers={'apikey': key, 'Authorization': f'Bearer {key}'}, stream=True, timeout=600) as r:
                            r.raise_for_status()
                            with open(p, 'wb') as f:
                                for ch in r.iter_content(8 << 20): f.write(ch)
                        hasil = jembatan.unggah(p, folder, os.path.basename(b)); os.remove(p)
                        TERAKHIR.setdefault('arsip', {})[b] = hasil['url']; print('arsip ok', b, flush=True)
                    except Exception as e:
                        TERAKHIR.setdefault('arsip', {})[b] = 'GAGAL: ' + str(e)[:200]; print('arsip gagal', b, e, flush=True)
            threading.Thread(target=kerja, daemon=True).start()
            return s.kirim(200, dict(ok=True, mulai=len(berkas)))
        if u.path == '/proses':
            import subprocess
            return s.kirim(200, dict(ps=subprocess.run(['ps', '-eo', 'pid,ppid,etime,pcpu,rss,args', '--sort=-pcpu'], capture_output=True, text=True).stdout[:6000],
                                     df=subprocess.run(['df', '-h', pipeline.DATA], capture_output=True, text=True).stdout))
        if u.path == '/posting/ambil':
            import posting
            try: return s.kirim(200, posting.ambil(int(q.get('jeda_hari', ['3'])[0]), q.get('paksa', ['0'])[0] == '1', q.get('uji_id', [''])[0], q.get('uji_nama', [''])[0]))
            except Exception as e: return s.kirim(200, dict(jadwal=False, ada=False, galat=str(e)[:300]))
        if u.path == '/posting/cek':
            import posting
            return s.kirim(200, dict(daftar=posting.perlu_cek_status()))
        if u.path == '/stok':
            import posting
            try: return s.kirim(200, dict(stok=[dict(nama=f['nama'], id=f['id']) for f in posting.daftar_stok()]))
            except Exception as e: return s.kirim(200, dict(galat=str(e)[:300]))
        if u.path == '/naskah':
            jid = q.get('tugas', [''])[0]; p = f'{pipeline.DATA}/tugas/{os.path.basename(jid)}/naskah.json'
            return s.kirim(200, json.load(open(p))) if os.path.exists(p) else s.kirim(404, dict(ok=False))
        s.kirim(404, dict(ok=False))
    def do_POST(s):
        u = urllib.parse.urlparse(s.path); q = urllib.parse.parse_qs(u.query)
        if not s.boleh(q): return s.kirim(403, dict(ok=False, galat='kunci'))
        if u.path == '/cek':
            tn = q.get('tenang', [None])[0]
            r = pipeline.cek(tenang_menit=float(tn) if tn is not None else None, uji=q.get('uji', ['0'])[0] == '1'); TERAKHIR['hasil'] = r
            return s.kirim(200, dict(ok=True, hasil=r))
        if u.path == '/ulang':
            return s.kirim(200, dict(ok=True, hasil=pipeline.ulang(q.get('tugas', [''])[0], q.get('dari', ['sutradara'])[0])))
        if u.path == '/uji-ai':  # tes koneksi Gemini lewat n8n
            import sutradara
            try:
                tanya = 'Balas JSON {"ok": true, "model": "<nama modelmu>"}'
                if q.get('penyedia', ['claude'])[0] == 'claude': out, use = sutradara.panggil_claude(tanya, [], timeout=120)
                else: out, use = sutradara.panggil_gemini(tanya, [], timeout=120)
                return s.kirim(200, dict(ok=True, jawab=out[:300], token=use))
            except Exception as e:
                return s.kirim(200, dict(ok=False, galat=str(e)[:500]))
        if u.path == '/posting/selesai':  # dipanggil n8n setelah kirim ke Buffer
            import posting
            n = int(s.headers.get('Content-Length') or 0); body = json.loads(s.rfile.read(n) or b'{}') if n else {}
            fid = body.get('id') or q.get('id', [''])[0]
            return s.kirim(200, posting.selesai(fid, body.get('nama') or q.get('nama', [''])[0], body.get('hasil') or [], bool(body.get('uji'))))
        if u.path == '/posting/status':
            import posting
            posting.catat_status(q.get('id', [''])[0], q.get('post', [''])[0], q.get('status', [''])[0], q.get('tautan', [''])[0], q.get('pesan', [''])[0])
            return s.kirim(200, dict(ok=True))
        if u.path == '/skrip':  # admin minta script mentahan lewat WA -> PDF dikirim balik ke chat itu
            import skrip
            n = int(s.headers.get('Content-Length') or 0); body = json.loads(s.rfile.read(n) or b'{}') if n else {}
            chat = body.get('chat_id') or q.get('chat', [''])[0]
            if not chat: return s.kirim(400, dict(ok=False, galat='chat_id kosong'))
            skrip.mulai(chat, body.get('permintaan') or q.get('permintaan', [''])[0], str(body.get('tes', q.get('tes', ['0'])[0])).lower() in ('1', 'true'))
            return s.kirim(200, dict(ok=True, mulai=True))
        if u.path in ('/invoice', '/rekap'):  # dari n8n: data invoice / laporan keuangan -> PDF -> WA
            import dokumen
            n = int(s.headers.get('Content-Length') or 0); body = json.loads(s.rfile.read(n) or b'{}') if n else {}
            tes = str(body.get('tes', '')).lower() in ('1', 'true')
            if u.path == '/invoice':
                if not body.get('invoice'): return s.kirim(400, dict(ok=False, galat='invoice kosong'))
                dokumen.mulai(dokumen.kirim_invoice, body['invoice'], body.get('chat_id'), tes)
            else:
                if not isinstance(body.get('laporan'), dict) or 'ringkas' not in body['laporan']: return s.kirim(400, dict(ok=False, galat='laporan tidak valid'))
                dokumen.mulai(dokumen.kirim_rekap, body['laporan'], body.get('chat_id'), tes)
            return s.kirim(200, dict(ok=True, mulai=True))
        if u.path == '/dokumen-uji':  # uji pembuatan PDF di server (tanpa kirim)
            import dokumen
            d = dict(no='INV/BF/UJI/0001', jenis='LUNAS', pesanan=0, sumber='online', tanggal='01/01/2026', jam='10.00',
                     pelanggan=dict(nama='Uji', wa='62800'), item=dict(kode='K-01', nama='Kambing Jawa', jumlah=1),
                     harga=1500000, ongkir=0, total=1500000, dp=100000, dibayar=1500000, pelunasan=1400000, sisa=0, rekening='BRI')
            try:
                tok, p = dokumen.pdf(dokumen.html_invoice(d), 'inv'); return s.kirim(200, dict(ok=True, url=dokumen.url_berkas(tok), ukuran=os.path.getsize(p)))
            except Exception as e:
                return s.kirim(200, dict(ok=False, galat=str(e)[:400]))
        if u.path == '/dokumen-status':
            import dokumen
            return s.kirim(200, dict(status=dokumen.STATUS))
        if u.path == '/skrip-status':
            import skrip
            return s.kirim(200, dict(status=skrip.STATUS))
        if u.path == '/hapus-tugas':  # bersihkan data tugas lama di server (mentahan/cache/video)
            jid = os.path.basename(q.get('tugas', [''])[0]); d = f'{pipeline.DATA}/tugas/{jid}'
            if not jid or not os.path.isdir(d) or pipeline.SEKARANG['tugas'] == jid: return s.kirim(404, dict(ok=False))
            shutil.rmtree(d, ignore_errors=True); return s.kirim(200, dict(ok=True, dihapus=jid))
        if u.path == '/uji-wa':
            pipeline.lapor_wa(q.get('teks', ['🔧 Tes dari mesin video Barokah Farm.'])[0]); return s.kirim(200, dict(ok=True))
        if u.path == '/uji-drive':
            import jembatan
            try:
                fs = jembatan.daftar_mentah(); return s.kirim(200, dict(ok=True, jembatan=jembatan.ada(), file=fs))
            except Exception as e:
                return s.kirim(200, dict(ok=False, galat=str(e)[:500]))
        s.kirim(404, dict(ok=False))

if __name__ == '__main__':
    os.makedirs(f'{pipeline.DATA}/tugas', exist_ok=True)
    if os.environ.get('CEK_OTOMATIS', '1') == '1': threading.Thread(target=loop, daemon=True).start()
    port = int(os.environ.get('PORT', '8080'))
    print(f'mesin video {VERSI} siap di port {port}', flush=True)
    ThreadingHTTPServer(('0.0.0.0', port), H).serve_forever()
