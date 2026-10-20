# Dokumen PDF Barokah Farm: invoice (DP / LUNAS / PENJUALAN) dan laporan keuangan ("rekapan").
# Template tetap di sini; data diisi dari database (fungsi _invoice & laporan_keuangan di Supabase).
import os, sys, html, json, time, glob, secrets, subprocess, datetime, threading

E = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, E)
DATA = os.environ.get('DATA', '/data')
BERKAS = f'{DATA}/berkas'
WIB = datetime.timezone(datetime.timedelta(hours=7))
USAHA = dict(nama='BAROKAH FARM', tagline='Peternakan Kambing & Domba · Paket Aqiqah · Hewan Qurban',
             alamat='Kampung Peusar RT 02/RW 01, Kel. Binong, Kec. Curug, Kab. Tangerang, Banten 15810',
             wa='0878-9014-0532', web='barokahfarm.pages.dev', ig='@barokah27farm', sejak='sejak 2004')

def esc(x): return html.escape('' if x is None else str(x))

def rp(n):
    try: n = int(round(float(n)))
    except Exception: return '-'
    s = f'{abs(n):,}'.replace(',', '.')
    return ('-Rp' if n < 0 else 'Rp') + s

F = lambda f: f'file://{E}/fonts/{f}'
GAYA = f"""
@font-face{{font-family:J;src:url({F('PlusJakartaSans_400Regular.ttf')});font-weight:400}}
@font-face{{font-family:J;src:url({F('PlusJakartaSans_600SemiBold.ttf')});font-weight:600}}
@font-face{{font-family:J;src:url({F('PlusJakartaSans_700Bold.ttf')});font-weight:700}}
@font-face{{font-family:J;src:url({F('PlusJakartaSans_800ExtraBold.ttf')});font-weight:800}}
@font-face{{font-family:B;src:url({F('BricolageGrotesque_800ExtraBold.ttf')});font-weight:800}}
@page{{size:A4;margin:0}}
*{{box-sizing:border-box}}
html,body{{margin:0}}
body{{font:400 10pt/1.45 J,sans-serif;color:#1d2a20;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.hal{{width:210mm;min-height:297mm;padding:13mm 15mm 12mm;position:relative;background:#fff;display:flex;flex-direction:column}}
.kop{{display:flex;align-items:center;gap:5mm;padding-bottom:4mm;border-bottom:3px solid #1E4A2C;position:relative}}
.kop:after{{content:"";position:absolute;left:0;right:0;bottom:-6px;height:1.5px;background:#C9A227}}
.kop img{{width:23mm;height:23mm;border-radius:50%}}
.kop h1{{font:800 22pt/1 B,sans-serif;color:#1E4A2C;margin:0;letter-spacing:.5px}}
.kop .tag{{font:700 9.5pt J;color:#8a6d12;margin:1.2mm 0 1.4mm}}
.kop .al{{font-size:8.6pt;color:#4b5a4f;line-height:1.4}}
.kop .kanan{{margin-left:auto;text-align:right;font-size:8.6pt;color:#4b5a4f;line-height:1.55}}
.kop .kanan b{{color:#1E4A2C}}
.kaki{{margin-top:auto;padding-top:5mm;border-top:1px solid #e3dccb;font-size:8.2pt;color:#7a857c;display:flex;justify-content:space-between;gap:6mm}}
h2{{font:800 12pt B,sans-serif;color:#1E4A2C;margin:6mm 0 2.5mm}}
table{{width:100%;border-collapse:collapse}}
th{{background:#1E4A2C;color:#fff;font:700 8.8pt J;text-align:left;padding:2.4mm 3mm}}
td{{padding:2.4mm 3mm;border-bottom:1px solid #ece5d5;vertical-align:top}}
.r{{text-align:right;white-space:nowrap}}
.muted{{color:#7a857c}}
"""

# ------------------------------------------------------------------ foto hewan di invoice
MAKS_FOTO = 6

