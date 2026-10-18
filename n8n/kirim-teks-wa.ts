import { workflow, node, trigger, ifElse, expr } from '@n8n/workflow-sdk';

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
          { name: 'teks', type: 'string' },
          { name: 'gambar_url', type: 'string' },
          { name: 'tes', type: 'boolean' },
          { name: 'catat', type: 'boolean' }
        ]
      }
    },
    position: [0, 300]
  },
  output: [{ chat_id: '6281234567890@c.us', teks: 'Halo Kak\n---\nAda yang bisa dibantu?', gambar_url: '', tes: true, catat: true }]
});

const ambilKonfigurasi = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Ambil Konfigurasi',
    parameters: { resource: 'row', operation: 'get', dataTableId: { __rl: true, mode: 'id', value: 'u7nj3ra9Giao0bMQ' }, returnAll: false, limit: 1 },
    executeOnce: true,
    position: [220, 300]
  },
  output: [{ supabase_url: 'https://x.supabase.co', supabase_key: 'sb_publishable_x', bot_key: 'bk_x', waha_url: 'https://waha.example', waha_key: 'k', foto_prefix: 'u1' }]
});

const siapkan = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Siapkan Pesan',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const a = $('Saat Dipanggil').first().json;\nconst raw = String(a.teks || '').trim();\nconst bubbles = raw.split(/\\n\\s*-{3,}\\s*\\n?/).map(s => s.trim()).filter(Boolean);\nconst bool = v => v === true || v === 'true';\nreturn [{ json: { chat_id: a.chat_id, bubbles, teks: bubbles.join('\\n\\n'), gambar_url: a.gambar_url || '', tes: bool(a.tes), catat: bool(a.catat) } }];"
    },
    position: [440, 300]
  },
  output: [{ chat_id: '6281234567890@c.us', bubbles: ['Halo Kak'], teks: 'Halo Kak', gambar_url: '', tes: true, catat: true }]
});

const perluCatat = ifElse({
  version: 2.2,
  config: {
    name: 'Perlu Dicatat?',
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'loose' },
        conditions: [{ leftValue: expr('{{ $json.catat }}'), operator: { type: 'boolean', operation: 'true', singleValue: true } }],
        combinator: 'and'
      }
    },
    position: [660, 160]
  }
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
    position: [880, 140]
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
    position: [660, 440]
  }
});

const adaGambar = ifElse({
  version: 2.2,
  config: {
    name: 'Ada Gambar?',
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'loose' },
        conditions: [{ leftValue: expr('{{ $json.gambar_url }}'), operator: { type: 'string', operation: 'notEmpty', singleValue: true } }],
        combinator: 'and'
      }
    },
    position: [880, 440]
  }
});

const kirimGambar = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Kirim Gambar ke WhatsApp',
    parameters: {
      method: 'POST',
      url: expr("{{ $('Ambil Konfigurasi').first().json.waha_url }}/api/sendImage"),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr('{{ JSON.stringify({ "X-Api-Key": $("Ambil Konfigurasi").first().json.waha_key }) }}'),
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify({ session: "default", chatId: $json.chat_id, file: { url: $json.gambar_url, mimetype: "image/jpeg", filename: "foto.jpg" }, caption: $json.teks }) }}')
    },
    retryOnFail: true,
    maxTries: 3,
    position: [1100, 360]
  },
  output: [{ id: 'true_x' }]
});

const pecahBubble = node({
  type: 'n8n-nodes-base.splitOut',
  version: 1.1,
  config: {
    name: 'Satu Item per Bubble',
    parameters: { fieldToSplitOut: 'bubbles', include: 'selectedOtherFields', fieldsToInclude: 'chat_id', options: { destinationFieldName: 'bubble' } },
    position: [1100, 540]
  },
  output: [{ chat_id: '6281234567890@c.us', bubble: 'Halo Kak' }]
});

const kirimTeks = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Kirim Teks ke WhatsApp',
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
    position: [1320, 540]
  },
  output: [{ id: 'true_x' }]
});

export default workflow('kambing-kirim-teks-wa', 'Kambing — Kirim Teks WA')
  .add(saatDipanggil)
  .to(ambilKonfigurasi)
  .to(siapkan)
  .to(perluCatat.onTrue(catatKeluar))
  .add(siapkan)
  .to(bukanUji.onTrue(adaGambar.onTrue(kirimGambar).onFalse(pecahBubble.to(kirimTeks))))
  .group('Catat', [perluCatat, catatKeluar], { description: 'Simpan pesan keluar ke riwayat percakapan di Supabase' })
  .group('Kirim lewat WAHA', [bukanUji, adaGambar, kirimGambar, pecahBubble, kirimTeks], { description: 'Kirim teks (dipecah per bubble) atau gambar+keterangan ke WhatsApp; dilewati saat mode uji' });
