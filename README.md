# Barokah Farm: katalog kambing & CS WhatsApp

Sistem penjualan kambing Barokah Farm, dibuat oleh [Otomaya](https://otomaya.pages.dev).

| Folder | Isi |
|---|---|
| `katalog/` | Website katalog statis (HTML/CSS/JS, tanpa build). Siap di-hosting di Cloudflare Pages. |
| `supabase/schema.sql` | Skema database: kambing, pesanan/DP, riwayat harga, testimoni, status percakapan. |
| `n8n/` | Kode workflow n8n (SDK): CS WhatsApp, Kirim Teks WA, Kirim Pesan Sistem, Jadwal DP. |
| `railway/` | Railway Function untuk memasang webhook WAHA → n8n. |

## Alur sistem

```
Pembeli WA ──► WAHA (Railway) ──webhook──► n8n "Kambing — CS WhatsApp"
                                              │  ├─ Supabase RPC bot_masuk (catat + konteks)
                                              │  ├─ Gemini: jawab sesuai SOP, tahan kambing, simpan alamat
                                              │  ├─ Gambar → Gemini baca bukti → Storage → teruskan ke admin
                                              │  └─ Admin: perintah bebas → Gemini → konfirmasi YA → admin_aksi
n8n "Kambing — Jadwal DP" (tiap 5 menit) ──► jadwal_cek: lepas tahan 60 mnt, pengingat H-1, DP hangus
Katalog (Cloudflare Pages) ──► Supabase view `katalog` (hanya baca)
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
- **Sekarang:** `katalog/data/kambing.json` berisi **data contoh** (ada tanda "Ini data contoh" di halaman).
- **Nanti:** isi `supabaseUrl` dan `supabaseAnonKey` di `config.js`. Katalog lalu membaca view `katalog` di Supabase,
  yang otomatis diperbarui oleh bot WhatsApp (tambah kambing, ubah harga, DP, terjual). Halaman memuat ulang stok tiap 60 detik.
- Anon key aman ditaruh di website: website hanya bisa membaca view publik, tanpa data pembeli.

### Tautan langsung ke satu kambing
`https://<domain>/#BF-07` langsung membuka detail kambing BF-07. Bot bisa mengirim tautan ini ke pembeli.
