import { workflow, node, trigger, ifElse, switchCase, languageModel, tool, fromAi, expr } from '@n8n/workflow-sdk';

const KIRIM_TEKS_ID = 'QUdqtULgALOhnglF';
const PESAN_SISTEM_ID = 'cbmyNmUG0jdT9LcO';

const skemaKirimTeks = [
  { id: 'chat_id', displayName: 'chat_id', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'string' },
  { id: 'teks', displayName: 'teks', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'string' },
  { id: 'gambar_url', displayName: 'gambar_url', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'string' },
  { id: 'tes', displayName: 'tes', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'boolean' },
  { id: 'catat', displayName: 'catat', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'boolean' }
];

const skemaPesanSistem = [
  { id: 'chat_id', displayName: 'chat_id', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'string' },
  { id: 'peristiwa', displayName: 'peristiwa', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'string' },
  { id: 'data', displayName: 'data', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'object' },
  { id: 'tes', displayName: 'tes', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'boolean' }
];

const H_SUPABASE = '{{ JSON.stringify({ apikey: $("Ambil Konfigurasi").first().json.supabase_key, Authorization: "Bearer " + $("Ambil Konfigurasi").first().json.supabase_key }) }}';
const URL_RPC = "{{ $('Ambil Konfigurasi').first().json.supabase_url }}/rest/v1/rpc/";
const KEY = '$("Ambil Konfigurasi").first().json.bot_key';
const CHAT = '$("Rapikan Pesan").first().json.chat_id';
const TES = '$("Rapikan Pesan").first().json.tes';

const masuk = trigger({
  type: 'n8n-nodes-base.webhook',
  version: 2.2,
  config: {
    name: 'Pesan WhatsApp Masuk',
    parameters: { httpMethod: 'POST', path: 'barokah-farm-wa', responseMode: 'onReceived', options: {} },
    position: [0, 600]
  },
  output: [{ body: { event: 'message', session: 'default', payload: { id: 'false_628@c.us_ABC', from: '6281234567890@c.us', fromMe: false, body: 'Halo, kambing BF-01 masih ada?', hasMedia: false, _data: { pushName: 'Budi' } } } }]
});

const rapikan = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Rapikan Pesan',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const j = $input.first().json;\nconst b = j.body || j;\nconst p = b.payload || {};\nconst ev = String(b.event || '');\nconst from = String(p.from || '');\nif (!(ev === 'message' || ev === 'message.any') || p.fromMe || !from || /@g\\.us$|@newsletter$|status@broadcast|@broadcast$/.test(from)) return [];\nconst d = p._data || {};\nconst key = d.key || {};\nconst cands = [key.remoteJidAlt, key.senderPn, key.participantAlt, d.senderPn, p.participant].filter(Boolean);\nconst alt = cands.find(x => /@s\\.whatsapp\\.net$|@c\\.us$/.test(String(x)));\nlet wa = '';\nif (/@c\\.us$|@s\\.whatsapp\\.net$/.test(from)) wa = from.split('@')[0];\nelse if (alt) wa = String(alt).split('@')[0];\nwa = wa.replace(/\\D/g, '').replace(/:\\d+$/, '');\nconst media = p.media || null;\nconst mime = String((media && media.mimetype) || '');\nconst adaGambar = !!(p.hasMedia && media && media.url && mime.startsWith('image/'));\nlet teks = String(p.body || (media && media.caption) || '').trim();\nif (!teks && p.hasMedia && !adaGambar) teks = '[pembeli mengirim ' + (mime.startsWith('audio') ? 'pesan suara' : 'file/media') + ', bukan teks]';\nif (!teks && adaGambar) teks = '[gambar]';\nif (!teks) return [];\nreturn [{ json: { chat_id: from, wa, nama: d.pushName || d.notifyName || p.notifyName || '', teks, ada_gambar: adaGambar, media_url: adaGambar ? media.url : '', tes: b.tes === true || b.tes === 'true' } }];"
    },
    position: [220, 600]
  },
  output: [{ chat_id: '6281234567890@c.us', wa: '6281234567890', nama: 'Budi', teks: 'Halo, kambing BF-01 masih ada?', ada_gambar: false, media_url: '', tes: true }]
});

const ambilKonfigurasi = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Ambil Konfigurasi',
    parameters: { resource: 'row', operation: 'get', dataTableId: { __rl: true, mode: 'id', value: 'u7nj3ra9Giao0bMQ' }, returnAll: false, limit: 1 },
    executeOnce: true,
    position: [440, 600]
  },
  output: [{ supabase_url: 'https://x.supabase.co', supabase_key: 'sb_publishable_x', bot_key: 'bk_x', waha_url: 'https://waha.example', waha_key: 'k', foto_prefix: 'u1' }]
});

const konteks = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Catat Pesan & Ambil Konteks',
    parameters: {
      method: 'POST',
      url: expr(URL_RPC + 'bot_masuk'),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr(H_SUPABASE),
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify({ p_key: ' + KEY + ', p_chat: ' + CHAT + ', p_wa: $("Rapikan Pesan").first().json.wa, p_nama: $("Rapikan Pesan").first().json.nama, p_teks: $("Rapikan Pesan").first().json.teks, p_media_url: $("Rapikan Pesan").first().json.media_url || null }) }}')
    },
    position: [660, 600]
  },
  output: [{ peran: 'pembeli', admin_baru: false, mode: 'bot', aksi_tertunda: null, nama: 'Budi', riwayat: [], pesanan: [], stok: [{ kode: 'BF-01', jenis: 'Kambing', ras: 'Jawa', kelamin: 'Jantan', berat_kg: 32, umur_bulan: 18, harga: 3250000, status: 'tersedia', layak_kurban: true }], sedang_dipesan: [], info: { rekening: 'BRI 808001004661537 a.n. Muriyadi', dp_min: 100000, batas_hari: 3, admin_wa: '62881010021694' }, sekarang: 'Senin, 19/10/2026 10:00' }]
});

const arahkan = switchCase({
  version: 3.2,
  config: {
    name: 'Siapa Pengirimnya?',
    parameters: {
      rules: {
        values: [
          { outputKey: 'Admin baru daftar', conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'loose' }, conditions: [{ leftValue: expr('{{ $json.admin_baru }}'), operator: { type: 'boolean', operation: 'true', singleValue: true } }], combinator: 'and' } },
          { outputKey: 'Admin', conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'loose' }, conditions: [{ leftValue: expr('{{ $json.peran }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'admin' }], combinator: 'and' } },
          { outputKey: 'Pembeli (bot aktif)', conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'loose' }, conditions: [{ leftValue: expr('{{ $json.peran }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'pembeli' }, { leftValue: expr('{{ $json.mode }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'bot' }], combinator: 'and' } }
        ]
      },
      options: {}
    },
    position: [880, 600]
  }
});

const sambutAdmin = node({
  type: 'n8n-nodes-base.executeWorkflow',
  version: 1.4,
  config: {
    name: 'Sambut Admin Baru',
    parameters: {
      mode: 'each',
      source: 'database',
      workflowId: { __rl: true, mode: 'id', value: KIRIM_TEKS_ID },
      workflowInputs: { mappingMode: 'defineBelow', value: { chat_id: expr('{{ ' + CHAT + ' }}'), teks: '✅ Nomor ini sekarang terdaftar sebagai *admin Barokah Farm*. Ketik *bantuan* untuk melihat daftar perintah.', gambar_url: '', tes: expr('{{ ' + TES + ' }}'), catat: false }, matchingColumns: [], schema: skemaKirimTeks, attemptToConvertTypes: false },
      options: { waitForSubWorkflow: true }
    },
    position: [1100, 300]
  },
  output: [{ ok: true }]
});

const pembeliGambar = ifElse({
  version: 2.2,
  config: {
    name: 'Pembeli Kirim Gambar?',
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'loose' },
        conditions: [{ leftValue: expr('{{ $("Rapikan Pesan").first().json.ada_gambar }}'), operator: { type: 'boolean', operation: 'true', singleValue: true } }],
        combinator: 'and'
      }
    },
    position: [1100, 900]
  }
});

