-- Fungsi bot & admin untuk katalog per produk (19/10/2026)

create or replace function public.bot_masuk(p_key text, p_chat text, p_wa text, p_nama text, p_teks text, p_media_url text default null)
returns jsonb language plpgsql security definer set search_path to 'public' as $function$
declare v_admin boolean; v_mode text; v_baru boolean := false; r jsonb;
begin
  perform _cek(p_key);
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
    'info', _info(),
    'sekarang', to_char(now() at time zone 'Asia/Jakarta','TMDay, DD/MM/YYYY HH24:MI')
  ) into r;
  return r;
end $function$;

-- Pesan (tahan) produk: p_jumlah = jumlah ekor (untuk paket aqiqah = pilihan ekor; untuk Qurban Paket = jumlah paket)
create or replace function public.bot_pesan(p_key text, p_chat text, p_kode text, p_jumlah integer default 1, p_nama text default null)
returns jsonb language plpgsql security definer set search_path to 'public' as $function$
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
  return jsonb_build_object('ok', true, 'no_pesanan', o.id, 'pesanan', _plabel(o), 'produk', _prod_ringkas(p),
    'jumlah', v_j, 'total_ekor', v_ekor, 'harga_total', v_harga, 'flash_sale', _flash_aktif(p),
    'dp_minimal', coalesce(_set('dp_min')::int,100000) * v_ekor,
    'ditahan_menit', v_menit, 'ditahan_sampai', to_char(o.ditahan_sampai at time zone 'Asia/Jakarta','HH24:MI'), 'info', _info());
end $function$;

create or replace function public.bot_batal(p_key text, p_chat text, p_kode text default null)
returns jsonb language plpgsql security definer set search_path to 'public' as $function$
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
end $function$;

create or replace function public.bot_bukti(p_key text, p_chat text, p_bukti_url text, p_nominal integer default null)
returns jsonb language plpgsql security definer set search_path to 'public' as $function$
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
end $function$;

create or replace function public.bot_ulasan(p_key text, p_chat text, p_bintang integer, p_komentar text default null)
returns jsonb language plpgsql security definer set search_path to 'public' as $function$
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
end $function$;

create or replace function public.jadwal_cek(p_key text)
returns jsonb language plpgsql security definer set search_path to 'public' as $function$
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
  -- minta ulasan 2 hari setelah lunas, hanya jam 09.00–19.59 WIB
  if v_jam between 9 and 19 then
    for r in update pesanan set ulasan_diminta = now()
             where status = 'lunas' and ulasan_diminta is null and lunas_at is not null and lunas_at < now() - interval '2 days'
               and not exists (select 1 from ulasan u where u.pesanan_id = pesanan.id)
             returning * loop
      v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'minta_ulasan', 'data', jsonb_build_object('kode', _plabel(r)));
    end loop;
  end if;
  return jsonb_build_object('notif', v_notif, 'admin', nullif(v_admin, ''), 'admin_wa', _set('admin_wa'));
end $function$;