def siapkan_foto(sumber, folder):
    """Unduh foto (URL Supabase / path lokal), putar sesuai EXIF, kecilkan -> daftar path JPEG lokal."""
    from PIL import Image, ImageOps
    import io, requests
    os.makedirs(folder, exist_ok=True); hasil = []
    for i, u in enumerate([x for x in (sumber or []) if isinstance(x, str) and x.strip()][:MAKS_FOTO]):
        try:
            if u.startswith('http'):
                r = requests.get(u, timeout=25); r.raise_for_status(); im = Image.open(io.BytesIO(r.content))
            else:
                im = Image.open(u.replace('file://', ''))
            im = ImageOps.exif_transpose(im).convert('RGB'); im.thumbnail((1600, 1600))
            f = f'{folder}/foto{i + 1}.jpg'; im.save(f, 'JPEG', quality=84); hasil.append(f)
        except Exception as e:
            print('foto invoice dilewati:', str(u)[:80], e, flush=True)
    return hasil

def html_foto(files, d):
    """Bingkai + grid foto: 1 besar · 2 berdampingan · 3 (1 besar + 2 kecil) · 4 (2x2) · 5-6 (3x2)."""
    n = len(files)
    if not n: return ''
    it = d.get('item') or {}
    kotak = lambda f, k, i: f'<figure class="bk {k}"><img src="file://{f}"><figcaption>{i}</figcaption></figure>'
    if n == 1: isi = kotak(files[0], 'satu', 'Foto 1'); g = 'g1'
    elif n == 2: isi = ''.join(kotak(f, '', f'Foto {i + 1}') for i, f in enumerate(files)); g = 'g2'
    elif n == 3: isi = kotak(files[0], 'besar', 'Foto 1') + ''.join(kotak(f, '', f'Foto {i + 2}') for i, f in enumerate(files[1:])); g = 'g3'
    elif n == 4: isi = ''.join(kotak(f, '', f'Foto {i + 1}') for i, f in enumerate(files)); g = 'g4'
    else: isi = ''.join(kotak(f, '', f'Foto {i + 1}') for i, f in enumerate(files)); g = 'g6'
    ket = ' · '.join(x for x in [esc(it.get('kode')), esc(it.get('nama')), f"diserahkan {esc(d.get('tanggal'))}"] if x)
    return f"""<div class="foto"><div class="fj"><span class="pita">FOTO HEWAN</span><span class="fk">{ket}</span></div>
      <div class="grid {g}">{isi}</div></div>"""

GAYA_FOTO = """
.foto{margin-top:5mm;border:1.5px solid #C9A227;border-radius:3.5mm;padding:3mm 3mm 3.2mm;background:#FBF8F0;position:relative;break-inside:avoid}
.foto:before{content:"";position:absolute;inset:1.2mm;border:.6px dashed #d9c27a;border-radius:2.6mm;pointer-events:none}
.fj{display:flex;align-items:center;gap:3mm;margin:0 0 2.6mm;position:relative}
.pita{background:#1E4A2C;color:#fff;font:800 8.4pt J;letter-spacing:.12em;padding:1.2mm 3.2mm;border-radius:1.6mm}
.fk{font:600 8.8pt J;color:#5b6a5f}
.grid{display:grid;gap:2.6mm;position:relative}
.g1{grid-template-columns:1fr} .g2{grid-template-columns:1fr 1fr} .g4{grid-template-columns:1fr 1fr}
.g3{grid-template-columns:1.55fr 1fr;grid-template-rows:1fr 1fr} .g6{grid-template-columns:repeat(3,1fr)}
.bk{margin:0;background:#fff;padding:1.6mm;border-radius:2.2mm;box-shadow:0 .5mm 1.8mm rgba(30,74,44,.18);border:1px solid #e3dccb;position:relative}
.bk img{display:block;width:100%;object-fit:cover;border-radius:1.4mm}
.g1 .bk img{height:66mm} .g2 .bk img{height:52mm} .g4 .bk img{height:31mm} .g6 .bk img{height:31mm}
.g3 .bk img{height:29.2mm} .g3 .besar{grid-row:1 / span 2} .g3 .besar img{height:62.8mm}
.bk figcaption{position:absolute;left:3.2mm;bottom:3.2mm;background:rgba(30,74,44,.88);color:#fff;font:700 7.2pt J;padding:.6mm 2mm;border-radius:1.2mm}
"""

