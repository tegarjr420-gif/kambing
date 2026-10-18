-- Patch 19/10/2026: katalog per kelas (produk + jumlah stok), Paket Aqiqah & Qurban,
-- Flash Sale, ulasan pembeli. Pesanan kini per produk + jumlah ekor, dan admin memakai
-- nomor pesanan (#12) untuk OK / TOLAK / lunas.

-- ---------- tabel ----------
create table if not exists produk (
  id bigint generated always as identity primary key,
  kode text unique not null,
  kategori text not null check (kategori in ('Kambing','Domba','Aqiqah','Qurban')),
  nama text not null,
  ras text,
  kelamin text,
  berat_min numeric,
  berat_max numeric,
  harga integer check (harga is null or harga > 0),
  stok integer check (stok is null or stok >= 0),
  isi_ekor integer not null default 1,
  opsi jsonb not null default '[]'::jsonb,
  flash_harga integer,
  flash_sampai timestamptz,
  layak_kurban boolean not null default false,
  foto text[] not null default '{}',
  deskripsi text,
  urutan integer not null default 100,
  tampil boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists ulasan (
  id bigint generated always as identity primary key,
  pesanan_id bigint references pesanan(id) on delete set null,
  produk_kode text references produk(kode) on update cascade on delete set null,
  chat_id text,
  nama text,
  bintang integer not null check (bintang between 1 and 5),
  komentar text,
  tampil boolean not null default true,
  created_at timestamptz not null default now()
);

alter table pesanan alter column kambing_kode drop not null;
alter table pesanan
  add column if not exists produk_kode text references produk(kode) on update cascade,
  add column if not exists jumlah integer not null default 1,
  add column if not exists opsi text,
  add column if not exists lunas_at timestamptz,
  add column if not exists ulasan_diminta timestamptz;
alter table riwayat_harga alter column kambing_kode drop not null;
alter table riwayat_harga add column if not exists produk_kode text;

alter table produk enable row level security;
alter table ulasan enable row level security;
revoke all on produk, ulasan from anon, authenticated;

create or replace function _sentuh_produk() returns trigger language plpgsql as $$
begin new.updated_at := now(); return new; end $$;
create trigger produk_sentuh before update on produk for each row execute function _sentuh_produk();

-- ---------- helper ----------
create or replace function _pkode(p text) returns text language sql immutable set search_path to 'public' as $$
  select case
    when p ~* '^\s*#?[a-z]+[\s-]*\d+\s*$'
      then upper((regexp_match(p, '([a-zA-Z]+)'))[1]) || '-' || lpad(((regexp_match(p, '(\d+)\s*$'))[1])::int::text, 2, '0')
    else upper(trim(coalesce(p,''))) end
$$;

create or replace function _flash_aktif(p produk) returns boolean language sql stable set search_path to 'public' as $$
  select p.flash_harga is not null and p.flash_sampai is not null and p.flash_sampai > now()
$$;

create or replace function _harga_aktif(p produk) returns integer language sql stable set search_path to 'public' as $$
  select case when _flash_aktif(p) then p.flash_harga else p.harga end
$$;

create or replace function _berat(p produk) returns text language sql immutable set search_path to 'public' as $$
  select case
    when p.berat_min is null and p.berat_max is null then null
    when p.berat_max is null or p.berat_min = p.berat_max then trim(to_char(coalesce(p.berat_min,p.berat_max),'FM999D9')) || ' kg'
    when p.berat_min is null then 'sampai ' || trim(to_char(p.berat_max,'FM999D9')) || ' kg'
    else trim(to_char(p.berat_min,'FM999D9')) || '–' || trim(to_char(p.berat_max,'FM999D9')) || ' kg' end
$$;

create or replace function _rp(n integer) returns text language sql immutable set search_path to 'public' as $$
  select case when n is null then 'harga tanya admin' else 'Rp' || replace(to_char(n, 'FM999,999,999,999'), ',', '.') end
$$;

create or replace function _prod_ringkas(p produk) returns jsonb language sql stable set search_path to 'public' as $$
  select jsonb_strip_nulls(jsonb_build_object(
    'kode', p.kode, 'kategori', p.kategori, 'nama', p.nama, 'ras', p.ras, 'kelamin', p.kelamin,
    'berat', _berat(p), 'harga_normal', p.harga,
    'harga_sekarang', _harga_aktif(p),
    'flash_sale', case when _flash_aktif(p) then jsonb_build_object('harga', p.flash_harga, 'sampai', to_char(p.flash_sampai at time zone 'Asia/Jakarta','DD/MM HH24:MI')) end,
    'stok_tersedia', p.stok,
    'isi_ekor_per_paket', case when p.kategori = 'Qurban' and p.isi_ekor > 1 then p.isi_ekor end,
    'pilihan_ekor', case when jsonb_array_length(p.opsi) > 0 then p.opsi end,
    'keterangan', p.deskripsi, 'layak_kurban', p.layak_kurban,
    'rating', (select round(avg(bintang)::numeric,1) from ulasan u where u.produk_kode = p.kode and u.tampil),
    'jumlah_ulasan', (select nullif(count(*),0) from ulasan u where u.produk_kode = p.kode and u.tampil)))
$$;

create or replace function _plabel(o pesanan) returns text language sql stable set search_path to 'public' as $$
  select '#' || o.id || ' ' || coalesce(o.produk_kode || ' ' || (select nama || coalesce(' ' || _berat(pr), '') from produk pr where pr.kode = o.produk_kode), o.kambing_kode, '')
    || case when o.opsi is not null then ' (' || o.opsi || ')' when o.jumlah > 1 then ' ×' || o.jumlah else '' end
$$;

create or replace function _stok_kembali(o pesanan) returns void language sql set search_path to 'public' as $$
  update produk set stok = stok + o.jumlah
  where kode = o.produk_kode and stok is not null and o.opsi is null;
$$;

-- ---------- tampilan publik untuk website ----------
create or replace view katalog_produk as
  select p.kode, p.kategori, p.nama, p.ras, p.kelamin, p.berat_min, p.berat_max, p.harga, p.stok, p.isi_ekor,
         p.opsi, p.layak_kurban, p.foto, p.deskripsi, p.urutan, p.updated_at,
         case when _flash_aktif(p) then p.flash_harga end as flash_harga,
         case when _flash_aktif(p) then p.flash_sampai end as flash_sampai,
         coalesce(u.rata, 0) as rating, coalesce(u.n, 0) as jumlah_ulasan
  from produk p
  left join (select produk_kode, round(avg(bintang)::numeric, 1) rata, count(*) n from ulasan where tampil group by 1) u
    on u.produk_kode = p.kode
  where p.tampil;

create or replace view ulasan_publik as
  select u.id, u.produk_kode, u.bintang, u.komentar, u.created_at,
         case when coalesce(trim(u.nama),'') = '' then 'Pembeli'
              else split_part(trim(u.nama), ' ', 1) || coalesce(' ' || nullif(left(split_part(trim(u.nama), ' ', 2), 1), '') || '.', '') end as nama
  from ulasan u where u.tampil;

grant select on katalog_produk, ulasan_publik to anon, authenticated;
