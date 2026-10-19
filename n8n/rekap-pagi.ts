import { workflow, node, trigger, expr } from '@n8n/workflow-sdk';

const skemaKirimTeks = [
  { id: 'chat_id', displayName: 'chat_id', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'string' },
  { id: 'teks', displayName: 'teks', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'string' },
  { id: 'gambar_url', displayName: 'gambar_url', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'string' },
  { id: 'tes', displayName: 'tes', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'boolean' },
  { id: 'catat', displayName: 'catat', required: false, defaultMatch: false, display: true, canBeUsedToMatch: true, type: 'boolean' }
];

const jamTujuh = trigger({
  type: 'n8n-nodes-base.scheduleTrigger',
  version: 1.4,
  config: {
    name: 'Setiap Jam 07.00 WIB',
    parameters: { rule: { interval: [{ field: 'cronExpression', expression: '0 7 * * *' }] } },
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
  output: [{ supabase_url: 'https://x.supabase.co', supabase_key: 'sb_publishable_x', bot_key: 'bk_x' }]
});

const ambilRekap = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Ambil Rekap Pagi',
    parameters: {
      method: 'POST',
      url: expr("{{ $('Ambil Konfigurasi').first().json.supabase_url }}/rest/v1/rpc/rekap_pagi"),
      sendHeaders: true,
      specifyHeaders: 'json',
      jsonHeaders: expr('{{ JSON.stringify({ apikey: $("Ambil Konfigurasi").first().json.supabase_key, Authorization: "Bearer " + $("Ambil Konfigurasi").first().json.supabase_key }) }}'),
      sendBody: true,
      contentType: 'json',
      specifyBody: 'json',
      jsonBody: expr('{{ JSON.stringify({ p_key: $("Ambil Konfigurasi").first().json.bot_key }) }}')
    },
    position: [440, 300]
  },
  output: [{ admin: 'Rekap admin', staf: 'Rekap kandang', ke_admin: ['62881010021694@c.us'], ke_staf: [] }]
});

const susun = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Satu Pesan per Penerima',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const r = $input.first().json;\nconst tes = $('Setiap Jam 07.00 WIB').first().json.tes === true;\nconst out = [];\nfor (const c of r.ke_admin || []) out.push({ json: { chat_id: c, teks: r.admin, tes } });\nfor (const c of r.ke_staf || []) out.push({ json: { chat_id: c, teks: r.staf, tes } });\nreturn out;"
    },
    position: [660, 300]
  },
  output: [{ chat_id: '62881010021694@c.us', teks: 'Rekap admin', tes: false }]
});

const kirim = node({
  type: 'n8n-nodes-base.executeWorkflow',
  version: 1.4,
  config: {
    name: 'Kirim Rekap ke WhatsApp',
    parameters: {
      mode: 'each',
      source: 'database',
      workflowId: { __rl: true, mode: 'id', value: 'QUdqtULgALOhnglF' },
      workflowInputs: { mappingMode: 'defineBelow', value: { chat_id: expr('{{ $json.chat_id }}'), teks: expr('{{ $json.teks }}'), gambar_url: '', tes: expr('{{ $json.tes }}'), catat: false }, matchingColumns: [], schema: skemaKirimTeks, attemptToConvertTypes: false },
      options: { waitForSubWorkflow: true }
    },
    onError: 'continueRegularOutput',
    position: [880, 300]
  },
  output: [{ ok: true }]
});

export default workflow('kambing-rekap-pagi', 'Kambing — Rekap Pagi (07.00 WIB)', { settings: { timezone: 'Asia/Jakarta', executionOrder: 'v1' } })
  .add(jamTujuh)
  .to(ambilKonfigurasi)
  .to(ambilRekap)
  .to(susun)
  .to(kirim);