const unduhGambar = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Unduh Gambar Pembeli',
    parameters: {
      method: 'GET',
      url: expr('{{ $("Rapikan Pesan").first().json.media_url }}'),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr('{{ JSON.stringify({ "X-Api-Key": $("Ambil Konfigurasi").first().json.waha_key }) }}'),
      options: { response: { response: { responseFormat: 'file', outputPropertyName: 'data' } } }
    },
    position: [1320, 800]
  },
  output: [{}]
});

const geminiVisi = languageModel({
  type: '@n8n/n8n-nodes-langchain.lmChatGoogleGemini',
  version: 1.2,
  config: {
    name: 'Gemini Baca Gambar',
    parameters: { modelName: 'models/gemini-2.5-flash', options: { temperature: 0.1, maxOutputTokens: 2048 } },
    credentials: { googlePalmApi: { id: 'F10q2z7pzu5B47PS', name: 'Google Gemini(PaLM) Api account' } },
    position: [1540, 1000]
  }
});

const bacaGambar = node({
  type: '@n8n/n8n-nodes-langchain.chainLlm',
  version: 1.9,
  config: {
    name: 'Baca Gambar Pembeli',
    parameters: {
      promptType: 'define',
      text: expr('Periksa gambar yang dikirim pembeli. Keterangan dari pembeli: {{ $("Rapikan Pesan").first().json.teks }}'),
      messages: {
        messageValues: [
          { type: 'SystemMessagePromptTemplate', message: 'Kamu memeriksa gambar yang dikirim pembeli ke WhatsApp toko kambing Barokah Farm. Jawab HANYA satu objek JSON valid, tanpa teks lain, dengan kunci: bukti_transfer (true bila gambar adalah bukti transfer/struk/mutasi bank), nominal (angka rupiah tanpa titik atau null), bank (string), tanggal (string seperti tertulis), nama_pengirim (string), rekening_tujuan_cocok (true bila tujuan BRI 808001004661537 a.n. Muriyadi, false bila jelas berbeda, null bila tidak terlihat), kejanggalan (array string, contoh: nominal di bawah Rp100.000, tujuan bukan rekening toko, foto buram, tanggal lama, tanda editan), deskripsi (satu kalimat isi gambar).' },
          { type: 'HumanMessagePromptTemplate', messageType: 'imageBinary', binaryImageDataKey: 'data', imageDetail: 'auto' }
        ]
      }
    },
    subnodes: { model: geminiVisi },
    position: [1540, 800]
  },
  output: [{ text: '{"bukti_transfer":true,"nominal":100000,"bank":"BRI","tanggal":"19 Okt 2026","nama_pengirim":"BUDI","rekening_tujuan_cocok":true,"kejanggalan":[],"deskripsi":"Struk transfer BRImo"}' }]
});

const nilaiGambar = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Nilai Gambar',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const raw = String($input.first().json.text || '');\nlet g = {};\ntry { g = JSON.parse(raw.slice(raw.indexOf('{'), raw.lastIndexOf('}') + 1)); } catch (e) { g = { bukti_transfer: false, deskripsi: 'gambar tidak terbaca' }; }\nconst k = $('Catat Pesan & Ambil Konteks').first().json;\nconst bayar = (k.pesanan || []).filter(p => ['ditahan', 'dp'].includes(p.status));\nconst kej = Array.isArray(g.kejanggalan) ? g.kejanggalan.slice() : [];\nif (g.nominal && Number(g.nominal) < 100000 && bayar.some(p => p.status === 'ditahan')) kej.push('nominal di bawah DP minimal Rp100.000');\nif (g.rekening_tujuan_cocok === false) kej.push('rekening tujuan tidak sama dengan rekening toko');\nreturn [{ json: { ...g, kejanggalan: [...new Set(kej)], untuk_pesanan: g.bukti_transfer === true && bayar.length > 0, kode_pesanan: bayar.map(p => p.kode) }, binary: $('Unduh Gambar Pembeli').first().binary }];"
    },
    position: [1880, 800]
  },
  output: [{ bukti_transfer: true, nominal: 100000, bank: 'BRI', tanggal: '19 Okt 2026', nama_pengirim: 'BUDI', kejanggalan: [], deskripsi: 'Struk transfer', untuk_pesanan: true, kode_pesanan: ['BF-01'] }]
});

const buktiPesanan = ifElse({
  version: 2.2,
  config: {
    name: 'Bukti untuk Pesanan?',
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'loose' },
        conditions: [{ leftValue: expr('{{ $json.untuk_pesanan }}'), operator: { type: 'boolean', operation: 'true', singleValue: true } }],
        combinator: 'and'
      }
    },
    position: [2100, 800]
  }
});

const simpanBukti = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Simpan Bukti ke Storage',
    parameters: {
      method: 'POST',
      url: expr('{{ $("Ambil Konfigurasi").first().json.supabase_url }}/storage/v1/object/foto/{{ $("Ambil Konfigurasi").first().json.foto_prefix }}/bukti/{{ $("Rapikan Pesan").first().json.chat_id.replace(/\\D/g, "") }}-{{ $now.toFormat("yyyyMMddHHmmss") }}.jpg'),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr('{{ JSON.stringify({ apikey: $("Ambil Konfigurasi").first().json.supabase_key, Authorization: "Bearer " + $("Ambil Konfigurasi").first().json.supabase_key, "x-upsert": "true", "Content-Type": "image/jpeg" }) }}'),
      sendBody: true,
      contentType: 'binaryData',
      inputDataFieldName: 'data'
    },
    position: [2320, 700]
  },
  output: [{ Key: 'foto/u1/bukti/628-20261019.jpg' }]
});

const catatBukti = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Catat Bukti Transfer',
    parameters: {
      method: 'POST',
      url: expr(URL_RPC + 'bot_bukti'),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr(H_SUPABASE),
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify({ p_key: ' + KEY + ', p_chat: ' + CHAT + ', p_bukti_url: $("Ambil Konfigurasi").first().json.supabase_url + "/storage/v1/object/public/" + $json.Key, p_nominal: $("Nilai Gambar").first().json.nominal ? Math.round(Number($("Nilai Gambar").first().json.nominal)) : null }) }}')
    },
    position: [2540, 700]
  },
  output: [{ ok: true, jenis: 'dp', pesanan: [{ kode: 'BF-01', harga: 3250000 }], nama: 'Budi', wa: '6281234567890' }]
});

