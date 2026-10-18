-- =========================================================
-- Database Barokah Farm (Supabase / Postgres)
-- Semua tabel PRIVAT (RLS aktif, anon tidak bisa baca/tulis tabel).
-- Website membaca VIEW publik: katalog, testimoni_publik.
-- Bot (n8n) memakai fungsi RPC yang dikunci dengan bot_key (tabel pengaturan).
-- =========================================================

create sequence if not exists kode_kambing_seq start 1;

create table if not exists pengaturan (
  k text primary key,
  v text not null
);

create table if not exists kambing (
  id            bigint generated always as identity primary key,
  kode          text unique not null default ('BF-' || lpad(nextval('kode_kambing_seq')::text, 2, '0')),
  jenis         text not null check (jenis in ('Kambing','Domba')),
  ras           text,
  kelamin       text check (kelamin in ('Jantan','Betina')),
  berat_kg      numeric(5,1),
  umur_bulan    int,
  harga         integer not null check (harga > 0),
  status        text not null default 'tersedia' check (status in ('tersedia','ditahan','dp','terjual')),
  layak_kurban  boolean not null default false,
  foto          text[] not null default '{}',
  catatan       text,
  dihapus       boolean not null default false,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create table if not exists pesanan (
  id              bigint generated always as identity primary key,
  kambing_kode    text not null references kambing(kode) on update cascade,
  chat_id         text not null,
  wa              text,
  nama            text,
  alamat_kirim    text,
  status          text not null default 'ditahan'
                  check (status in ('ditahan','menunggu_cek','dp','cek_lunas','lunas','batal','hangus')),
  harga           integer,
  nominal_dp      integer,
  bukti_url       text,
  bukti_lunas_url text,
  ditahan_sampai  timestamptz,
  bukti_at        timestamptz,
  dp_dikonfirmasi timestamptz,
  batas_lunas     timestamptz,
  diingatkan_h1   boolean not null default false,
  alasan          text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create unique index if not exists pesanan_satu_aktif_per_kambing
  on pesanan(kambing_kode) where status in ('ditahan','menunggu_cek','dp','cek_lunas');
create index if not exists pesanan_chat_idx on pesanan(chat_id);

create table if not exists riwayat_harga (
  id            bigint generated always as identity primary key,
  kambing_kode  text,
  harga_lama    integer,
  harga_baru    integer,
  alasan        text,
  created_at    timestamptz not null default now()
);

create table if not exists testimoni (
  id            bigint generated always as identity primary key,
  kambing_kode  text,
  foto_url      text not null,
  caption       text,
  kota          text,
  tanggal       date not null default current_date,
  tampil        boolean not null default true,
  created_at    timestamptz not null default now()
);

create table if not exists percakapan (
  chat_id      text primary key,
  wa           text,
  nama         text,
  mode         text not null default 'bot' check (mode in ('bot','manusia')),
  alasan_oper  text,
  terakhir     timestamptz not null default now()
);

create table if not exists pesan (
  id         bigint generated always as identity primary key,
  chat_id    text not null,
  arah       text not null check (arah in ('masuk','keluar')),
  teks       text,
  media_url  text,
  created_at timestamptz not null default now()
);
create index if not exists pesan_chat_idx on pesan(chat_id, created_at desc);

-- updated_at otomatis
create or replace function set_updated_at() returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;
drop trigger if exists t_kambing_upd on kambing;
create trigger t_kambing_upd before update on kambing for each row execute function set_updated_at();
drop trigger if exists t_pesanan_upd on pesanan;
create trigger t_pesanan_upd before update on pesanan for each row execute function set_updated_at();

-- RLS: semua tabel privat
alter table pengaturan    enable row level security;
alter table kambing       enable row level security;
alter table pesanan       enable row level security;
alter table riwayat_harga enable row level security;
alter table testimoni     enable row level security;
alter table percakapan    enable row level security;
alter table pesan         enable row level security;
revoke all on pengaturan, kambing, pesanan, riwayat_harga, testimoni, percakapan, pesan from anon, authenticated;

-- VIEW publik untuk website (tanpa data pembeli)
create or replace view katalog with (security_invoker = false) as
  select kode, jenis, ras, kelamin, berat_kg, umur_bulan, harga, status,
         layak_kurban, foto, catatan, updated_at
  from kambing
  where not dihapus and status in ('tersedia','ditahan','dp');
create or replace view testimoni_publik with (security_invoker = false) as
  select kambing_kode, foto_url, caption, kota, tanggal from testimoni where tampil;
grant select on katalog, testimoni_publik to anon;

-- ================= helper =================
create or replace function _cek(p_key text) returns void
language plpgsql security definer set search_path = public as $$
begin
  if p_key is null or p_key is distinct from (select v from pengaturan where k = 'bot_key') then
    raise exception 'akses ditolak' using errcode = '42501';
  end if;
end $$;

create or replace function _set(p_k text) returns text
language sql stable security definer set search_path = public as $$ select v from pengaturan where k = p_k $$;

-- 'bf7', 'BF 07', '7' -> 'BF-07'
create or replace function _kode(p text) returns text language sql immutable as $$
  select case when p ~ '\d' then 'BF-' || lpad(regexp_replace(p, '\D', '', 'g')::int::text, 2, '0') else upper(p) end
$$;

create or replace function _info() returns jsonb
language sql stable security definer set search_path = public as $$
  select jsonb_build_object(
    'rekening', _set('rekening'), 'dp_min', _set('dp_min')::int, 'batas_hari', _set('batas_hari')::int,
    'iduladha', coalesce(_set('iduladha'),'false')::boolean, 'link_katalog', _set('link_katalog'),
    'alamat', _set('alamat'), 'maps', _set('maps'), 'jam_buka', _set('jam_buka'),
    'admin_wa', _set('admin_wa'))
$$;

create or replace function _ringkas(k kambing) returns jsonb language sql immutable as $$
  select jsonb_build_object('kode', k.kode, 'jenis', k.jenis, 'ras', k.ras, 'kelamin', k.kelamin,
    'berat_kg', k.berat_kg, 'umur_bulan', k.umur_bulan, 'harga', k.harga, 'status', k.status,
    'layak_kurban', k.layak_kurban, 'ada_foto', cardinality(k.foto) > 0, 'catatan', k.catatan)
$$;

-- ================= pesan masuk =================
create or replace function bot_masuk(p_key text, p_chat text, p_wa text, p_nama text, p_teks text, p_media_url text default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare
  v_admin boolean; v_mode text; v_baru boolean := false; r jsonb;
begin
  perform _cek(p_key);
  -- daftar admin dengan PIN: "ADMIN 123456"
  if upper(trim(coalesce(p_teks,''))) = 'ADMIN ' || _set('admin_pin') then
    update pengaturan set v = v || ',' || p_chat where k = 'admin_chat' and not (p_chat = any(string_to_array(v, ',')));
    v_baru := true;
  end if;
  v_admin := (coalesce(p_wa,'') <> '' and p_wa = any(string_to_array(_set('admin_wa'), ',')))
          or p_chat = any(string_to_array(_set('admin_chat'), ','));

  insert into percakapan(chat_id, wa, nama) values (p_chat, nullif(p_wa,''), p_nama)
  on conflict (chat_id) do update set wa = coalesce(excluded.wa, percakapan.wa),
    nama = coalesce(excluded.nama, percakapan.nama), terakhir = now()
  returning mode into v_mode;

  insert into pesan(chat_id, arah, teks, media_url) values (p_chat, 'masuk', p_teks, p_media_url);

  select jsonb_build_object(
    'peran', case when v_admin then 'admin' else 'pembeli' end,
    'admin_baru', v_baru,
    'mode', v_mode,
    'nama', p_nama,
    'riwayat', coalesce((select jsonb_agg(jsonb_build_object('dari', case arah when 'masuk' then 'pembeli' else 'cs' end, 'teks', teks, 'waktu', to_char(created_at at time zone 'Asia/Jakarta','DD/MM HH24:MI')) order by created_at)
                 from (select * from pesan where chat_id = p_chat order by created_at desc limit 16) x), '[]'::jsonb),
    'pesanan', coalesce((select jsonb_agg(jsonb_build_object('kode', p.kambing_kode, 'status', p.status, 'harga', p.harga,
                 'ditahan_sampai', to_char(p.ditahan_sampai at time zone 'Asia/Jakarta','HH24:MI'),
                 'batas_lunas', to_char(p.batas_lunas at time zone 'Asia/Jakarta','DD/MM/YYYY HH24:MI'),
                 'nominal_dp', p.nominal_dp, 'alamat', p.alamat_kirim))
               from pesanan p where p.chat_id = p_chat and p.status in ('ditahan','menunggu_cek','dp','cek_lunas')), '[]'::jsonb),
    'stok', coalesce((select jsonb_agg(_ringkas(k) order by k.harga) from kambing k where not k.dihapus and k.status = 'tersedia'), '[]'::jsonb),
    'sedang_dipesan', coalesce((select jsonb_agg(k.kode order by k.kode) from kambing k where not k.dihapus and k.status in ('ditahan','dp')), '[]'::jsonb),
    'info', _info(),
    'sekarang', to_char(now() at time zone 'Asia/Jakarta','Day, DD/MM/YYYY HH24:MI')
  ) into r;
  return r;
end $$;

create or replace function bot_keluar(p_key text, p_chat text, p_teks text)
returns void language plpgsql security definer set search_path = public as $$
begin
  perform _cek(p_key);
  insert into pesan(chat_id, arah, teks) values (p_chat, 'keluar', p_teks);
end $$;

-- ================= aksi pembeli =================
create or replace function bot_tahan(p_key text, p_chat text, p_kode text, p_nama text default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare k kambing; v_kode text := _kode(p_kode); v_menit int := coalesce(_set('tahan_menit'),'60')::int;
begin
  perform _cek(p_key);
  select * into k from kambing where kode = v_kode and not dihapus for update;
  if not found then return jsonb_build_object('ok', false, 'alasan', 'Nomor ' || v_kode || ' tidak ada di katalog'); end if;
  if k.status <> 'tersedia' then
    if exists (select 1 from pesanan where kambing_kode = v_kode and chat_id = p_chat and status in ('ditahan','menunggu_cek','dp','cek_lunas')) then
      return jsonb_build_object('ok', true, 'sudah_milik_anda', true, 'kambing', _ringkas(k), 'info', _info());
    end if;
    return jsonb_build_object('ok', false, 'alasan', v_kode || ' sudah dipesan pembeli lain', 'stok_lain',
      (select jsonb_agg(_ringkas(x) order by abs(x.harga - k.harga)) from (select * from kambing where status='tersedia' and not dihapus and jenis = k.jenis order by abs(harga - k.harga) limit 3) x));
  end if;
  update kambing set status = 'ditahan' where kode = v_kode;
  insert into pesanan(kambing_kode, chat_id, wa, nama, harga, ditahan_sampai)
    values (v_kode, p_chat, (select wa from percakapan where chat_id = p_chat), coalesce(p_nama, (select nama from percakapan where chat_id = p_chat)), k.harga, now() + make_interval(mins => v_menit));
  return jsonb_build_object('ok', true, 'kambing', _ringkas(k), 'ditahan_menit', v_menit,
    'ditahan_sampai', to_char((now() + make_interval(mins => v_menit)) at time zone 'Asia/Jakarta','HH24:MI'), 'info', _info());
end $$;

create or replace function bot_bukti(p_key text, p_chat text, p_bukti_url text, p_nominal int default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare v_list jsonb; v_jenis text;
begin
  perform _cek(p_key);
  with u as (
    update pesanan set status = 'menunggu_cek', bukti_url = p_bukti_url, bukti_at = now(), nominal_dp = coalesce(p_nominal, nominal_dp)
    where chat_id = p_chat and status = 'ditahan' returning kambing_kode, harga)
  select jsonb_agg(jsonb_build_object('kode', kambing_kode, 'harga', harga)) into v_list from u;
  if v_list is not null then v_jenis := 'dp';
  else
    with u as (
      update pesanan set status = 'cek_lunas', bukti_lunas_url = p_bukti_url
      where chat_id = p_chat and status = 'dp' returning kambing_kode, harga, nominal_dp)
    select jsonb_agg(jsonb_build_object('kode', kambing_kode, 'harga', harga, 'nominal_dp', nominal_dp)) into v_list from u;
    if v_list is not null then v_jenis := 'pelunasan'; end if;
  end if;
  if v_list is null then return jsonb_build_object('ok', false, 'alasan', 'Tidak ada pesanan yang menunggu pembayaran'); end if;
  return jsonb_build_object('ok', true, 'jenis', v_jenis, 'pesanan', v_list,
    'nama', (select nama from percakapan where chat_id = p_chat), 'wa', (select wa from percakapan where chat_id = p_chat));
end $$;

create or replace function bot_batal(p_key text, p_chat text, p_kode text default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare v jsonb;
begin
  perform _cek(p_key);
  with u as (
    update pesanan set status = 'batal', alasan = 'dibatalkan pembeli'
    where chat_id = p_chat and status = 'ditahan' and (p_kode is null or kambing_kode = _kode(p_kode))
    returning kambing_kode)
  , k as (update kambing set status = 'tersedia' where kode in (select kambing_kode from u) returning kode)
  select jsonb_agg(kode) into v from k;
  if v is null then
    return jsonb_build_object('ok', false, 'alasan', 'Tidak ada pesanan yang bisa dibatalkan lewat bot (yang sudah DP harus lewat admin)');
  end if;
  return jsonb_build_object('ok', true, 'dibatalkan', v);
end $$;

create or replace function bot_alamat(p_key text, p_chat text, p_alamat text)
returns jsonb language plpgsql security definer set search_path = public as $$
declare n int;
begin
  perform _cek(p_key);
  update pesanan set alamat_kirim = p_alamat where chat_id = p_chat and status in ('ditahan','menunggu_cek','dp','cek_lunas');
  get diagnostics n = row_count;
  return jsonb_build_object('ok', n > 0, 'diperbarui', n);
end $$;

create or replace function bot_oper(p_key text, p_chat text, p_alasan text)
returns jsonb language plpgsql security definer set search_path = public as $$
begin
  perform _cek(p_key);
  update percakapan set mode = 'manusia', alasan_oper = p_alasan where chat_id = p_chat;
  return jsonb_build_object('ok', true, 'wa', (select wa from percakapan where chat_id = p_chat),
    'nama', (select nama from percakapan where chat_id = p_chat), 'alasan', p_alasan);
end $$;

-- ================= perintah admin =================
create or replace function admin_aksi(p_key text, p_aksi jsonb)
returns jsonb language plpgsql security definer set search_path = public as $$
declare
  a text := p_aksi->>'aksi';
  kodes text[];
  v_notif jsonb := '[]'::jsonb;
  v_hasil text := '';
  r record; k kambing; n int; v_kode text; v_umur int; v_jenis text;
  v_batas int := coalesce(_set('batas_hari'),'3')::int;
begin
  perform _cek(p_key);
  select coalesce(array_agg(_kode(x)), '{}') into kodes
    from jsonb_array_elements_text(case when jsonb_typeof(p_aksi->'kode') = 'array' then p_aksi->'kode'
                                        when p_aksi ? 'kode' then jsonb_build_array(p_aksi->>'kode') else '[]'::jsonb end) x;

  if a = 'konfirmasi_dp' then
    for r in update pesanan set status = 'dp', dp_dikonfirmasi = now(), batas_lunas = now() + make_interval(days => v_batas),
               nominal_dp = coalesce((p_aksi->>'nominal')::int, nominal_dp)
             where kambing_kode = any(kodes) and status in ('menunggu_cek','ditahan') returning * loop
      update kambing set status = 'dp' where kode = r.kambing_kode;
      v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'dp_dikonfirmasi',
        'data', jsonb_build_object('kode', r.kambing_kode, 'harga', r.harga, 'nominal_dp', r.nominal_dp,
          'batas_lunas', to_char(r.batas_lunas at time zone 'Asia/Jakarta','DD/MM/YYYY HH24:MI'),
          'sisa', r.harga - coalesce(r.nominal_dp, 0)));
      v_hasil := v_hasil || r.kambing_kode || ' DP dikonfirmasi, batas lunas ' || to_char(r.batas_lunas at time zone 'Asia/Jakarta','DD/MM HH24:MI') || E'\n';
    end loop;

  elsif a = 'tolak_dp' then
    for r in update pesanan set status = 'batal', alasan = coalesce(p_aksi->>'alasan', 'ditolak admin')
             where kambing_kode = any(kodes) and status in ('menunggu_cek','ditahan','cek_lunas') returning * loop
      update kambing set status = 'tersedia' where kode = r.kambing_kode;
      v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'dp_ditolak',
        'data', jsonb_build_object('kode', r.kambing_kode, 'alasan', p_aksi->>'alasan'));
      v_hasil := v_hasil || r.kambing_kode || ' ditolak, kembali tersedia' || E'\n';
    end loop;

  elsif a = 'lunas' then
    for r in update pesanan set status = 'lunas' where kambing_kode = any(kodes) and status in ('dp','cek_lunas','menunggu_cek') returning * loop
      update kambing set status = 'terjual' where kode = r.kambing_kode;
      v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'lunas',
        'data', jsonb_build_object('kode', r.kambing_kode, 'alamat', r.alamat_kirim));
      v_hasil := v_hasil || r.kambing_kode || ' LUNAS, ditandai terjual' || E'\n';
    end loop;

  elsif a = 'terjual' then
    for r in update pesanan set status = 'batal', alasan = 'terjual langsung di kandang'
             where kambing_kode = any(kodes) and status in ('ditahan','menunggu_cek') returning * loop
      v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'kambing_terjual_lain', 'data', jsonb_build_object('kode', r.kambing_kode));
    end loop;
    update kambing set status = 'terjual' where kode = any(kodes);
    get diagnostics n = row_count;
    v_hasil := n || ' ekor ditandai terjual: ' || array_to_string(kodes, ', ');

  elsif a = 'tersedia' then
    update kambing set status = 'tersedia', dihapus = false where kode = any(kodes);
    get diagnostics n = row_count;
    v_hasil := n || ' ekor dibuka lagi: ' || array_to_string(kodes, ', ');

  elsif a = 'hapus' then
    update kambing set dihapus = true where kode = any(kodes);
    get diagnostics n = row_count;
    v_hasil := n || ' ekor disembunyikan dari katalog: ' || array_to_string(kodes, ', ');

  elsif a = 'tambah' then
    v_jenis := coalesce(initcap(p_aksi->>'jenis'), 'Kambing');
    v_umur := nullif(p_aksi->>'umur_bulan','')::int;
    insert into kambing(jenis, ras, kelamin, berat_kg, umur_bulan, harga, layak_kurban, foto, catatan)
    values (v_jenis, initcap(p_aksi->>'ras'), initcap(p_aksi->>'kelamin'), nullif(p_aksi->>'berat_kg','')::numeric,
            v_umur, (p_aksi->>'harga')::int,
            coalesce((p_aksi->>'layak_kurban')::boolean, coalesce(v_umur,0) >= 12),
            case when coalesce(p_aksi->>'foto','') <> '' then array[p_aksi->>'foto'] else '{}' end,
            p_aksi->>'catatan')
    returning * into k;
    v_hasil := 'Ditambahkan ' || k.kode || ': ' || k.jenis || coalesce(' ' || k.ras, '') || coalesce(' ' || lower(k.kelamin), '')
      || coalesce(', ' || k.berat_kg || ' kg', '') || ', Rp' || to_char(k.harga, 'FM999G999G999') ||
      case when cardinality(k.foto) = 0 then E'\n(belum ada foto: kirim foto dengan keterangan "foto ' || k.kode || '")' else '' end;

  elsif a = 'ubah' then
    v_kode := kodes[1];
    select * into k from kambing where kode = v_kode;
    if not found then return jsonb_build_object('ok', false, 'ringkasan', 'Nomor ' || v_kode || ' tidak ditemukan'); end if;
    if p_aksi ? 'harga' then
      insert into riwayat_harga(kambing_kode, harga_lama, harga_baru, alasan) values (v_kode, k.harga, (p_aksi->>'harga')::int, 'ubah satu');
    end if;
    update kambing set
      harga = coalesce((p_aksi->>'harga')::int, harga),
      berat_kg = coalesce(nullif(p_aksi->>'berat_kg','')::numeric, berat_kg),
      umur_bulan = coalesce(nullif(p_aksi->>'umur_bulan','')::int, umur_bulan),
      ras = coalesce(initcap(p_aksi->>'ras'), ras),
      kelamin = coalesce(initcap(p_aksi->>'kelamin'), kelamin),
      jenis = coalesce(initcap(p_aksi->>'jenis'), jenis),
      catatan = coalesce(p_aksi->>'catatan', catatan),
      layak_kurban = coalesce((p_aksi->>'layak_kurban')::boolean, layak_kurban)
    where kode = v_kode returning * into k;
    v_hasil := 'Diperbarui ' || k.kode || ': ' || k.jenis || coalesce(' ' || k.ras,'') || ', ' || coalesce(k.berat_kg::text,'-') || ' kg, Rp' || to_char(k.harga, 'FM999G999G999');

  elsif a = 'foto' then
    update kambing set foto = foto || array[p_aksi->>'foto'] where kode = kodes[1] returning * into k;
    v_hasil := case when k.kode is null then 'Nomor ' || kodes[1] || ' tidak ditemukan' else 'Foto ditambahkan ke ' || k.kode || ' (' || cardinality(k.foto) || ' foto)' end;

  elsif a = 'harga_rata' then
    n := (p_aksi->>'selisih')::int;
    insert into riwayat_harga(kambing_kode, harga_lama, harga_baru, alasan)
      select kode, harga, harga + n, case when n >= 0 then 'naik rata ' else 'turun rata ' end || abs(n)
      from kambing where status = 'tersedia' and not dihapus;
    update kambing set harga = harga + n where status = 'tersedia' and not dihapus and harga + n > 0;
    get diagnostics n = row_count;
    v_hasil := 'Harga ' || n || ' ekor yang tersedia ' || case when (p_aksi->>'selisih')::int >= 0 then 'naik' else 'turun' end
      || ' Rp' || to_char(abs((p_aksi->>'selisih')::int), 'FM999G999G999') || '. Kambing yang sudah dipesan/DP tidak berubah.';

  elsif a = 'testimoni' then
    insert into testimoni(kambing_kode, foto_url, caption, kota) values (kodes[1], p_aksi->>'foto', p_aksi->>'caption', p_aksi->>'kota');
    v_hasil := 'Testimoni ditambahkan ke katalog';

  elsif a in ('ambil_alih', 'kembali_bot') then
    update percakapan set mode = case a when 'ambil_alih' then 'manusia' else 'bot' end
      where wa = regexp_replace(regexp_replace(p_aksi->>'wa', '\D', '', 'g'), '^0', '62') or chat_id = p_aksi->>'wa';
    get diagnostics n = row_count;
    v_hasil := case when n = 0 then 'Nomor tidak ditemukan di percakapan' when a = 'ambil_alih' then 'Bot berhenti membalas ' || (p_aksi->>'wa') || '. Silakan balas manual.' else 'Bot aktif lagi untuk ' || (p_aksi->>'wa') end;

  elsif a = 'iduladha' then
    update pengaturan set v = (p_aksi->>'aktif') where k = 'iduladha';
    v_hasil := 'Mode Iduladha ' || case when (p_aksi->>'aktif')::boolean then 'AKTIF' else 'mati' end;

  elsif a in ('stok', 'laporan') then
    select string_agg(kode || ' ' || jenis || coalesce(' ' || ras,'') || ' ' || coalesce(berat_kg::text,'-') || 'kg Rp' || to_char(harga,'FM999G999G999') || ' [' || status || ']', E'\n' order by kode)
      into v_hasil from kambing where not dihapus and status <> 'terjual';
    v_hasil := coalesce(v_hasil, 'Belum ada stok.') || E'\n\nMenunggu cek transfer: ' ||
      coalesce((select string_agg(kambing_kode, ', ') from pesanan where status in ('menunggu_cek','cek_lunas')), '-') ||
      E'\nSudah DP: ' || coalesce((select string_agg(kambing_kode || ' (lunas s/d ' || to_char(batas_lunas at time zone 'Asia/Jakarta','DD/MM HH24:MI') || ')', ', ') from pesanan where status = 'dp'), '-');

  else
    return jsonb_build_object('ok', false, 'ringkasan', 'Perintah tidak dikenali');
  end if;

  return jsonb_build_object('ok', true, 'ringkasan', coalesce(nullif(v_hasil, ''), 'Tidak ada yang berubah (cek nomor kambing/status).'), 'notif', v_notif);
end $$;

-- ================= jadwal (dipanggil tiap 5 menit) =================
create or replace function jadwal_cek(p_key text)
returns jsonb language plpgsql security definer set search_path = public as $$
declare r record; v_notif jsonb := '[]'::jsonb; v_admin text := '';
begin
  perform _cek(p_key);
  -- 1. tahan 60 menit habis tanpa bukti
  for r in update pesanan set status = 'batal', alasan = 'waktu tahan habis'
           where status = 'ditahan' and ditahan_sampai < now() returning * loop
    update kambing set status = 'tersedia' where kode = r.kambing_kode and status = 'ditahan';
    v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'tahan_habis', 'data', jsonb_build_object('kode', r.kambing_kode));
  end loop;
  -- 2. pengingat H-1
  for r in update pesanan set diingatkan_h1 = true
           where status = 'dp' and not diingatkan_h1 and batas_lunas - now() <= interval '24 hours' and batas_lunas > now() returning * loop
    v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'pengingat_h1', 'data', jsonb_build_object(
      'kode', r.kambing_kode, 'batas_lunas', to_char(r.batas_lunas at time zone 'Asia/Jakarta','DD/MM/YYYY HH24:MI'),
      'sisa', r.harga - coalesce(r.nominal_dp,0)));
  end loop;
  -- 3. lewat batas: DP hangus, kambing kembali dijual
  for r in update pesanan set status = 'hangus', alasan = 'lewat batas pelunasan'
           where status = 'dp' and batas_lunas < now() returning * loop
    update kambing set status = 'tersedia' where kode = r.kambing_kode and status = 'dp';
    v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'dp_hangus', 'data', jsonb_build_object(
      'kode', r.kambing_kode, 'nominal_dp', r.nominal_dp));
    v_admin := v_admin || r.kambing_kode || ' DP hangus (' || coalesce(r.nama, r.wa, r.chat_id) || '), kembali tersedia di katalog' || E'\n';
  end loop;
  return jsonb_build_object('notif', v_notif, 'admin', nullif(v_admin, ''));
end $$;

-- hanya fungsi bot_* / admin_aksi / jadwal_cek yang boleh dipanggil dari luar (tetap butuh bot_key)
revoke execute on function _cek(text), _set(text), _info(), set_updated_at() from public, anon, authenticated;
