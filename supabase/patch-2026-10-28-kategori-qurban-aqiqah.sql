-- 28 Okt 2026: susunan kategori baru (permintaan klien).
-- QURBAN: Domba Qurban kelas 1-5 dan Kambing Qurban kelas 1-5; paket qurban (QP-xx) dihapus.
-- AQIQAH: Catering Aqiqah (Paket A/B/C), Hewan Aqiqah + Potong (domba jantan tanduk & dugul), Paket Pesta.
-- Pengelompokan di katalog memakai awal nama produk (lihat katalog/app.js: grupProduk).
begin;

-- Paket qurban dihapus (tidak ada pesanan yang memakainya); bila pernah diulas, cukup disembunyikan.
update produk set tampil = false
 where kode like 'QP-%' and exists (select 1 from ulasan u where u.produk_kode = produk.kode);
delete from produk
 where kode like 'QP-%' and not exists (select 1 from ulasan u where u.produk_kode = produk.kode);

-- Qurban kelas lama menjadi Domba Qurban kelas 1-5 (berat, harga, stok tetap).
update produk set nama = 'Domba Qurban Kelas ' || right(kode, 1), ras = 'Domba', urutan = 50 + right(kode, 1)::int,
       layak_kurban = true, updated_at = now()
 where kode in ('QK-01','QK-02','QK-03','QK-04','QK-05');

-- Kambing Qurban kelas 1-5: harga, berat, dan stok belum ditetapkan klien (tampil "Harga tanya admin").
insert into produk (kode, kategori, nama, ras, layak_kurban, urutan, opsi)
select 'QK-' || lpad((5 + n)::text, 2, '0'), 'Qurban', 'Kambing Qurban Kelas ' || n, 'Kambing', true, 55 + n, '[]'::jsonb
  from generate_series(1, 5) n
on conflict (kode) do update set nama = excluded.nama, ras = excluded.ras, kategori = 'Qurban',
  layak_kurban = true, urutan = excluded.urutan, tampil = true, updated_at = now();

-- Aqiqah: AQ-01 .. AQ-12 (AQ-01/AQ-02 lama diganti; tidak ada pesanan yang memakainya).
insert into produk (kode, kategori, nama, ras, kelamin, berat_min, berat_max, harga, stok, isi_ekor, opsi, urutan, deskripsi, tampil)
values
  ('AQ-01','Aqiqah','Catering Aqiqah Paket A',null,'Jantan',null,null,2900000,null,1,'[]',31,'1 ekor domba jantan, 50 box. Catering aqiqah memakai domba jantan yang memenuhi syarat untuk aqiqah.',true),
  ('AQ-02','Aqiqah','Catering Aqiqah Paket B',null,'Jantan',null,null,3600000,null,1,'[]',32,'1 ekor domba jantan, 75 box. Catering aqiqah memakai domba jantan yang memenuhi syarat untuk aqiqah.',true),
  ('AQ-03','Aqiqah','Catering Aqiqah Paket C',null,'Jantan',null,null,4300000,null,1,'[]',33,'1 ekor domba jantan, 100 box. Catering aqiqah memakai domba jantan yang memenuhi syarat untuk aqiqah.',true),
  ('AQ-04','Aqiqah','Domba Jantan Tanduk','Domba','Jantan',15,20,1500000,20,1,'[]',34,'Hewan aqiqah + potong.',true),
  ('AQ-05','Aqiqah','Domba Jantan Tanduk','Domba','Jantan',20,25,2000000,20,1,'[]',35,'Hewan aqiqah + potong.',true),
  ('AQ-06','Aqiqah','Domba Jantan Tanduk','Domba','Jantan',25,30,2500000,20,1,'[]',36,'Hewan aqiqah + potong.',true),
  ('AQ-07','Aqiqah','Domba Jantan Non Tanduk (Dugul)','Domba','Jantan',15,20,1200000,10,1,'[]',37,'Hewan aqiqah + potong.',true),
  ('AQ-08','Aqiqah','Domba Jantan Non Tanduk (Dugul)','Domba','Jantan',20,25,1700000,10,1,'[]',38,'Hewan aqiqah + potong.',true),
  ('AQ-09','Aqiqah','Domba Jantan Non Tanduk (Dugul)','Domba','Jantan',25,30,2000000,10,1,'[]',39,'Hewan aqiqah + potong.',true),
  ('AQ-10','Aqiqah','Paket Pesta 1 box',null,'Betina',null,null,28000,null,1,'[]',41,'1 box. Paket pesta memakai domba betina.',true),
  ('AQ-11','Aqiqah','Paket Pesta 50 box',null,'Betina',null,null,1350000,null,1,'[]',42,'50 box. Paket pesta memakai domba betina.',true),
  ('AQ-12','Aqiqah','Paket Pesta 100 box',null,'Betina',null,null,2700000,null,1,'[]',43,'100 box. Paket pesta memakai domba betina.',true)
on conflict (kode) do update set kategori = excluded.kategori, nama = excluded.nama, ras = excluded.ras, kelamin = excluded.kelamin,
  berat_min = excluded.berat_min, berat_max = excluded.berat_max, harga = excluded.harga, stok = excluded.stok,
  isi_ekor = excluded.isi_ekor, opsi = excluded.opsi, urutan = excluded.urutan, deskripsi = excluded.deskripsi,
  flash_harga = null, flash_sampai = null, layak_kurban = false, tampil = true, updated_at = now();

-- Kode aqiqah lain yang mungkin tersisa dari susunan lama disembunyikan.
update produk set tampil = false
 where kategori = 'Aqiqah' and kode not in ('AQ-01','AQ-02','AQ-03','AQ-04','AQ-05','AQ-06','AQ-07','AQ-08','AQ-09','AQ-10','AQ-11','AQ-12');

commit;