const laporanBukti = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Susun Laporan Bukti',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const r = $input.first().json;\nconst g = $('Nilai Gambar').first().json;\nconst k = $('Catat Pesan & Ambil Konteks').first().json;\nconst m = $('Rapikan Pesan').first().json;\nconst url = $('Ambil Konfigurasi').first().json.supabase_url + '/storage/v1/object/public/' + $('Simpan Bukti ke Storage').first().json.Key;\nconst rp = n => n ? 'Rp' + Number(n).toLocaleString('id-ID') : '-';\nconst kode = (r.pesanan || []).map(p => p.kode);\nconst jenis = r.jenis === 'pelunasan' ? 'PELUNASAN' : 'DP';\nconst kej = (g.kejanggalan || []).length ? '\\n⚠️ Perlu dicek: ' + g.kejanggalan.join('; ') : '';\nconst teks = `🧾 *Bukti ${jenis} masuk*\\nKambing: ${kode.join(', ')}\\nPembeli: ${m.nama || '-'} (wa.me/${m.wa || m.chat_id.split('@')[0]})\\nTerbaca: ${rp(g.nominal)} ${g.bank || ''} ${g.tanggal || ''} a.n. ${g.nama_pengirim || '-'}${kej}\\n\\nCek mutasi, lalu balas:\\n*OK ${kode[0] || ''}* bila dana masuk\\n*TOLAK ${kode[0] || ''} alasan* bila tidak`;\nconst admin = String(k.info.admin_wa || '').split(',').map(s => s.trim()).filter(Boolean).map(n => n + '@c.us');\nreturn [{ json: { admin: admin.map(c => ({ chat_id: c })), teks, gambar_url: url, catatan: `Bukti transfer ${jenis} dari pembeli untuk ${kode.join(', ')} sudah DITERIMA sistem dan DITERUSKAN ke admin untuk dicek mutasinya. Terbaca: ${rp(g.nominal)}. Sampaikan bahwa bukti sudah diterima dan sedang dicek admin; JANGAN bilang dana sudah masuk.${kej ? ' Ada kejanggalan (' + g.kejanggalan.join('; ') + '): sampaikan dengan sopan bahwa admin akan mengecek dan mungkin menghubungi.' : ''}` } }];"
    },
    position: [2760, 700]
  },
  output: [{ admin: [{ chat_id: '62881010021694@c.us' }], teks: 'Bukti DP masuk', gambar_url: 'https://x/foto.jpg', catatan: 'Bukti diterima' }]
});

const pecahAdminBukti = node({
  type: 'n8n-nodes-base.splitOut',
  version: 1.1,
  config: {
    name: 'Per Admin (Bukti)',
    parameters: { fieldToSplitOut: 'admin', include: 'selectedOtherFields', fieldsToInclude: 'teks, gambar_url', options: {} },
    position: [2980, 560]
  },
  output: [{ chat_id: '62881010021694@c.us', teks: 'Bukti DP masuk', gambar_url: 'https://x/foto.jpg' }]
});

const teruskanBukti = node({
  type: 'n8n-nodes-base.executeWorkflow',
  version: 1.4,
  config: {
    name: 'Teruskan Bukti ke Admin',
    parameters: {
      mode: 'each',
      source: 'database',
      workflowId: { __rl: true, mode: 'id', value: KIRIM_TEKS_ID },
      workflowInputs: { mappingMode: 'defineBelow', value: { chat_id: expr('{{ $json.chat_id }}'), teks: expr('{{ $json.teks }}'), gambar_url: expr('{{ $json.gambar_url }}'), tes: expr('{{ ' + TES + ' }}'), catat: false }, matchingColumns: [], schema: skemaKirimTeks, attemptToConvertTypes: false },
      options: { waitForSubWorkflow: true }
    },
    onError: 'continueRegularOutput',
    position: [3200, 560]
  },
  output: [{ ok: true }]
});

const catatanBukti = node({
  type: 'n8n-nodes-base.set',
  version: 3.4,
  config: {
    name: 'Catatan: Bukti Diteruskan',
    parameters: { mode: 'manual', includeOtherFields: false, assignments: { assignments: [{ id: 'c1', name: 'catatan', value: expr('{{ $json.catatan }}'), type: 'string' }] } },
    position: [2980, 820]
  },
  output: [{ catatan: 'Bukti diterima' }]
});

const catatanGambar = node({
  type: 'n8n-nodes-base.set',
  version: 3.4,
  config: {
    name: 'Catatan: Gambar Biasa',
    parameters: { mode: 'manual', includeOtherFields: false, assignments: { assignments: [{ id: 'c2', name: 'catatan', value: expr('Pembeli mengirim gambar. Isi gambar: {{ $json.deskripsi || "-" }}. {{ $json.bukti_transfer ? "Gambar tampak seperti bukti transfer, tetapi pembeli belum punya pesanan yang sedang ditahan/DP. Tanyakan kambing mana yang dimaksud dan jangan bilang dana sudah masuk; bila membingungkan, oper ke admin." : "Ini bukan bukti transfer." }}'), type: 'string' }] } },
    position: [2320, 960]
  },
  output: [{ catatan: 'Pembeli mengirim gambar.' }]
});

const catatanTeks = node({
  type: 'n8n-nodes-base.set',
  version: 3.4,
  config: {
    name: 'Catatan: Pesan Teks',
    parameters: { mode: 'manual', includeOtherFields: false, assignments: { assignments: [{ id: 'c3', name: 'catatan', value: '-', type: 'string' }] } },
    position: [1320, 1100]
  },
  output: [{ catatan: '-' }]
});

const geminiCs = languageModel({
  type: '@n8n/n8n-nodes-langchain.lmChatGoogleGemini',
  version: 1.2,
  config: {
    name: 'Gemini 2.5 Flash (CS)',
    parameters: { modelName: 'models/gemini-2.5-flash', options: { temperature: 0.7, maxOutputTokens: 4096 } },
    credentials: { googlePalmApi: { id: 'F10q2z7pzu5B47PS', name: 'Google Gemini(PaLM) Api account' } },
    position: [3200, 1260]
  }
});

const alatTahan = tool({
  type: 'n8n-nodes-base.httpRequestTool',
  version: 4.5,
  config: {
    name: 'tahan_kambing',
    parameters: {
      toolDescription: 'Kunci (tahan) satu kambing untuk pembeli ini selama 60 menit saat pembeli mau DP/pesan. Input: kode kambing (contoh BF-07) dan nama pembeli bila diketahui. Mengembalikan ok, data kambing, jam batas tahan, dan info rekening; atau alasan gagal beserta stok_lain.',
      method: 'POST',
      url: expr(URL_RPC + 'bot_tahan'),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr(H_SUPABASE),
      sendBody: true,
      contentType: 'json',
      specifyBody: 'keypair',
      bodyParameters: {
        parameters: [
          { name: 'p_key', value: expr('{{ ' + KEY + ' }}') },
          { name: 'p_chat', value: expr('{{ ' + CHAT + ' }}') },
          { name: 'p_kode', value: fromAi('kode', 'Nomor kambing, contoh BF-07', 'string') },
          { name: 'p_nama', value: fromAi('nama', 'Nama pembeli bila sudah diketahui, kosongkan bila belum', 'string') }
        ]
      }
    },
    position: [3360, 1260]
  }
});

