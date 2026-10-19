# Mesin Editing Video Barokah Farm (Otomaya)

Video vertikal 1080×1920, 30 fps, siap TikTok/Reels/Facebook (opsi `--landscape` → 1920×1080). Berjalan otomatis di Railway (service **mesin-video**).

## Alur
1. **Tarik mentahan** dari folder Drive "1. Video Mentah" (akses link: Pelihat) lewat workflow n8n
   *Otomaya — Pindah Video Mentah* → Supabase Storage bucket `mentah` (potongan ≤49 MB) → `puller.py` menyusun ulang ke `raw/`.
2. **Analisa**: `ana/asr.py` + `ana/utuh2.py` (Whisper turbo = teks, Dolphin CTC = waktu kata), `ana/wajah.py` (posisi wajah untuk auto-reframe),
   contact sheet `ana/sheet/` untuk memilih momen.
3. **Naskah edit** per video di `spec/VN.json` (lihat format di bawah).
4. **Render**: `python3 edit.py spec/V1.json` → `out/<file>.mp4`. Cek: `python3 cek.py out/<file>.mp4 0.75`.
5. Setelah mentahan habis dipakai dan hasil disetujui: pindahkan mentahan ke Sampah Drive, kabari admin lewat WA untuk kirim mentahan baru.

## 5 gaya (`gaya.py`)
| Gaya | Ciri |
|---|---|
| `edukasi` | Jump cut rapat + zoom selang-seling, kata kunci muncul, subtitle sorot per kata, cutaway B-roll |
| `sinematik` | Slow motion 2× (sumber 60 fps), grade hangat, transisi dissolve, teks serif elegan |
| `hook` | Potongan cepat mengikuti ketukan, teks besar Anton, transisi slide + whoosh |
| `vlog` | Natural, suara kandang terdengar, catatan tulisan tangan, subtitle kotak |
| `promo` | Kartu info (ongkir, DP, katalog), warna cerah, CTA |

## Musik (`musik.py`)
10 gaya, dibuat per video sesuai durasi (aman hak cipta, soundfont GeneralUser GS):
akustik, lofi, sinematik, pop, inspirasi, tropis, folk, funk, religi, hiphop. `seed` beda = lagu beda.
Musik otomatis turun saat ada yang bicara (ducking) dan naik penuh di jeda. Level: `musik_db`, `duck_db` per gaya, `musik.db` per video.

## Suara
Rantai perbaikan suara: high-pass, pengurang bising (afftdn), EQ kejelasan 3 kHz, kompresor, normalisasi −16 LUFS. Hasil akhir −14 LUFS (standar TikTok/IG).

## Format spec
```json
{"id":"V2","file":"Nama-File","gaya":"edukasi","musik":{"gaya":"akustik","seed":4,"drop":0},
 "bagian":[
  {"jenis":"bicara","src":"20261019_161116","in":0.0,"out":12.75,"rapat":0.4,
   "kata":[{"at":1.0,"dur":1.5,"teks":"RESELLER?"}],
   "sisip":[{"at":3.0,"dur":1.6,"src":"VID_..._153438","in":0.3}]},
  {"jenis":"broll","klip":[{"src":"VID_...","in":2.6,"dur":2.2}],"suara":-8,
   "teks":[{"kind":"kunci","at":0.4,"dur":3,"teks":"Baris 1\\nBaris 2","sub2":"keterangan"}]},
  {"jenis":"penutup","src":"VID_...","in":10,"dur":3.6}],
 "penutup":{"judul":"Barokah Farm","sub":"..."}}
```
Koreksi ejaan subtitle: `koreksi.json` (`_kata` untuk ganti kata, `_teks` untuk teks penuh per klip).

