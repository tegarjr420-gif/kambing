import { workflow, node, trigger, ifElse, languageModel, expr } from '@n8n/workflow-sdk';

const saatDipanggil = trigger({
  type: 'n8n-nodes-base.executeWorkflowTrigger',
  version: 1.3,
  config: {
    name: 'Saat Dipanggil',
    parameters: {
      inputSource: 'workflowInputs',
      workflowInputs: {
        values: [
          { name: 'chat_id', type: 'string' },
          { name: 'peristiwa', type: 'string' },
          { name: 'data', type: 'object' },
          { name: 'tes', type: 'boolean' }
        ]
      }
    },
    position: [0, 300]
  },
  output: [{ chat_id: '6281234567890@c.us', peristiwa: 'dp_dikonfirmasi', data: { kode: 'BF-07', harga: 3250000, nominal_dp: 100000, batas_lunas: '21/10/2026 14:00', sisa: 3150000 }, tes: true }]
});

const ambilKonfigurasi = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Ambil Konfigurasi',
    parameters: {
      resource: 'row',
      operation: 'get',
      dataTableId: { __rl: true, mode: 'id', value: 'u7nj3ra9Giao0bMQ' },
      returnAll: false,
      limit: 1
    },
    executeOnce: true,
    position: [220, 300]
  },
  output: [{ supabase_url: 'https://x.supabase.co', supabase_key: 'sb_publishable_x', bot_key: 'bk_x', waha_url: 'https://waha.example', waha_key: 'k', foto_prefix: 'u1' }]
});

const ambilInfo = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Ambil Info Toko',
    parameters: {
      method: 'POST',
      url: expr("{{ $('Ambil Konfigurasi').first().json.supabase_url }}/rest/v1/rpc/bot_info"),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr('{{ JSON.stringify({ apikey: $("Ambil Konfigurasi").first().json.supabase_key, Authorization: "Bearer " + $("Ambil Konfigurasi").first().json.supabase_key }) }}'),
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify({ p_key: $("Ambil Konfigurasi").first().json.bot_key, p_chat: $("Saat Dipanggil").first().json.chat_id }) }}')
    },
    position: [440, 300]
  },
  output: [{ rekening: 'BRI 808001004661537 a.n. Muriyadi', dp_min: 100000, batas_hari: 3, link_katalog: '', alamat: 'Kampung Peusar', maps: 'https://maps.app.goo.gl/x', jam_buka: '10.00–17.00 WIB', nama_pembeli: 'Budi', sekarang: '19/10/2026 10:00', riwayat: [] }]
});

const gemini = languageModel({
  type: '@n8n/n8n-nodes-langchain.lmChatGoogleGemini',
  version: 1.2,
  config: {
    name: 'Gemini 2.5 Flash',
    parameters: { modelName: 'models/gemini-2.5-flash', options: { temperature: 0.8, maxOutputTokens: 2048 } },
    credentials: { googlePalmApi: { id: 'F10q2z7pzu5B47PS', name: 'Google Gemini(PaLM) Api account' } },
    position: [660, 520]
  }
});

const tulisPesan = node({
  type: '@n8n/n8n-nodes-langchain.chainLlm',
  version: 1.9,
  config: {
    name: 'Tulis Pesan Sistem',
    parameters: {
      promptType: 'define',
      text: expr('PERISTIWA: {{ $("Saat Dipanggil").first().json.peristiwa }}\nDATA: {{ JSON.stringify($("Saat Dipanggil").first().json.data) }}\nINFO TOKO: {{ JSON.stringify({ rekening: $json.rekening, dp_min: $json.dp_min, batas_hari: $json.batas_hari, link_katalog: $json.link_katalog, alamat: $json.alamat, maps: $json.maps, jam_buka: $json.jam_buka }) }}\nNAMA PEMBELI: {{ $json.nama_pembeli || "(tidak diketahui)" }}\nWAKTU SEKARANG: {{ $json.sekarang }} WIB\nCHAT TERAKHIR: {{ JSON.stringify($json.riwayat) }}\n\nTulis pesannya sekarang.'),
      messages: {
        messageValues: [
          {
            type: 'SystemMessagePromptTemplate',
            message: 'Kamu admin WhatsApp Barokah Farm, peternakan yang menjual kambing dan domba di Curug, Tangerang. Tulis SATU pesan WhatsApp untuk pembeli berdasarkan PERISTIWA dan DATA.\n\nIsi wajib per peristiwa (semua angka, nomor kambing, tanggal, dan jam ditulis lengkap dan persis):\n- dp_dikonfirmasi: DP untuk kambing {kode} sudah diterima admin; kambing sudah masuk area karantina penjualan atas nama pembeli; sisa pembayaran {sisa}; batas pelunasan {batas_lunas} WIB (3 x 24 jam sejak konfirmasi); cara melunasi: transfer ke rekening toko lalu kirim bukti di chat ini, atau bayar langsung di kandang; ucapan terima kasih.\n- dp_ditolak: bukti transfer untuk {kode} belum bisa diterima admin, sebut alasannya {alasan} bila ada; kambing dilepas lagi ke katalog; tawarkan bantuan (kirim ulang bukti yang benar atau pilih lagi).\n- lunas: pelunasan {kode} sudah diterima, terima kasih; tanyakan jadwal pengiriman atau pengambilan, dan alamat lengkap bila belum ada.\n- pengingat_h1: pengingat ramah; nomor kambing {kode}; sisa pembayaran {sisa}; batas {batas_lunas} WIB; cara melunasi (transfer lalu kirim bukti, atau di kandang); bila lewat batas DP hangus sesuai ketentuan.\n- dp_hangus: pesanan {kode} dibatalkan karena melewati batas pelunasan; DP menjadi biaya pakan dan perawatan selama karantina sesuai ketentuan; permintaan maaf yang tulus; ajakan memilih kambing lain di katalog. Nada hangat, tidak menyalahkan.\n- tahan_habis: waktu tahan 60 menit untuk {kode} habis karena belum ada bukti transfer, kambing dilepas lagi ke katalog; bila sudah terlanjur transfer, minta kirim bukti di chat ini dan akan dicek ketersediaannya.\n- kambing_terjual_lain: mohon maaf, {kode} baru saja terjual langsung di kandang; tawarkan bantu carikan kambing lain.\n\nAturan gaya:\n- Bahasa Indonesia santai-sopan, panggil "Kak" (atau nama pembeli bila ada). Jangan membuka dengan kata yang sama seperti pesan CS sebelumnya di CHAT TERAKHIR.\n- 1 sampai 3 bubble. Pisahkan bubble dengan satu baris berisi tiga tanda minus: ---\n- Tiap bubble paling banyak 3 kalimat. Emoji paling banyak satu per bubble.\n- Format rupiah dengan titik ribuan, contoh Rp3.150.000. Format tebal WhatsApp memakai *teks*, jangan pakai markdown lain.\n- Rekening ditulis persis seperti INFO TOKO. Link katalog hanya ditulis bila ada isinya.\n- Jangan pernah menyebut harga bisa ditawar, jangan memberi diskon, jangan mengarang informasi di luar DATA dan INFO TOKO.\n- Keluarkan hanya isi pesan, tanpa penjelasan tambahan.'
          }
        ]
      }
    },
    subnodes: { model: gemini },
    position: [660, 300]
  },
  output: [{ text: 'Kak Budi, DP untuk BF-07 sudah kami terima 🙏\n---\nSisa pembayaran Rp3.150.000, paling lambat 21/10/2026 14:00 WIB.' }]
});

