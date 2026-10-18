import { workflow, node, trigger, expr } from '@n8n/workflow-sdk';

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

const tiap5Menit = trigger({
  type: 'n8n-nodes-base.scheduleTrigger',
  version: 1.4,
  config: {
    name: 'Tiap 5 Menit',
    parameters: { rule: { interval: [{ field: 'minutes', minutesInterval: 5 }] } },
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

const cekJadwal = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.5,
  config: {
    name: 'Cek Tahan, H-1, dan DP Hangus',
    parameters: {
      method: 'POST',
      url: expr("{{ $('Ambil Konfigurasi').first().json.supabase_url }}/rest/v1/rpc/jadwal_cek"),
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
  output: [{ notif: [{ chat_id: '6281234567890@c.us', peristiwa: 'pengingat_h1', data: { kode: 'BF-01' } }], admin: 'BF-02 DP hangus', admin_wa: '62881010021694' }]
});

const susun = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Susun Kiriman',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const r = $input.first().json || {};\nconst notif = (r.notif || []).map(n => ({ chat_id: n.chat_id, peristiwa: n.peristiwa, data: n.data }));\nconst admin = r.admin ? String(r.admin_wa || '').split(',').map(s => s.trim()).filter(Boolean).map(n => ({ chat_id: n + '@c.us', teks: '⏰ *Laporan otomatis*\\n' + r.admin })) : [];\nreturn [{ json: { notif, admin } }];"
    },
    position: [660, 300]
  },
  output: [{ notif: [{ chat_id: '6281234567890@c.us', peristiwa: 'pengingat_h1', data: { kode: 'BF-01' } }], admin: [{ chat_id: '62881010021694@c.us', teks: 'BF-02 DP hangus' }] }]
});

const perPembeli = node({
  type: 'n8n-nodes-base.splitOut',
  version: 1.1,
  config: {
    name: 'Per Pembeli',
    parameters: { fieldToSplitOut: 'notif', include: 'noOtherFields', options: {} },
    position: [880, 200]
  },
  output: [{ chat_id: '6281234567890@c.us', peristiwa: 'pengingat_h1', data: { kode: 'BF-01' } }]
});

const kabariPembeli = node({
  type: 'n8n-nodes-base.executeWorkflow',
  version: 1.4,
  config: {
    name: 'Kirim Pesan Otomatis ke Pembeli',
    parameters: {
      mode: 'each',
      source: 'database',
      workflowId: { __rl: true, mode: 'id', value: 'cbmyNmUG0jdT9LcO' },
      workflowInputs: { mappingMode: 'defineBelow', value: { chat_id: expr('{{ $json.chat_id }}'), peristiwa: expr('{{ $json.peristiwa }}'), data: expr('{{ $json.data }}'), tes: false }, matchingColumns: [], schema: skemaPesanSistem, attemptToConvertTypes: false },
      options: { waitForSubWorkflow: true }
    },
    onError: 'continueRegularOutput',
    position: [1100, 200]
  },
  output: [{ ok: true }]
});

const perAdmin = node({
  type: 'n8n-nodes-base.splitOut',
  version: 1.1,
  config: {
    name: 'Per Admin',
    parameters: { fieldToSplitOut: 'admin', include: 'noOtherFields', options: {} },
    position: [880, 420]
  },
  output: [{ chat_id: '62881010021694@c.us', teks: 'BF-02 DP hangus' }]
});

const kabariAdmin = node({
  type: 'n8n-nodes-base.executeWorkflow',
  version: 1.4,
  config: {
    name: 'Laporkan ke Admin',
    parameters: {
      mode: 'each',
      source: 'database',
      workflowId: { __rl: true, mode: 'id', value: 'QUdqtULgALOhnglF' },
      workflowInputs: { mappingMode: 'defineBelow', value: { chat_id: expr('{{ $json.chat_id }}'), teks: expr('{{ $json.teks }}'), gambar_url: '', tes: false, catat: false }, matchingColumns: [], schema: skemaKirimTeks, attemptToConvertTypes: false },
      options: { waitForSubWorkflow: true }
    },
    onError: 'continueRegularOutput',
    position: [1100, 420]
  },
  output: [{ ok: true }]
});

export default workflow('kambing-jadwal-dp', 'Kambing — Jadwal DP (tiap 5 menit)')
  .add(tiap5Menit)
  .to(ambilKonfigurasi)
  .to(cekJadwal)
  .to(susun)
  .to(perPembeli.to(kabariPembeli))
  .add(susun)
  .to(perAdmin.to(kabariAdmin))
  .group('Proses jadwal', [ambilKonfigurasi, cekJadwal, susun], { description: 'Lepas kambing yang ditahan >60 menit, tandai pengingat H-1, hanguskan DP yang lewat 3x24 jam' })
  .group('Kabari pembeli', [perPembeli, kabariPembeli], { description: 'Pesan otomatis ditulis AI sesuai SOP lalu dikirim ke WhatsApp pembeli' })
  .group('Kabari admin', [perAdmin, kabariAdmin], { description: 'Laporan DP hangus ke nomor admin' });