## Komponen editing profesional (upgrade 19/10/2026)
| Komponen | Cara kerja di mesin |
|---|---|
| Cutting, trimming, timeline | Potong per kata dari transkrip, jump cut di akhir kalimat, buang jeda, durasi kelipatan frame |
| J-cut / L-cut, cutaway | Suara orang mulai sebelum gambarnya (`jcut`), B-roll menimpa saat orang bicara (`sisip`) |
| Transisi halus | cut, dissolve, whip (slide + motion blur arah gerak), zoom, wipe; whoosh mulai 0.2 dtk sebelum potongan |
| Color correction | Otomatis per shot: white balance (gray-world) + exposure (gamma) → semua shot disamakan (shot matching) |
| LUT cinematic | `aset/lut/*.cube` (komersial, sinematik, hangat, natural) dibuat `lut.py`, melindungi warna kulit |
| Stabilization | vid.stab 2 tahap untuk klip HP genggam |
| Speed ramp & slow motion | `ramp` cepat→lambat dari sumber 60 fps, frame blending di bagian cepat |
| Keyframe animation | `kf` zoom/pan dengan easing smoothstep; animasi teks dengan ease-out |
| Motion blur | dblur di sekitar transisi whip, tmix pada bagian cepat speed ramp |
| Masking & tracking | Deteksi wajah → kamera mengikuti subjek (auto-reframe) + vignette lembut berpusat di subjek |
| Noise reduction audio | Filter dengung 50/100 Hz, de-click, RNNoise (jaringan saraf), FFT denoise, de-esser, EQ, kompresor |
| Sound design & mixing | SFX (whoosh, tick, thump, riser) di titik yang pas, suara kandang asli, limiter, −14 LUFS |
| Backsound | Selalu ≥ 9 dB di bawah suara orang; turun otomatis saat ada yang bicara |
| SFX ikut ketukan | `musik.bpm` → potongan B-roll jatuh tepat di ketukan musik |
| Subtitle & motion graphics | Subtitle ucapan kecil & bersih, logo reveal, lower third, kartu promo |

Aturan sutradara AI: `sutradara/MASTER_PROMPT.txt` + `sutradara/TUGAS_SUTRADARA.md`.

## Otomatis di Railway (20/10/2026)
```
Admin unggah mentahan ke Drive "1. Video Mentah"
  → mesin-video cek tiap 20 menit (mulai bila unggahan terakhir sudah ≥15 menit)
  → unduh semua video → hapus mentahan dari Drive (masuk Sampah, bisa dipulihkan 30 hari)
  → WA admin: "Mentahan diterima, sedang diedit"
  → analisa: transkrip per kata, wajah, guncangan, kecerahan, contact sheet
  → sutradara Gemini (lewat n8n "Kambing — Mesin Video") menulis 1–6 naskah, diperiksa mesin; bila gagal → aturan cadangan
  → render (portrait 1080×1920), tulisan otomatis menghindari wajah & memilih latar tenang
  → cek teknis (durasi, volume −14 LUFS)
  → unggah ke Drive "2. Video Jadi/<tanggal jam>" (folder dibagikan via link)
  → WA admin: daftar video + link + minta mentahan baru
```
| Bagian | Tempat |
|---|---|
| Server mesin | Railway project giving-success → service `mesin-video` (Dockerfile di folder ini), volume `/data` |
| AI sutradara + lapor WA | n8n workflow "Kambing — Mesin Video (AI Sutradara & Lapor WA)" (kredensial Gemini yang sama dengan bot CS) |
| Akses Drive | Apps Script "Jembatan Drive" milik akun pemilik Drive (hanya folder mentah & video jadi) |

Variabel Railway: `ENGINE_KEY`, `GEMINI_PROXY_URL/KEY`, `GEMINI_MODEL`, `LAPOR_URL`, `JEMBATAN_URL/KEY`, `FOLDER_MENTAH`, `FOLDER_JADI`,
`CEK_MENIT` (jeda cek), `TENANG_MENIT` (tunggu unggahan selesai), `CEK_OTOMATIS` (1 = aktif).

Endpoint (kunci `?k=ENGINE_KEY`): `GET /sehat`, `GET /status`, `POST /cek?tenang=0` (cek sekarang), `POST /uji-ai`, `POST /uji-wa`, `POST /uji-drive`,
`GET /hasil/<tugas>/<file>`, `GET /naskah?tugas=`.

### Tips merekam (portrait)
- Kamera utama 1x, 4K/1080p, 30 atau 60 fps, pegang stabil atau pakai tripod.
- Orang yang bicara di tengah, terlihat dari dada/pinggang ke atas, sisakan ruang di atas kepala.
- Mikrofon dekat (clip-on), hindari angin dan suara mesin.
- Rekam B-roll: kambing dari dekat, kandang, pakan, proses timbang, pengiriman — tiap klip 5–15 detik.
