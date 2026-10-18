-- =========================================================
-- Skema database Barokah Farm (Supabase / Postgres)
-- Tabel inti bersifat privat (RLS aktif, tanpa akses anon).
-- Website hanya membaca VIEW publik: katalog & testimoni_publik.
-- =========================================================

create table if not exists kambing (
  id            bigint generated always as identity primary key,
  kode          text unique not null,                 -- BF-01, BF-02, ...
  jenis         text not null check (jenis in ('Kambing','Domba')),
  ras           text,
  kelamin       text check (kelamin in ('Jantan','Betina')),
  berat_kg      numeric(5,1),
  umur_bulan    int,
  harga         integer not null check (harga > 0),
  status        text not null default 'tersedia'
                check (status in ('tersedia','ditahan','dp','terjual')),
  layak_kurban  boolean not null default false,
  foto          text[] not null default '{}',         -- URL foto (Supabase Storage)
  catatan       text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create table if not exists pesanan (
  id              bigint generated always as identity primary key,
  kambing_kode    text not null references kambing(kode),
  pembeli_wa      text not null,
  pembeli_nama    text,
  alamat_kirim    text,
  status          text not null default 'ditahan'
                  check (status in ('ditahan','menunggu_cek','dp','lunas','batal','hangus')),
  nominal_dp      integer,
  bukti_url       text,
  ditahan_sampai  timestamptz,          -- tahan 60 menit menunggu bukti DP
  dp_dikonfirmasi timestamptz,
  batas_lunas     timestamptz,          -- dp_dikonfirmasi + 3 hari
  diingatkan_h1   boolean not null default false,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create table if not exists riwayat_harga (
  id          bigint generated always as identity primary key,
  kambing_kode text references kambing(kode),
  harga_lama  integer, harga_baru integer,
  alasan      text,                      -- mis. "naik rata 100rb"
  oleh        text,
  created_at  timestamptz not null default now()
);

create table if not exists testimoni (
  id           bigint generated always as identity primary key,
  kambing_kode text,
  foto_url     text not null,            -- foto yang wajahnya SUDAH diblur
  caption      text,
  kota         text,
  tanggal      date not null default current_date,
  tampil       boolean not null default true,
  created_at   timestamptz not null default now()
);

create table if not exists percakapan (
  wa           text primary key,          -- nomor pembeli
  mode         text not null default 'bot' check (mode in ('bot','manusia')),
  ringkasan    text,
  terakhir     timestamptz not null default now()
);

-- updated_at otomatis
create or replace function set_updated_at() returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;
drop trigger if exists t_kambing_upd on kambing;
create trigger t_kambing_upd before update on kambing for each row execute function set_updated_at();
drop trigger if exists t_pesanan_upd on pesanan;
create trigger t_pesanan_upd before update on pesanan for each row execute function set_updated_at();

-- RLS: semua tabel privat
alter table kambing       enable row level security;
alter table pesanan       enable row level security;
alter table riwayat_harga enable row level security;
alter table testimoni     enable row level security;
alter table percakapan    enable row level security;

-- VIEW publik untuk website (tanpa data pembeli)
create or replace view katalog as
  select kode, jenis, ras, kelamin, berat_kg, umur_bulan, harga, status,
         layak_kurban, foto, catatan, updated_at
  from kambing
  where status in ('tersedia','ditahan','dp');

create or replace view testimoni_publik as
  select kambing_kode, foto_url, caption, kota, tanggal
  from testimoni where tampil;

grant select on katalog, testimoni_publik to anon;

-- Naik/turun harga rata untuk semua kambing yang belum terjual
create or replace function ubah_harga_rata(selisih integer, oleh text default 'admin')
returns integer language plpgsql security definer as $$
declare n integer;
begin
  insert into riwayat_harga(kambing_kode, harga_lama, harga_baru, alasan, oleh)
    select kode, harga, harga + selisih,
           case when selisih >= 0 then 'naik rata ' else 'turun rata ' end || abs(selisih), oleh
    from kambing where status <> 'terjual';
  update kambing set harga = harga + selisih where status <> 'terjual';
  get diagnostics n = row_count;
  return n;
end $$;
revoke execute on function ubah_harga_rata(integer, text) from anon, authenticated;
