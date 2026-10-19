-- Snapshot skema LIVE Supabase Barokah Farm, 19/10/2026 (setelah semua patch hari ini).
-- Isi: tabel, view publik, dan semua fungsi (bot_*, admin_*, jadwal_cek, rekap_pagi,
-- alarm_cek, bot_cek, catat_kunjungan, hak akses staf di bot_masuk, ringkasan pesanan).
-- Pakai file ini untuk membangun ulang database dari nol; patch-*.sql adalah riwayatnya.
-- Nilai rahasia (bot_key, PIN admin/staf) TIDAK ada di sini; disimpan di tabel pengaturan.

-- tabel galeri
create table if not exists galeri (
  id bigint generated always as identity not null,
  foto_url text not null,
  caption text,
  tampil boolean not null default true,
  created_at timestamp with time zone not null default now(),
  constraint galeri_pkey PRIMARY KEY (id)
);

-- tabel kambing
create table if not exists kambing (
  id bigint generated always as identity not null,
  kode text not null default ('BF-'::text || lpad((nextval('kode_kambing_seq'::regclass))::text, 2, '0'::text)),
  jenis text not null,
  ras text,
  kelamin text,
  berat_kg numeric(5,1),
  umur_bulan integer,
  harga integer not null,
  status text not null default 'tersedia'::text,
  layak_kurban boolean not null default false,
  foto text[] not null default '{}'::text[],
  catatan text,
  dihapus boolean not null default false,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  constraint kambing_harga_check CHECK ((harga > 0)),
  constraint kambing_jenis_check CHECK ((jenis = ANY (ARRAY['Kambing'::text, 'Domba'::text]))),
  constraint kambing_kelamin_check CHECK ((kelamin = ANY (ARRAY['Jantan'::text, 'Betina'::text]))),
  constraint kambing_kode_key UNIQUE (kode),
  constraint kambing_pkey PRIMARY KEY (id),
  constraint kambing_status_check CHECK ((status = ANY (ARRAY['tersedia'::text, 'ditahan'::text, 'dp'::text, 'terjual'::text])))
);

-- tabel kunjungan
create table if not exists kunjungan (
  hari date not null default ((now() AT TIME ZONE 'Asia/Jakarta'::text))::date,
  jenis text not null,
  kode text not null default ''::text,
  jumlah integer not null default 0,
  constraint kunjungan_pkey PRIMARY KEY (hari, jenis, kode)
);

-- tabel pengaturan
create table if not exists pengaturan (
  k text not null,
  v text not null,
  constraint pengaturan_pkey PRIMARY KEY (k)
);

-- tabel percakapan
create table if not exists percakapan (
  chat_id text not null,
  wa text,
  nama text,
  mode text not null default 'bot'::text,
  alasan_oper text,
  terakhir timestamp with time zone not null default now(),
  aksi_tertunda jsonb,
  constraint percakapan_mode_check CHECK ((mode = ANY (ARRAY['bot'::text, 'manusia'::text]))),
  constraint percakapan_pkey PRIMARY KEY (chat_id)
);

-- tabel pesan
create table if not exists pesan (
  id bigint generated always as identity not null,
  chat_id text not null,
  arah text not null,
  teks text,
  media_url text,
  created_at timestamp with time zone not null default now(),
  constraint pesan_arah_check CHECK ((arah = ANY (ARRAY['masuk'::text, 'keluar'::text]))),
  constraint pesan_pkey PRIMARY KEY (id)
);

-- tabel pesanan
create table if not exists pesanan (
  id bigint generated always as identity not null,
  kambing_kode text,
  chat_id text not null,
  wa text,
  nama text,
  alamat_kirim text,
  status text not null default 'ditahan'::text,
  harga integer,
  nominal_dp integer,
  bukti_url text,
  bukti_lunas_url text,
  ditahan_sampai timestamp with time zone,
  bukti_at timestamp with time zone,
  dp_dikonfirmasi timestamp with time zone,
  batas_lunas timestamp with time zone,
  diingatkan_h1 boolean not null default false,
  alasan text,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  bukti_lunas_at timestamp with time zone,
  tunggu_dikabari timestamp with time zone,
  produk_kode text,
  jumlah integer not null default 1,
  opsi text,
  lunas_at timestamp with time zone,
  ulasan_diminta timestamp with time zone,
  constraint pesanan_kambing_kode_fkey FOREIGN KEY (kambing_kode) REFERENCES kambing(kode) ON UPDATE CASCADE,
  constraint pesanan_pkey PRIMARY KEY (id),
  constraint pesanan_produk_kode_fkey FOREIGN KEY (produk_kode) REFERENCES produk(kode) ON UPDATE CASCADE,
  constraint pesanan_status_check CHECK ((status = ANY (ARRAY['ditahan'::text, 'menunggu_cek'::text, 'dp'::text, 'cek_lunas'::text, 'lunas'::text, 'batal'::text, 'hangus'::text])))
);

-- tabel produk
create table if not exists produk (
  id bigint generated always as identity not null,
  kode text not null,
  kategori text not null,
  nama text not null,
  ras text,
  kelamin text,
  berat_min numeric,
  berat_max numeric,
  harga integer,
  stok integer,
  isi_ekor integer not null default 1,
  opsi jsonb not null default '[]'::jsonb,
  flash_harga integer,
  flash_sampai timestamp with time zone,
  layak_kurban boolean not null default false,
  foto text[] not null default '{}'::text[],
  deskripsi text,
  urutan integer not null default 100,
  tampil boolean not null default true,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  constraint produk_harga_check CHECK (((harga IS NULL) OR (harga > 0))),
  constraint produk_kategori_check CHECK ((kategori = ANY (ARRAY['Kambing'::text, 'Domba'::text, 'Aqiqah'::text, 'Qurban'::text]))),
  constraint produk_kode_key UNIQUE (kode),
  constraint produk_pkey PRIMARY KEY (id),
  constraint produk_stok_check CHECK (((stok IS NULL) OR (stok >= 0)))
);

-- tabel riwayat_harga
create table if not exists riwayat_harga (
  id bigint generated always as identity not null,
  kambing_kode text,
  harga_lama integer,
  harga_baru integer,
  alasan text,
  created_at timestamp with time zone not null default now(),
  produk_kode text,
  constraint riwayat_harga_pkey PRIMARY KEY (id)
);

-- tabel testimoni
create table if not exists testimoni (
  id bigint generated always as identity not null,
  kambing_kode text,
  foto_url text not null,
  caption text,
  kota text,
  tanggal date not null default CURRENT_DATE,
  tampil boolean not null default true,
  created_at timestamp with time zone not null default now(),
  constraint testimoni_pkey PRIMARY KEY (id)
);

-- tabel ulasan
create table if not exists ulasan (
  id bigint generated always as identity not null,
  pesanan_id bigint,
  produk_kode text,
  chat_id text,
  nama text,
  bintang integer not null,
  komentar text,
  tampil boolean not null default true,
  created_at timestamp with time zone not null default now(),
  constraint ulasan_bintang_check CHECK (((bintang >= 1) AND (bintang <= 5))),
  constraint ulasan_pesanan_id_fkey FOREIGN KEY (pesanan_id) REFERENCES pesanan(id) ON DELETE SET NULL,
  constraint ulasan_pkey PRIMARY KEY (id),
  constraint ulasan_produk_kode_fkey FOREIGN KEY (produk_kode) REFERENCES produk(kode) ON UPDATE CASCADE ON DELETE SET NULL
);

create or replace view galeri_publik as
 SELECT id,
    foto_url,
    caption,
    created_at
   FROM galeri
  WHERE tampil;

create or replace view katalog as
 SELECT kode,
    jenis,
    ras,
    kelamin,
    berat_kg,
    umur_bulan,
    harga,
    status,
    layak_kurban,
    foto,
    catatan,
    updated_at
   FROM kambing
  WHERE NOT dihapus AND (status = ANY (ARRAY['tersedia'::text, 'ditahan'::text, 'dp'::text]));

create or replace view katalog_produk as
 SELECT p.kode,
    p.kategori,
    p.nama,
    p.ras,
    p.kelamin,
    p.berat_min,
    p.berat_max,
    p.harga,
    p.stok,
    p.isi_ekor,
    p.opsi,
    p.layak_kurban,
    p.foto,
    p.deskripsi,
    p.urutan,
    p.updated_at,
        CASE
            WHEN _flash_aktif(p.*) THEN p.flash_harga
            ELSE NULL::integer
        END AS flash_harga,
        CASE
            WHEN _flash_aktif(p.*) THEN p.flash_sampai
            ELSE NULL::timestamp with time zone
        END AS flash_sampai,
    COALESCE(u.rata, 0::numeric) AS rating,
    COALESCE(u.n, 0::bigint) AS jumlah_ulasan
   FROM produk p
     LEFT JOIN ( SELECT ulasan.produk_kode,
            round(avg(ulasan.bintang), 1) AS rata,
            count(*) AS n
           FROM ulasan
          WHERE ulasan.tampil
          GROUP BY ulasan.produk_kode) u ON u.produk_kode = p.kode
  WHERE p.tampil;

