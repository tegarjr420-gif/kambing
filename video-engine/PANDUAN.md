# Mesin Editing Video Barokah Farm (Otomaya)

Video vertikal 1080×1920, 30 fps, siap TikTok/Reels/Shorts. Semua langkah jalan di sandbox (ffmpeg + Python + Playwright).

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
