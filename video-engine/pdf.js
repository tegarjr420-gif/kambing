// HTML -> PDF A4. node pdf.js masuk.html keluar.pdf
let pw; try { pw = require('playwright'); } catch (e) { pw = require('/tmp/claude-0/-home-claude/8530fe1f-175c-5546-b869-127bbb89636c/scratchpad/node_modules/playwright'); }
const [masuk, keluar] = process.argv.slice(2);
const henti = setTimeout(() => { console.error('waktu habis'); process.exit(3); }, 90000);
(async () => {
  const b = await pw.chromium.launch({ args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'], ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}) });
  try {
    const p = await b.newPage();
    await p.goto('file://' + require('path').resolve(masuk), { waitUntil: 'load', timeout: 60000 });
    await p.pdf({ path: keluar, format: 'A4', printBackground: true, margin: { top: '14mm', bottom: '16mm', left: '13mm', right: '13mm' },
      displayHeaderFooter: true, headerTemplate: '<span></span>',
      footerTemplate: '<div style="width:100%;font:9px sans-serif;color:#7a857c;text-align:center">Barokah Farm · Script mentahan video · halaman <span class="pageNumber"></span>/<span class="totalPages"></span></div>' });
  } finally { await b.close(); clearTimeout(henti); }
  process.exit(0);
})().catch((e) => { console.error(e); process.exit(2); });