create or replace view pengaturan_publik as
 SELECT COALESCE(( SELECT pengaturan.v
           FROM pengaturan
          WHERE pengaturan.k = 'iduladha'::text), 'false'::text)::boolean AS iduladha;

create or replace view testimoni_publik as
 SELECT kambing_kode,
    foto_url,
    caption,
    kota,
    tanggal
   FROM testimoni
  WHERE tampil;

create or replace view ulasan_publik as
 SELECT id,
    produk_kode,
    bintang,
    komentar,
    created_at,
        CASE
            WHEN COALESCE(TRIM(BOTH FROM nama), ''::text) = ''::text THEN 'Pembeli'::text
            ELSE split_part(TRIM(BOTH FROM nama), ' '::text, 1) || COALESCE((' '::text || NULLIF("left"(split_part(TRIM(BOTH FROM nama), ' '::text, 2), 1), ''::text)) || '.'::text, ''::text)
        END AS nama
   FROM ulasan u
  WHERE tampil;

CREATE OR REPLACE FUNCTION public._berat(p produk)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
 SET search_path TO 'public'
AS $function$
  select case
    when p.berat_min is null and p.berat_max is null then null
    when p.berat_max is null or p.berat_min = p.berat_max then rtrim(to_char(coalesce(p.berat_min,p.berat_max),'FM999D9'), '.,') || ' kg'
    when p.berat_min is null then 'sampai ' || rtrim(to_char(p.berat_max,'FM999D9'), '.,') || ' kg'
    else rtrim(to_char(p.berat_min,'FM999D9'), '.,') || '–' || rtrim(to_char(p.berat_max,'FM999D9'), '.,') || ' kg' end
$function$
;

