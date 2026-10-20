-- 2026-10-20 malam: foto hewan ikut masuk invoice + invoice penjualan kandang dikirim ke ADMIN.
--   * admin/staf mengirim foto + "lunas 12 ..." / "laku K-01 ..." -> URL foto disimpan di pesanan.foto_invoice
--     dan ikut di data invoice (mesin menyusunnya jadi bingkai/grid foto).
--   * laku di kandang: invoice TIDAK dikirim bot ke nomor pembeli (nomor baru = risiko blokir WA),
--     tetapi dikirim ke semua admin dengan permintaan untuk meneruskannya dari HP admin.
--   * pesanan kandang tidak dimintai ulasan otomatis oleh bot (alasan yang sama).

alter table pesanan add column if not exists foto_invoice jsonb;

-- daftar URL foto yang valid (maks 6) dari p_aksi->'foto_invoice'
create or replace function _foto_inv(p_aksi jsonb) returns jsonb
language sql immutable set search_path to 'public' as $$
  select nullif(coalesce((select jsonb_agg(u) from (
      select u from jsonb_array_elements_text(case when jsonb_typeof(p_aksi->'foto_invoice') = 'array' then p_aksi->'foto_invoice'
                                                    when jsonb_typeof(p_aksi->'foto_invoice') = 'string' then jsonb_build_array(p_aksi->>'foto_invoice')
                                                    else '[]'::jsonb end) u
       where u ~ '^https?://' limit 6) x), '[]'::jsonb), '[]'::jsonb)
$$;
revoke execute on function _foto_inv(jsonb) from public, anon, authenticated;

-- _invoice: sertakan foto
do $$
declare d text := pg_get_functiondef('public._invoice(pesanan,text)'::regprocedure);
begin
  if position('foto_invoice' in d) = 0 then
    if position($a$'total', v_total, 'dp', v_dp,$a$ in d) = 0 then raise exception 'anchor _invoice'; end if;
    d := replace(d, $a$'total', v_total, 'dp', v_dp,$a$, $a$'foto', coalesce(o.foto_invoice, '[]'::jsonb), 'total', v_total, 'dp', v_dp,$a$);
    execute d;
  end if;
end $$;

-- admin_aksi: lunas & laku menyimpan foto; invoice kandang ke admin
do $$
declare d text := pg_get_functiondef('public.admin_aksi'::regproc);
  procedure_ok boolean;
  function_pairs text[][] := array[
    -- lunas: simpan foto
    array[$a$               ambil_sendiri = v_ambil or coalesce(ambil_sendiri, false)
             where id = any(ids) and status in ('dp','cek_lunas','menunggu_cek') returning * loop$a$,
          $a$               ambil_sendiri = v_ambil or coalesce(ambil_sendiri, false),
               foto_invoice = coalesce(_foto_inv(p_aksi), foto_invoice)
             where id = any(ids) and status in ('dp','cek_lunas','menunggu_cek') returning * loop$a$],
    -- lunas: info jumlah foto
    array[$a$'. Invoice ' || (v_inv->>'no') || ' dikirim ke pembeli.' || E'\n';$a$,
          $a$'. Invoice ' || (v_inv->>'no') || case when jsonb_array_length(coalesce(r.foto_invoice, '[]'::jsonb)) > 0 then ' (dengan ' || jsonb_array_length(r.foto_invoice) || ' foto hewan)' else '' end || ' dikirim ke pembeli.' || E'\n';$a$],
    -- laku: kolom foto + tanpa permintaan ulasan otomatis
    array[$a$gratis_ongkir, ambil_sendiri, sumber, lunas_at, ulasan_diminta)$a$,
          $a$gratis_ongkir, ambil_sendiri, sumber, lunas_at, ulasan_diminta, foto_invoice)$a$],
    array[$a$'lunas', v_harga, v_harga, v_ongkir, v_ongkir = 0 and not v_ambil, v_ambil, 'kandang', now(),
                  case when v_wa is null then now() end)$a$,
          $a$'lunas', v_harga, v_harga, v_ongkir, v_ongkir = 0 and not v_ambil, v_ambil, 'kandang', now(),
                  now(), _foto_inv(p_aksi))$a$],
    -- laku: invoice ke semua admin untuk diteruskan manual
    array[$a$          if r.chat_id is not null then
            v_notif := v_notif || jsonb_build_object('chat_id', r.chat_id, 'peristiwa', 'invoice', 'invoice', v_inv);
          end if;$a$,
          $a$          v_notif := v_notif || coalesce((select jsonb_agg(jsonb_build_object('chat_id', trim(x) || '@c.us', 'peristiwa', 'invoice',
                       'invoice', v_inv || jsonb_build_object('ke_admin', true, 'teruskan_ke', v_wa)))
                     from unnest(string_to_array(coalesce(_set('admin_wa'), ''), ',')) x where trim(x) <> ''), '[]'::jsonb);$a$],
    array[$a$            || case when r.chat_id is not null then '. Invoice ' || (v_inv->>'no') || ' dikirim ke ' || v_wa || '.'
                    else '. Invoice tidak dikirim karena nomor WA pembeli tidak disebut.' end;$a$,
          $a$            || '. Invoice ' || (v_inv->>'no')
            || case when jsonb_array_length(coalesce(r.foto_invoice, '[]'::jsonb)) > 0 then ' (dengan ' || jsonb_array_length(r.foto_invoice) || ' foto hewan)' else '' end
            || ' dikirim ke WhatsApp admin'
            || case when v_wa is not null then ' untuk diteruskan ke pembeli (' || v_wa || ').' else ' (nomor WA pembeli tidak disebut).' end;$a$]
  ];
  i int;
begin
  if position('_foto_inv' in d) = 0 then
    for i in 1 .. array_length(function_pairs, 1) loop
      if position(function_pairs[i][1] in d) = 0 then raise exception 'anchor admin_aksi % tidak ketemu', i; end if;
      d := replace(d, function_pairs[i][1], function_pairs[i][2]);
    end loop;
    execute d;
  end if;
end $$;

-- "YA" setelah kirim foto tanpa perintah: beri petunjuk, jangan error
do $$
declare d text := pg_get_functiondef('public.admin_aksi'::regproc);
  lama text := $a$  else
    return jsonb_build_object('ok', false, 'ringkasan', 'Perintah tidak dikenali.$a$;
begin
  if position('foto_lepas' in d) = 0 then
    if position(lama in d) = 0 then raise exception 'anchor else admin_aksi'; end if;
    d := replace(d, lama, $a$  elsif a = 'foto_lepas' then
    return jsonb_build_object('ok', false, 'ringkasan', 'Fotonya sudah diterima, tapi belum ada perintahnya. Ketik dulu misalnya "lunas 12 harga 1,5jt" atau "laku K-01 1 harga 1,6jt wa 0812xxxx", nanti fotonya ikut masuk invoice.');
$a$ || lama);
    execute d;
  end if;
end $$;
