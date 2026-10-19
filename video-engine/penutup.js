// Kartu penutup (CTA) transparan 1080x1920. node penutup.js out.png <terang|gelap|kuning|hijau> '{"judul":"..."}'
const { chromium } = require('/tmp/claude-0/-home-claude/8530fe1f-175c-5546-b869-127bbb89636c/scratchpad/node_modules/playwright');
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
html,body{margin:0;width:1080px;height:1920px;background:transparent}
.wrap{position:absolute;inset:0;display:flex;align-items:center;justify-content:center}
.card{width:880px;padding:70px 64px 64px;border-radius:56px;background:${V.card};color:${V.ink};text-align:center;box-shadow:0 40px 90px rgba(0,0,0,.35);${V.line ? 'border:2px solid rgba(233,199,123,.55);backdrop-filter:blur(6px)' : ''}}
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
<div class="btn"><svg viewBox="0 0 24 24"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2c-1.6 0-3.1-.4-4.4-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.2-.4.2-.4.7-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.8 11.9 11.9 0 0 0 4.6 4c1.7.7 2.4.8 3.2.7.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.2-1.2-.1-.1-.2-.2-.5-.3z"/></svg>${opt.wa || '0878-9014-0532'}</div>
<div class="web">${opt.web || 'barokahfarm.pages.dev'}</div>
<div class="chips">${(opt.chips || ['Gratis ongkir Jabodetabek', 'DP mulai Rp100rb']).map(c => `<span class="chip">${c}</span>`).join('')}</div>
</div></div></body></html>`;
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell' });
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  const fs = require('fs'); const tmp = `${E}/aset/_penutup_${process.pid}.html`; fs.writeFileSync(tmp, html);
  await p.goto('file://' + tmp, { waitUntil: 'load' }); fs.unlinkSync(tmp);
  await p.evaluate(() => document.fonts.ready);
  await p.screenshot({ path: out, omitBackground: true });
  await b.close();
})();
