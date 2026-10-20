-- 2026-10-20: invoice (DP, lunas, penjualan kandang), buku kas (transaksi), laporan keuangan.
-- Bagian 1: struktur & fungsi bantu. Bagian 2 (admin_aksi, rekap_pagi) ada di patch-2026-10-20-admin-aksi-invoice.sql

alter table pesanan
  add column if not exists harga_final int,          -- harga hewan akhir (disebut staf saat lunas / laku)
  add column if not exists ongkir int,               -- ongkir yang dibayar pembeli (0 = gratis)
  add column if not exists gratis_ongkir boolean,
  add column if not exists ambil_sendiri boolean,
  add column if not exists sumber text default 'online',   -- online (lewat bot) / kandang (laku langsung)
  add column if not exists invoice_dp text,
  add column if not exists invoice_lunas text;

create table if not exists transaksi (            -- buku kas: setiap uang masuk/keluar
  id bigint generated always as identity primary key,
  waktu timestamptz not null default now(),
  jenis text not null check (jenis in ('dp','pelunasan','penjualan_kandang','refund_dp')),
  pesanan_id bigint references pesanan(id),
  produk_kode text,
  jumlah int default 1,
  nama text,
  wa text,
  nominal int not null,            -- uang diterima (negatif = dikembalikan)
  harga int,                       -- harga hewan pada transaksi itu
  ongkir int default 0,
  invoice_no text,
  oleh text,
  catatan text
);
create index if not exists transaksi_waktu on transaksi(waktu);
create index if not exists transaksi_pesanan on transaksi(pesanan_id);
alter table transaksi enable row level security;

create table if not exists invoice (
  no text primary key,
  jenis text not null,             -- DP / LUNAS / PENJUALAN
  pesanan_id bigint references pesanan(id),
  data jsonb not null,
  dibuat timestamptz not null default now()
);
alter table invoice enable row level security;

-- DP minimal untuk satu pesanan (sama dengan ringkasan pesanan)
create or replace function _dp_min(o pesanan) returns int language sql stable set search_path to 'public' as $$
  select coalesce(_set('dp_min')::int, 100000) * case when o.opsi is not null then greatest(o.jumlah, 1)
    else greatest(o.jumlah, 1) * coalesce((select isi_ekor from produk where kode = o.produk_kode), 1) end
$$;

create or replace function _wa62(p text) returns text language sql immutable as $$
  select nullif(regexp_replace(regexp_replace(coalesce(p, ''), '\D', '', 'g'), '^0', '62'), '')
$$;

-- Buat nomor invoice + simpan isinya. Template PDF ada di mesin (invoice.html); di sini hanya datanya.
create or replace function _invoice(o pesanan, j text) returns jsonb
language plpgsql security definer set search_path to 'public' as $$
declare v_no text; d jsonb; pr produk; v_dp int; v_harga int; v_ongkir int; v_total int;
  v_bln text := to_char(now() at time zone 'Asia/Jakarta', 'YYMM');
begin
  select * into pr from produk where kode = o.produk_kode;
  v_dp := coalesce((select sum(nominal) from transaksi where pesanan_id = o.id and jenis = 'dp'), 0);
  v_harga := coalesce(o.harga_final, o.harga, 0);
  v_ongkir := coalesce(o.ongkir, 0);
  v_total := v_harga + v_ongkir;
  v_no := 'INV/BF/' || v_bln || '/' || lpad(((select count(*) from invoice where no like 'INV/BF/' || v_bln || '/%') + 1)::text, 4, '0');
  d := jsonb_build_object(
    'no', v_no, 'jenis', j, 'pesanan', o.id, 'sumber', coalesce(o.sumber, 'online'),
    'tanggal', to_char(now() at time zone 'Asia/Jakarta', 'DD/MM/YYYY'), 'jam', to_char(now() at time zone 'Asia/Jakarta', 'HH24.MI'),
    'pelanggan', jsonb_build_object('nama', o.nama, 'wa', coalesce(o.wa, split_part(o.chat_id, '@', 1)), 'alamat', o.alamat_kirim),
    'item', jsonb_build_object('kode', o.produk_kode, 'nama', coalesce(pr.nama, o.produk_kode), 'kategori', pr.kategori, 'berat', _berat(pr),
                               'opsi', o.opsi, 'jumlah', coalesce(o.jumlah, 1)),
    'harga', v_harga, 'ongkir', v_ongkir, 'gratis_ongkir', coalesce(o.gratis_ongkir, v_ongkir = 0), 'ambil_sendiri', coalesce(o.ambil_sendiri, false),
    'total', v_total, 'dp', v_dp,
    'dibayar', case when j = 'DP' then v_dp else v_total end,
    'pelunasan', case when j = 'DP' then null else v_total - v_dp end,
    'sisa', case when j = 'DP' then greatest(v_total - v_dp, 0) else 0 end,
    'batas_lunas', to_char(o.batas_lunas at time zone 'Asia/Jakarta', 'DD/MM/YYYY HH24.MI'),
    'rekening', _set('rekening'), 'alamat_usaha', _set('alamat'), 'ongkir_info', _set('ongkir'));
  insert into invoice(no, jenis, pesanan_id, data) values (v_no, j, o.id, d);
  if j = 'DP' then update pesanan set invoice_dp = v_no where id = o.id;
  else update pesanan set invoice_lunas = v_no where id = o.id; end if;
  return d;
end $$;