CREATE OR REPLACE FUNCTION public._cek(p_key text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  if p_key is null or p_key is distinct from (select v from pengaturan where k = 'bot_key') then
    raise exception 'akses ditolak' using errcode = '42501';
  end if;
end $function$
;

CREATE OR REPLACE FUNCTION public._flash_aktif(p produk)
 RETURNS boolean
 LANGUAGE sql
 STABLE
 SET search_path TO 'public'
AS $function$
  select p.flash_harga is not null and p.flash_sampai is not null and p.flash_sampai > now()
$function$
;

CREATE OR REPLACE FUNCTION public._harga_aktif(p produk)
 RETURNS integer
 LANGUAGE sql
 STABLE
 SET search_path TO 'public'
AS $function$
  select case when _flash_aktif(p) then p.flash_harga else p.harga end
$function$
;

CREATE OR REPLACE FUNCTION public._info()
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
  select jsonb_build_object(
    'rekening', _set('rekening'), 'dp_min', _set('dp_min')::int, 'batas_hari', _set('batas_hari')::int,
    'kebijakan_dp', _set('kebijakan_dp'), 'profil_toko', _set('profil'), 'media_sosial', _set('sosial'),
    'iduladha', coalesce(_set('iduladha'),'false')::boolean, 'link_katalog', _set('link_katalog'),
    'alamat', _set('alamat'), 'maps', _set('maps'), 'jam_buka', _set('jam_buka'), 'ongkir', _set('ongkir'),
    'admin_wa', _set('admin_wa'))
$function$
;

CREATE OR REPLACE FUNCTION public._kode(p text)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
 SET search_path TO 'public'
AS $function$
  select case when p ~ '\d' then 'BF-' || lpad(regexp_replace(p, '\D', '', 'g')::int::text, 2, '0') else upper(p) end
$function$
;

CREATE OR REPLACE FUNCTION public._penerima(p_wa_key text, p_chat_key text)
 RETURNS jsonb
 LANGUAGE sql
 STABLE
 SET search_path TO 'public'
AS $function$
  select coalesce(jsonb_agg(distinct x), '[]'::jsonb) from (
    select trim(w) || '@c.us' x from unnest(string_to_array(coalesce(_set(p_wa_key),''), ',')) w where trim(w) <> ''
    union select trim(c) from unnest(string_to_array(coalesce(_set(p_chat_key),''), ',')) c where trim(c) <> ''
  ) s
$function$
;

CREATE OR REPLACE FUNCTION public._pkode(p text)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
 SET search_path TO 'public'
AS $function$
  select case
    when p ~* '^\s*#?[a-z]+[\s-]*\d+\s*$'
      then upper((regexp_match(p, '([a-zA-Z]+)'))[1]) || '-' || lpad(((regexp_match(p, '(\d+)\s*$'))[1])::int::text, 2, '0')
    else upper(trim(coalesce(p,''))) end
$function$
;

CREATE OR REPLACE FUNCTION public._plabel(o pesanan)
 RETURNS text
 LANGUAGE sql
 STABLE
 SET search_path TO 'public'
AS $function$
  select '#' || o.id || ' ' || coalesce(o.produk_kode || ' ' || (select nama || coalesce(' ' || _berat(pr), '') from produk pr where pr.kode = o.produk_kode), o.kambing_kode, '')
    || case when o.opsi is not null then ' (' || o.opsi || ')' when o.jumlah > 1 then ' ×' || o.jumlah else '' end
$function$
;

CREATE OR REPLACE FUNCTION public._prod_ringkas(p produk)
 RETURNS jsonb
 LANGUAGE sql
 STABLE
 SET search_path TO 'public'
AS $function$
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
$function$
;

CREATE OR REPLACE FUNCTION public._rapikan(t text)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
 SET search_path TO 'public'
AS $function$
  select regexp_replace(
           regexp_replace(
             regexp_replace(t, '(\d),(\d{3})', '\1.\2', 'g'),
           '(\d),(\d{3})', '\1.\2', 'g'),
         '(\d+)\.0(kg| kg)', '\1\2', 'g')
$function$
;

CREATE OR REPLACE FUNCTION public._ringkas(k kambing)
 RETURNS jsonb
 LANGUAGE sql
 IMMUTABLE
 SET search_path TO 'public'
AS $function$
  select jsonb_build_object('kode', k.kode, 'jenis', k.jenis, 'ras', k.ras, 'kelamin', k.kelamin,
    'berat_kg', k.berat_kg, 'umur_bulan', k.umur_bulan, 'harga', k.harga, 'status', k.status,
    'layak_kurban', k.layak_kurban, 'ada_foto', cardinality(k.foto) > 0, 'catatan', k.catatan)
$function$
;

CREATE OR REPLACE FUNCTION public._ringkasan_pesanan(o pesanan)
 RETURNS text
 LANGUAGE sql
 STABLE
 SET search_path TO 'public'
AS $function$
  select '🧾 *Pesanan #' || o.id || '*' || E'\n'
    || coalesce(o.produk_kode || ' ' || (select nama || coalesce(' ' || _berat(pr), '') from produk pr where pr.kode = o.produk_kode), '')
    || case when o.opsi is not null then ' (' || o.opsi || ')' when o.jumlah > 1 then ' × ' || o.jumlah else '' end || E'\n'
    || 'Total: ' || _rp(o.harga) || E'\n'
    || 'DP minimal: ' || _rp(coalesce(_set('dp_min')::int,100000) * case when o.opsi is not null then o.jumlah else o.jumlah * coalesce((select isi_ekor from produk where kode = o.produk_kode),1) end) || E'\n'
    || 'Transfer ke: ' || _set('rekening') || E'\n'
    || 'Ditahan sampai: ' || to_char(o.ditahan_sampai at time zone 'Asia/Jakarta','HH24.MI') || ' WIB' || E'\n'
    || 'Kirim foto bukti transfer di chat ini. Cek status kapan saja: ketik *cek pesanan*'
$function$
;

CREATE OR REPLACE FUNCTION public._rp(n integer)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
 SET search_path TO 'public'
AS $function$
  select case when n is null then 'harga tanya admin' else 'Rp' || replace(to_char(n, 'FM999,999,999,999'), ',', '.') end
$function$
;

CREATE OR REPLACE FUNCTION public._sentuh_produk()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public'
AS $function$
begin new.updated_at := now(); return new; end $function$
;

CREATE OR REPLACE FUNCTION public._set(p_k text)
 RETURNS text
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $function$ select v from pengaturan where k = p_k $function$
;

CREATE OR REPLACE FUNCTION public._stok_kembali(o pesanan)
 RETURNS void
 LANGUAGE sql
 SET search_path TO 'public'
AS $function$
  update produk set stok = stok + o.jumlah
  where kode = o.produk_kode and stok is not null and o.opsi is null;
$function$
;

CREATE OR REPLACE FUNCTION public.admin_aksi(p_key text, p_aksi jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare
  a text := p_aksi->>'aksi';
  ids bigint[];
  v_notif jsonb := '[]'::jsonb;
  v_hasil text := '';
  r pesanan; p produk; n int; v_kode text; v_pref text; v_kat text; v_opsi jsonb; v_sampai timestamptz;
  v_batas int := coalesce(_set('batas_hari'),'3')::int;
begin
  perform _cek(p_key);
  select coalesce(array_agg(regexp_replace(x, '\D', '', 'g')::bigint) filter (where x ~ '\d'), '{}') into ids
    from jsonb_array_elements_text(case
      when jsonb_typeof(p_aksi->'pesanan') = 'array' then p_aksi->'pesanan'
      when jsonb_typeof(p_aksi->'pesanan') in ('number','string') then jsonb_build_array(p_aksi->>'pesanan')
      when jsonb_typeof(p_aksi->'kode') = 'array' then p_aksi->'kode'
      when jsonb_typeof(p_aksi->'kode') = 'string' then jsonb_build_array(p_aksi->>'kode') else '[]'::jsonb end) x;
  v_kode := _pkode(coalesce(nullif(p_aksi->>'produk',''), ''));
  if v_kode <> '' then select * into p from produk where kode = v_kode; end if;

  if a = 'konfirmasi_dp' then
    for r in update pesanan set status = 'dp', dp_dikonfirmasi = now(), batas_lunas = now() + make_interval(days => v_batas),
               nominal_dp = coalesce(nullif(p_aksi->>'nominal','')::int, nominal_dp)
             where id = any(ids) and status in ('menunggu_cek','ditahan') returning * loop
      if r.kambing_kode is not null then update kambing set status = 'dp' where kode = r.kambing_kode; end if;
      v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'dp_dikonfirmasi',
        'data', jsonb_build_object('kode', _plabel(r), 'harga', r.harga, 'nominal_dp', r.nominal_dp,
          'batas_lunas', to_char(r.batas_lunas at time zone 'Asia/Jakarta','DD/MM/YYYY HH24:MI'),
          'sisa', r.harga - coalesce(r.nominal_dp, 0)));
      v_hasil := v_hasil || _plabel(r) || ': DP dikonfirmasi, batas lunas ' || to_char(r.batas_lunas at time zone 'Asia/Jakarta','DD/MM HH24:MI') || E'\n';
    end loop;

  elsif a = 'tolak_dp' then
    for r in update pesanan set status = 'batal', alasan = coalesce(nullif(p_aksi->>'alasan',''), 'ditolak admin')
             where id = any(ids) and status in ('menunggu_cek','ditahan','cek_lunas') returning * loop
      perform _stok_kembali(r);
      if r.kambing_kode is not null then update kambing set status = 'tersedia' where kode = r.kambing_kode; end if;
      v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'dp_ditolak',
        'data', jsonb_build_object('kode', _plabel(r), 'alasan', p_aksi->>'alasan'));
      v_hasil := v_hasil || _plabel(r) || ': ditolak, stok dikembalikan' || E'\n';
    end loop;

  elsif a = 'lunas' then
    for r in update pesanan set status = 'lunas', lunas_at = now() where id = any(ids) and status in ('dp','cek_lunas','menunggu_cek') returning * loop
      if r.kambing_kode is not null then update kambing set status = 'terjual' where kode = r.kambing_kode; end if;
      v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'lunas',
        'data', jsonb_build_object('kode', _plabel(r), 'alamat', r.alamat_kirim));
      v_hasil := v_hasil || _plabel(r) || ': LUNAS' || E'\n';
    end loop;

  elsif a = 'batal_pesanan' then
    for r in update pesanan set status = 'batal', alasan = coalesce(nullif(p_aksi->>'alasan',''), 'dibatalkan admin')
             where id = any(ids) and status in ('ditahan','menunggu_cek','dp','cek_lunas') returning * loop
      perform _stok_kembali(r);
      v_hasil := v_hasil || _plabel(r) || ': dibatalkan, stok dikembalikan (urus pengembalian DP bila ada)' || E'\n';
    end loop;

  elsif a = 'produk_tambah' then
    v_kat := initcap(coalesce(nullif(p_aksi->>'kategori',''), 'Kambing'));
    if v_kat not in ('Kambing','Domba','Aqiqah','Qurban') then
      return jsonb_build_object('ok', false, 'ringkasan', 'Kategori harus Kambing, Domba, Aqiqah, atau Qurban');
    end if;
    v_pref := case v_kat when 'Kambing' then 'K' when 'Domba' then 'D' when 'Aqiqah' then 'AQ' else 'QK' end;
    if v_kode = '' or exists (select 1 from produk where kode = v_kode) then
      select v_pref || '-' || lpad((coalesce(max(nullif(regexp_replace(kode, '\D', '', 'g'), '')::int), 0) + 1)::text, 2, '0')
        into v_kode from produk where kode ~ ('^' || v_pref || '-[0-9]+$');
    end if;
    insert into produk(kode, kategori, nama, ras, kelamin, berat_min, berat_max, harga, stok, layak_kurban, foto, deskripsi, urutan)
    values (v_kode, v_kat,
      coalesce(nullif(p_aksi->>'nama',''), v_kat || coalesce(' ' || initcap(nullif(p_aksi->>'ras','')), '')),
      initcap(nullif(p_aksi->>'ras','')), initcap(nullif(p_aksi->>'kelamin','')),
      nullif(p_aksi->>'berat_min','')::numeric, nullif(p_aksi->>'berat_max','')::numeric,
      nullif(p_aksi->>'harga','')::int,
      case when v_kat in ('Kambing','Domba') then coalesce(nullif(p_aksi->>'stok','')::int, 0) else nullif(p_aksi->>'stok','')::int end,
      coalesce(nullif(p_aksi->>'layak_kurban','')::boolean, v_kat = 'Qurban'),
      case when coalesce(p_aksi->>'foto','') <> '' then array[p_aksi->>'foto'] else '{}' end,
      nullif(p_aksi->>'deskripsi',''),
      case v_kat when 'Kambing' then 10 when 'Domba' then 20 when 'Aqiqah' then 30 else 50 end)
    returning * into p;
    v_hasil := 'Ditambahkan ' || p.kode || ': ' || p.nama || coalesce(' ' || _berat(p), '') || ', ' || _rp(p.harga)
      || coalesce(', stok ' || p.stok || ' ekor', '')
      || case when cardinality(p.foto) = 0 then E'\n(belum ada foto: kirim foto dengan keterangan "foto ' || p.kode || '")' else '' end;

  elsif a in ('produk_ubah','stok_atur','stok_tambah','laku','flash_on','flash_off','tampilkan','sembunyikan','foto') then
    if p.kode is null then
      return jsonb_build_object('ok', false, 'ringkasan', 'Kode produk ' || coalesce(nullif(v_kode,''), '?') || ' tidak ditemukan. Ketik "stok" untuk melihat daftar kode.');
    end if;
    if a = 'produk_ubah' then
      if nullif(p_aksi->>'harga','') is not null and (p_aksi->>'harga')::int is distinct from p.harga then
        insert into riwayat_harga(produk_kode, harga_lama, harga_baru, alasan) values (p.kode, p.harga, (p_aksi->>'harga')::int, 'ubah satu');
      end if;
      v_opsi := p.opsi;
      if nullif(p_aksi->>'opsi_ekor','') is not null then
        select jsonb_agg(case when (e->>'ekor')::int = (p_aksi->>'opsi_ekor')::int
                 then e || jsonb_strip_nulls(jsonb_build_object('bobot', nullif(p_aksi->>'opsi_bobot',''), 'harga', nullif(p_aksi->>'opsi_harga','')::int))
                 else e end order by (e->>'ekor')::int)
          into v_opsi from jsonb_array_elements(p.opsi) e;
      end if;
      update produk set
        nama = coalesce(nullif(p_aksi->>'nama',''), nama),
        ras = coalesce(initcap(nullif(p_aksi->>'ras','')), ras),
        kelamin = coalesce(initcap(nullif(p_aksi->>'kelamin','')), kelamin),
        berat_min = coalesce(nullif(p_aksi->>'berat_min','')::numeric, berat_min),
        berat_max = coalesce(nullif(p_aksi->>'berat_max','')::numeric, berat_max),
        harga = coalesce(nullif(p_aksi->>'harga','')::int, harga),
        stok = coalesce(nullif(p_aksi->>'stok','')::int, stok),
        deskripsi = coalesce(nullif(p_aksi->>'deskripsi',''), deskripsi),
        layak_kurban = coalesce(nullif(p_aksi->>'layak_kurban','')::boolean, layak_kurban),
        opsi = coalesce(v_opsi, opsi)
      where kode = p.kode returning * into p;
      v_hasil := 'Diperbarui ' || p.kode || ': ' || p.nama || coalesce(' ' || _berat(p), '') || ', ' || _rp(p.harga) || coalesce(', stok ' || p.stok || ' ekor', '')
        || case when nullif(p_aksi->>'opsi_ekor','') is not null then E'\nPilihan ' || (p_aksi->>'opsi_ekor') || ' ekor: '
             || coalesce((select coalesce(nullif(e->>'bobot',''), '-') || ', ' || _rp(nullif(e->>'harga','')::int) from jsonb_array_elements(p.opsi) e where (e->>'ekor')::int = (p_aksi->>'opsi_ekor')::int), '-') else '' end;
    elsif a = 'stok_atur' then
      update produk set stok = greatest(0, (p_aksi->>'stok')::int), tampil = true where kode = p.kode returning * into p;
      v_hasil := 'Stok ' || p.kode || ' ' || p.nama || ' sekarang ' || p.stok || ' ekor (tampil di katalog)';
    elsif a in ('stok_tambah','laku') then
      n := coalesce(nullif(p_aksi->>'jumlah','')::int, nullif(p_aksi->>'selisih','')::int, 1);
      if a = 'laku' then n := -abs(n); end if;
      update produk set stok = greatest(0, coalesce(stok, 0) + n) where kode = p.kode returning * into p;
      v_hasil := case when a = 'laku' then abs(n) || ' ekor ' || p.nama || ' laku di kandang. ' else '' end
        || 'Stok ' || p.kode || ' sekarang ' || p.stok || ' ekor';
    elsif a = 'flash_on' then
      if nullif(p_aksi->>'harga','') is null then return jsonb_build_object('ok', false, 'ringkasan', 'Sebutkan harga flash sale-nya, contoh: flash ' || p.kode || ' 1,6jt sampai 20.00'); end if;
      v_sampai := coalesce(
        (nullif(p_aksi->>'sampai',''))::timestamp at time zone 'Asia/Jakarta',
        now() + make_interval(hours => coalesce(nullif(p_aksi->>'jam','')::int, 24)));
      if v_sampai <= now() then return jsonb_build_object('ok', false, 'ringkasan', 'Waktu berakhir flash sale sudah lewat. Sebutkan jam/tanggal yang akan datang.'); end if;
      update produk set flash_harga = (p_aksi->>'harga')::int, flash_sampai = v_sampai where kode = p.kode returning * into p;
      v_hasil := '⚡ Flash sale ' || p.kode || ' ' || p.nama || coalesce(' ' || _berat(p), '') || ': ' || _rp(p.harga) || ' → ' || _rp(p.flash_harga)
        || ' sampai ' || to_char(p.flash_sampai at time zone 'Asia/Jakarta', 'DD/MM HH24:MI') || ' WIB';
    elsif a = 'flash_off' then
      update produk set flash_harga = null, flash_sampai = null where kode = p.kode returning * into p;
      v_hasil := 'Flash sale ' || p.kode || ' dimatikan, harga kembali ' || _rp(p.harga);
    elsif a in ('tampilkan','sembunyikan') then
      update produk set tampil = (a = 'tampilkan') where kode = p.kode returning * into p;
      v_hasil := p.kode || ' ' || p.nama || case when p.tampil then ' tampil di katalog' else ' disembunyikan dari katalog' end;
    elsif a = 'foto' then
      update produk set foto = foto || array[p_aksi->>'foto'] where kode = p.kode and coalesce(p_aksi->>'foto','') <> '' returning * into p;
      v_hasil := 'Foto ditambahkan ke ' || p.kode || ' (' || cardinality(p.foto) || ' foto)';
    end if;

  elsif a = 'harga_rata' then
    n := (p_aksi->>'selisih')::int;
    insert into riwayat_harga(produk_kode, harga_lama, harga_baru, alasan)
      select kode, harga, harga + n, case when n >= 0 then 'naik rata ' else 'turun rata ' end || abs(n)
      from produk where harga is not null and harga + n > 0
        and (nullif(p_aksi->>'kategori','') is null or kategori ilike p_aksi->>'kategori')
        and (nullif(p_aksi->>'ras','') is null or coalesce(ras,'') ilike '%' || (p_aksi->>'ras') || '%' or nama ilike '%' || (p_aksi->>'ras') || '%');
    update produk set harga = harga + n where harga is not null and harga + n > 0
        and (nullif(p_aksi->>'kategori','') is null or kategori ilike p_aksi->>'kategori')
        and (nullif(p_aksi->>'ras','') is null or coalesce(ras,'') ilike '%' || (p_aksi->>'ras') || '%' or nama ilike '%' || (p_aksi->>'ras') || '%');
    get diagnostics n = row_count;
    v_hasil := 'Harga ' || n || ' produk ' || case when (p_aksi->>'selisih')::int >= 0 then 'naik' else 'turun' end
      || ' ' || _rp(abs((p_aksi->>'selisih')::int)) || '. Pesanan yang sudah berjalan tidak berubah. Harga per pilihan ekor paket diubah satu per satu.';

  elsif a = 'ulasan' then
    select string_agg('#' || id || ' ' || coalesce(produk_kode,'-') || ' ' || repeat('★', bintang) || ' ' || coalesce(nama,'') || ': ' || coalesce(komentar,'(tanpa komentar)')
                      || case when tampil then '' else ' [disembunyikan]' end, E'\n' order by id desc)
      into v_hasil from (select * from ulasan order by id desc limit 15) u;
    v_hasil := 'Ulasan terbaru:' || E'\n' || coalesce(v_hasil, 'Belum ada ulasan.') || E'\n\nSembunyikan: "sembunyikan ulasan 3"';
  elsif a in ('ulasan_sembunyikan','ulasan_tampilkan') then
    update ulasan set tampil = (a = 'ulasan_tampilkan') where id = any(ids);
    get diagnostics n = row_count;
    v_hasil := n || ' ulasan ' || case when a = 'ulasan_tampilkan' then 'ditampilkan lagi' else 'disembunyikan dari katalog' end;

  elsif a = 'galeri' then
    if coalesce(p_aksi->>'foto','') = '' then return jsonb_build_object('ok', false, 'ringkasan', 'Kirim fotonya sekaligus dengan keterangan "galeri ..." ya.'); end if;
    insert into galeri(foto_url, caption) values (p_aksi->>'foto', nullif(coalesce(p_aksi->>'caption', p_aksi->>'deskripsi'),'')) returning id into n;
    v_hasil := 'Foto #' || n || ' ditambahkan ke Galeri Kegiatan di website. Hapus: "hapus galeri ' || n || '"';
  elsif a = 'galeri_hapus' then
    update galeri set tampil = false where id = any(ids);
    get diagnostics n = row_count;
    v_hasil := n || ' foto disembunyikan dari Galeri Kegiatan';
  elsif a = 'testimoni' then
    insert into testimoni(foto_url, caption, kota) values (p_aksi->>'foto', nullif(p_aksi->>'caption',''), nullif(p_aksi->>'kota',''));
    v_hasil := 'Foto testimoni ditambahkan ke katalog';

  elsif a in ('ambil_alih', 'kembali_bot') then
    update percakapan set mode = case a when 'ambil_alih' then 'manusia' else 'bot' end
      where wa = regexp_replace(regexp_replace(coalesce(p_aksi->>'wa',''), '\D', '', 'g'), '^0', '62') or chat_id = p_aksi->>'wa';
    get diagnostics n = row_count;
    v_hasil := case when n = 0 then 'Nomor tidak ditemukan di percakapan' when a = 'ambil_alih' then 'Bot berhenti membalas ' || (p_aksi->>'wa') || '. Silakan balas manual.' else 'Bot aktif lagi untuk ' || (p_aksi->>'wa') end;

  elsif a = 'iduladha' then
    update pengaturan set v = coalesce(p_aksi->>'aktif','false') where k = 'iduladha';
    v_hasil := 'Mode Iduladha ' || case when coalesce((p_aksi->>'aktif')::boolean,false) then 'AKTIF' else 'mati' end;

  elsif a in ('stok', 'laporan') then
    select string_agg(kode || ' ' || nama || coalesce(' ' || _berat(pr), '') || ' · '
        || case when jsonb_array_length(opsi) > 0
             then (select count(*) filter (where nullif(e->>'harga','') is not null) || '/' || count(*) || ' pilihan ekor sudah ada harga' from jsonb_array_elements(opsi) e)
             else _rp(harga) end
        || case when _flash_aktif(pr) then ' ⚡' || _rp(flash_harga) else '' end
        || coalesce(' · stok ' || stok, '') || case when tampil then '' else ' [disembunyikan]' end, E'\n' order by urutan, kode)
      into v_hasil from produk pr;
    v_hasil := '*Produk*' || E'\n' || coalesce(v_hasil, 'Belum ada produk.') || E'\n\n*Pesanan aktif*\n' ||
      coalesce((select string_agg(_plabel(o) || ' · ' || coalesce(o.nama, o.wa, '-') || ' · ' ||
          case o.status when 'ditahan' then 'ditahan s/d ' || to_char(o.ditahan_sampai at time zone 'Asia/Jakarta','HH24:MI')
                        when 'menunggu_cek' then 'CEK BUKTI DP'
                        when 'cek_lunas' then 'CEK BUKTI PELUNASAN'
                        else 'DP, lunas s/d ' || to_char(o.batas_lunas at time zone 'Asia/Jakarta','DD/MM HH24:MI') end, E'\n' order by o.id)
        from pesanan o where o.status in ('ditahan','menunggu_cek','dp','cek_lunas')), '-');

  else
    return jsonb_build_object('ok', false, 'ringkasan', 'Perintah tidak dikenali. Ketik "bantuan" untuk daftar perintah.');
  end if;

  return jsonb_build_object('ok', true, 'ringkasan', _rapikan(coalesce(nullif(v_hasil, ''), 'Tidak ada yang berubah (cek nomor pesanan/kode produk dan statusnya).')), 'notif', v_notif);