const alatBatal = tool({
  type: 'n8n-nodes-base.httpRequestTool',
  version: 4.5,
  config: {
    name: 'batal_pesanan',
    parameters: {
      toolDescription: 'Batalkan pesanan pembeli ini yang masih DITAHAN (belum kirim bukti/belum DP) sehingga kambing kembali tersedia. Input: kode kambing. Pesanan yang sudah DP tidak bisa dibatalkan lewat alat ini.',
      method: 'POST',
      url: expr(URL_RPC + 'bot_batal'),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr(H_SUPABASE),
      sendBody: true,
      contentType: 'json',
      specifyBody: 'keypair',
      bodyParameters: {
        parameters: [
          { name: 'p_key', value: expr('{{ ' + KEY + ' }}') },
          { name: 'p_chat', value: expr('{{ ' + CHAT + ' }}') },
          { name: 'p_kode', value: fromAi('kode', 'Nomor kambing yang dibatalkan, contoh BF-07', 'string') }
        ]
      }
    },
    position: [3520, 1260]
  }
});

const alatAlamat = tool({
  type: 'n8n-nodes-base.httpRequestTool',
  version: 4.5,
  config: {
    name: 'simpan_alamat',
    parameters: {
      toolDescription: 'Simpan nama, alamat/area pengiriman, dan rencana waktu kirim/ambil yang diberikan pembeli ke pesanan aktifnya. Input: teks lengkap data pengiriman.',
      method: 'POST',
      url: expr(URL_RPC + 'bot_alamat'),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr(H_SUPABASE),
      sendBody: true,
      contentType: 'json',
      specifyBody: 'keypair',
      bodyParameters: {
        parameters: [
          { name: 'p_key', value: expr('{{ ' + KEY + ' }}') },
          { name: 'p_chat', value: expr('{{ ' + CHAT + ' }}') },
          { name: 'p_alamat', value: fromAi('alamat', 'Nama penerima, alamat atau area pengiriman, dan rencana waktu kirim/ambil', 'string') }
        ]
      }
    },
    position: [3680, 1260]
  }
});

const csAgent = node({
  type: '@n8n/n8n-nodes-langchain.agent',
  version: 3.1,
  config: {
    name: 'CS Barokah Farm',
    parameters: {
      promptType: 'define',
      text: expr('KONTEKS: {{ JSON.stringify({ sekarang: $("Catat Pesan & Ambil Konteks").first().json.sekarang, nama_whatsapp: $("Catat Pesan & Ambil Konteks").first().json.nama, stok_tersedia: $("Catat Pesan & Ambil Konteks").first().json.stok, sedang_dipesan_orang_lain: $("Catat Pesan & Ambil Konteks").first().json.sedang_dipesan, pesanan_pembeli_ini: $("Catat Pesan & Ambil Konteks").first().json.pesanan, info_toko: $("Catat Pesan & Ambil Konteks").first().json.info, riwayat_chat: $("Catat Pesan & Ambil Konteks").first().json.riwayat }) }}\n\nCATATAN SISTEM: {{ $json.catatan || "-" }}\n\nPESAN TERBARU PEMBELI: {{ $("Rapikan Pesan").first().json.teks }}'),
      options: {
        systemMessage: 'Kamu adalah admin penjualan WhatsApp *Barokah Farm*, peternakan kambing dan domba di Kampung Peusar, Binong, Curug, Tangerang. Kamu ramah, sigap, dan jujur. Tugasmu membantu pembeli memilih kambing, menjawab pertanyaan, dan mengantar sampai DP serta pelunasan.\n\nSUMBER DATA: KONTEKS berisi stok_tersedia (kode, jenis, ras, kelamin, berat_kg, umur_bulan, harga, layak_kurban), sedang_dipesan_orang_lain (jangan ditawarkan), pesanan_pembeli_ini, riwayat_chat, info_toko (rekening, dp_min, batas_hari, alamat, maps, jam_buka, ongkir, link_katalog, iduladha), dan waktu sekarang. HANYA gunakan data ini. Jangan mengarang kambing, harga, jadwal, atau janji. Bila data tidak ada, bilang akan dicek ke tim.\n\nATURAN BAKU (tidak boleh dilanggar):\n1. Harga katalog adalah harga pas. Jangan menawarkan diskon dan jangan pernah menyebut harga bisa ditawar. Hanya bila pembeli sendiri menanyakan nego/tawar, jawab bahwa hal itu bisa dibicarakan langsung dengan tim saat datang ke kandang, tanpa menjanjikan potongan.\n2. Dua cara beli: (a) DP lewat transfer minimal Rp100.000 per ekor, lalu lunasi paling lambat 3 x 24 jam sejak DP dikonfirmasi admin; (b) datang langsung ke kandang (alamat, link maps, dan jam dari info_toko).\n3. Gratis ongkir khusus Jabodetabek: sampai 10 km dari kandang gratis untuk 1 ekor; lebih dari 10 km gratis minimal 2 ekor. Di luar syarat itu atau di luar Jabodetabek: oper ke admin.\n4. Kamu hanya menerima dan meneruskan bukti transfer. Jangan pernah bilang dana sudah masuk; hanya admin yang memutuskan.\n5. Satu kambing hanya untuk satu pembeli.\n6. Bila belum lunas sampai batas, DP hangus sebagai biaya pakan dan perawatan selama karantina dan kambing kembali dijual. Jangan mengubah aturan ini.\n7. Jangan memberi klaim kesehatan/medis atau umur pasti di luar data; bilang akan ditanyakan ke tim kandang lalu oper ke admin.\n8. Jangan membagikan data pembeli lain.\n\nALUR:\n- Pahami kebutuhan bila belum jelas (kurban, aqiqah, ternak, atau lainnya; budget; jenis). Bila pesan pertama sudah menyebut nomor kambing (dari tombol katalog), langsung bahas kambing itu.\n- Sarankan 1 sampai 3 kambing tersedia yang paling cocok, lengkap dengan nomor, berat, dan harga. Sertakan link_katalog bila tidak kosong.\n- Bila kambing yang diminta tidak ada di stok_tersedia, sampaikan dengan sopan dan tawarkan 2 yang serupa.\n- Bila pembeli mau pesan/DP kambing tertentu: panggil alat tahan_kambing. Bila berhasil, sampaikan kambing ditahan untuknya selama 60 menit (sebut jam batasnya), tulis rekening persis dari hasil alat/info_toko dan DP minimal, minta kirim foto bukti transfer di chat ini, serta tanyakan nama, area pengiriman, dan rencana waktu kirim atau ambil. Bila gagal, jelaskan alasannya dan tawarkan stok_lain.\n- Bila pembeli memberi nama/alamat/area/waktu pengiriman untuk pesanannya: panggil simpan_alamat.\n- Bila pembeli membatalkan sebelum transfer: panggil batal_pesanan.\n- Bila pembeli bilang sudah transfer tapi belum mengirim foto: minta fotonya dengan ramah.\n- CATATAN SISTEM menjelaskan kejadian otomatis (misalnya bukti transfer sudah diterima dan diteruskan ke admin). Ikuti catatan itu.\n- Untuk pesanan berstatus menunggu_cek: bukti sedang dicek admin. Status dp: DP sudah dikonfirmasi; ingatkan batas_lunas bila relevan.\n\nOPER KE ADMIN MANUSIA: pembeli boleh minta bicara dengan admin/orang kapan saja. Wajib oper juga bila pembeli kesal, mengeluh, atau mengulang pertanyaan yang sama dua kali; minta pengecualian (perpanjangan waktu, pengembalian DP, harga khusus); pengiriman di luar syarat gratis ongkir atau luar Jabodetabek; pertanyaan yang tidak bisa dijawab dari data; atau ada kejanggalan bukti transfer. Caranya: beri tahu pembeli bahwa admin akan segera membalas, lalu tulis baris paling akhir persis seperti ini: [[OPER_ADMIN: alasan singkat]]\n\nGAYA BALASAN:\n- Susun baru setiap kali, bukan template. Jangan membuka dengan kata/sapaan yang sama seperti balasan cs sebelumnya di riwayat_chat. Jangan menyapa ulang "Halo" bila percakapan sudah berjalan.\n- Ikuti gaya pembeli: santai dibalas santai, formal dibalas sopan. Panggil "Kak", atau "Bapak/Ibu" bila terdengar lebih tua atau formal. Sebut nama bila diketahui.\n- Pendek seperti chat WhatsApp: 1 sampai 3 bubble. Pisahkan bubble dengan satu baris berisi --- saja. Tiap bubble paling banyak 3 kalimat. Emoji paling banyak satu per bubble.\n- Sebut detail spesifik (nomor kambing, jenis, berat, harga). Rupiah pakai titik ribuan, contoh Rp3.250.000. Umur dari umur_bulan (18 bulan = 1,5 tahun).\n- Akhiri dengan satu langkah berikutnya yang jelas: satu pertanyaan atau ajakan, bukan daftar pilihan panjang.\n- Tebal pakai *teks* (format WhatsApp). Jangan pakai markdown lain, heading, atau tabel.\n- Bila pembeli mengirim pesan suara/file: minta dengan sopan untuk mengetik pesannya.\n- Bila info_toko.iduladha true, sebut label layak kurban bila relevan.\nKeluarkan hanya isi balasan untuk pembeli.',
        maxIterations: 6
      }
    },
    subnodes: { model: geminiCs, tools: [alatTahan, alatBatal, alatAlamat] },
    position: [3200, 1060]
  },
  output: [{ output: 'Masih ada Kak, BF-01 Kambing Jawa jantan 32 kg harganya Rp3.250.000.\n---\nMau saya tahan untuk Kakak?' }]
});

