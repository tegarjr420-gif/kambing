-- 2026-10-20: chat yang dioper OTOMATIS ke admin tidak boleh macet selamanya.
-- Masalah: kalau AI gagal / AI mengoper ke admin, percakapan masuk mode 'manusia'
-- dan bot diam terus sampai admin mengetik "bot <nomor>". Bila admin tidak sempat
-- membalas, pembeli tidak dijawab sama sekali (kasus Kak Gusti 19-20/10).
-- Perbaikan:
--   * oper otomatis (bot_oper) -> mode manusia hanya sampai oper_sampai (2 jam);
--   * bot_masuk mengembalikan chat ke bot bila waktu oper sudah lewat;
--   * "ambil alih" oleh admin tetap permanen (oper_sampai null) sampai "bot <nomor>".

alter table percakapan add column if not exists oper_sampai timestamptz;

create or replace function public.bot_oper(p_key text, p_chat text, p_alasan text)
 returns jsonb language plpgsql security definer set search_path to 'public' as $function$
begin
  perform _cek(p_key);
  update percakapan set mode = 'manusia', alasan_oper = p_alasan,
         oper_sampai = now() + interval '2 hours'
   where chat_id = p_chat;
  return jsonb_build_object('ok', true, 'wa', (select wa from percakapan where chat_id = p_chat),
    'nama', (select nama from percakapan where chat_id = p_chat), 'alasan', p_alasan);
end $function$;

-- kembalikan chat yang terlanjur macet (oper otomatis lama, belum punya oper_sampai)
update percakapan set mode = 'bot', alasan_oper = null, oper_sampai = null
 where mode = 'manusia' and oper_sampai is null and alasan_oper is not null;

-- bot_masuk: oper otomatis yang sudah lewat waktunya -> kembali ke bot
do $$
declare d text := pg_get_functiondef('public.bot_masuk'::regproc);
begin
  if position('oper_sampai' in d) = 0 then
    d := replace(d, E'  returning mode into v_mode;\n',
      E'  returning mode into v_mode;\n\n'
      || E'  if v_mode = ''manusia'' and exists (select 1 from percakapan where chat_id = p_chat\n'
      || E'       and oper_sampai is not null and oper_sampai < now()) then\n'
      || E'    update percakapan set mode = ''bot'', alasan_oper = null, oper_sampai = null where chat_id = p_chat;\n'
      || E'    v_mode := ''bot'';\n'
      || E'  end if;\n');
    if position('oper_sampai' in d) = 0 then raise exception 'anchor bot_masuk tidak ketemu'; end if;
    execute d;
  end if;
end $$;

-- admin_aksi: "ambil alih" = permanen sampai "bot <nomor>"; "bot <nomor>" membersihkan sisa oper
do $$
declare d text := pg_get_functiondef('public.admin_aksi'::regproc);
  lama text := E'update percakapan set mode = case a when ''ambil_alih'' then ''manusia'' else ''bot'' end\n';
begin
  if position('oper_sampai' in d) = 0 then
    if position(lama in d) = 0 then raise exception 'anchor admin_aksi tidak ketemu'; end if;
    d := replace(d, lama, E'update percakapan set mode = case a when ''ambil_alih'' then ''manusia'' else ''bot'' end,\n'
      || E'           oper_sampai = null, alasan_oper = case a when ''ambil_alih'' then ''diambil alih admin'' end\n');
    execute d;
  end if;
end $$;
