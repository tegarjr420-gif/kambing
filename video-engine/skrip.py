# Script pembuatan mentahan video (PDF) untuk admin/staf, diminta lewat WhatsApp ("minta script mentahan").
# Claude menyusun daftar adegan (momen apa, cara merekam, apa yang diucapkan) -> HTML -> PDF -> dikirim lewat n8n/WAHA.
import os, sys, json, html, time, glob, secrets, subprocess, datetime, re, threading

E = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, E)
DATA = os.environ.get('DATA', '/data')
WIB = datetime.timezone(datetime.timedelta(hours=7))
BERKAS = f'{DATA}/berkas'

FAKTA = """Barokah Farm: peternakan & penjual kambing dan domba di Curug, Tangerang. Pemilik Bpk. Muri, berdiri 2004.
Layanan: jual kambing & domba, paket aqiqah (hewan + masak), hewan qurban, program reseller.
Fakta yang boleh disebut: DP mulai Rp100.000 per ekor, gratis ongkir se-Jabodetabek (syarat jarak), katalog barokahfarm.pages.dev,
WA 0878-9014-0532. JANGAN menyuruh menyebut harga tertentu, testimoni karangan, sertifikasi, atau klaim yang belum pasti.
JANGAN ada adegan penyembelihan/darah."""

ATURAN_MESIN = """Mentahan diedit otomatis oleh mesin AI, jadi supaya hasilnya maksimal:
- rekam POTRAIT (HP berdiri), 1080p atau 4K, 30 atau 60 fps; lensa dibersihkan.
- stabil: pegang dua tangan / tripod / sandarkan; gerakan kamera pelan.
- adegan bicara: HP 1–1,5 m dari orang, wajah di sepertiga atas layar, cahaya dari depan (jangan membelakangi matahari), tempat tidak bising, mic/HP dekat.
- diam 2 detik sebelum mulai bicara dan 2 detik setelah selesai; kalau salah ucap, ulangi KALIMATNYA dari awal (tidak perlu stop rekaman).
- satu adegan = satu file video; B-roll 8–20 detik per file, bicara cukup satu atau dua kalimat per file.
- unggah SEMUA file ke folder Google Drive "1. Video Mentah" (sekaligus); mesin mengambil otomatis."""

def susun(permintaan='', konteks=None):
    import sutradara
    k = konteks or {}
    teks = f"""Kamu produser konten media sosial (TikTok, Instagram Reels, Facebook) untuk peternakan kambing.
Tulis SCRIPT PEMBUATAN MENTAHAN video untuk admin/staf Barokah Farm yang akan merekam pakai HP.

{FAKTA}

{ATURAN_MESIN}

Video yang SUDAH ada/terposting (hindari tema & kalimat yang sama persis): {json.dumps(k.get('sudah', [])[:30], ensure_ascii=False)}
Tanggal sekarang: {datetime.datetime.now(WIB).strftime('%d %B %Y')} (sesuaikan momen musiman: aqiqah sepanjang tahun, qurban menjelang Iduladha).
Permintaan khusus admin: {permintaan or '(tidak ada, buat paket umum yang variatif)'}

Buat paket rekaman yang cukup untuk ±10 video jadi: 18–24 adegan (sekitar 8–10 adegan BICARA + 10–14 adegan B-ROLL).
Adegan bicara: kalimat pendek, natural, bahasa Indonesia santai sopan, mudah dihafal, 1–2 kalimat per adegan, tiap kalimat diakhiri titik.
Variasikan pembicara (pemilik, staf kandang, admin), lokasi (kandang, area pakan, halaman, dapur aqiqah, mobil pengiriman), dan sudut.
B-roll: jelaskan persis apa yang direkam dan cara merekamnya (jarak, sudut, gerakan kamera, durasi).

Keluarkan HANYA JSON:
{{"judul": "...", "ringkasan": "1-2 kalimat tujuan paket ini",
 "persiapan": ["checklist singkat sebelum rekaman", ...],
 "adegan": [{{"no": 1, "jenis": "Bicara" | "B-roll", "judul": "...", "lokasi": "...", "siapa": "...", "durasi": "± 10 dtk",
             "cara_rekam": "...", "ucapan": "teks yang diucapkan (kosong untuk B-roll)", "untuk": "dipakai untuk video tentang ..."}}],
 "ide_video": ["judul video yang bisa jadi dari paket ini", ...],
 "penutup": "pesan singkat penyemangat + cara unggah"}}"""
    out, use = sutradara.panggil_claude(teks, [], timeout=300)
    J = sutradara.baca_json(out)
    J['_biaya'] = use.get('biaya_usd')
    return J