const pisahBalasan = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Pisah Balasan',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "let raw = String($input.first().json.output || '').trim();\nconst m = raw.match(/\\[\\[\\s*OPER_ADMIN\\s*:?\\s*([^\\]]*)\\]\\]/i);\nraw = raw.replace(/\\[\\[[^\\]]*\\]\\]/g, '').trim();\nconst k = $('Catat Pesan & Ambil Konteks').first().json;\nconst msg = $('Rapikan Pesan').first().json;\nconst admin = String((k.info || {}).admin_wa || '').split(',').map(s => s.trim()).filter(Boolean).map(n => ({ chat_id: n + '@c.us' }));\nconst pesanan = (k.pesanan || []).map(p => p.kode + ' (' + p.status + ')').join(', ') || '-';\nconst riwayat = (k.riwayat || []).slice(-6).map(r => (r.dari === 'pembeli' ? '👤 ' : '🤖 ') + String(r.teks || '').slice(0, 160)).join('\\n');\nconst alasan = m ? (m[1] || 'pembeli minta bicara dengan admin').trim() : '';\nconst teksAdmin = `🙋 *Chat dioper ke admin*\\nPembeli: ${msg.nama || '-'} (wa.me/${msg.wa || msg.chat_id.split('@')[0]})\\nPesanan: ${pesanan}\\nAlasan: ${alasan}\\n\\nRingkasan chat:\\n${riwayat}\\n👤 ${msg.teks}\\n\\nBot berhenti membalas pembeli ini. Setelah selesai, kirim: *bot ${msg.wa || msg.chat_id}*`;\nreturn [{ json: { chat_id: msg.chat_id, teks: raw || 'Baik Kak, sebentar ya, admin kami akan segera membalas.', tes: msg.tes, oper: !!m, alasan, admin, teks_admin: teksAdmin } }];"
    },
    position: [3540, 1060]
  },
  output: [{ chat_id: '6281234567890@c.us', teks: 'Masih ada Kak', tes: true, oper: false, alasan: '', admin: [{ chat_id: '62881010021694@c.us' }], teks_admin: '' }]
});

const kirimBalasan = node({
  type: 'n8n-nodes-base.executeWorkflow',
  version: 1.4,
  config: {
    name: 'Kirim Balasan ke Pembeli',
    parameters: {
      mode: 'each',
      source: 'database',
      workflowId: { __rl: true, mode: 'id', value: KIRIM_TEKS_ID },
      workflowInputs: { mappingMode: 'defineBelow', value: { chat_id: expr('{{ $json.chat_id }}'), teks: expr('{{ $json.teks }}'), gambar_url: '', tes: expr('{{ $json.tes }}'), catat: true }, matchingColumns: [], schema: skemaKirimTeks, attemptToConvertTypes: false },
      options: { waitForSubWorkflow: true }
    },
    position: [3760, 960]
  },
  output: [{ ok: true }]
});

const perluOper = ifElse({
  version: 2.2,
  config: {
    name: 'Perlu Oper ke Admin?',
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'loose' },
        conditions: [{ leftValue: expr('{{ $json.oper }}'), operator: { type: 'boolean', operation: 'true', singleValue: true } }],
        combinator: 'and'
      }
    },
    position: [3760, 1180]
  }
});

const catatOper = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Alihkan ke Mode Manusia',
    parameters: {
      method: 'POST',
      url: expr(URL_RPC + 'bot_oper'),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr(H_SUPABASE),
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify({ p_key: ' + KEY + ', p_chat: $json.chat_id, p_alasan: $json.alasan }) }}')
    },
    position: [3980, 1160]
  },
  output: [{ ok: true }]
});

const pecahAdminOper = node({
  type: 'n8n-nodes-base.splitOut',
  version: 1.1,
  config: {
    name: 'Per Admin (Oper)',
    parameters: { fieldToSplitOut: 'admin', include: 'noOtherFields', options: {} },
    position: [4200, 1160]
  },
  output: [{ chat_id: '62881010021694@c.us' }]
});

const kabariAdmin = node({
  type: 'n8n-nodes-base.executeWorkflow',
  version: 1.4,
  config: {
    name: 'Kabari Admin',
    parameters: {
      mode: 'each',
      source: 'database',
      workflowId: { __rl: true, mode: 'id', value: KIRIM_TEKS_ID },
      workflowInputs: { mappingMode: 'defineBelow', value: { chat_id: expr('{{ $json.chat_id }}'), teks: expr('{{ $("Pisah Balasan").first().json.teks_admin }}'), gambar_url: '', tes: expr('{{ ' + TES + ' }}'), catat: false }, matchingColumns: [], schema: skemaKirimTeks, attemptToConvertTypes: false },
      options: { waitForSubWorkflow: true }
    },
    position: [4420, 1160]
  },
  output: [{ ok: true }]
});

const adminGambar = ifElse({
  version: 2.2,
  config: {
    name: 'Admin Kirim Foto?',
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'loose' },
        conditions: [{ leftValue: expr('{{ $("Rapikan Pesan").first().json.ada_gambar }}'), operator: { type: 'boolean', operation: 'true', singleValue: true } }],
        combinator: 'and'
      }
    },
    position: [1100, 600]
  }
});

