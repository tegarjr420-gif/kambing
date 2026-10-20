// Kartu penutup (CTA) transparan 1080x1920. node penutup.js out.png <terang|gelap|kuning|hijau> '{"judul":"..."}'
let pw; try { pw = require('playwright'); } catch (e) { pw = require('/tmp/claude-0/-home-claude/8530fe1f-175c-5546-b869-127bbb89636c/scratchpad/node_modules/playwright'); }
const { chromium } = pw;
const path = require('path');
const [out, varian = 'terang', optJson = '{}'] = process.argv.slice(2);
const opt = JSON.parse(optJson || '{}');
const E = __dirname;
const F = (f) => `file://${E}/fonts/${f}`;
const logo = `file://${E}/aset/logo.png`;
const V = {
  terang: { card: '#FBF8F1', ink: '#1d2a20', acc: '#1E4A2C', btn: '#25D366', btnInk: '#fff', chip: '#F2C14E', head: 'Bricolage Grotesque', body: 'Plus Jakarta Sans' },
  gelap: { card: 'rgba(12,16,13,.82)', ink: '#f4efe4', acc: '#E9C77B', btn: 'transparent', btnInk: '#E9C77B', chip: '#E9C77B', head: 'Playfair Display', body: 'Plus Jakarta Sans', line: true },
  kuning: { card: '#FFD43B', ink: '#111', acc: '#111', btn: '#111', btnInk: '#FFD43B', chip: '#fff', head: 'Anton', body: 'Montserrat' },
  hijau: { card: '#1E4A2C', ink: '#fff', acc: '#F2C14E', btn: '#25D366', btnInk: '#fff', chip: '#F2C14E', head: 'Montserrat', body: 'Montserrat' },
}[varian];
const judul = opt.judul || 'Barokah Farm';
const sub = opt.sub || 'Kambing · Domba · Aqiqah · Qurban';
const html = `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:'Bricolage Grotesque';src:url(${F('BricolageGrotesque_800ExtraBold.ttf')});font-weight:800}
@font-face{font-family:'Plus Jakarta Sans';src:url(${F('PlusJakartaSans_700Bold.ttf')});font-weight:700}
@font-face{font-family:'Plus Jakarta Sans';src:url(${F('PlusJakartaSans_400Regular.ttf')});font-weight:400}
@font-face{font-family:'Playfair Display';src:url(${F('PlayfairDisplay_700Bold.ttf')});font-weight:700}
@font-face{font-family:'Anton';src:url(${F('Anton_400Regular.ttf')});font-weight:700}
@font-face{font-family:'Montserrat';src:url(${F('Montserrat_800ExtraBold.ttf')});font-weight:800}
@font-face{font-family:'Montserrat';src:url(${F('Montserrat_600SemiBold.ttf')});font-weight:600}
html,body{margin:0;width:${opt.w || 1080}px;height:${opt.h || 1920}px;background:transparent}
.wrap{position:absolute;inset:0;display:flex;align-items:center;justify-content:center}
.card{transform:scale(${(opt.w || 1080) > (opt.h || 1920) ? 0.86 : 1});width:880px;padding:70px 64px 64px;border-radius:56px;background:${V.card};color:${V.ink};text-align:center;box-shadow:0 40px 90px rgba(0,0,0,.35);${V.line ? 'border:2px solid rgba(233,199,123,.55);backdrop-filter:blur(6px)' : ''}}
.logo{width:230px;height:230px;border-radius:50%;margin:0 auto 34px;display:block;box-shadow:0 10px 30px rgba(0,0,0,.25)}
h1{font:800 104px/1 '${V.head}',sans-serif;margin:0;letter-spacing:${V.head === 'Anton' ? '1px' : '-1px'};text-transform:${V.head === 'Anton' ? 'uppercase' : 'none'};color:${V.acc}}
.sub{font:600 38px/1.3 '${V.body}',sans-serif;margin:22px 0 44px;opacity:.9}
.btn{display:flex;align-items:center;justify-content:center;gap:18px;height:118px;border-radius:999px;background:${V.btn};color:${V.btnInk};font:800 46px '${V.body}',sans-serif;${V.line ? `border:2px solid ${V.btnInk}` : ''}}
.btn svg{width:52px;height:52px;fill:currentColor}
.web{margin-top:26px;font:700 40px '${V.body}',sans-serif;color:${V.acc}}
.chips{display:flex;justify-content:center;gap:14px;margin-top:38px;flex-wrap:wrap}
.chip{padding:12px 24px;border-radius:999px;font:700 28px '${V.body}',sans-serif;background:${V.chip};color:#1d2a20}
</style></head><body><div class="wrap"><div class="card">
<img class="logo" src="${logo}">
<h1>${judul}</h1>
<div class="sub">${sub}</div>
<div class="btn">${opt.cta || 'Info lengkap: link di bio'}</div>
${opt.web ? `<div class="web">${opt.web}</div>` : ''}
<div class="chips">${(opt.chips || ['Curug, Tangerang', 'Sejak 2004']).map(c => `<span class="chip">${c}</span>`).join('')}</div>
</div></div></body></html>`;
(async () => {
  const lokal = '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';
  const ARGS = ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'];
  const b = await chromium.launch(Object.assign({ args: ARGS, timeout: 60000 }, process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : (require('fs').existsSync(lokal) ? { executablePath: lokal } : {})));
  const p = await b.newPage({ viewport: { width: opt.w || 1080, height: opt.h || 1920 } });
  const fs = require('fs'); const tmp = `${E}/aset/_penutup_${process.pid}.html`; fs.writeFileSync(tmp, html);
  await p.goto('file://' + tmp, { waitUntil: 'load', timeout: 30000 }); fs.unlinkSync(tmp);
  await Promise.race([p.evaluate(() => document.fonts.ready), new Promise(r => setTimeout(r, 15000))]);
  await p.screenshot({ path: out, omitBackground: true, timeout: 30000 });
  await b.close();
})().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