# ------------------------------------------------------------------ invoice
JUDUL = {'DP': ('INVOICE · TANDA TERIMA DP', 'DP DITERIMA', '#C9A227'),
         'LUNAS': ('INVOICE · PELUNASAN', 'LUNAS', '#1E4A2C'),
         'PENJUALAN': ('INVOICE · PENJUALAN', 'LUNAS', '#1E4A2C')}

def html_invoice(d, foto=None):
    j = d.get('jenis', 'LUNAS'); judul, cap, warna = JUDUL.get(j, JUDUL['LUNAS'])
    it = d.get('item') or {}; pl = d.get('pelanggan') or {}
    uraian = esc(it.get('nama') or it.get('kode'))
    detail = ' · '.join(x for x in [esc(it.get('kode')), esc(it.get('berat')) if it.get('berat') else '', esc(it.get('opsi')) if it.get('opsi') else ''] if x)
    jumlah = it.get('jumlah') or 1
    satuan = 'paket' if (it.get('kategori') == 'Aqiqah' and it.get('opsi')) else 'ekor'
    if j == 'DP':
        kirim = '<span class="muted">Dihitung saat pelunasan</span>'
    elif d.get('ambil_sendiri'):
        kirim = 'Diambil di kandang'
    elif int(d.get('ongkir') or 0) > 0:
        kirim = rp(d['ongkir'])
    else:
        kirim = '<b style="color:#1E4A2C">GRATIS ONGKIR</b>'
    baris = f"""<tr><td><b>{uraian}</b><div class="muted" style="font-size:8.6pt">{detail}</div></td>
      <td class="r">{jumlah} {satuan}</td><td class="r">{rp(d.get('harga'))}</td></tr>
      <tr><td>Pengiriman{'' if j == 'DP' else (' (Jabodetabek)' if d.get('gratis_ongkir') else '')}</td><td class="r">–</td><td class="r">{kirim}</td></tr>"""
    rinci = [('Total harga', rp(d.get('total')), True)]
    if j == 'DP':
        rinci += [('DP diterima', rp(d.get('dp')), False), ('Sisa yang harus dilunasi', rp(d.get('sisa')), True)]
    elif j == 'LUNAS':
        rinci += [('DP sebelumnya', rp(d.get('dp')), False), ('Pelunasan diterima', rp(d.get('pelunasan')), False), ('Sisa tagihan', 'Rp0', True)]
    else:
        rinci += [('Dibayar', rp(d.get('dibayar')), False), ('Sisa tagihan', 'Rp0', True)]
    rinci_html = ''.join(f'<tr class="{"tebal" if t else ""}"><td>{esc(a)}</td><td class="r">{b}</td></tr>' for a, b, t in rinci)
    if j == 'DP':
        info = f"""<div class="info kuning"><b>Langkah berikutnya</b><ul>
          <li>Lunasi sisa <b>{rp(d.get('sisa'))}</b> paling lambat <b>{esc(d.get('batas_lunas'))} WIB</b>.</li>
          <li>Transfer hanya ke rekening resmi: <b>{esc(d.get('rekening'))}</b>, lalu kirim foto buktinya di chat WhatsApp Barokah Farm.</li>
          <li>Ongkir: {esc(d.get('ongkir_info') or 'gratis se-Jabodetabek (syarat jarak).')}</li>
          <li>Bila sampai batas waktu belum lunas, pesanan batal otomatis dan DP digunakan untuk biaya pakan &amp; perawatan hewan.</li></ul></div>"""
    else:
        info = f"""<div class="info hijau"><b>Terima kasih!</b> Pembayaran sudah kami terima lengkap.
          {'Hewan diambil langsung di kandang.' if d.get('ambil_sendiri') else 'Tim kami akan mengatur pengiriman sesuai jadwal yang disepakati.'}
          Simpan invoice ini sebagai bukti pembelian. Pertanyaan: WhatsApp {USAHA['wa']}.</div>"""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{GAYA}