const pisahBubble = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Pisah Bubble',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const raw = String($input.first().json.text || '').replace(/^```[a-z]*\\s*/i, '').replace(/```\\s*$/, '').trim();\nconst bubbles = raw.split(/\\n\\s*-{3,}\\s*\\n?/).map(s => s.trim()).filter(Boolean).slice(0, 3);\nconst awal = $('Saat Dipanggil').first().json;\nreturn [{ json: { chat_id: awal.chat_id, tes: awal.tes === true || awal.tes === 'true', bubbles, teks: bubbles.join('\\n\\n') } }];"
    },
    position: [1000, 300]
  },
  output: [{ chat_id: '6281234567890@c.us', tes: true, bubbles: ['Halo Kak'], teks: 'Halo Kak' }]
});

const catatKeluar = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Catat Pesan Keluar',
    parameters: {
      method: 'POST',
      url: expr("{{ $('Ambil Konfigurasi').first().json.supabase_url }}/rest/v1/rpc/bot_keluar"),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr('{{ JSON.stringify({ apikey: $("Ambil Konfigurasi").first().json.supabase_key, Authorization: "Bearer " + $("Ambil Konfigurasi").first().json.supabase_key }) }}'),
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify({ p_key: $("Ambil Konfigurasi").first().json.bot_key, p_chat: $json.chat_id, p_teks: $json.teks }) }}')
    },
    onError: 'continueRegularOutput',
    position: [1240, 180]
  },
  output: [{}]
});

const bukanUji = ifElse({
  version: 2.2,
  config: {
    name: 'Bukan Mode Uji?',
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'loose' },
        conditions: [{ leftValue: expr('{{ $json.tes }}'), operator: { type: 'boolean', operation: 'false', singleValue: true } }],
        combinator: 'and'
      }
    },
    position: [1240, 420]
  }
});

const pecahBubble = node({
  type: 'n8n-nodes-base.splitOut',
  version: 1.1,
  config: {
    name: 'Satu Item per Bubble',
    parameters: { fieldToSplitOut: 'bubbles', include: 'selectedOtherFields', fieldsToInclude: 'chat_id', options: { destinationFieldName: 'bubble' } },
    position: [1460, 400]
  },
  output: [{ chat_id: '6281234567890@c.us', bubble: 'Halo Kak' }]
});

const kirimWa = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Kirim ke WhatsApp',
    parameters: {
      method: 'POST',
      url: expr("{{ $('Ambil Konfigurasi').first().json.waha_url }}/api/sendText"),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr('{{ JSON.stringify({ "X-Api-Key": $("Ambil Konfigurasi").first().json.waha_key }) }}'),
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify({ session: "default", chatId: $json.chat_id, text: $json.bubble }) }}'),
      options: { batching: { batch: { batchSize: 1, batchInterval: 1500 } } }
    },
    retryOnFail: true,
    maxTries: 3,
    position: [1680, 400]
  },
  output: [{ id: 'true_x' }]
});

export default workflow('kambing-kirim-pesan-sistem', 'Kambing — Kirim Pesan Sistem')
  .add(saatDipanggil)
  .to(ambilKonfigurasi)
  .to(ambilInfo)
  .to(tulisPesan)
  .to(pisahBubble)
  .to(catatKeluar)
  .add(pisahBubble)
  .to(bukanUji.onTrue(pecahBubble.to(kirimWa)));