-- Laporan keuangan untuk PDF "rekapan" (periode tanggal WIB, inklusif)
create or replace function laporan_keuangan(p_key text, p_dari date, p_sampai date) returns jsonb
language plpgsql security definer set search_path to 'public' as $$
declare a timestamptz := (p_dari::timestamp at time zone 'Asia/Jakarta');
        b timestamptz := ((p_sampai + 1)::timestamp at time zone 'Asia/Jakarta');
begin
  perform _cek(p_key);
  return jsonb_build_object(
    'dari', to_char(p_dari, 'DD/MM/YYYY'), 'sampai', to_char(p_sampai, 'DD/MM/YYYY'),
    'dibuat', to_char(now() at time zone 'Asia/Jakarta', 'DD/MM/YYYY HH24.MI'),
    'ringkas', (select jsonb_build_object(
        'uang_masuk', coalesce(sum(nominal) filter (where nominal > 0), 0),
        'uang_keluar', coalesce(-sum(nominal) filter (where nominal < 0), 0),
        'bersih', coalesce(sum(nominal), 0),
        'dp', coalesce(sum(nominal) filter (where jenis = 'dp'), 0), 'n_dp', count(*) filter (where jenis = 'dp'),
        'pelunasan', coalesce(sum(nominal) filter (where jenis = 'pelunasan'), 0), 'n_pelunasan', count(*) filter (where jenis = 'pelunasan'),
        'kandang', coalesce(sum(nominal) filter (where jenis = 'penjualan_kandang'), 0), 'n_kandang', count(*) filter (where jenis = 'penjualan_kandang'),
        'refund', coalesce(-sum(nominal) filter (where jenis = 'refund_dp'), 0), 'n_refund', count(*) filter (where jenis = 'refund_dp'),
        'ongkir', coalesce(sum(ongkir) filter (where jenis in ('pelunasan', 'penjualan_kandang')), 0))
      from transaksi where waktu >= a and waktu < b),
    'terjual', (select jsonb_build_object('pesanan', count(*), 'ekor', coalesce(sum(coalesce(o.jumlah, 1)), 0),
        'omzet', coalesce(sum(coalesce(o.harga_final, o.harga, 0) + coalesce(o.ongkir, 0)), 0),
        'online', count(*) filter (where coalesce(o.sumber, 'online') <> 'kandang'), 'kandang', count(*) filter (where o.sumber = 'kandang'))
      from pesanan o where o.status = 'lunas' and o.lunas_at >= a and o.lunas_at < b),
    'per_produk', coalesce((select jsonb_agg(x order by (x->>'omzet')::numeric desc) from (
        select jsonb_build_object('kode', o.produk_kode, 'nama', coalesce(pr.nama, o.produk_kode), 'kategori', pr.kategori,
          'pesanan', count(*), 'ekor', sum(coalesce(o.jumlah, 1)), 'omzet', sum(coalesce(o.harga_final, o.harga, 0))) x
        from pesanan o left join produk pr on pr.kode = o.produk_kode
        where o.status = 'lunas' and o.lunas_at >= a and o.lunas_at < b group by o.produk_kode, pr.nama, pr.kategori) t), '[]'),
    'per_hari', coalesce((select jsonb_agg(jsonb_build_object('hari', to_char(h, 'DD/MM'), 'masuk', m) order by h) from (
        select (waktu at time zone 'Asia/Jakarta')::date h, sum(nominal) m from transaksi where waktu >= a and waktu < b group by 1) t), '[]'),
    'piutang', coalesce((select jsonb_agg(jsonb_build_object('pesanan', o.id, 'label', _plabel(o), 'nama', coalesce(o.nama, o.wa),
          'harga', o.harga, 'dp', coalesce((select sum(nominal) from transaksi t where t.pesanan_id = o.id and t.jenis = 'dp'), o.nominal_dp, 0),
          'sisa', o.harga - coalesce((select sum(nominal) from transaksi t where t.pesanan_id = o.id and t.jenis = 'dp'), o.nominal_dp, 0),
          'batas', to_char(o.batas_lunas at time zone 'Asia/Jakarta', 'DD/MM HH24.MI')) order by o.batas_lunas)
        from pesanan o where o.status in ('dp', 'cek_lunas')), '[]'),
    'hangus', (select jsonb_build_object('n', count(*), 'nominal', coalesce(sum(nominal_dp), 0)) from pesanan
        where status = 'hangus' and updated_at >= a and updated_at < b),
    'batal', (select count(*) from pesanan where status = 'batal' and updated_at >= a and updated_at < b),
    'transaksi', coalesce((select jsonb_agg(jsonb_build_object('waktu', to_char(t.waktu at time zone 'Asia/Jakarta', 'DD/MM HH24.MI'),
          'jenis', t.jenis, 'pesanan', t.pesanan_id, 'produk', t.produk_kode, 'jumlah', t.jumlah, 'nama', coalesce(t.nama, t.wa, '-'),
          'nominal', t.nominal, 'invoice', t.invoice_no, 'oleh', t.oleh) order by t.waktu)
        from transaksi t where t.waktu >= a and t.waktu < b), '[]'),
    'stok', coalesce((select jsonb_agg(jsonb_build_object('kode', kode, 'nama', nama, 'stok', stok) order by urutan, kode)
        from produk where stok is not null and (tampil or stok > 0)), '[]'));
end $$;

revoke execute on function _invoice(pesanan, text) from public, anon, authenticated;
revoke execute on function _dp_min(pesanan) from public, anon, authenticated;
revoke execute on function _wa62(text) from public, anon, authenticated;
