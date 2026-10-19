import { workflow, node, trigger, switchCase, expr } from '@n8n/workflow-sdk';

const skemaKirimTeks = [
  { id: 'chat_id', displayName: 'chat_id', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'string' },
  { id: 'teks', displayName: 'teks', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'string' },
  { id: 'gambar_url', displayName: 'gambar_url', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'string' },
  { id: 'tes', displayName: 'tes', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'boolean' },
  { id: 'catat', displayName: 'catat', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'boolean' }
];

const tiap15 = trigger({
  type: 'n8n-nodes-base.scheduleTrigger',
  version: 1.4,
  config: {
    name: 'Tiap 15 Menit',
    parameters: { rule: { interval: [{ field: 'minutes', minutesInterval: 15 }] } },
    position: [0, 300]
  },
  output: [{}]
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
  output: [{ supabase_url: 'https://x.supabase.co', supabase_key: 'sb_publishable_x', bot_key: 'bk_x', waha_url: 'https://waha.example', waha_key: 'k' }]
});

const cekSesi = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Cek Sesi WhatsApp',
    parameters: {
      method: 'GET',
      url: expr("{{ $('Ambil Konfigurasi').first().json.waha_url }}/api/sessions/default"),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr('{{ JSON.stringify({ "X-Api-Key": $("Ambil Konfigurasi").first().json.waha_key }) }}'),
      options: { timeout: 20000 }
    },
    onError: 'continueRegularOutput',
    alwaysOutputData: true,
    position: [440, 300]
  },
  output: [{ name: 'default', status: 'WORKING' }]
});

const cekAI = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Cek Gangguan AI',
    parameters: {
      method: 'POST',
      url: expr("{{ $('Ambil Konfigurasi').first().json.supabase_url }}/rest/v1/rpc/alarm_cek"),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr('{{ JSON.stringify({ apikey: $("Ambil Konfigurasi").first().json.supabase_key, Authorization: "Bearer " + $("Ambil Konfigurasi").first().json.supabase_key }) }}'),
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify({ p_key: $("Ambil Konfigurasi").first().json.bot_key }) }}')
    },
    executeOnce: true,
    onError: 'continueRegularOutput',
    alwaysOutputData: true,
    position: [660, 300]
  },
  output: [{ ai_gagal_1jam: 0, pesan_masuk_1jam: 0, ke_admin: ['62881010021694@c.us'] }]
});

const nilai = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Nilai Kondisi',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const st = $getWorkflowStaticData('global');\nconst ses = $('Cek Sesi WhatsApp').first().json || {};\nconst status = ses.status || (ses.error ? 'TIDAK TERJANGKAU' : 'TIDAK DIKETAHUI');\nconst ai = $('Cek Gangguan AI').first().json || {};\nconst gagal = Number(ai.ai_gagal_1jam || 0);\nconst admin = ai.ke_admin || [];\nconst now = Date.now();\nconst JEDA = 3 * 3600 * 1000;\nconst out = [];\nconst ntfy = (title, message, priority, tags) => out.push({ json: { kanal: 'ntfy', body: { topic: 'barokahfarm-alarm-65928d0b', title, message, priority, tags } } });\nconst wa = (teks) => admin.forEach(c => out.push({ json: { kanal: 'wa', chat_id: c, teks } }));\nif (status !== 'WORKING') {\n  if (['STOPPED', 'FAILED'].includes(status)) out.push({ json: { kanal: 'restart' } });\n  if (!st.waDown || now - (st.waAlertAt || 0) > JEDA) {\n    const saran = status === 'SCAN_QR_CODE' ? 'Nomor CS terlepas dari WhatsApp. Hubungi Otomaya untuk menautkan ulang (perlu HP nomor CS).' : ['STOPPED', 'FAILED'].includes(status) ? 'Sistem sedang mencoba menyalakan ulang otomatis. Bila 15 menit lagi masih terputus, hubungi Otomaya.' : 'Server WhatsApp tidak menjawab. Hubungi Otomaya.';\n    ntfy('Bot WhatsApp Barokah Farm TERPUTUS', 'Status: ' + status + '. Pembeli tidak dibalas sampai tersambung lagi. ' + saran, 5, ['rotating_light']);\n    st.waAlertAt = now;\n  }\n  st.waDown = true;\n} else if (st.waDown) {\n  ntfy('Bot WhatsApp tersambung lagi', 'Bot Barokah Farm kembali membalas pembeli.', 3, ['white_check_mark']);\n  wa('✅ Bot WhatsApp Barokah Farm sudah tersambung lagi. Cek chat pembeli yang masuk selama terputus.');\n  st.waDown = false;\n}\nif (gagal >= 3) {\n  if (!st.aiDown || now - (st.aiAlertAt || 0) > JEDA) {\n    const isi = gagal + ' chat pembeli dalam 1 jam terakhir tidak bisa dijawab AI dan dioper ke admin. Kemungkinan saldo Gemini habis atau AI gangguan. Cek saldo di aistudio.google.com.';\n    ntfy('AI bot Barokah Farm gangguan', isi, 4, ['warning']);\n    wa('⚠️ *AI bot gangguan*\\n' + isi + '\\nSetelah normal, kembalikan pembeli ke bot dengan *bot <nomor>*.');\n    st.aiAlertAt = now;\n  }\n  st.aiDown = true;\n} else if (st.aiDown && gagal === 0) {\n  wa('✅ AI bot sudah normal lagi.');\n  st.aiDown = false;\n}\nreturn out;"
    },
    position: [880, 300]
  },
  output: [{ kanal: 'ntfy', body: { topic: 't', title: 'x', message: 'y', priority: 5, tags: [] } }]
});

