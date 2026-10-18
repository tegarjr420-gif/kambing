-- Patch 19/10/2026: ketentuan DP baru (sudah diterapkan di database live)
-- * Batal sebelum batas pelunasan -> DP dikembalikan penuh (bot_batal menandai refund, bot mengoper ke admin)
-- * Lewat 3 hari sejak konfirmasi admin -> otomatis batal, DP untuk pakan & perawatan 1 bulan (jadwal_cek)
-- * Bukti belum dikonfirmasi admin > 60 menit -> pembeli dikabari (malam: admin istirahat), admin diingatkan
alter table pesanan add column if not exists bukti_lunas_at timestamptz, add column if not exists tunggu_dikabari timestamptz;
insert into pengaturan(k, v) values ('kebijakan_dp', 'Batas pelunasan 3 x 24 jam dihitung sejak admin mengonfirmasi DP (bukan sejak transfer). Bila pembeli membatalkan sebelum batas pelunasan, DP dikembalikan penuh. Bila lewat 3 hari belum lunas, pesanan otomatis dibatalkan dan DP tidak dikembalikan karena dipakai untuk biaya pakan dan perawatan kambing selama 1 bulan; kambing kembali dijual.')
on conflict (k) do update set v = excluded.v;
update pengaturan set v = 'https://barokahfarm.pages.dev' where k = 'link_katalog';
-- Fungsi _info, bot_bukti, bot_batal, jadwal_cek: lihat definisi live (pg_get_functiondef).