const unduhFotoAdmin = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Unduh Foto Admin',
    parameters: {
      method: 'GET',
      url: expr('{{ $("Rapikan Pesan").first().json.media_url }}'),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr('{{ JSON.stringify({ "X-Api-Key": $("Ambil Konfigurasi").first().json.waha_key }) }}'),
      options: { response: { response: { responseFormat: 'file', outputPropertyName: 'data' } } }
    },
    position: [1320, 500]
  },
  output: [{}]
});

const simpanFotoAdmin = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Simpan Foto Kambing',
    parameters: {
      method: 'POST',
      url: expr('{{ $("Ambil Konfigurasi").first().json.supabase_url }}/storage/v1/object/foto/{{ $("Ambil Konfigurasi").first().json.foto_prefix }}/kambing/{{ $now.toFormat("yyyyMMddHHmmss") }}-{{ Math.floor(Math.random() * 1e6) }}.jpg'),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr('{{ JSON.stringify({ apikey: $("Ambil Konfigurasi").first().json.supabase_key, Authorization: "Bearer " + $("Ambil Konfigurasi").first().json.supabase_key, "x-upsert": "true", "Content-Type": "image/jpeg" }) }}'),
      sendBody: true,
      contentType: 'binaryData',
      inputDataFieldName: 'data'
    },
    position: [1540, 500]
  },
  output: [{ Key: 'foto/u1/kambing/20261019.jpg' }]
});

const fotoAdmin = node({
  type: 'n8n-nodes-base.set',
  version: 3.4,
  config: {
    name: 'Foto Admin Tersimpan',
    parameters: { mode: 'manual', includeOtherFields: false, assignments: { assignments: [{ id: 'f1', name: 'foto_url', value: expr('{{ $("Ambil Konfigurasi").first().json.supabase_url }}/storage/v1/object/public/{{ $json.Key }}'), type: 'string' }] } },
    position: [1760, 500]
  },
  output: [{ foto_url: 'https://x.supabase.co/storage/v1/object/public/foto/u1/kambing/1.jpg' }]
});

const tanpaFoto = node({
  type: 'n8n-nodes-base.set',
  version: 3.4,
  config: {
    name: 'Tanpa Foto',
    parameters: { mode: 'manual', includeOtherFields: false, assignments: { assignments: [{ id: 'f2', name: 'foto_url', value: '', type: 'string' }] } },
    position: [1320, 700]
  },
  output: [{ foto_url: '' }]
});

const adminYa = ifElse({
  version: 2.2,
  config: {
    name: 'Admin Balas YA?',
    parameters: {
      conditions: {
        options: { caseSensitive: false, leftValue: '', typeValidation: 'loose' },
        conditions: [
          { leftValue: expr('{{ /^(ya|iya|y|yes|yap|ok ya|ya simpan|simpan|lanjut)[.!]*$/i.test($("Rapikan Pesan").first().json.teks.trim()) }}'), operator: { type: 'boolean', operation: 'true', singleValue: true } },
          { leftValue: expr('{{ $("Catat Pesan & Ambil Konteks").first().json.aksi_tertunda ? true : false }}'), operator: { type: 'boolean', operation: 'true', singleValue: true } }
        ],
        combinator: 'and'
      }
    },
    position: [1980, 600]
  }
});

const ambilTertunda = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Ambil & Kosongkan Perintah Tertunda',
    parameters: {
      method: 'POST',
      url: expr(URL_RPC + 'admin_tunda'),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr(H_SUPABASE),
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify({ p_key: ' + KEY + ', p_chat: ' + CHAT + ', p_aksi: null }) }}')
    },
    position: [2200, 440]
  },
  output: [{ ok: true, sebelumnya: { aksi: 'konfirmasi_dp', kode: ['BF-01'] } }]
});

const jalankanTertunda = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Jalankan Perintah Tertunda',
    parameters: {
      method: 'POST',
      url: expr(URL_RPC + 'admin_aksi'),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr(H_SUPABASE),
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify({ p_key: ' + KEY + ', p_aksi: $json.sebelumnya || { aksi: "kosong" } }) }}')
    },
    position: [2420, 440]
  },
  output: [{ ok: true, ringkasan: 'BF-01 DP dikonfirmasi', notif: [] }]
});

const geminiAdmin = languageModel({
  type: '@n8n/n8n-nodes-langchain.lmChatGoogleGemini',
  version: 1.2,
  config: {
    name: 'Gemini Pahami Admin',
    parameters: { modelName: 'models/gemini-2.5-flash', options: { temperature: 0.1, maxOutputTokens: 2048 } },
    credentials: { googlePalmApi: { id: 'F10q2z7pzu5B47PS', name: 'Google Gemini(PaLM) Api account' } },
    position: [2200, 900]
  }
});

const pahamiAdmin = node({
  type: '@n8n/n8n-nodes-langchain.chainLlm',
  version: 1.9,
  config: {
    name: 'Pahami Perintah Admin',
    parameters: {
      promptType: 'define',
      text: expr('ADA_FOTO: {{ $json.foto_url ? "ya" : "tidak" }}\nPERINTAH TERTUNDA: {{ JSON.stringify($("Catat Pesan & Ambil Konteks").first().json.aksi_tertunda) }}\nSTOK SAAT INI: {{ JSON.stringify(($("Catat Pesan & Ambil Konteks").first().json.stok || []).map(s => s.kode + " " + s.jenis + " " + (s.ras || "") + " Rp" + s.harga)) }}\nSEDANG DIPESAN/DP: {{ JSON.stringify($("Catat Pesan & Ambil Konteks").first().json.sedang_dipesan) }}\nPESAN ADMIN: {{ $("Rapikan Pesan").first().json.teks }}'),
      messages: {
        messageValues: [
          { type: 'SystemMessagePromptTemplate', message: 'Kamu menerjemahkan pesan WhatsApp dari ADMIN Barokah Farm (toko kambing & domba) menjadi perintah untuk database. Jawab HANYA satu objek JSON valid tanpa teks lain dengan kunci: aksi, kode (array), jenis, ras, kelamin, berat_kg, umur_bulan, harga, selisih, nominal, alasan, wa, aktif, catatan, ringkasan. Isi null atau "" untuk yang tidak disebut.\n\nDaftar aksi:\n- tambah: kambing baru masuk (wajib jenis dan harga; opsional ras, kelamin, berat, umur, dan nomor bila admin menyebut nomor).\n- ubah: ubah data satu kambing (harga, berat, umur, ras, kelamin, catatan, layak_kurban). "harga 12 jadi 4,3 juta" = ubah.\n- harga_rata: harga semua kambing tersedia naik/turun sama rata. selisih positif = naik, negatif = turun. Bila disebut ras/jenis ("harga garut naik 200rb") isi ras atau jenis.\n- konfirmasi_dp: "OK 12", "12 dp masuk". Boleh beberapa kode. Isi nominal bila disebut.\n- tolak_dp: "TOLAK 12 dana belum masuk" (isi alasan).\n- lunas: "lunas 12".\n- terjual: "sold 12", "12 laku di kandang".\n- tersedia: buka lagi kambing yang tersembunyi/terjual karena salah input.\n- hapus: sembunyikan kambing dari katalog (mati, dijual ke tempat lain, salah input).\n- foto: tambahkan foto ke kambing (admin melampirkan foto dan menyebut nomor).\n- ambil_alih: admin ingin membalas sendiri chat pembeli, isi wa dengan nomor pembeli. kembali_bot: kembalikan chat pembeli ke bot ("bot 0812..."), isi wa.\n- iduladha: mode kurban/iduladha on atau off, isi aktif true/false.\n- stok: lihat stok, laporan, rekap.\n- bantuan: minta daftar perintah, menyapa, atau berterima kasih.\n- batal: membatalkan perintah yang sedang menunggu konfirmasi ("batal", "gak jadi").\n- tidak_jelas: maksud tidak jelas atau data penting kurang.\n\nKonversi: "no 12", "12", "bf12", "BF 12" menjadi "BF-12" (minimal dua digit, "5" menjadi "BF-05"). "4,5 juta"/"4.5jt"/"4500rb" = 4500000. "100rb"/"100k" = 100000. "1,5 tahun" = 18 bulan, "8 bulan" = 8. kelamin "Jantan" atau "Betina". jenis "Kambing" atau "Domba" (garut, merino, texel, ekor gemuk, dorper = Domba; jawa, etawa, kacang, boer, jawarandu, PE = Kambing).\n\nringkasan: satu sampai dua kalimat bahasa Indonesia yang menjelaskan persis apa yang akan dilakukan beserta angka-angkanya, untuk dikonfirmasi admin. Contoh: "Tambah Domba Garut jantan 35 kg, umur 1,5 tahun, harga Rp4.500.000, dengan foto terlampir."' }
        ]
      }
    },
    subnodes: { model: geminiAdmin },
    position: [2200, 700]
  },
  output: [{ text: '{"aksi":"konfirmasi_dp","kode":["BF-01"],"ringkasan":"Konfirmasi DP BF-01"}' }]
});

