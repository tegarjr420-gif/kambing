# Server mesin video Barokah Farm (Railway). Cek folder mentahan berkala, jalankan alur otomatis, sediakan status & unduhan.
import os, json, threading, time, glob, urllib.parse, traceback
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import pipeline

VERSI = '2026-10-20.1'
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
    def do_GET(s):
        u = urllib.parse.urlparse(s.path); q = urllib.parse.parse_qs(u.query)
        if u.path in ('/cek', '/uji-ai', '/uji-wa', '/uji-drive'): return s.do_POST()
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
        if u.path == '/uji-ai':  # tes koneksi Gemini lewat n8n
            import sutradara
            try:
                out, use = sutradara.panggil_gemini('Balas JSON {"ok": true, "model": "<nama modelmu>"}', [], timeout=120)
                return s.kirim(200, dict(ok=True, jawab=out[:300], token=use))
            except Exception as e:
                return s.kirim(200, dict(ok=False, galat=str(e)[:500]))
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