const jalur = switchCase({
  version: 3.2,
  config: {
    name: 'Kirim Lewat Mana?',
    parameters: {
      rules: {
        values: [
          { outputKey: 'Notifikasi HP (ntfy)', conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' }, conditions: [{ leftValue: expr('{{ $json.kanal }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'ntfy' }], combinator: 'and' } },
          { outputKey: 'WhatsApp admin', conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' }, conditions: [{ leftValue: expr('{{ $json.kanal }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'wa' }], combinator: 'and' } },
          { outputKey: 'Nyalakan ulang', conditions: { options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' }, conditions: [{ leftValue: expr('{{ $json.kanal }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'restart' }], combinator: 'and' } }
        ]
      },
      options: {}
    },
    position: [1100, 300]
  }
});

const kirimNtfy = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Kirim Notifikasi HP',
    parameters: {
      method: 'POST',
      url: 'https://ntfy.sh',
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify($json.body) }}')
    },
    onError: 'continueRegularOutput',
    position: [1340, 160]
  },
  output: [{ id: 'x' }]
});

const kirimWa = node({
  type: 'n8n-nodes-base.executeWorkflow',
  version: 1.4,
  config: {
    name: 'Kabari Admin di WhatsApp',
    parameters: {
      mode: 'each',
      source: 'database',
      workflowId: { __rl: true, mode: 'id', value: 'QUdqtULgALOhnglF' },
      workflowInputs: { mappingMode: 'defineBelow', value: { chat_id: expr('{{ $json.chat_id }}'), teks: expr('{{ $json.teks }}'), gambar_url: '', tes: false, catat: false }, matchingColumns: [], schema: skemaKirimTeks, attemptToConvertTypes: false },
      options: { waitForSubWorkflow: true }
    },
    onError: 'continueRegularOutput',
    position: [1340, 320]
  },
  output: [{ ok: true }]
});

const restart = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Nyalakan Ulang Sesi',
    parameters: {
      method: 'POST',
      url: expr("{{ $('Ambil Konfigurasi').first().json.waha_url }}/api/sessions/default/start"),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr('{{ JSON.stringify({ "X-Api-Key": $("Ambil Konfigurasi").first().json.waha_key }) }}')
    },
    onError: 'continueRegularOutput',
    position: [1340, 480]
  },
  output: [{ status: 'STARTING' }]
});

export default workflow('kambing-alarm', 'Kambing — Alarm WhatsApp & AI (tiap 15 menit)', { settings: { timezone: 'Asia/Jakarta', executionOrder: 'v1' } })
  .add(tiap15)
  .to(ambilKonfigurasi)
  .to(cekSesi)
  .to(cekAI)
  .to(nilai)
  .to(jalur.onCase(0, kirimNtfy).onCase(1, kirimWa).onCase(2, restart));