end $function$
;

CREATE OR REPLACE FUNCTION public.admin_tunda(p_key text, p_chat text, p_aksi jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v jsonb;
begin
  perform _cek(p_key);
  select aksi_tertunda into v from percakapan where chat_id = p_chat;
  update percakapan set aksi_tertunda = p_aksi where chat_id = p_chat;
  return jsonb_build_object('ok', true, 'sebelumnya', v);
end $function$
;

CREATE OR REPLACE FUNCTION public.alarm_cek(p_key text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform _cek(p_key);
  return jsonb_build_object(
    'ai_gagal_1jam', (select count(*) from pesan where arah = 'keluar' and created_at > now() - interval '60 minutes'
                        and teks like 'Terima kasih sudah menghubungi Barokah Farm. Sebentar ya Kak, admin kami akan segera membalas%'),
    'pesan_masuk_1jam', (select count(*) from pesan where arah = 'masuk' and created_at > now() - interval '60 minutes'),
    'ke_admin', _penerima('admin_wa', 'admin_chat'));
end $function$
;

CREATE OR REPLACE FUNCTION public.bot_alamat(p_key text, p_chat text, p_alamat text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare n int;
begin
  perform _cek(p_key);
  update pesanan set alamat_kirim = p_alamat where chat_id = p_chat and status in ('ditahan','menunggu_cek','dp','cek_lunas');
  get diagnostics n = row_count;
  return jsonb_build_object('ok', n > 0, 'diperbarui', n);
end $function$
;

CREATE OR REPLACE FUNCTION public.bot_batal(p_key text, p_chat text, p_kode text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare r pesanan; v_batal jsonb := '[]'::jsonb; v_refund jsonb := '[]'::jsonb; v_tolak jsonb := '[]'::jsonb; v_cari text := nullif(trim(coalesce(p_kode,'')),'');
begin
  perform _cek(p_key);
  for r in select * from pesanan
           where chat_id = p_chat and status in ('ditahan','menunggu_cek','dp','cek_lunas')
             and (v_cari is null or produk_kode = _pkode(v_cari) or id::text = regexp_replace(v_cari, '\D', '', 'g') or kambing_kode = _kode(v_cari)) for update loop
    if r.status = 'cek_lunas' or (r.status = 'dp' and r.batas_lunas is not null and r.batas_lunas < now()) then
      v_tolak := v_tolak || jsonb_build_object('pesanan', _plabel(r), 'alasan', 'pelunasan sedang dicek admin atau sudah lewat batas; oper ke admin');
      continue;
    end if;
    update pesanan set status = 'batal',
      alasan = case when r.status = 'ditahan' then 'dibatalkan pembeli' else 'dibatalkan pembeli sebelum batas pelunasan, DP wajib dikembalikan' end
      where id = r.id;
    perform _stok_kembali(r);
    if r.kambing_kode is not null then update kambing set status = 'tersedia' where kode = r.kambing_kode and status in ('ditahan','dp'); end if;
    if r.status = 'ditahan' then
      v_batal := v_batal || to_jsonb(_plabel(r));
    else
      v_refund := v_refund || jsonb_build_object('pesanan', _plabel(r), 'nominal_dp', r.nominal_dp,
        'status_sebelumnya', case r.status when 'dp' then 'DP sudah dikonfirmasi admin' else 'bukti DP sedang dicek admin' end);
    end if;
  end loop;
  if jsonb_array_length(v_batal) = 0 and jsonb_array_length(v_refund) = 0 then
    return jsonb_build_object('ok', false, 'alasan', case when jsonb_array_length(v_tolak) > 0 then 'Pesanan ini tidak bisa dibatalkan lewat bot' else 'Tidak ada pesanan aktif untuk dibatalkan' end, 'tidak_bisa', v_tolak);
  end if;
  return jsonb_build_object('ok', true, 'dibatalkan_tanpa_dp', v_batal, 'dibatalkan_dp_dikembalikan', v_refund, 'tidak_bisa', v_tolak,
    'petunjuk', case when jsonb_array_length(v_refund) > 0 then 'DP dikembalikan penuh oleh admin: minta nama bank, nomor rekening, dan nama pemilik rekening untuk pengembalian, lalu oper ke admin dengan [[OPER_ADMIN: Refund DP ...]]' end);
end $function$
;

CREATE OR REPLACE FUNCTION public.bot_bukti(p_key text, p_chat text, p_bukti_url text, p_nominal integer DEFAULT NULL::integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v_list jsonb; v_jenis text;
begin
  perform _cek(p_key);
  with u as (
    update pesanan set status = 'menunggu_cek', bukti_url = p_bukti_url, bukti_at = now(), nominal_dp = coalesce(p_nominal, nominal_dp)
    where chat_id = p_chat and status = 'ditahan' returning *)
  select jsonb_agg(jsonb_build_object('no', u.id, 'kode', _plabel(u::pesanan), 'harga', u.harga)) into v_list from u;
  if v_list is not null then v_jenis := 'dp';
  else
    with u as (
      update pesanan set status = 'cek_lunas', bukti_lunas_url = p_bukti_url, bukti_lunas_at = now()
      where chat_id = p_chat and status = 'dp' returning *)
    select jsonb_agg(jsonb_build_object('no', u.id, 'kode', _plabel(u::pesanan), 'harga', u.harga, 'nominal_dp', u.nominal_dp)) into v_list from u;
    if v_list is not null then v_jenis := 'pelunasan'; end if;
  end if;
  if v_list is null then return jsonb_build_object('ok', false, 'alasan', 'Tidak ada pesanan yang menunggu pembayaran'); end if;
  return jsonb_build_object('ok', true, 'jenis', v_jenis, 'pesanan', v_list,
    'nama', (select nama from percakapan where chat_id = p_chat), 'wa', (select wa from percakapan where chat_id = p_chat));
end $function$
;

CREATE OR REPLACE FUNCTION public.bot_cek(p_key text, p_chat text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare r pesanan; t text := ''; n int := 0;
begin
  perform _cek(p_key);
  for r in select * from pesanan where chat_id = p_chat
             and (status in ('ditahan','menunggu_cek','dp','cek_lunas')
                  or (status = 'lunas' and coalesce(lunas_at, updated_at) > now() - interval '14 days')
                  or (status in ('batal','hangus') and updated_at > now() - interval '3 days'))
           order by id loop
    n := n + 1;
    t := t || case when n > 1 then E'\n\n' else '' end || '🧾 *' || _plabel(r) || '*' || E'\nTotal: ' || _rp(r.harga)
      || coalesce(E'\nDP diterima: ' || _rp(r.nominal_dp) || case when r.status in ('dp','cek_lunas') then ' · sisa ' || _rp(r.harga - r.nominal_dp) else '' end, '')
      || E'\nStatus: ' || case r.status
          when 'ditahan' then 'menunggu bukti DP, ditahan sampai ' || to_char(r.ditahan_sampai at time zone 'Asia/Jakarta','HH24.MI') || ' WIB. Transfer ke ' || _set('rekening') || ' lalu kirim fotonya di sini.'
          when 'menunggu_cek' then 'bukti DP sedang dicek admin.'
          when 'dp' then 'DP diterima. Lunasi paling lambat ' || to_char(r.batas_lunas at time zone 'Asia/Jakarta','DD/MM HH24.MI') || ' WIB.'
          when 'cek_lunas' then 'bukti pelunasan sedang dicek admin.'
          when 'lunas' then 'LUNAS ✅ Tim kami mengonfirmasi jadwal kirim atau ambil.'
          when 'hangus' then 'dibatalkan, lewat batas pelunasan.'
          else 'dibatalkan.' end;
  end loop;
  if n = 0 then
    t := 'Belum ada pesanan dari nomor ini. Lihat stok dan paket di ' || coalesce(nullif(_set('link_katalog'),''), 'katalog kami') || ', atau tanya admin di sini ya.';
  end if;
  return jsonb_build_object('teks', t, 'jumlah', n);
end $function$
;

CREATE OR REPLACE FUNCTION public.bot_info(p_key text, p_chat text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform _cek(p_key);
  return _info() || jsonb_build_object('nama_pembeli', (select nama from percakapan where chat_id = p_chat),
    'sekarang', to_char(now() at time zone 'Asia/Jakarta','DD/MM/YYYY HH24:MI'),
    'riwayat', coalesce((select jsonb_agg(jsonb_build_object('dari', case arah when 'masuk' then 'pembeli' else 'cs' end, 'teks', teks) order by created_at)
                 from (select * from pesan where chat_id = p_chat order by created_at desc limit 6) x), '[]'::jsonb));
end $function$
;

CREATE OR REPLACE FUNCTION public.bot_keluar(p_key text, p_chat text, p_teks text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform _cek(p_key);
  insert into pesan(chat_id, arah, teks) values (p_chat, 'keluar', p_teks);
end $function$
;

CREATE OR REPLACE FUNCTION public.bot_masuk(p_key text, p_chat text, p_wa text, p_nama text, p_teks text, p_media_url text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v_admin boolean; v_staf boolean; v_mode text; v_baru boolean := false; v_staf_baru boolean := false; r jsonb; v_t text := upper(trim(coalesce(p_teks,'')));
begin
  perform _cek(p_key);
  if v_t = 'ADMIN ' || _set('admin_pin') then
    update pengaturan set v = v || ',' || p_chat where k = 'admin_chat' and not (p_chat = any(string_to_array(v, ',')));
    v_baru := true;
  elsif v_t = 'STAF ' || _set('staf_pin') then
    update pengaturan set v = v || ',' || p_chat where k = 'staf_chat' and not (p_chat = any(string_to_array(v, ',')));
    v_staf_baru := true;
  end if;
  v_admin := (coalesce(p_wa,'') <> '' and p_wa = any(string_to_array(_set('admin_wa'), ',')))
          or p_chat = any(string_to_array(_set('admin_chat'), ','));
  v_staf := not v_admin and p_chat = any(string_to_array(coalesce(_set('staf_chat'),''), ','));

  insert into percakapan(chat_id, wa, nama) values (p_chat, nullif(p_wa,''), p_nama)
  on conflict (chat_id) do update set wa = coalesce(excluded.wa, percakapan.wa),
    nama = coalesce(excluded.nama, percakapan.nama), terakhir = now()
  returning mode into v_mode;

  insert into pesan(chat_id, arah, teks, media_url) values (p_chat, 'masuk', p_teks, p_media_url);

  select jsonb_build_object(
    'peran', case when v_admin then 'admin' when v_staf then 'staf' else 'pembeli' end,
    'admin_baru', v_baru,
    'staf_baru', v_staf_baru,
    'mode', v_mode,
    'aksi_tertunda', (select aksi_tertunda from percakapan where chat_id = p_chat),
    'nama', p_nama,
    'riwayat', coalesce((select jsonb_agg(jsonb_build_object('dari', case arah when 'masuk' then 'pembeli' else 'cs' end, 'teks', teks, 'waktu', to_char(created_at at time zone 'Asia/Jakarta','DD/MM HH24:MI')) order by created_at)
                 from (select * from pesan where chat_id = p_chat order by created_at desc limit 16) x), '[]'::jsonb),
    'pesanan', coalesce((select jsonb_agg(jsonb_strip_nulls(jsonb_build_object('no', p.id, 'kode', _plabel(p), 'produk', p.produk_kode,
                 'jumlah', p.jumlah, 'pilihan', p.opsi, 'status', p.status, 'harga_total', p.harga,
                 'dp_minimal', coalesce(_set('dp_min')::int,100000) * case when p.opsi is not null then p.jumlah
                                 else p.jumlah * coalesce((select isi_ekor from produk where kode = p.produk_kode),1) end,
                 'ditahan_sampai', to_char(p.ditahan_sampai at time zone 'Asia/Jakarta','HH24:MI'),
                 'batas_lunas', to_char(p.batas_lunas at time zone 'Asia/Jakarta','DD/MM/YYYY HH24:MI'),
                 'nominal_dp', p.nominal_dp, 'sisa', case when p.nominal_dp is not null then p.harga - p.nominal_dp end,
                 'alamat', p.alamat_kirim)) order by p.id)
               from pesanan p where p.chat_id = p_chat and p.status in ('ditahan','menunggu_cek','dp','cek_lunas')), '[]'::jsonb),
    'menunggu_ulasan', coalesce((select jsonb_agg(_plabel(p)) from pesanan p
               where p.chat_id = p_chat and p.status = 'lunas' and p.ulasan_diminta is not null
                 and p.ulasan_diminta > now() - interval '14 days'
                 and not exists (select 1 from ulasan u where u.pesanan_id = p.id)), '[]'::jsonb),
    'stok', coalesce((select jsonb_agg(_prod_ringkas(pr) order by pr.urutan, pr.kode) from produk pr where pr.tampil), '[]'::jsonb),
    'sedang_dipesan', '[]'::jsonb,
    'produk_semua', case when v_admin or v_staf then (select jsonb_agg(kode || ' ' || nama || coalesce(' ' || _berat(pr), '') || ' ' || _rp(harga) || coalesce(' stok ' || stok, '')
                        || case when jsonb_array_length(opsi) > 0 then ' (pilihan 1-' || jsonb_array_length(opsi) || ' ekor)' else '' end
                        || case when _flash_aktif(pr) then ' FLASH ' || _rp(flash_harga) else '' end || case when tampil then '' else ' [disembunyikan]' end order by urutan, kode) from produk pr) end,
    'pesanan_aktif', case when v_admin or v_staf then (select jsonb_agg(_plabel(o) || ' ' || coalesce(o.nama, o.wa, '') || ' [' || o.status || ']' order by o.id) from pesanan o where o.status in ('ditahan','menunggu_cek','dp','cek_lunas')) end,
    'info', _info(),
    'sekarang', to_char(now() at time zone 'Asia/Jakarta','TMDay, DD/MM/YYYY HH24:MI')
  ) into r;
  return r;
end $function$
;

CREATE OR REPLACE FUNCTION public.bot_oper(p_key text, p_chat text, p_alasan text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform _cek(p_key);
  update percakapan set mode = 'manusia', alasan_oper = p_alasan where chat_id = p_chat;
  return jsonb_build_object('ok', true, 'wa', (select wa from percakapan where chat_id = p_chat),
    'nama', (select nama from percakapan where chat_id = p_chat), 'alasan', p_alasan);
end $function$
;

CREATE OR REPLACE FUNCTION public.bot_pesan(p_key text, p_chat text, p_kode text, p_jumlah integer DEFAULT 1, p_nama text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare p produk; o pesanan; v_kode text := _pkode(p_kode); v_j int := greatest(coalesce(p_jumlah,1),1);
  v_harga int; v_opsi text; x jsonb; v_ekor int; v_menit int := coalesce(_set('tahan_menit'),'60')::int;
begin
  perform _cek(p_key);
  select * into p from produk where kode = v_kode and tampil for update;
  if not found then
    return jsonb_build_object('ok', false, 'alasan', 'Kode ' || v_kode || ' tidak ada di katalog',
      'daftar_kode', (select jsonb_agg(kode || ' ' || nama order by urutan) from produk where tampil));
  end if;
  if jsonb_array_length(p.opsi) > 0 then
    select e into x from jsonb_array_elements(p.opsi) e where (e->>'ekor')::int = v_j;
    if x is null then return jsonb_build_object('ok', false, 'alasan', 'Pilihan ' || v_j || ' ekor tidak ada untuk ' || p.nama || ' (pilihan 1–' || jsonb_array_length(p.opsi) || ' ekor)'); end if;
    v_harga := nullif(x->>'harga','')::int;
    v_opsi := v_j || ' ekor' || coalesce(', ' || nullif(x->>'bobot',''), '');
    v_ekor := v_j;
  else
    v_harga := _harga_aktif(p) * v_j;
    v_ekor := v_j * p.isi_ekor;
  end if;
  if v_harga is null then
    return jsonb_build_object('ok', false, 'harga_belum_ada', true,
      'alasan', 'Harga ' || p.nama || coalesce(' ' || v_opsi, '') || ' belum ditentukan admin. Sampaikan admin akan memberi harga, lalu oper ke admin.');
  end if;
  if p.stok is not null and v_opsi is null then
    if p.stok < v_j then
      return jsonb_build_object('ok', false, 'alasan', case when p.stok = 0 then p.nama || ' ' || coalesce(_berat(p),'') || ' sedang habis' else 'Stok ' || p.nama || ' hanya tersisa ' || p.stok || ' ekor' end,
        'stok_lain', (select jsonb_agg(_prod_ringkas(q)) from (select * from produk where tampil and kategori = p.kategori and kode <> p.kode and coalesce(stok,1) > 0 order by urutan limit 3) q));
    end if;
    update produk set stok = stok - v_j where kode = p.kode;
  end if;
  insert into pesanan(produk_kode, chat_id, wa, nama, harga, jumlah, opsi, ditahan_sampai)
  values (p.kode, p_chat, (select wa from percakapan where chat_id = p_chat), coalesce(nullif(p_nama,''), (select nama from percakapan where chat_id = p_chat)),
          v_harga, v_j, v_opsi, now() + make_interval(mins => v_menit))
  returning * into o;
  return jsonb_build_object('ok', true, 'ringkasan', _ringkasan_pesanan(o), 'no_pesanan', o.id, 'pesanan', _plabel(o), 'produk', _prod_ringkas(p),
    'jumlah', v_j, 'total_ekor', v_ekor, 'harga_total', v_harga, 'flash_sale', _flash_aktif(p),
    'dp_minimal', coalesce(_set('dp_min')::int,100000) * v_ekor,
    'ditahan_menit', v_menit, 'ditahan_sampai', to_char(o.ditahan_sampai at time zone 'Asia/Jakarta','HH24:MI'), 'info', _info());
end $function$
;

CREATE OR REPLACE FUNCTION public.bot_tahan(p_key text, p_chat text, p_kode text, p_nama text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
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
      (select jsonb_agg(_ringkas(x)) from (select * from kambing where status='tersedia' and not dihapus and jenis = k.jenis order by abs(harga - k.harga) limit 3) x));
  end if;
  update kambing set status = 'ditahan' where kode = v_kode;
  insert into pesanan(kambing_kode, chat_id, wa, nama, harga, ditahan_sampai)
    values (v_kode, p_chat, (select wa from percakapan where chat_id = p_chat), coalesce(p_nama, (select nama from percakapan where chat_id = p_chat)), k.harga, now() + make_interval(mins => v_menit));
  return jsonb_build_object('ok', true, 'kambing', _ringkas(k), 'ditahan_menit', v_menit,
    'ditahan_sampai', to_char((now() + make_interval(mins => v_menit)) at time zone 'Asia/Jakarta','HH24:MI'), 'info', _info());
end $function$
;

CREATE OR REPLACE FUNCTION public.bot_ulasan(p_key text, p_chat text, p_bintang integer, p_komentar text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare o pesanan; v_id bigint; v_b int := least(5, greatest(1, coalesce(p_bintang, 5)));
begin
  perform _cek(p_key);
  select * into o from pesanan where chat_id = p_chat and status = 'lunas' order by coalesce(lunas_at, updated_at) desc limit 1;
  if not found then return jsonb_build_object('ok', false, 'alasan', 'Belum ada pesanan lunas dari nomor ini, jadi ulasan belum bisa disimpan'); end if;
  select id into v_id from ulasan where pesanan_id = o.id;
  if v_id is null then
    insert into ulasan(pesanan_id, produk_kode, chat_id, nama, bintang, komentar)
    values (o.id, o.produk_kode, p_chat, coalesce(o.nama, (select nama from percakapan where chat_id = p_chat)), v_b, nullif(trim(coalesce(p_komentar,'')),''))
    returning id into v_id;
  else
    update ulasan set bintang = v_b, komentar = coalesce(nullif(trim(coalesce(p_komentar,'')),''), komentar) where id = v_id;
  end if;
  return jsonb_build_object('ok', true, 'ulasan_id', v_id, 'pesanan', _plabel(o), 'bintang', v_b,
    'catatan', 'Ulasan tersimpan dan akan tampil di katalog. Ucapkan terima kasih.');
end $function$
;

CREATE OR REPLACE FUNCTION public.catat_kunjungan(p_jenis text, p_kode text DEFAULT ''::text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  if p_jenis not in ('lihat','detail','wa') then return; end if;
  insert into kunjungan(hari, jenis, kode, jumlah)
  values ((now() at time zone 'Asia/Jakarta')::date, p_jenis, left(regexp_replace(coalesce(p_kode,''), '[^A-Za-z0-9-]', '', 'g'), 12), 1)
  on conflict (hari, jenis, kode) do update set jumlah = kunjungan.jumlah + 1;
end $function$
;

CREATE OR REPLACE FUNCTION public.jadwal_cek(p_key text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare r pesanan; v_notif jsonb := '[]'::jsonb; v_admin text := '';
  v_jam int := extract(hour from now() at time zone 'Asia/Jakarta')::int;
  v_malam boolean := v_jam >= 21 or v_jam < 6;
begin
  perform _cek(p_key);
  for r in update pesanan set status = 'batal', alasan = 'waktu tahan habis'
           where status = 'ditahan' and ditahan_sampai < now() returning * loop
    perform _stok_kembali(r);
    if r.kambing_kode is not null then update kambing set status = 'tersedia' where kode = r.kambing_kode and status = 'ditahan'; end if;
    v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'tahan_habis', 'data', jsonb_build_object('kode', _plabel(r)));
  end loop;
  for r in update pesanan set tunggu_dikabari = now()
           where ((status = 'menunggu_cek' and bukti_at < now() - interval '60 minutes'
                   and (tunggu_dikabari is null or tunggu_dikabari < bukti_at))
               or (status = 'cek_lunas' and bukti_lunas_at < now() - interval '60 minutes'
                   and (tunggu_dikabari is null or tunggu_dikabari < bukti_lunas_at)))
           returning * loop
    v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'admin_belum_balas', 'data', jsonb_build_object(
      'kode', _plabel(r), 'jenis', case r.status when 'cek_lunas' then 'pelunasan' else 'DP' end, 'malam', v_malam));
    v_admin := v_admin || 'Bukti ' || case r.status when 'cek_lunas' then 'pelunasan ' else 'DP ' end || _plabel(r)
      || ' (' || coalesce(r.nama, r.wa, r.chat_id) || ') belum dikonfirmasi lebih dari 1 jam. Balas: '
      || case r.status when 'cek_lunas' then 'lunas ' else 'OK ' end || r.id || ' atau TOLAK ' || r.id || E'\n';
  end loop;
  for r in update pesanan set diingatkan_h1 = true
           where status = 'dp' and not diingatkan_h1 and batas_lunas - now() <= interval '24 hours' and batas_lunas > now() returning * loop
    v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'pengingat_h1', 'data', jsonb_build_object(
      'kode', _plabel(r), 'batas_lunas', to_char(r.batas_lunas at time zone 'Asia/Jakarta','DD/MM/YYYY HH24:MI'),
      'sisa', r.harga - coalesce(r.nominal_dp,0)));
  end loop;
  for r in update pesanan set status = 'hangus', alasan = 'lewat batas pelunasan, DP untuk pakan dan perawatan 1 bulan'
           where status = 'dp' and batas_lunas < now() returning * loop
    perform _stok_kembali(r);
    if r.kambing_kode is not null then update kambing set status = 'tersedia' where kode = r.kambing_kode and status = 'dp'; end if;
    v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'dp_hangus', 'data', jsonb_build_object(
      'kode', _plabel(r), 'nominal_dp', r.nominal_dp));
    v_admin := v_admin || _plabel(r) || ' DP hangus (' || coalesce(r.nama, r.wa, r.chat_id) || '), DP tidak dikembalikan (biaya pakan & perawatan 1 bulan). Stok dikembalikan ke katalog.' || E'\n';
  end loop;
  if v_jam between 9 and 19 then
    for r in update pesanan set ulasan_diminta = now()
             where status = 'lunas' and ulasan_diminta is null and lunas_at is not null and lunas_at < now() - interval '2 days'
               and not exists (select 1 from ulasan u where u.pesanan_id = pesanan.id)
             returning * loop
      v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'minta_ulasan', 'data', jsonb_build_object('kode', _plabel(r)));
    end loop;
  end if;
  return jsonb_build_object('notif', v_notif, 'admin', nullif(v_admin, ''), 'admin_wa', _set('admin_wa'));
end $function$
;

CREATE OR REPLACE FUNCTION public.rekap_pagi(p_key text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare
  v_hari text := (array['Minggu','Senin','Selasa','Rabu','Kamis','Jumat','Sabtu'])[extract(dow from now() at time zone 'Asia/Jakarta')::int + 1] || ', ' || to_char(now() at time zone 'Asia/Jakarta', 'DD/MM');
  v_kmr date := (now() at time zone 'Asia/Jakarta')::date - 1;
  a text := ''; s text := ''; x text;
begin
  perform _cek(p_key);
  select string_agg('• ' || _plabel(o) || ' (' || coalesce(o.nama, o.wa, '-') || ') → *' || case o.status when 'cek_lunas' then 'lunas ' else 'OK ' end || o.id || '* / *TOLAK ' || o.id || '*', E'\n' order by o.id)
    into x from pesanan o where o.status in ('menunggu_cek','cek_lunas');
  if x is not null then a := a || E'\n\n*Bukti transfer menunggu dicek*\n' || x; end if;
  select string_agg('• ' || _plabel(o) || ' (' || coalesce(o.nama, o.wa, '-') || ') batas ' || to_char(o.batas_lunas at time zone 'Asia/Jakarta','DD/MM HH24.MI') || ', sisa ' || _rp(o.harga - coalesce(o.nominal_dp,0)), E'\n' order by o.batas_lunas)
    into x from pesanan o where o.status = 'dp' and o.batas_lunas < now() + interval '36 hours';
  if x is not null then a := a || E'\n\n*Jatuh tempo pelunasan (hari ini/besok)*\n' || x; end if;
  select string_agg('• ' || _plabel(o) || ' (' || coalesce(o.nama, o.wa, '-') || ')' || coalesce(' — ' || left(o.alamat_kirim, 80), ' — alamat belum ada'), E'\n' order by o.id)
    into x from pesanan o where o.status = 'lunas' and o.lunas_at > now() - interval '3 days';
  if x is not null then a := a || E'\n\n*Lunas, siapkan kirim/ambil*\n' || x; end if;
  select string_agg('• ' || coalesce(pc.nama, '-') || ' (wa.me/' || coalesce(pc.wa, split_part(pc.chat_id,'@',1)) || ')' || coalesce(': ' || left(pc.alasan_oper, 60), ''), E'\n')
    into x from percakapan pc where pc.mode = 'manusia' and pc.terakhir > now() - interval '7 days'
      and pc.chat_id <> all(string_to_array(coalesce(_set('admin_chat'),'') || ',' || coalesce(_set('staf_chat'),''), ','));
  if x is not null then a := a || E'\n\n*Chat menunggu dibalas admin*\n' || x || E'\nSelesai? kirim *bot <nomor>*'; end if;
  select string_agg('• ' || pr.kode || ' ' || pr.nama || coalesce(' ' || _berat(pr), '') || ': ' || case when pr.stok = 0 then 'HABIS' else 'tinggal ' || pr.stok end, E'\n' order by pr.urutan)
    into x from produk pr where pr.tampil and pr.stok is not null and pr.stok <= 2;
  if x is not null then a := a || E'\n\n*Stok menipis*\n' || x; end if;
  select string_agg('• ' || pr.kode || ' ' || _rp(pr.flash_harga) || ' sampai ' || to_char(pr.flash_sampai at time zone 'Asia/Jakarta','DD/MM HH24.MI'), E'\n')
    into x from produk pr where _flash_aktif(pr);
  if x is not null then a := a || E'\n\n*Flash sale aktif*\n' || x; end if;
  a := a || E'\n\n*Kemarin*\n• Pengunjung website: ' || coalesce((select sum(k.jumlah) from kunjungan k where k.hari = v_kmr and k.jenis = 'lihat'), 0)
    || E'\n• Klik WhatsApp di website: ' || coalesce((select sum(k.jumlah) from kunjungan k where k.hari = v_kmr and k.jenis = 'wa'), 0)
    || coalesce(' (paling diminati ' || (select k.kode from kunjungan k where k.hari = v_kmr and k.jenis in ('wa','detail') and k.kode <> '' group by k.kode order by sum(k.jumlah) desc limit 1) || ')', '')
    || E'\n• Pesanan baru: ' || (select count(*) from pesanan o where (o.created_at at time zone 'Asia/Jakarta')::date = v_kmr)
    || E'\n• Lunas: ' || (select count(*) from pesanan o where o.status = 'lunas' and (o.lunas_at at time zone 'Asia/Jakarta')::date = v_kmr)
    || E'\n• Ulasan baru: ' || (select count(*) from ulasan u where (u.created_at at time zone 'Asia/Jakarta')::date = v_kmr);
  a := '☀️ *Rekap pagi Barokah Farm* · ' || v_hari || a || E'\n\nKetik *stok* untuk detail, *bantuan* untuk daftar perintah.';

  select string_agg('• ' || _plabel(o) || coalesce(' — ' || left(o.alamat_kirim, 80), ''), E'\n' order by o.id)
    into x from pesanan o where o.status = 'lunas' and o.lunas_at > now() - interval '3 days';
  if x is not null then s := s || E'\n\n*Lunas, siapkan untuk dikirim/diambil*\n' || x; end if;
  select string_agg('• ' || _plabel(o) || ' (lunas paling lambat ' || to_char(o.batas_lunas at time zone 'Asia/Jakarta','DD/MM') || ')', E'\n' order by o.id)
    into x from pesanan o where o.status in ('dp','cek_lunas');
  if x is not null then s := s || E'\n\n*Sudah DP, sisihkan ekornya*\n' || x; end if;
  select string_agg('• ' || pr.kode || ' ' || pr.nama || coalesce(' ' || _berat(pr), '') || ': ' || pr.stok || ' ekor', E'\n' order by pr.urutan)
    into x from produk pr where pr.stok is not null and (pr.tampil or pr.stok > 0);
  s := '☀️ *Rekap kandang* · ' || v_hari || s || E'\n\n*Stok di website*\n' || coalesce(x, '-')
    || E'\n\nCocokkan dengan isi kandang. Ada yang laku langsung? kirim *laku K-01 1*. Kambing baru masuk? *tambah stok K-01 5*.';

  return jsonb_build_object('admin', _rapikan(a), 'staf', _rapikan(s),
    'ke_admin', _penerima('admin_wa', 'admin_chat'), 'ke_staf', _penerima('staf_wa', 'staf_chat'));
end $function$
;

CREATE OR REPLACE FUNCTION public.set_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public'
AS $function$
begin new.updated_at = now(); return new; end $function$
;

-- ---------- hak akses (RLS aktif di semua tabel; akses publik hanya lewat view & fungsi) ----------
grant select on galeri_publik, katalog, katalog_produk, pengaturan_publik, testimoni_publik, ulasan_publik to anon;
grant execute on function admin_aksi(text, jsonb), admin_tunda(text, text, jsonb), alarm_cek(text),
  bot_alamat(text, text, text), bot_batal(text, text, text), bot_bukti(text, text, text, integer), bot_cek(text, text),
  bot_info(text, text), bot_keluar(text, text, text), bot_masuk(text, text, text, text, text, text), bot_oper(text, text, text),
  bot_pesan(text, text, text, integer, text), bot_tahan(text, text, text, text), bot_ulasan(text, text, integer, text),
  catat_kunjungan(text, text), jadwal_cek(text), rekap_pagi(text) to anon;
