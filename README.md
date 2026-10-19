# Barokah Farm: katalog kambing & CS WhatsApp

Sistem penjualan kambing Barokah Farm, dibuat oleh [Otomaya](https://otomaya.pages.dev).

| Folder | Isi |
|---|---|
| `katalog/` | Website katalog statis (HTML/CSS/JS, tanpa build). Siap di-hosting di Cloudflare Pages. |
| `supabase/skema-live-2026-10-19.sql` | Snapshot lengkap database live (tabel, view, semua fungsi). `schema.sql` + `patch-*.sql` = riwayat. |
| `n8n/` | Kode workflow n8n (SDK): CS WhatsApp, Kirim Teks WA, Kirim Pesan Sistem, Jadwal DP, Rekap Pagi, Alarm. |
| `docs/contekan/` | Contekan 1 halaman (PDF A4) untuk admin dan staf kandang, plus sumber HTML-nya. |
| `railway/` | Railway Function untuk memasang webhook WAHA → n8n. |

## Alur sistem

```
Pembeli WA ──► WAHA (Railway) ──webhook──► n8n "Kambing — CS WhatsApp"
                                              │  ├─ Supabase RPC bot_masuk (catat + konteks)
                                              │  ├─ Gemini: jawab sesuai SOP, tahan kambing, simpan alamat
                                              │  ├─ Gambar → Gemini baca bukti → Storage → teruskan ke admin
                                              │  └─ Admin: perintah bebas → Gemini → konfirmasi YA → admin_aksi
n8n "Kambing — Jadwal DP" (tiap 5 menit) ──► jadwal_cek: lepas tahan 60 mnt, pengingat H-1, DP hangus
n8n "Kambing — Rekap Pagi" (07.00 WIB) ──► rekap_pagi: rekap admin & rekap kandang ke WhatsApp
n8n "Kambing — Alarm WhatsApp & AI" (tiap 15 mnt) ──► cek sesi WAHA + alarm_cek ──► notifikasi HP (ntfy) & WA admin
Katalog (Cloudflare Pages) ──► Supabase view `katalog_produk` (hanya baca) + catat_kunjungan (penghitung pengunjung)
```

## Pasang katalog di Cloudflare Pages

**Cara 1, upload langsung (paling cepat)**
1. Cloudflare dashboard → *Workers & Pages* → *Create* → *Pages* → *Upload assets*.
2. Beri nama proyek, misalnya `barokahfarm`.
3. Seret **isi** folder `katalog/` (bukan folder luarnya) → *Deploy*.
4. Situs aktif di `https://barokahfarm.pages.dev`.

**Cara 2, sambungkan ke GitHub (update otomatis tiap push)**
1. *Create* → *Pages* → *Connect to Git* → pilih repo `kambing`.
2. Framework preset: **None**. Build command: *(kosongkan)*. Build output directory: **`katalog`**.
3. *Save and Deploy*.

## Pengaturan

Semua pengaturan ada di `katalog/config.js`: nomor WhatsApp CS, alamat, jam buka, rekening, DP minimal,
batas pelunasan, mode Iduladha (`iduladha: true/false`), dan tautan Otomaya.

### Sumber data stok
- Katalog membaca view `katalog_produk` dan `ulasan_publik` di Supabase (`supabaseUrl` dan `supabaseAnonKey` di `config.js`),
  yang otomatis diperbarui oleh bot WhatsApp (tambah kambing, ubah harga, DP, terjual). Halaman memuat ulang stok tiap 60 detik.
- Anon key aman ditaruh di website: website hanya bisa membaca view publik, tanpa data pembeli.

### Tautan langsung ke satu produk
`https://<domain>/#K-01` langsung membuka detail produk K-01. Bot bisa mengirim tautan ini ke pembeli.

### Kode produk
Katalog dijual per kelas: `K-xx` kambing, `D-xx` domba, `AQ-xx` paket aqiqah (harga per pilihan 1–10 ekor),
`QP-xx` qurban paket, `QK-xx` qurban kelas. Admin mengatur stok, harga, flash sale, dan ulasan lewat WhatsApp
(ketik `bantuan` dari nomor admin). Pesanan pembeli memakai nomor pesanan (`OK 12`, `lunas 12`).

### Peran di WhatsApp
- **Admin**: semua perintah. Nomor admin terdaftar di pengaturan `admin_wa` / `admin_chat`.
- **Staf kandang**: daftar dengan mengirim `STAF <PIN>` ke nomor bot. Hanya boleh `stok`, `laku`, `stok K-01 24`,
  `tambah stok`, `foto`, `galeri`, `tampilkan/sembunyikan`. Perintah lain dibalas "khusus admin".
- **Pembeli**: dilayani AI. Ketik `cek pesanan` untuk melihat status, batas waktu, dan sisa bayar (tanpa AI).

### Alarm ke HP
Pasang aplikasi **ntfy** (Android/iOS), *Subscribe to topic*, isi nama topik yang diberikan Otomaya.
Alarm berbunyi bila sesi WhatsApp terputus (sistem juga mencoba menyalakan ulang) atau ≥3 chat dalam 1 jam gagal dijawab AI.