.hal{{min-height:296mm;height:296mm;overflow:hidden}}
.atas{{display:flex;justify-content:space-between;align-items:flex-start;margin-top:6mm}}
.atas h3{{font:800 15pt B,sans-serif;margin:0;color:#1d2a20;letter-spacing:.3px}}
.meta td{{border:0;padding:.6mm 0 .6mm 4mm;font-size:9.2pt}} .meta td:first-child{{color:#7a857c;padding-left:0}}
.ke{{margin-top:4.5mm;background:#F6F2E8;border-radius:3mm;padding:3.5mm 4.5mm;font-size:9.6pt}}
.ke .lbl{{font:700 8pt J;color:#8a6d12;letter-spacing:.06em;text-transform:uppercase;margin-bottom:1mm}}
.item{{margin-top:4.5mm}}
.ringkas{{display:flex;justify-content:space-between;align-items:center;margin-top:3mm}}
.ringkas table{{width:88mm}} .ringkas td{{border-bottom:1px dashed #e3dccb;padding:2mm 0}}
.ringkas tr.tebal td{{font:800 11pt J;color:#1E4A2C;border-bottom:2px solid #1E4A2C}}
.cap{{margin-left:14mm;transform:rotate(-10deg);border:4px solid {warna};color:{warna};border-radius:4mm;
  padding:2mm 6mm;font:800 22pt B,sans-serif;letter-spacing:2px;opacity:.85}}
.info{{margin-top:5mm;border-radius:3mm;padding:3.5mm 4.5mm;font-size:9.3pt}} .info ul{{margin:1.5mm 0 0;padding-left:5mm}} .info li{{margin:1mm 0}}
.kuning{{background:#fff6dc;border:1px solid #f0d891}} .hijau{{background:#e9f8ee;border:1px solid #bfe3cb}}
{GAYA_FOTO}</style></head><body><div class="hal">
<div class="kop"><img src="file://{E}/aset/logo.png"><div><h1>{USAHA['nama']}</h1><div class="tag">{USAHA['tagline']}</div>
<div class="al">{USAHA['alamat']}</div></div>
<div class="kanan">WhatsApp <b>{USAHA['wa']}</b><br>Katalog <b>{USAHA['web']}</b><br>Instagram/TikTok <b>{USAHA['ig']}</b><br>{USAHA['sejak']}</div></div>
<div class="atas"><div><h3>{judul}</h3><div class="muted" style="font-size:9pt;margin-top:1mm">{'Penjualan langsung di kandang' if d.get('sumber') == 'kandang' else 'Pemesanan lewat WhatsApp'}</div></div>
<table class="meta" style="width:auto"><tr><td>No. invoice</td><td><b>{esc(d.get('no'))}</b></td></tr>
<tr><td>Tanggal</td><td>{esc(d.get('tanggal'))}, {esc(d.get('jam'))} WIB</td></tr>
<tr><td>No. pesanan</td><td>#{esc(d.get('pesanan'))}</td></tr></table></div>
<div class="ke"><div class="lbl">Kepada</div><b>{esc(pl.get('nama') or 'Pelanggan Barokah Farm')}</b>
{('<br>WhatsApp: ' + esc(pl.get('wa'))) if pl.get('wa') else ''}{('<br>Alamat: ' + esc(pl.get('alamat'))) if pl.get('alamat') else ''}</div>
<table class="item"><tr><th>Uraian</th><th class="r">Jumlah</th><th class="r">Harga</th></tr>{baris}</table>
<div class="ringkas"><div class="cap">{cap}</div><table>{rinci_html}</table></div>
{html_foto(foto or [], d)}
{info}
<div class="kaki"><span>Invoice ini dibuat otomatis oleh sistem Barokah Farm dan sah tanpa tanda tangan.</span><span>Rekening resmi: {esc(d.get('rekening'))}</span></div>
</div></body></html>"""

def teks_invoice(d):
    j = d.get('jenis'); it = d.get('item') or {}
    nama = esc(it.get('nama') or it.get('kode'))
    if j == 'DP':
        return (f"🧾 *Invoice DP {d.get('no')}*\nTerima kasih, DP *{rp(d.get('dp'))}* untuk pesanan #{d.get('pesanan')} ({nama}) sudah kami terima.\n"
                f"Sisa pembayaran *{rp(d.get('sisa'))}*, paling lambat {d.get('batas_lunas')} WIB. Simpan invoice ini sebagai bukti ya.")
    if j == 'LUNAS':
        return (f"🧾 *Invoice Lunas {d.get('no')}*\nPesanan #{d.get('pesanan')} ({nama}) sudah *LUNAS*.\n"
                f"Total {rp(d.get('total'))} = DP {rp(d.get('dp'))} + pelunasan {rp(d.get('pelunasan'))}"
                + (f" (termasuk ongkir {rp(d.get('ongkir'))})" if int(d.get('ongkir') or 0) > 0 else (' · diambil di kandang' if d.get('ambil_sendiri') else ' · gratis ongkir'))
                + ".\nTerima kasih sudah berbelanja di Barokah Farm 🙏")
    return (f"🧾 *Invoice {d.get('no')}*\nTerima kasih sudah membeli langsung di kandang Barokah Farm 🙏\n"
            f"{nama} × {it.get('jumlah') or 1}, total *{rp(d.get('total'))}*, status *LUNAS*.")

def teks_teruskan(d):
    """Pesan ke ADMIN: invoice penjualan kandang diteruskan manual dari HP admin (nomor CS aman dari blokir)."""
    it = d.get('item') or {}; pl = d.get('pelanggan') or {}; wa = d.get('teruskan_ke') or ''
    nama = it.get('nama') or it.get('kode')
    t = (f"🧾 *Invoice penjualan kandang {d.get('no')}*\n{nama} × {it.get('jumlah') or 1}, total *{rp(d.get('total'))}*"
         f"{' · ' + str(len(d.get('foto') or [])) + ' foto' if d.get('foto') else ''}\nPembeli: {pl.get('nama') or '-'}\n\n")
    if wa:
        return t + (f"👉 Mohon *teruskan PDF ini* ke pembeli dari HP admin: wa.me/{wa}\n"
                    "(Tekan lama file ini → Teruskan, atau buka link di atas lalu kirim filenya.)\n"
                    "Bot tidak mengirim langsung ke nomor baru supaya nomor CS aman dari blokir WhatsApp.")
    return t + "Nomor WA pembeli tidak dicatat. Simpan atau cetak invoice ini untuk pembeli."

# ------------------------------------------------------------------ laporan keuangan
JENIS = {'dp': 'DP masuk', 'pelunasan': 'Pelunasan', 'penjualan_kandang': 'Jual di kandang', 'refund_dp': 'DP dikembalikan'}

def html_rekap(L):
    R = L.get('ringkas') or {}; T = L.get('terjual') or {}; piutang = L.get('piutang') or []
    sisa = sum(int(p.get('sisa') or 0) for p in piutang)
    hari = L.get('per_hari') or []
    mx = max([abs(int(h.get('masuk') or 0)) for h in hari] + [1])
    bar = ''.join(f"""<div class="bt"><div class="bv">{rp(h['masuk']).replace('Rp', '')}</div><div class="bb" style="height:{max(2, 38 * abs(int(h['masuk'])) / mx):.1f}mm"></div><div class="bl">{esc(h['hari'])}</div></div>""" for h in hari[-31:])
    kal = []
    if int(R.get('uang_masuk') or 0) == 0: kal.append('Belum ada uang masuk yang tercatat pada periode ini.')
    else:
        kal.append(f"Pada periode ini Barokah Farm menerima uang <b>{rp(R.get('uang_masuk'))}</b> dari {int(R.get('n_dp') or 0) + int(R.get('n_pelunasan') or 0) + int(R.get('n_kandang') or 0)} transaksi.")
        kal.append(f"Hewan terjual <b>{T.get('ekor', 0)} ekor/paket</b> ({T.get('online', 0)} pesanan online, {T.get('kandang', 0)} penjualan langsung di kandang) dengan nilai penjualan {rp(T.get('omzet'))}.")
    if piutang: kal.append(f"Masih ada <b>{len(piutang)} pesanan</b> yang sudah DP tapi belum lunas, sisa tagihan <b>{rp(sisa)}</b>.")
    if int((L.get('hangus') or {}).get('n') or 0): kal.append(f"{L['hangus']['n']} pesanan DP-nya hangus karena lewat batas pelunasan ({rp(L['hangus'].get('nominal'))}).")
    if int(R.get('refund') or 0): kal.append(f"DP yang dikembalikan ke pembeli: {rp(R.get('refund'))}.")
    tiles = [('Uang masuk', rp(R.get('uang_masuk')), 'semua uang yang diterima'), ('Terjual', f"{T.get('ekor', 0)} ekor/paket", f"{T.get('pesanan', 0)} pesanan lunas"),
             ('Belum dilunasi', rp(sisa), f'{len(piutang)} pesanan sudah DP'), ('Bersih', rp(R.get('bersih')), 'uang masuk − dikembalikan')]
    tile_html = ''.join(f'<div class="tile"><div class="tl">{a}</div><div class="tv">{b}</div><div class="ts">{c}</div></div>' for a, b, c in tiles)
    rincian = [('DP masuk', R.get('n_dp'), R.get('dp')), ('Pelunasan', R.get('n_pelunasan'), R.get('pelunasan')),
               ('Penjualan langsung di kandang', R.get('n_kandang'), R.get('kandang')), ('DP dikembalikan ke pembeli', R.get('n_refund'), -int(R.get('refund') or 0))]
    rinc_html = ''.join(f'<tr><td>{a}</td><td class="r">{int(n or 0)}×</td><td class="r">{rp(v)}</td></tr>' for a, n, v in rincian)
    rinc_html += f'<tr class="tot"><td>Total uang bersih</td><td></td><td class="r">{rp(R.get("bersih"))}</td></tr>'
    rinc_html += f'<tr><td class="muted" colspan="2">Termasuk ongkir yang dibayar pembeli</td><td class="r muted">{rp(R.get("ongkir"))}</td></tr>'
    prod = ''.join(f"<tr><td><b>{esc(p.get('kode'))}</b> {esc(p.get('nama'))}</td><td class='r'>{p.get('pesanan')}</td><td class='r'>{p.get('ekor')}</td><td class='r'>{rp(p.get('omzet'))}</td></tr>" for p in L.get('per_produk') or []) \
        or '<tr><td colspan="4" class="muted">Belum ada penjualan lunas.</td></tr>'
    piut = ''.join(f"<tr><td>#{p.get('pesanan')}</td><td>{esc(p.get('nama'))}</td><td class='r'>{rp(p.get('harga'))}</td><td class='r'>{rp(p.get('dp'))}</td><td class='r'><b>{rp(p.get('sisa'))}</b></td><td class='r'>{esc(p.get('batas'))}</td></tr>" for p in piutang) \
        or '<tr><td colspan="6" class="muted">Tidak ada. Semua pesanan yang sudah DP sudah lunas.</td></tr>'
    trx = ''.join(f"<tr><td>{esc(t.get('waktu'))}</td><td>{JENIS.get(t.get('jenis'), esc(t.get('jenis')))}</td><td>{('#' + str(t['pesanan'])) if t.get('pesanan') else ''} {esc(t.get('produk'))}</td><td>{esc(t.get('nama'))}</td><td class='r'>{rp(t.get('nominal'))}</td><td class='muted' style='font-size:8pt'>{esc(t.get('invoice') or '')}</td></tr>" for t in L.get('transaksi') or []) \
        or '<tr><td colspan="6" class="muted">Belum ada transaksi.</td></tr>'
    stok = ' · '.join(f"{esc(s.get('kode'))} {esc(s.get('nama'))}: <b>{s.get('stok')}</b>" for s in L.get('stok') or []) or '-'
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{GAYA}
.hal{{min-height:auto}}
.judul{{display:flex;justify-content:space-between;align-items:flex-end;margin-top:7mm}}
.judul h3{{font:800 17pt B,sans-serif;margin:0}} .judul .p{{font:700 10.5pt J;color:#8a6d12}}
.cerita{{margin-top:4mm;background:#F6F2E8;border-radius:3mm;padding:3.5mm 4.5mm;font-size:10.2pt;line-height:1.6}}
.tiles{{display:grid;grid-template-columns:repeat(4,1fr);gap:3mm;margin-top:4mm}}
.tile{{border:1px solid #e3dccb;border-radius:3mm;padding:3mm 3.5mm;border-top:4px solid #1E4A2C}}
.tl{{font:700 8.4pt J;color:#7a857c;text-transform:uppercase;letter-spacing:.04em}} .tv{{font:800 13pt B,sans-serif;color:#1E4A2C;margin:1mm 0}} .ts{{font-size:8pt;color:#7a857c}}
tr.tot td{{font:800 10.5pt J;color:#1E4A2C;border-top:2px solid #1E4A2C}}
.grafik{{display:flex;align-items:flex-end;gap:1.5mm;height:52mm;border-bottom:1.5px solid #1E4A2C;padding:0 1mm}}
.bt{{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;min-width:0}}
.bb{{width:70%;background:#2A6139;border-radius:1mm 1mm 0 0}} .bv{{font-size:6.5pt;color:#4b5a4f;margin-bottom:.8mm;white-space:nowrap}} .bl{{font-size:7pt;color:#7a857c;margin-top:1mm;position:absolute;transform:translateY(5mm)}}
.bt{{position:relative}}
section{{break-inside:avoid}}
</style></head><body><div class="hal">
<div class="kop"><img src="file://{E}/aset/logo.png"><div><h1>{USAHA['nama']}</h1><div class="tag">{USAHA['tagline']}</div><div class="al">{USAHA['alamat']}</div></div>
<div class="kanan">Laporan dibuat<br><b>{esc(L.get('dibuat'))} WIB</b></div></div>
<div class="judul"><h3>Laporan Keuangan</h3><div class="p">Periode {esc(L.get('dari'))} – {esc(L.get('sampai'))}</div></div>
<div class="cerita">{' '.join(kal)}</div>
<div class="tiles">{tile_html}</div>
<section><h2>Rincian uang masuk</h2><table><tr><th>Jenis</th><th class="r">Jumlah</th><th class="r">Nominal</th></tr>{rinc_html}</table></section>
{f'<section><h2>Uang masuk per hari</h2><div class="grafik">{bar}</div><div style="height:7mm"></div></section>' if hari else ''}
<section><h2>Penjualan per produk (lunas)</h2><table><tr><th>Produk</th><th class="r">Pesanan</th><th class="r">Ekor/paket</th><th class="r">Nilai</th></tr>{prod}</table></section>
<section><h2>Belum dilunasi (sudah DP)</h2><table><tr><th>Pesanan</th><th>Pembeli</th><th class="r">Harga</th><th class="r">DP</th><th class="r">Sisa</th><th class="r">Batas</th></tr>{piut}</table></section>
<h2>Daftar semua transaksi</h2><table><tr><th>Waktu</th><th>Jenis</th><th>Pesanan</th><th>Pembeli</th><th class="r">Nominal</th><th>Invoice</th></tr>{trx}</table>
<section><h2>Stok saat ini</h2><div style="font-size:9.4pt">{stok}</div></section>
<div class="kaki"><span>Dihitung otomatis dari catatan DP, pelunasan, dan penjualan kandang di sistem Barokah Farm.</span><span>Pesanan batal: {L.get('batal', 0)}</span></div>
</div></body></html>"""

# ------------------------------------------------------------------ pembuatan & pengiriman
def pdf(isi_html, nama_awal='dok', kaki='-'):
    os.makedirs(BERKAS, exist_ok=True)
    for f in glob.glob(f'{BERKAS}/*'):
        if time.time() - os.path.getmtime(f) > 30 * 86400: os.remove(f)
    tok = f'{nama_awal}-' + secrets.token_urlsafe(18)
    h = f'{BERKAS}/{tok}.html'; p = f'{BERKAS}/{tok}.pdf'
    open(h, 'w').write(isi_html)
    r = subprocess.run(['node', f'{E}/pdf.js', h, p, kaki], capture_output=True, text=True, timeout=150)
    os.remove(h)
    if r.returncode != 0 or not os.path.exists(p): raise RuntimeError('PDF gagal: ' + (r.stderr or r.stdout)[-300:])
    return tok, p

def url_berkas(tok):
    dom = os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'mesin-video-production.up.railway.app')
    return f'https://{dom}/berkas/{tok}.pdf'

STATUS = {}

def buat_invoice(d):
    """-> (token, path pdf). Foto hewan (d['foto'] = daftar URL) diunduh sementara lalu dihapus."""
    import shutil
    tmp = f'{BERKAS}/foto-' + secrets.token_hex(6)
    try:
        return pdf(html_invoice(d, siapkan_foto(d.get('foto'), tmp)), 'inv')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def kirim_invoice(d, chat_id, tes=False):
    import pipeline
    try:
        tok, _ = buat_invoice(d)
        nama = 'Invoice-' + str(d.get('no', '')).replace('/', '-') + '.pdf'
        STATUS[d.get('no')] = url_berkas(tok)
        teks = teks_teruskan(d) if d.get('ke_admin') else teks_invoice(d)
        if not tes and chat_id: pipeline.lapor_wa(teks, print, chat_id=chat_id, berkas_url=url_berkas(tok), berkas_nama=nama)
        print(f"invoice {d.get('no')} -> {str(chat_id)[:6]}… {url_berkas(tok)}", flush=True)
    except Exception as e:
        STATUS[d.get('no')] = 'gagal: ' + str(e)[:200]; print('invoice gagal:', e, flush=True)

def kirim_rekap(L, chat_id, tes=False):
    import pipeline
    try:
        tok, _ = pdf(html_rekap(L), 'rekap', 'Barokah Farm · Laporan keuangan ' + str(L.get('dari')) + '–' + str(L.get('sampai')))
        R = L.get('ringkas') or {}
        teks = (f"📊 *Laporan keuangan {L.get('dari')} – {L.get('sampai')}*\nUang masuk {rp(R.get('uang_masuk'))}, "
                f"terjual {(L.get('terjual') or {}).get('ekor', 0)} ekor/paket. Rincian lengkap ada di PDF.")
        STATUS['rekap'] = url_berkas(tok)
        if not tes and chat_id:
            pipeline.lapor_wa(teks, print, chat_id=chat_id, berkas_url=url_berkas(tok),
                              berkas_nama=f"Laporan-Keuangan-BarokahFarm-{str(L.get('dari')).replace('/', '')}-{str(L.get('sampai')).replace('/', '')}.pdf")
        print('rekap ->', url_berkas(tok), flush=True)
    except Exception as e:
        STATUS['rekap'] = 'gagal: ' + str(e)[:200]; print('rekap gagal:', e, flush=True)
        if not tes and chat_id: pipeline.lapor_wa('⚠️ Maaf, laporan keuangan gagal dibuat. Coba lagi beberapa menit lagi.', print, chat_id=chat_id)

def mulai(fungsi, *a): threading.Thread(target=fungsi, args=a, daemon=True).start()