def esc(x): return html.escape(str(x or ''))

def ke_html(J):
    F = lambda f: f'file://{E}/fonts/{f}'
    adegan = ''
    for a in J.get('adegan', []):
        bicara = str(a.get('jenis', '')).lower().startswith('bicara')
        adegan += f"""<div class="adegan {'bicara' if bicara else 'broll'}">
  <div class="kepala"><span class="no">{esc(a.get('no'))}</span><span class="jenis">{esc(a.get('jenis'))}</span>
  <h3>{esc(a.get('judul'))}</h3><span class="cek">☐ sudah direkam</span></div>
  <table><tr><th>Lokasi</th><td>{esc(a.get('lokasi'))}</td><th>Siapa</th><td>{esc(a.get('siapa'))}</td><th>Durasi</th><td>{esc(a.get('durasi'))}</td></tr></table>
  <p class="cara"><b>Cara merekam:</b> {esc(a.get('cara_rekam'))}</p>
  {f'<blockquote>“{esc(a.get("ucapan"))}”</blockquote>' if bicara and a.get('ucapan') else ''}
  <p class="untuk">{esc(a.get('untuk'))}</p>
</div>"""
    nb = sum(1 for a in J.get('adegan', []) if str(a.get('jenis', '')).lower().startswith('bicara'))
    li = lambda xs: ''.join(f'<li>{esc(x)}</li>' for x in xs or [])
    aturan = li([x.strip('- ') for x in ATURAN_MESIN.splitlines()[1:]])
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:J;src:url({F('PlusJakartaSans_400Regular.ttf')});font-weight:400}}
@font-face{{font-family:J;src:url({F('PlusJakartaSans_700Bold.ttf')});font-weight:700}}
@font-face{{font-family:B;src:url({F('BricolageGrotesque_800ExtraBold.ttf')});font-weight:800}}
body{{font:400 10.5pt/1.45 J,sans-serif;color:#1d2a20;margin:0}}
.sampul{{background:#1E4A2C;color:#fff;border-radius:14px;padding:22px 26px;display:flex;gap:20px;align-items:center}}
.sampul img{{width:74px;height:74px;border-radius:50%;background:#fff}}
.sampul h1{{font:800 22pt/1.1 B,sans-serif;margin:0 0 6px}} .sampul p{{margin:0;opacity:.92}}
.ringkas{{display:flex;gap:10px;margin:14px 0}} .ringkas div{{flex:1;background:#F3EFE4;border-radius:10px;padding:10px 12px}}
.ringkas b{{display:block;font:800 16pt B,sans-serif;color:#1E4A2C}}
h2{{font:800 13pt B,sans-serif;color:#1E4A2C;margin:18px 0 6px}}
ul{{margin:4px 0 0 18px;padding:0}} li{{margin:2px 0}}
.adegan{{border:1px solid #d9d3c4;border-left:6px solid #1E4A2C;border-radius:10px;padding:10px 14px;margin:10px 0;break-inside:avoid}}
.adegan.broll{{border-left-color:#C9A227}}
.kepala{{display:flex;align-items:center;gap:10px}} .kepala h3{{flex:1;margin:0;font:700 11.5pt J,sans-serif}}
.no{{background:#1E4A2C;color:#fff;border-radius:50%;width:24px;height:24px;display:inline-flex;align-items:center;justify-content:center;font-weight:700;font-size:10pt}}
.broll .no{{background:#C9A227}}
.jenis{{font-size:8.5pt;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#7a857c}}
.cek{{font-size:9pt;color:#7a857c}}
table{{width:100%;border-collapse:collapse;margin:6px 0;font-size:9.5pt}} th{{text-align:left;color:#7a857c;font-weight:700;width:9%;padding:2px 4px}} td{{padding:2px 6px}}
.cara{{margin:4px 0}}
blockquote{{margin:6px 0;padding:8px 12px;background:#EEF5EF;border-radius:8px;font-size:11.5pt;font-weight:700;color:#1E4A2C}}
.untuk{{margin:2px 0 0;font-size:9pt;color:#7a857c;font-style:italic}}
.penutup{{background:#F3EFE4;border-radius:10px;padding:12px 14px;margin-top:14px}}
</style></head><body>
<div class="sampul"><img src="file://{E}/aset/logo.png"><div><h1>{esc(J.get('judul') or 'Script Mentahan Video')}</h1>
<p>{esc(J.get('ringkasan'))}</p><p style="margin-top:6px;font-size:9pt">Dibuat {datetime.datetime.now(WIB).strftime('%d/%m/%Y %H.%M')} WIB</p></div></div>
<div class="ringkas"><div><b>{len(J.get('adegan', []))}</b>adegan</div><div><b>{nb}</b>adegan bicara</div><div><b>{len(J.get('adegan', [])) - nb}</b>adegan B-roll</div><div><b>±{max(4, len(J.get('ide_video', [])))}</b>video jadi</div></div>
<h2>Sebelum merekam</h2><ul>{li(J.get('persiapan'))}</ul>
<h2>Aturan rekam (wajib, supaya mesin edit maksimal)</h2><ul>{aturan}</ul>
<h2>Daftar adegan</h2>{adegan}
<h2>Video yang bisa jadi dari paket ini</h2><ul>{li(J.get('ide_video'))}</ul>
<div class="penutup">{esc(J.get('penutup'))}</div>
</body></html>"""

def buat_pdf(J):
    os.makedirs(BERKAS, exist_ok=True)
    for f in glob.glob(f'{BERKAS}/*'):
        if time.time() - os.path.getmtime(f) > 2 * 86400: os.remove(f)
    tok = secrets.token_urlsafe(18)
    h = f'{BERKAS}/{tok}.html'; p = f'{BERKAS}/{tok}.pdf'
    open(h, 'w').write(ke_html(J))
    r = subprocess.run(['node', f'{E}/pdf.js', h, p], capture_output=True, text=True, timeout=150)
    os.remove(h)
    if r.returncode != 0 or not os.path.exists(p): raise RuntimeError('PDF gagal: ' + (r.stderr or r.stdout)[-300:])
    return tok, p

def url_berkas(tok):
    dom = os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'mesin-video-production.up.railway.app')
    return f'https://{dom}/berkas/{tok}.pdf'

def konteks():
    sudah = []
    try:
        T = json.load(open(f'{DATA}/terposting.json')); sudah += [v.get('nama', '') for v in T.values()]
    except Exception: pass
    try:
        import posting; sudah += [f['nama'] for f in posting.daftar_stok()]
    except Exception: pass
    return dict(sudah=[re.sub(r'^BarokahFarm-[\d-]+?-\d{2}-', '', os.path.splitext(n)[0]) for n in sudah if n])

STATUS = {}

def kerjakan(chat_id, permintaan='', tes=False):
    import pipeline, sutradara
    STATUS[chat_id] = 'proses'
    try:
        J = susun(permintaan, konteks())
        tok, p = buat_pdf(J)
        nama = 'Script-Mentahan-BarokahFarm-' + datetime.datetime.now(WIB).strftime('%Y%m%d-%H%M') + '.pdf'
        nb = sum(1 for a in J.get('adegan', []) if str(a.get('jenis', '')).lower().startswith('bicara'))
        teks = (f"📄 *{J.get('judul') or 'Script mentahan video'}*\n{len(J.get('adegan', []))} adegan ({nb} bicara, {len(J.get('adegan', [])) - nb} B-roll). "
                "Rekam potrait & stabil, lalu unggah semua file ke folder *1. Video Mentah* di Drive.")
        STATUS[chat_id] = dict(ok=True, url=url_berkas(tok), biaya=J.get('_biaya'))
        if not tes: pipeline.lapor_wa(teks, print, chat_id=chat_id, berkas_url=url_berkas(tok), berkas_nama=nama)
        print(f'skrip PDF untuk {chat_id[:6]}…: {url_berkas(tok)} (biaya ${J.get("_biaya")})', flush=True)
    except sutradara.BatasHarian:
        STATUS[chat_id] = 'batas'
        if not tes: pipeline.lapor_wa('⏳ Batas biaya harian AI (Claude) sudah tercapai hari ini, script belum bisa dibuat. Coba lagi besok ya.', print, chat_id=chat_id)
    except Exception as e:
        STATUS[chat_id] = 'gagal: ' + str(e)[:200]; print('skrip gagal:', e, flush=True)
        if not tes: pipeline.lapor_wa('⚠️ Maaf, script mentahan gagal dibuat (gangguan AI/PDF). Coba ketik lagi beberapa menit lagi.', print, chat_id=chat_id)

def mulai(chat_id, permintaan='', tes=False):
    threading.Thread(target=kerjakan, args=(chat_id, permintaan, tes), daemon=True).start()
