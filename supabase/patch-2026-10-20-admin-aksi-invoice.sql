-- 2026-10-20 bagian 2: admin_aksi mencatat buku kas + membuat invoice (DP, lunas, penjualan kandang).
--   konfirmasi_dp  -> transaksi 'dp' + invoice DP ke pembeli
--   lunas          -> harga akhir (opsional "harga"), ongkir (opsional), transaksi 'pelunasan' + invoice LUNAS
--   laku + harga   -> pesanan sumber 'kandang' (lunas) + transaksi 'penjualan_kandang' + invoice ke nomor WA pembeli
--   batal_pesanan  -> DP yang sudah tercatat dicatat dikembalikan (refund_dp)
-- Notif invoice dikirim dengan peristiwa 'invoice' (n8n meneruskan ke mesin untuk dibuat PDF lalu dikirim lewat WA).

create or replace function public.admin_aksi(p_key text, p_aksi jsonb)
 returns jsonb
 language plpgsql
 security definer
 set search_path to 'public'
as $function$
declare
  a text := p_aksi->>'aksi';
  ids bigint[];
  v_notif jsonb := '[]'::jsonb;
  v_hasil text := '';
  r pesanan; p produk; n int; v_kode text; v_pref text; v_kat text; v_opsi jsonb; v_sampai timestamptz;
  v_batas int := coalesce(_set('batas_hari'),'3')::int;
  v_inv jsonb; v_tid bigint; v_harga int; v_ongkir int; v_dp int; v_wa text; v_ambil boolean;
  v_oleh text := nullif(p_aksi->>'oleh','');
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
               nominal_dp = coalesce(nullif(p_aksi->>'nominal','')::int, nominal_dp, _dp_min(pesanan.*))
             where id = any(ids) and status in ('menunggu_cek','ditahan') returning * loop
      if r.kambing_kode is not null then update kambing set status = 'dp' where kode = r.kambing_kode; end if;
      v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'dp_dikonfirmasi',
        'data', jsonb_build_object('kode', _plabel(r), 'harga', r.harga, 'nominal_dp', r.nominal_dp,
          'batas_lunas', to_char(r.batas_lunas at time zone 'Asia/Jakarta','DD/MM/YYYY HH24:MI'),
          'sisa', r.harga - coalesce(r.nominal_dp, 0)));
      insert into transaksi(jenis, pesanan_id, produk_kode, jumlah, nama, wa, nominal, harga, oleh)
        values ('dp', r.id, r.produk_kode, r.jumlah, r.nama, r.wa, r.nominal_dp, r.harga, v_oleh) returning id into v_tid;
      v_inv := _invoice(r, 'DP');
      update transaksi set invoice_no = v_inv->>'no' where id = v_tid;
      v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'invoice', 'invoice', v_inv);
      v_hasil := v_hasil || _plabel(r) || ': DP ' || _rp(r.nominal_dp) || ' dikonfirmasi, batas lunas '
        || to_char(r.batas_lunas at time zone 'Asia/Jakarta','DD/MM HH24:MI') || '. Invoice DP ' || (v_inv->>'no') || ' dikirim ke pembeli.' || E'\n';
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
    v_harga := case when cardinality(ids) = 1 then nullif(p_aksi->>'harga','')::int end;
    v_ongkir := nullif(p_aksi->>'ongkir','')::int;
    v_ambil := coalesce(p_aksi->>'ambil','') in ('true','ya','1');
    for r in update pesanan set status = 'lunas', lunas_at = now(),
               harga_final = coalesce(v_harga, harga_final, harga),
               ongkir = coalesce(v_ongkir, ongkir, 0),
               gratis_ongkir = coalesce(v_ongkir, ongkir, 0) = 0 and not v_ambil,
               ambil_sendiri = v_ambil or coalesce(ambil_sendiri, false)
             where id = any(ids) and status in ('dp','cek_lunas','menunggu_cek') returning * loop
      if r.kambing_kode is not null then update kambing set status = 'terjual' where kode = r.kambing_kode; end if;
      v_dp := coalesce((select sum(nominal) from transaksi where pesanan_id = r.id and jenis = 'dp'), 0);
      insert into transaksi(jenis, pesanan_id, produk_kode, jumlah, nama, wa, nominal, harga, ongkir, oleh)
        values ('pelunasan', r.id, r.produk_kode, r.jumlah, r.nama, r.wa,
                coalesce(r.harga_final, 0) + coalesce(r.ongkir, 0) - v_dp, r.harga_final, coalesce(r.ongkir, 0), v_oleh) returning id into v_tid;
      v_inv := _invoice(r, 'LUNAS');
      update transaksi set invoice_no = v_inv->>'no' where id = v_tid;
      v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'lunas',
        'data', jsonb_build_object('kode', _plabel(r), 'alamat', r.alamat_kirim, 'total', (v_inv->>'total')::int,
          'dp', v_dp, 'pelunasan', (v_inv->>'pelunasan')::int, 'ongkir', coalesce(r.ongkir, 0), 'ambil_sendiri', r.ambil_sendiri));
      v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'invoice', 'invoice', v_inv);
      v_hasil := v_hasil || _plabel(r) || ': LUNAS. Total ' || _rp((v_inv->>'total')::int) || ' (hewan ' || _rp(r.harga_final)
        || case when coalesce(r.ongkir, 0) > 0 then ' + ongkir ' || _rp(r.ongkir) when r.ambil_sendiri then ', diambil sendiri' else ', gratis ongkir' end
        || '), DP ' || _rp(v_dp) || ', pelunasan ' || _rp((v_inv->>'pelunasan')::int) || '. Invoice ' || (v_inv->>'no') || ' dikirim ke pembeli.' || E'\n';
    end loop;

  elsif a = 'batal_pesanan' then
    for r in update pesanan set status = 'batal', alasan = coalesce(nullif(p_aksi->>'alasan',''), 'dibatalkan admin')
             where id = any(ids) and status in ('ditahan','menunggu_cek','dp','cek_lunas') returning * loop
      perform _stok_kembali(r);
      v_dp := coalesce((select sum(nominal) from transaksi where pesanan_id = r.id and jenis in ('dp','refund_dp')), 0);
      if v_dp > 0 then
        insert into transaksi(jenis, pesanan_id, produk_kode, jumlah, nama, wa, nominal, oleh, catatan)
          values ('refund_dp', r.id, r.produk_kode, r.jumlah, r.nama, r.wa, -v_dp, v_oleh, 'DP dikembalikan, pesanan dibatalkan sebelum batas');
      end if;
      v_hasil := v_hasil || _plabel(r) || ': dibatalkan, stok dikembalikan'
        || case when v_dp > 0 then '. DP ' || _rp(v_dp) || ' dicatat DIKEMBALIKAN, mohon transfer balik ke pembeli' else '' end || E'\n';
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
      if a = 'laku' then
        v_harga := nullif(p_aksi->>'harga','')::int;
        v_ongkir := coalesce(nullif(p_aksi->>'ongkir','')::int, 0);
        v_wa := _wa62(p_aksi->>'wa');
        if length(coalesce(v_wa, '')) < 9 then v_wa := null; end if;
        v_ambil := v_ongkir = 0 and coalesce(p_aksi->>'kirim','') not in ('true','ya','1');
        if v_harga is not null then
          insert into pesanan(produk_kode, jumlah, chat_id, wa, nama, alamat_kirim, status, harga, harga_final, ongkir,
                              gratis_ongkir, ambil_sendiri, sumber, lunas_at, ulasan_diminta)
          values (p.kode, abs(n), case when v_wa is not null then v_wa || '@c.us' end, v_wa, nullif(p_aksi->>'nama',''), nullif(p_aksi->>'alamat',''),
                  'lunas', v_harga, v_harga, v_ongkir, v_ongkir = 0 and not v_ambil, v_ambil, 'kandang', now(),
                  case when v_wa is null then now() end)
          returning * into r;
          insert into transaksi(jenis, pesanan_id, produk_kode, jumlah, nama, wa, nominal, harga, ongkir, oleh)
            values ('penjualan_kandang', r.id, p.kode, abs(n), r.nama, v_wa, v_harga + v_ongkir, v_harga, v_ongkir, v_oleh) returning id into v_tid;
          v_inv := _invoice(r, 'PENJUALAN');
          update transaksi set invoice_no = v_inv->>'no' where id = v_tid;
          if r.chat_id is not null then
            v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'invoice', 'invoice', v_inv);
          end if;
          v_hasil := v_hasil || E'\nTercatat penjualan #' || r.id || ' ' || _rp(v_harga + v_ongkir)
            || case when v_ongkir > 0 then ' (termasuk ongkir ' || _rp(v_ongkir) || ')' else '' end
            || case when r.chat_id is not null then '. Invoice ' || (v_inv->>'no') || ' dikirim ke ' || v_wa || '.'
                    else '. Invoice tidak dikirim karena nomor WA pembeli tidak disebut.' end;
        else
          v_hasil := v_hasil || E'\n(Harga tidak disebut, penjualan ini TIDAK masuk rekap keuangan. Lain kali tulis: "laku '
            || p.kode || ' 1 harga 1,5jt wa 0812xxxx")';
        end if;
      end if;
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
end $function$;

-- rekap pagi: penjualan langsung di kandang tidak perlu "disiapkan", + uang masuk kemarin
do $$
declare d text := pg_get_functiondef('public.rekap_pagi'::regproc);
begin
  if position('o.status = ''lunas'' and o.lunas_at > now() - interval ''3 days''' in d) = 0 then raise exception 'rekap_pagi berubah'; end if;
  d := replace(d, 'o.status = ''lunas'' and o.lunas_at > now() - interval ''3 days''',
                  'o.status = ''lunas'' and coalesce(o.sumber, ''online'') <> ''kandang'' and o.lunas_at > now() - interval ''3 days''');
  d := replace(d, '|| E''\n• Ulasan baru: ''',
                  '|| E''\n• Uang masuk: '' || _rp(coalesce((select sum(t.nominal) from transaksi t where (t.waktu at time zone ''Asia/Jakarta'')::date = v_kmr), 0)::int) || '' (ketik *rekapan* untuk laporan PDF)'' || E''\n• Ulasan baru: ''');
  execute d;
end $$;
