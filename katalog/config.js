/* =========================================================
   PENGATURAN KATALOG BAROKAH FARM
   Ubah nilai di bawah ini saja, tidak perlu menyentuh file lain.
   ========================================================= */
window.BF_CONFIG = {
  namaToko: "Barokah Farm",

  // Nomor WhatsApp CS (bot). Format internasional tanpa + dan tanpa spasi.
  waCS: "6287890140532",

  alamat: "Kampung Peusar RT 02/RW 01, Kel. Binong, Kec. Curug, Kabupaten Tangerang",
  mapsUrl: "https://maps.app.goo.gl/LSNuAis26oHkBoNE7",
  jamBuka: "10.00–17.00",

  rekening: { bank: "BRI", nomor: "808001004661537", nama: "Muriyadi" },
  dpMinimal: 100000,
  batasPelunasanHari: 3,

  // Lokasi: semua dalam satu tempat
  lokasiIsi: ["Kantor", "Kandang", "Dapur pemotongan & olahan"],
  // Peta kecil di bagian lokasi (Google Maps embed, tanpa API key)
  mapsEmbed: "https://maps.google.com/maps?q=peternakan%20pak%20muri%2C%20Jl.%20Kp.%20Peusar%2C%20Binong%2C%20Curug%2C%20Tangerang&z=15&output=embed",

  // Tim. Isi "foto" dengan nama file di folder img/ (mis. "img/tim-muri.jpg") kalau fotonya sudah ada.
  tim: [
    { nama: "Bpk. Muri", peran: "Owner", foto: "" },
    { nama: "Bpk. Tamsil", peran: "Pengelola harian kandang", foto: "" },
    { nama: "Bung Raja", peran: "Pengelola harian & admin", foto: "" },
  ],

  // Mode Iduladha: true = tampilkan banner kurban & filter "Layak kurban".
  iduladha: false,

  // Sumber data. Kalau supabaseUrl & supabaseAnonKey diisi, katalog membaca stok asli
  // dari Supabase (diperbarui otomatis oleh bot WhatsApp).
  // Kalau kosong, katalog membaca file data/kambing.json & data/testimoni.json.
  // Catatan: anon key memang boleh ada di website (aksesnya dibatasi RLS, hanya baca).
  supabaseUrl: "https://jjkrkdyqkdhwmoathwbz.supabase.co",
  supabaseAnonKey: "sb_publishable_M-c-ba8AfKp06mNyDStOag_wUqRu1MJ",

  // Muat ulang stok otomatis tiap N detik (0 = mati)
  refreshDetik: 60,

  // Kredit pembuat
  otomaya: {
    web: "https://otomaya.pages.dev",
    instagram: "https://www.instagram.com/otomaya.id",
    tiktok: "https://www.tiktok.com/@otomaya.id",
    igHandle: "@otomaya.id",
    tiktokHandle: "@otomaya.id"
  }
};