const susunPerintah = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Susun Perintah',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const raw = String($input.first().json.text || '');\nlet a = {};\ntry { a = JSON.parse(raw.slice(raw.indexOf('{'), raw.lastIndexOf('}') + 1)); } catch (e) { a = { aksi: 'tidak_jelas' }; }\nlet foto = '';\ntry { foto = $('Foto Admin Tersimpan').first().json.foto_url || ''; } catch (e) { foto = ''; }\nconst bersih = {};\nfor (const [k, v] of Object.entries(a)) { if (v === null || v === '' || (Array.isArray(v) && !v.length) || k === 'ringkasan') continue; bersih[k] = v; }\nif (foto && ['tambah', 'foto'].includes(bersih.aksi)) bersih.foto = foto;\nlet kategori = 'tunda';\nlet balas = '';\nconst bantuan = '📋 *Perintah admin Barokah Farm* (bahasa bebas):\\n• Tambah: kirim foto + \"tambah domba garut jantan 35kg 1,5th 4,5jt\"\\n• Ubah: \"BF-12 berat 37kg\" / \"harga 12 jadi 4,3jt\"\\n• Harga massal: \"harga semua turun 100rb\" / \"harga garut naik 200rb\"\\n• DP: \"OK 12\" / \"TOLAK 12 dana belum masuk\"\\n• Lunas: \"lunas 12\" · Laku di kandang: \"sold 12\"\\n• Foto tambahan: kirim foto + \"foto 12\"\\n• Sembunyikan: \"hapus 12\" · Buka lagi: \"tersedia 12\"\\n• Balas chat sendiri: \"ambil alih 0812xxxx\" · Kembalikan: \"bot 0812xxxx\"\\n• Mode kurban: \"mode kurban on/off\"\\n• Lihat stok: \"stok\"\\nSetiap perubahan akan minta konfirmasi, balas *YA* untuk menyimpan.';\nif (['stok', 'laporan'].includes(bersih.aksi)) kategori = 'langsung';\nelse if (bersih.aksi === 'bantuan') { kategori = 'balas'; balas = bantuan; }\nelse if (bersih.aksi === 'batal') { kategori = 'batal'; }\nelse if (bersih.aksi === 'tidak_jelas' || !bersih.aksi) { kategori = 'balas'; balas = 'Maaf, perintahnya belum saya pahami. Coba tulis lebih lengkap ya, misalnya \"OK 12\" atau \"tambah kambing jawa jantan 30kg 3,2jt\".\\n---\\nKetik *bantuan* untuk daftar perintah.'; }\nelse if (bersih.aksi === 'tambah' && (!bersih.harga || !bersih.jenis)) { kategori = 'balas'; balas = 'Untuk menambah kambing, minimal sebutkan jenis (kambing/domba) dan harganya ya. Contoh: kirim foto + \"tambah domba garut jantan 35kg 1,5th 4,5jt\".'; }\nelse if (bersih.aksi === 'testimoni') { bersih.aksi = 'terjual'; }\nconst ringkasan = a.ringkasan || JSON.stringify(bersih);\nconst m = $('Rapikan Pesan').first().json;\nreturn [{ json: { kategori, aksi: bersih, ringkasan, balas, konfirmasi: '📝 ' + ringkasan + '\\n\\nBalas *YA* untuk menyimpan, atau *batal*.', chat_id: m.chat_id, tes: m.tes } }];"
    },
    position: [2540, 700]
  },
  output: [{ kategori: 'tunda', aksi: { aksi: 'konfirmasi_dp', kode: ['BF-01'] }, ringkasan: 'Konfirmasi DP BF-01', balas: '', konfirmasi: 'Balas YA', chat_id: '62881010021694@c.us', tes: true }]
});

const jenisPerintah = switchCase({
  version: 3.2,
  config: {
    name: 'Jenis Perintah',
    parameters: {
      rules: {
        values: [
          { outputKey: 'Perlu konfirmasi', conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'loose' }, conditions: [{ leftValue: expr('{{ $json.kategori }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'tunda' }], combinator: 'and' } },
          { outputKey: 'Langsung jalan', conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'loose' }, conditions: [{ leftValue: expr('{{ $json.kategori }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'langsung' }], combinator: 'and' } },
          { outputKey: 'Balas saja', conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'loose' }, conditions: [{ leftValue: expr('{{ $json.kategori }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'balas' }], combinator: 'and' } },
          { outputKey: 'Batalkan', conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'loose' }, conditions: [{ leftValue: expr('{{ $json.kategori }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'batal' }], combinator: 'and' } }
        ]
      },
      options: {}
    },
    position: [2760, 700]
  }
});

const simpanTertunda = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Simpan Perintah Tertunda',
    parameters: {
      method: 'POST',
      url: expr(URL_RPC + 'admin_tunda'),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr(H_SUPABASE),
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify({ p_key: ' + KEY + ', p_chat: $json.chat_id, p_aksi: $json.aksi }) }}')
    },
    position: [2980, 560]
  },
  output: [{ ok: true }]
});

const mintaKonfirmasi = node({
  type: 'n8n-nodes-base.executeWorkflow',
  version: 1.4,
  config: {
    name: 'Minta Konfirmasi Admin',
    parameters: {
      mode: 'each',
      source: 'database',
      workflowId: { __rl: true, mode: 'id', value: KIRIM_TEKS_ID },
      workflowInputs: { mappingMode: 'defineBelow', value: { chat_id: expr('{{ ' + CHAT + ' }}'), teks: expr('{{ $("Susun Perintah").first().json.konfirmasi }}'), gambar_url: '', tes: expr('{{ ' + TES + ' }}'), catat: false }, matchingColumns: [], schema: skemaKirimTeks, attemptToConvertTypes: false },
      options: { waitForSubWorkflow: true }
    },
    position: [3200, 560]
  },
  output: [{ ok: true }]
});

const jalankanLangsung = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Jalankan Perintah Langsung',
    parameters: {
      method: 'POST',
      url: expr(URL_RPC + 'admin_aksi'),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr(H_SUPABASE),
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify({ p_key: ' + KEY + ', p_aksi: $json.aksi }) }}')
    },
    position: [2980, 700]
  },
  output: [{ ok: true, ringkasan: 'BF-01 Kambing Jawa 32kg Rp3.250.000 [tersedia]', notif: [] }]
});

const balasAdmin = node({
  type: 'n8n-nodes-base.executeWorkflow',
  version: 1.4,
  config: {
    name: 'Balas Admin',
    parameters: {
      mode: 'each',
      source: 'database',
      workflowId: { __rl: true, mode: 'id', value: KIRIM_TEKS_ID },
      workflowInputs: { mappingMode: 'defineBelow', value: { chat_id: expr('{{ $json.chat_id }}'), teks: expr('{{ $json.balas }}'), gambar_url: '', tes: expr('{{ $json.tes }}'), catat: false }, matchingColumns: [], schema: skemaKirimTeks, attemptToConvertTypes: false },
      options: { waitForSubWorkflow: true }
    },
    position: [2980, 840]
  },
  output: [{ ok: true }]
});

const batalTertunda = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Batalkan Perintah Tertunda',
    parameters: {
      method: 'POST',
      url: expr(URL_RPC + 'admin_tunda'),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr(H_SUPABASE),
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify({ p_key: ' + KEY + ', p_chat: $json.chat_id, p_aksi: null }) }}')
    },
    position: [2980, 980]
  },
  output: [{ ok: true }]
});

const infoBatal = node({
  type: 'n8n-nodes-base.executeWorkflow',
  version: 1.4,
  config: {
    name: 'Kabari Perintah Dibatalkan',
    parameters: {
      mode: 'each',
      source: 'database',
      workflowId: { __rl: true, mode: 'id', value: KIRIM_TEKS_ID },
      workflowInputs: { mappingMode: 'defineBelow', value: { chat_id: expr('{{ ' + CHAT + ' }}'), teks: 'Oke, perintah sebelumnya dibatalkan, tidak ada yang diubah.', gambar_url: '', tes: expr('{{ ' + TES + ' }}'), catat: false }, matchingColumns: [], schema: skemaKirimTeks, attemptToConvertTypes: false },
      options: { waitForSubWorkflow: true }
    },
    position: [3200, 980]
  },
  output: [{ ok: true }]
});

const hasilPerintah = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Hasil Perintah',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const r = $input.first().json || {};\nconst m = $('Rapikan Pesan').first().json;\nconst ok = r.ok !== false;\nconst teks = (ok ? '✅ ' : '⚠️ ') + (r.ringkasan || 'Selesai.');\nconst notif = (r.notif || []).map(n => ({ chat_id: n.chat_id, peristiwa: n.peristiwa, data: n.data }));\nreturn [{ json: { chat_id: m.chat_id, tes: m.tes, balas: teks, notif } }];"
    },
    position: [3200, 440]
  },
  output: [{ chat_id: '62881010021694@c.us', tes: true, balas: '✅ Selesai', notif: [{ chat_id: '6281234567890@c.us', peristiwa: 'dp_dikonfirmasi', data: { kode: 'BF-01' } }] }]
});

const laporHasil = node({
  type: 'n8n-nodes-base.executeWorkflow',
  version: 1.4,
  config: {
    name: 'Laporkan Hasil ke Admin',
    parameters: {
      mode: 'each',
      source: 'database',
      workflowId: { __rl: true, mode: 'id', value: KIRIM_TEKS_ID },
      workflowInputs: { mappingMode: 'defineBelow', value: { chat_id: expr('{{ $json.chat_id }}'), teks: expr('{{ $json.balas }}'), gambar_url: '', tes: expr('{{ $json.tes }}'), catat: false }, matchingColumns: [], schema: skemaKirimTeks, attemptToConvertTypes: false },
      options: { waitForSubWorkflow: true }
    },
    position: [3420, 340]
  },
  output: [{ ok: true }]
});

const pecahNotif = node({
  type: 'n8n-nodes-base.splitOut',
  version: 1.1,
  config: {
    name: 'Per Pembeli yang Dikabari',
    parameters: { fieldToSplitOut: 'notif', include: 'selectedOtherFields', fieldsToInclude: 'tes', options: {} },
    position: [3420, 520]
  },
  output: [{ chat_id: '6281234567890@c.us', peristiwa: 'dp_dikonfirmasi', data: { kode: 'BF-01' }, tes: true }]
});

const kabariPembeli = node({
  type: 'n8n-nodes-base.executeWorkflow',
  version: 1.4,
  config: {
    name: 'Kabari Pembeli',
    parameters: {
      mode: 'each',
      source: 'database',
      workflowId: { __rl: true, mode: 'id', value: PESAN_SISTEM_ID },
      workflowInputs: { mappingMode: 'defineBelow', value: { chat_id: expr('{{ $json.chat_id }}'), peristiwa: expr('{{ $json.peristiwa }}'), data: expr('{{ $json.data }}'), tes: expr('{{ $json.tes }}') }, matchingColumns: [], schema: skemaPesanSistem, attemptToConvertTypes: false },
      options: { waitForSubWorkflow: true }
    },
    onError: 'continueRegularOutput',
    position: [3640, 520]
  },
  output: [{ ok: true }]
});

export default workflow('kambing-cs-whatsapp', 'Kambing — CS WhatsApp')
  .add(masuk)
  .to(rapikan)
  .to(ambilKonfigurasi)
  .to(konteks)
  .to(arahkan
    .onCase(0, sambutAdmin)
    .onCase(1, adminGambar.onTrue(unduhFotoAdmin.to(simpanFotoAdmin).to(fotoAdmin)).onFalse(tanpaFoto))
    .onCase(2, pembeliGambar.onTrue(unduhGambar.to(bacaGambar).to(nilaiGambar).to(buktiPesanan.onTrue(simpanBukti.to(catatBukti).to(laporanBukti)).onFalse(catatanGambar))).onFalse(catatanTeks)))
  .add(fotoAdmin)
  .to(adminYa)
  .add(tanpaFoto)
  .to(adminYa.onTrue(ambilTertunda.to(jalankanTertunda).to(hasilPerintah)).onFalse(pahamiAdmin.to(susunPerintah).to(jenisPerintah
    .onCase(0, simpanTertunda.to(mintaKonfirmasi))
    .onCase(1, jalankanLangsung.to(hasilPerintah))
    .onCase(2, balasAdmin)
    .onCase(3, batalTertunda.to(infoBatal)))))
  .add(hasilPerintah)
  .to(laporHasil)
  .add(hasilPerintah)
  .to(pecahNotif.to(kabariPembeli))
  .add(laporanBukti)
  .to(pecahAdminBukti.to(teruskanBukti))
  .add(laporanBukti)
  .to(catatanBukti)
  .add(catatanBukti)
  .to(csAgent)
  .add(catatanGambar)
  .to(csAgent)
  .add(catatanTeks)
  .to(csAgent)
  .to(pisahBalasan)
  .to(kirimBalasan)
  .add(pisahBalasan)
  .to(perluOper.onTrue(catatOper.to(pecahAdminOper).to(kabariAdmin)));
