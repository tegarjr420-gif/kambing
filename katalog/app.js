(() => {
  "use strict";
  const C = window.BF_CONFIG || {};
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));

  /* ---------- format ---------- */
  const rupiah = (n) => "Rp" + Math.round(Number(n) || 0).toLocaleString("id-ID");
  const num = (n) => String(n).replace(".", ",");
  const beratTxt = (p) => {
    const a = p.berat_min, b = p.berat_max;
    if (a == null && b == null) return "";
    if (b == null || a === b) return `${num(a ?? b)} kg`;
    if (a == null) return `sampai ${num(b)} kg`;
    return `${num(a)}–${num(b)} kg`;
  };
  const relTime = (iso) => {
    const t = new Date(iso).getTime();
    if (!t) return "";
    const d = Math.max(0, (Date.now() - t) / 1000);
    if (d < 90) return "baru saja";
    if (d < 3600) return `${Math.round(d / 60)} menit lalu`;
    if (d < 86400) return `${Math.round(d / 3600)} jam lalu`;
    return new Date(t).toLocaleDateString("id-ID", { day: "numeric", month: "long" });
  };
  const sisaWaktu = (iso) => {
    let s = Math.max(0, Math.floor((new Date(iso).getTime() - Date.now()) / 1000));
    const h = Math.floor(s / 3600); s -= h * 3600;
    const m = Math.floor(s / 60); s -= m * 60;
    const pad = (x) => String(x).padStart(2, "0");
    return h >= 48 ? `${Math.floor(h / 24)} hari ${h % 24} jam` : `${pad(h)}:${pad(m)}:${pad(s)}`;
  };

  /* ---------- produk ---------- */
  const KAT = { Kambing: "Kambing", Domba: "Domba", Aqiqah: "Paket Aqiqah", Qurban: "Paket Qurban" };
  const flashOn = (p) => !!(p.flash_harga && p.flash_sampai && new Date(p.flash_sampai) > new Date());
  const hargaNow = (p) => (flashOn(p) ? p.flash_harga : p.harga);
  const punyaOpsi = (p) => Array.isArray(p.opsi) && p.opsi.length > 0;
  const dihitung = (p) => p.stok !== null && p.stok !== undefined && !punyaOpsi(p);
  const habis = (p) => dihitung(p) && p.stok <= 0;
  const satuan = (p) => (p.kategori === "Qurban" && p.isi_ekor > 1 ? "paket" : "ekor");
  const PILIH = {}; // kode -> jumlah ekor/paket yang dipilih

  /* ---------- WhatsApp ---------- */
  const wa = (text) => `https://wa.me/${C.waCS}?text=${encodeURIComponent(text)}`;
  const MSG = {
    umum: `Halo ${C.namaToko}, saya mau tanya kambing/domba yang tersedia.`,
    stok: `Halo ${C.namaToko}, saya cari kambing/domba dengan kriteria: `,
    kunjung: `Halo ${C.namaToko}, saya mau datang ke kandang hari … sekitar jam …`,
  };
  const judul = (p) => [p.nama, beratTxt(p)].filter(Boolean).join(" ");
  function msgPesan(p) {
    const n = PILIH[p.kode] || 1;
    if (habis(p)) return `Halo ${C.namaToko}, kalau *${p.kode}* ${judul(p)} ada stok lagi, tolong kabari saya ya.`;
    if (punyaOpsi(p)) {
      const o = p.opsi.find((x) => +x.ekor === n) || {};
      return o.harga
        ? `Halo ${C.namaToko}, saya mau pesan *${p.kode}* ${p.nama}, pilihan ${n} ekor (${rupiah(o.harga)}). Masih bisa?`
        : `Halo ${C.namaToko}, saya mau tanya harga *${p.kode}* ${p.nama} untuk ${n} ekor.`;
    }
    const h = hargaNow(p);
    if (!h) return `Halo ${C.namaToko}, saya mau tanya harga *${p.kode}* ${judul(p)}.`;
    const u = satuan(p);
    return `Halo ${C.namaToko}, saya mau pesan *${p.kode}* ${judul(p)}, ${n} ${u} (${rupiah(h)}/${u}${flashOn(p) ? ", harga flash sale" : ""}). Masih tersedia?`;
  }

  /* ---------- ilustrasi pengganti foto ---------- */
  const SCENE = [
    { sky: "#EAF1E0", hill: "#D2E2C0", ground: "#BDD6A6" },
    { sky: "#F6EEDA", hill: "#E6DDBA", ground: "#CFDAA2" },
    { sky: "#E4EEE9", hill: "#CCDFCF", ground: "#B5D1AD" },
  ];
  const GOAT = [
    { coat: "#FBFAF5", shade: "#DCD8CC", patch: "#9A6136", horn: "#A89878", hoof: "#3A3530", eye: "#2A2622" },
    { coat: "#A9693A", shade: "#7F4B26", patch: null, horn: "#5E4A36", hoof: "#2B2018", eye: "#1C1410" },
    { coat: "#33302D", shade: "#1F1D1B", patch: "#F3EEE2", horn: "#7A7064", hoof: "#121110", eye: "#F0C24B" },
    { coat: "#EADFC6", shade: "#CBBB97", patch: "#3A3531", horn: "#9C8B70", hoof: "#3A3530", eye: "#2A2622" },
  ];
  const SHEEP = [
    { wool: "#F6F1E4", woolShade: "#DDD3BD", face: "#3B312B", horn: "#B9A27C" },
    { wool: "#EADCBF", woolShade: "#CDBB98", face: "#EFE3CF", horn: "#9C8B70" },
    { wool: "#DCD3C2", woolShade: "#BDB09A", face: "#2F2925", horn: "#A89878" },
  ];
  const hash = (s) => { let h = [...String(s)].reduce((a, c) => (Math.imul(a, 31) + c.charCodeAt(0)) >>> 0, 7); h = Math.imul(h ^ (h >>> 15), 2246822507) >>> 0; return Math.imul(h ^ (h >>> 13), 3266489909) >>> 0; };
  function animalSVG(seed, domba, jantan) {
    const h = hash(seed);
    if (domba) {
      const p = SHEEP[(h >>> 3) % SHEEP.length];
      const puffs = [[150, 168, 30], [178, 146, 30], [214, 140, 31], [250, 146, 30], [276, 166, 28], [270, 194, 27], [238, 206, 28], [200, 208, 29], [164, 200, 28], [144, 186, 24]];
      const horn = jantan ? `<path d="M304 112C288 96 266 106 268 126C270 144 292 148 298 134C302 124 292 118 284 124" fill="none" stroke="${p.horn}" stroke-width="10" stroke-linecap="round"/>` : "";
      return `
        <g fill="${p.face}"><rect x="160" y="196" width="12" height="58" rx="6"/><rect x="182" y="200" width="12" height="54" rx="6"/><rect x="242" y="200" width="12" height="54" rx="6"/><rect x="262" y="196" width="12" height="58" rx="6"/></g>
        <ellipse cx="212" cy="178" rx="78" ry="38" fill="${p.wool}"/>
        ${puffs.map(([x, y, r]) => `<circle cx="${x}" cy="${y}" r="${r}" fill="${p.wool}" stroke="${p.woolShade}" stroke-width="3"/>`).join("")}
        <ellipse cx="212" cy="178" rx="64" ry="26" fill="${p.wool}"/>
        <path d="M282 152C288 132 300 116 312 112L330 136C322 150 310 162 296 172Z" fill="${p.wool}"/>
        <path d="M300 122C306 106 330 102 342 116C352 128 352 150 340 160C328 168 310 162 304 150C300 142 298 132 300 122Z" fill="${p.face}"/>
        <ellipse cx="298" cy="134" rx="16" ry="6.5" transform="rotate(-18 298 134)" fill="${p.face}"/>
        <circle cx="306" cy="110" r="11" fill="${p.wool}"/><circle cx="320" cy="104" r="11" fill="${p.wool}"/><circle cx="333" cy="110" r="9" fill="${p.wool}"/>
        ${horn}
        <circle cx="330" cy="128" r="3.6" fill="${p.face === "#EFE3CF" ? "#2A2622" : "#F6F1E4"}"/>`;
    }
    const p = GOAT[(h >>> 3) % GOAT.length];
    const id = "c" + h.toString(36) + Math.random().toString(36).slice(2, 6);
    const body = "M132 170C130 146 156 136 196 136C236 136 262 134 280 146C296 157 298 192 286 206C266 224 176 226 146 212C134 205 132 188 132 170Z";
    const patch = p.patch ? `<g clip-path="url(#${id})"><ellipse cx="170" cy="160" rx="34" ry="24" fill="${p.patch}"/><ellipse cx="258" cy="190" rx="26" ry="20" fill="${p.patch}"/></g>` : "";
    const legs = [[148, 196], [170, 200], [250, 200], [270, 196]]
      .map(([x, y]) => `<rect x="${x}" y="${y}" width="13" height="${254 - y}" rx="6" fill="${p.coat}" stroke="${p.shade}" stroke-width="2"/><rect x="${x}" y="248" width="13" height="8" rx="3" fill="${p.hoof}"/>`).join("");
    const beard = jantan ? `<path d="M336 130C336 144 332 156 326 162C322 152 322 140 326 130Z" fill="${p.shade}"/>` : "";
    const horns = jantan
      ? `<path d="M310 82C306 58 290 46 270 50" fill="none" stroke="${p.horn}" stroke-width="9" stroke-linecap="round"/><path d="M318 80C318 60 306 48 290 46" fill="none" stroke="${p.horn}" stroke-width="7" stroke-linecap="round"/>`
      : `<path d="M312 82C310 68 302 60 292 58" fill="none" stroke="${p.horn}" stroke-width="7" stroke-linecap="round"/>`;
    return `
      <defs><clipPath id="${id}"><path d="${body}"/></clipPath></defs>
      ${legs}
      <path d="M136 164C124 156 120 144 124 132C132 138 138 148 140 158Z" fill="${p.coat}" stroke="${p.shade}" stroke-width="2"/>
      <path d="M258 156C262 128 276 104 296 92L322 108C310 126 300 146 292 174Z" fill="${p.coat}" stroke="${p.shade}" stroke-width="3" stroke-linejoin="round"/>
      <path d="${body}" fill="${p.coat}" stroke="${p.shade}" stroke-width="3"/>
      ${patch}
      <path d="M150 208C190 220 250 220 282 204" fill="none" stroke="${p.shade}" stroke-width="3" opacity=".6"/>
      ${horns}
      <path d="M292 92C298 76 318 70 332 78C344 85 352 104 354 118C356 128 348 134 340 132C332 130 326 122 320 116C310 108 298 104 292 92Z" fill="${p.coat}" stroke="${p.shade}" stroke-width="3" stroke-linejoin="round"/>
      <ellipse cx="298" cy="104" rx="26" ry="8.5" transform="rotate(38 298 104)" fill="${p.coat}" stroke="${p.shade}" stroke-width="3"/>
      ${beard}
      <circle cx="328" cy="95" r="3.8" fill="${p.eye}"/>
      <circle cx="349" cy="121" r="2.4" fill="${p.shade}"/>`;
  }
  // Paket: kawanan kecil (2–3 ekor) supaya beda dari kartu per kelas
  function sceneSVG(p) {
    const h = hash(p.kode);
    const s = SCENE[h % SCENE.length];
    const bg = `<rect width="400" height="300" fill="${s.sky}"/>
      <path d="M0 178C70 150 150 146 220 164S350 150 400 140V300H0Z" fill="${s.hill}"/>
      <path d="M0 246C90 232 210 232 300 240S380 246 400 244V300H0Z" fill="${s.ground}"/>`;
    const domba = p.kategori === "Domba" || /domba|garut|merino|texel|dorper/i.test(`${p.nama} ${p.ras || ""}`);
    const jantan = !/betina/i.test(p.kelamin || "");
    let body;
    if (p.kategori === "Aqiqah" || p.kategori === "Qurban") {
      body = `<g transform="translate(-70 18) scale(.78)">${animalSVG(p.kode + "a", false, true)}</g>
              <g transform="translate(120 30) scale(.7)">${animalSVG(p.kode + "b", true, false)}</g>
              <g transform="translate(40 52) scale(.82)"><ellipse cx="214" cy="257" rx="112" ry="9" fill="#000" opacity=".08"/>${animalSVG(p.kode + "c", false, false)}</g>`;
    } else {
      body = `<ellipse cx="214" cy="257" rx="112" ry="9" fill="#000" opacity=".09"/>${animalSVG(p.kode, domba, jantan)}`;
    }
    return `<svg class="goat" viewBox="0 0 400 300" role="img" aria-label="Ilustrasi ${esc(p.nama)}, foto menyusul" preserveAspectRatio="xMidYMid slice">
      ${bg}${body}
      <text x="200" y="290" text-anchor="middle" font-family="Plus Jakarta Sans, sans-serif" font-size="12.5" font-weight="700" fill="#1E4A2C" opacity=".5">foto menyusul</text>
    </svg>`;
  }
  const media = (p, i = 0) =>
    p.foto && p.foto[i]
      ? `<img src="${esc(p.foto[i])}" alt="Foto ${esc(p.kode)}, ${esc(p.nama)}" loading="lazy" decoding="async">`
      : sceneSVG(p);

  /* ---------- data ---------- */
  const H = () => ({ apikey: C.supabaseAnonKey, Authorization: `Bearer ${C.supabaseAnonKey}` });
  const SB = !!(C.supabaseUrl && C.supabaseAnonKey);
  let ALL = [], ULASAN = [], META = { contoh: false };
  async function loadProduk() {
    if (SB) {
      const r = await fetch(`${C.supabaseUrl}/rest/v1/katalog_produk?select=*&order=urutan.asc,kode.asc`, { headers: H() });
      if (!r.ok) throw new Error("supabase " + r.status);
      return { contoh: false, produk: await r.json() };
    }
    const r = await fetch(`data/produk.json?v=${Date.now()}`);
    if (!r.ok) throw new Error("json " + r.status);
    return r.json();
  }
  async function loadUlasan() {
    try {
      if (SB) {
        const r = await fetch(`${C.supabaseUrl}/rest/v1/ulasan_publik?select=*&order=created_at.desc&limit=200`, { headers: H() });
        return r.ok ? r.json() : [];
      }
      const r = await fetch(`data/produk.json?v=${Date.now()}`);
      return r.ok ? (await r.json()).ulasan || [] : [];
    } catch { return []; }
  }
  async function loadTesti() {
    try {
      if (SB) {
        const r = await fetch(`${C.supabaseUrl}/rest/v1/testimoni_publik?select=*&order=tanggal.desc&limit=24`, { headers: H() });
        return r.ok ? r.json() : [];
      }
      return [];
    } catch { return []; }
  }

  /* ---------- filter ---------- */
  const F = { kat: "", flash: false, ada: false, kurban: false, q: "", sort: "urut" };
  function visible() {
    const q = F.q.trim().toLowerCase();
    const qs = q.replace(/[\s-]/g, "");
    let list = ALL.filter((p) =>
      (!F.kat || p.kategori === F.kat) &&
      (!F.flash || flashOn(p)) &&
      (!F.ada || !habis(p)) &&
      (!F.kurban || p.layak_kurban) &&
      (!q || String(p.kode).toLowerCase().replace(/-/g, "").includes(qs) ||
        `${p.nama} ${p.ras || ""} ${p.kategori} ${KAT[p.kategori] || ""} ${p.deskripsi || ""}`.toLowerCase().includes(q))
    );
    const harga = (p) => hargaNow(p) || (punyaOpsi(p) ? Math.min(...p.opsi.map((o) => o.harga || Infinity)) : Infinity);
    const by = {
      urut: (a, b) => (a.urutan - b.urutan) || String(a.kode).localeCompare(b.kode),
      murah: (a, b) => harga(a) - harga(b),
      mahal: (a, b) => (harga(b) === Infinity ? -1 : harga(b)) - (harga(a) === Infinity ? -1 : harga(a)),
      rating: (a, b) => (b.rating || 0) - (a.rating || 0) || (b.jumlah_ulasan || 0) - (a.jumlah_ulasan || 0),
    }[F.sort];
    return list.sort((a, b) => (habis(a) - habis(b)) || (flashOn(b) - flashOn(a)) * (F.sort === "urut" ? 1 : 0) || by(a, b));
  }

  /* ---------- bagian kartu ---------- */
  const bintang = (r) => {
    const w = Math.max(0, Math.min(100, (Number(r) || 0) * 20));
    return `<span class="stars" aria-hidden="true"><span class="stars-on" style="width:${w}%">★★★★★</span>★★★★★</span>`;
  };
  const ratingRow = (p) => p.jumlah_ulasan > 0
    ? `<p class="rating">${bintang(p.rating)}<b>${num(Number(p.rating).toFixed(1))}</b><span>${p.jumlah_ulasan} ulasan</span></p>`
    : "";
  const stokRow = (p) => {
    if (!dihitung(p)) return "";
    return p.stok > 0 ? `<span class="stok">Tersedia ${p.stok} ekor</span>` : `<span class="stok stok-0">Stok habis</span>`;
  };
  function opsiChips(p) {
    if (!punyaOpsi(p)) return "";
    const n = PILIH[p.kode] || 1;
    return `<div class="opsi" role="radiogroup" aria-label="Pilih jumlah ekor ${esc(p.nama)}">
      ${p.opsi.map((o) => `<button type="button" role="radio" aria-checked="${+o.ekor === n}" data-opsi="${esc(p.kode)}" data-n="${o.ekor}">${o.ekor}</button>`).join("")}
      <span class="opsi-lbl">ekor</span></div>`;
  }
  function priceBlock(p) {
    const n = PILIH[p.kode] || 1;
    if (punyaOpsi(p)) {
      const o = p.opsi.find((x) => +x.ekor === n) || {};
      return `<div class="price-wrap" data-price="${esc(p.kode)}">
        <p class="price">${o.harga ? rupiah(o.harga) : `<span class="ask">Harga tanya admin</span>`}<span class="per">untuk ${n} ekor</span></p>
        <p class="bobot">${o.bobot ? `Bobot: ${esc(o.bobot)}` : "Bobot &amp; harga diumumkan segera"}</p>
      </div>`;
    }
    if (!p.harga) return `<div class="price-wrap"><p class="price"><span class="ask">Harga tanya admin</span></p><p class="bobot">Bobot &amp; harga diumumkan segera</p></div>`;
    const u = satuan(p);
    if (flashOn(p)) {
      const hemat = Math.round((1 - p.flash_harga / p.harga) * 100);
      return `<div class="price-wrap flash">
        <p class="flash-top"><svg aria-hidden="true"><use href="#ic-bolt"/></svg>Flash sale${hemat > 0 ? ` · hemat ${hemat}%` : ""}</p>
        <p class="price"><s>${rupiah(p.harga)}</s>${rupiah(p.flash_harga)}<span class="per">/${u}</span></p>
        <p class="timer">Berakhir dalam <b data-sampai="${esc(p.flash_sampai)}">${sisaWaktu(p.flash_sampai)}</b></p>
      </div>`;
    }
    return `<div class="price-wrap"><p class="price">${rupiah(p.harga)}<span class="per">/${u}</span></p></div>`;
  }
  const btnLabel = (p) => habis(p) ? "Kabari saya kalau ada stok"
    : (punyaOpsi(p) ? ((p.opsi.find((x) => +x.ekor === (PILIH[p.kode] || 1)) || {}).harga ? "Pesan lewat WhatsApp" : "Tanya harga lewat WhatsApp")
      : hargaNow(p) ? "Pesan lewat WhatsApp" : "Tanya harga lewat WhatsApp");
  const btnShort = (p) => { const l = btnLabel(p); return l.startsWith("Kabari") ? "Kabari saya" : l.startsWith("Tanya") ? "Tanya harga" : "Pesan"; };
  const btn = (p, kartu = false) => `<a class="btn ${habis(p) ? "btn-ghost" : "btn-wa"} btn-block" data-wa="${esc(p.kode)}" href="${wa(msgPesan(p))}" target="_blank" rel="noopener"><svg aria-hidden="true"><use href="#ic-wa"/></svg>${kartu ? `<span class="l-long">${btnLabel(p)}</span><span class="l-short">${btnShort(p)}</span>` : `<span>${btnLabel(p)}</span>`}</a>`;
  const sub = (p) => [p.ras && !p.nama.toLowerCase().includes(p.ras.toLowerCase()) ? p.ras : null, p.kelamin].filter(Boolean).join(", ");

  function card(p) {
    const n = (p.foto || []).length;
    const b = beratTxt(p);
    const ringkas = p.kategori === "Qurban" && !n && !hargaNow(p) && !punyaOpsi(p);
    return `<article class="card${habis(p) ? " is-off" : ""}${flashOn(p) ? " is-flash" : ""}${ringkas ? " is-compact" : ""}" data-kode="${esc(p.kode)}">
      <button class="media" type="button" data-open="${esc(p.kode)}" aria-label="Lihat detail ${esc(p.nama)}">
        ${media(p)}
        <span class="tag">${esc(p.kode)}</span>
        ${flashOn(p) ? `<span class="ribbon"><svg aria-hidden="true"><use href="#ic-bolt"/></svg>Flash sale</span>` : ""}
        ${n > 1 ? `<span class="count">${n} foto</span>` : ""}
      </button>
      <div class="c-body">
        <div class="c-head">
          <h3 class="c-title">${esc(p.nama)}</h3>
          ${sub(p) ? `<p class="c-sub">${esc(sub(p))}</p>` : ""}
        </div>
        ${p.deskripsi && !b ? `<p class="c-desc">${esc(p.deskripsi)}</p>` : ""}
        ${b || dihitung(p) ? `<p class="c-meta">${b ? `<span class="berat"><svg aria-hidden="true"><use href="#ic-scale"/></svg>${b}</span>` : ""}${stokRow(p)}</p>` : ""}
        ${ratingRow(p)}
        ${opsiChips(p)}
        ${punyaOpsi(p) ? `<p class="opsi-mini">Pilih 1–${p.opsi.length} ekor</p>` : ""}
        ${priceBlock(p)}
        ${btn(p, true)}
      </div>
    </article>`;
  }

  function render() {
    const list = visible();
    const grouped = !F.kat && F.sort === "urut" && !F.q && !F.flash;
    let html = "";
    if (grouped) {
      const order = ["Kambing", "Domba", "Aqiqah", "Qurban"];
      for (const k of order) {
        const g = list.filter((p) => p.kategori === k);
        if (!g.length) continue;
        html += `<h3 class="grp" id="grp-${k.toLowerCase()}">${KAT[k]}<span>${g.length} pilihan</span></h3>` + g.map(card).join("");
      }
    } else html = list.map(card).join("");
    $("#grid").innerHTML = html;
    $("#empty").hidden = list.length > 0;
    const kosong = ALL.length === 0;
    $("#empty p b").textContent = kosong ? "Katalog sedang diperbarui." : "Belum ada yang cocok dengan pilihanmu.";
    $("#empty p + p").textContent = kosong ? "Tanya admin untuk stok terbaru, atau datang langsung ke kandang." : "Coba hapus saringan, atau tanya admin.";
    $("#reset").hidden = kosong;
    $("#chip-flash").hidden = !ALL.some(flashOn);
  }
  function renderMeta() {
    const ekor = ALL.filter(dihitung).reduce((a, p) => a + Math.max(0, p.stok), 0);
    const paket = ALL.filter((p) => p.kategori === "Aqiqah" || p.kategori === "Qurban").length;
    const fl = ALL.filter(flashOn).length;
    $("#live-text").textContent = [ekor ? `${ekor} ekor siap dibawa pulang` : "", paket ? `${paket} paket aqiqah & qurban` : "", fl ? `${fl} flash sale` : ""].filter(Boolean).join(" · ") || "Tanya admin untuk stok terbaru";
    const last = ALL.map((k) => k.updated_at).filter(Boolean).sort().pop();
    $("#updated").textContent = last ? `Diperbarui ${relTime(last)}` : "";
    $("#notice-contoh").hidden = !META.contoh;
  }
  function renderTesti(t) {
    $("#testi").innerHTML = t.map((x) => `<figure>
      <img src="${esc(x.foto_url)}" alt="Serah terima kepada pembeli" loading="lazy">
      <figcaption>${esc(x.caption || "Terima kasih sudah percaya Barokah Farm")}<small>${[x.kota, x.tanggal && new Date(x.tanggal).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" })].filter(Boolean).map(esc).join(", ")}</small></figcaption>
    </figure>`).join("");
    renderTestiEmpty();
  }
  const ulasanItem = (u) => {
    const p = ALL.find((x) => x.kode === u.produk_kode);
    return `<li class="rev"><p class="rev-top">${bintang(u.bintang)}<span class="rev-nm">${esc(u.nama || "Pembeli")}</span></p>
      ${u.komentar ? `<p class="rev-txt">${esc(u.komentar)}</p>` : ""}
      <p class="rev-meta">${[p ? p.nama : u.produk_kode, relTime(u.created_at)].filter(Boolean).map(esc).join(", ")}</p></li>`;
  };
  function renderUlasan() {
    const top = ULASAN.filter((u) => u.komentar).slice(0, 6);
    $("#reviews").innerHTML = top.map(ulasanItem).join("");
    $("#reviews").hidden = !top.length;
    renderTestiEmpty();
  }
  const renderTestiEmpty = () => { $("#testi-empty").hidden = !!($("#testi").children.length || $("#reviews").children.length); };

  /* ---------- detail ---------- */
  const dlg = $("#detail");
  let CUR = null;
  function fillDetail(p) {
    const b = beratTxt(p);
    $("#d-tag").textContent = p.kode;
    $("#d-kat").textContent = KAT[p.kategori] || p.kategori;
    $("#d-title").textContent = p.nama;
    $("#d-desc").hidden = !p.deskripsi;
    $("#d-desc").textContent = p.deskripsi || "";
    $("#d-specs").innerHTML = [
      b && ["Berat", b],
      dihitung(p) && ["Stok", p.stok > 0 ? `${p.stok} ekor` : "Habis"],
      p.kategori === "Qurban" && p.isi_ekor > 1 && ["Isi paket", `${p.isi_ekor} ekor`],
      p.ras && ["Ras", p.ras],
      C.iduladha && (p.kategori === "Kambing" || p.kategori === "Domba") && ["Kurban", p.layak_kurban ? "Layak kurban" : "–"],
    ].filter(Boolean).map(([a, v]) => `<div${a === "Stok" && p.stok > 0 ? ' class="is-stok"' : ""}><dt>${a}</dt><dd>${esc(v)}</dd></div>`).join("");
    $("#d-specs").hidden = !$("#d-specs").children.length;
    $("#d-rating").innerHTML = ratingRow(p);
    $("#d-opsi").innerHTML = opsiChips(p);
    // jumlah untuk kelas berstok / qurban paket
    const maxN = punyaOpsi(p) || habis(p) || !hargaNow(p) ? 0 : (dihitung(p) ? Math.min(p.stok, 20) : 10);
    $("#d-qty").hidden = maxN < 2;
    if (maxN >= 2) {
      const n = Math.min(PILIH[p.kode] || 1, maxN);
      PILIH[p.kode] = n;
      $("#q-n").textContent = n;
      $("#q-unit").textContent = satuan(p);
      $("#q-min").disabled = n <= 1;
      $("#q-plus").disabled = n >= maxN;
      $("#q-plus").dataset.max = maxN;
    }
    $("#d-price").innerHTML = priceBlock(p) + (maxN >= 2 && (PILIH[p.kode] || 1) > 1 ? `<p class="total">Total ${PILIH[p.kode]} ${satuan(p)}: <b>${rupiah(hargaNow(p) * PILIH[p.kode])}</b></p>` : "");
    $("#d-btn").innerHTML = btn(p);
    $("#d-fine").textContent = habis(p)
      ? "Stok kelas ini sedang habis. Kami kabari lewat WhatsApp begitu ada lagi."
      : `DP minimal ${rupiah(C.dpMinimal)} per ekor, pelunasan paling lambat ${C.batasPelunasanHari} hari setelah DP dikonfirmasi. Atau datang langsung ke kandang jam ${C.jamBuka}.`;
    const rv = ULASAN.filter((u) => u.produk_kode === p.kode);
    $("#d-rev").innerHTML = rv.length ? `<h4>Ulasan pembeli</h4><ul class="revs">${rv.slice(0, 8).map(ulasanItem).join("")}</ul>` : "";
  }
  function openDetail(kode, push = true) {
    const p = ALL.find((x) => String(x.kode).toLowerCase() === String(kode).toLowerCase());
    if (!p) return;
    CUR = p.kode;
    const n = Math.max(1, (p.foto || []).length);
    $("#d-media").innerHTML = Array.from({ length: n }, (_, i) => media(p, i)).join("");
    fillDetail(p);
    if (!dlg.open) dlg.showModal();
    if (push) history.replaceState(null, "", `#${p.kode}`);
  }
  const closeDetail = () => { if (dlg.open) dlg.close(); };
  dlg.addEventListener("close", () => { CUR = null; if (ALL.some((k) => `#${k.kode}` === location.hash)) history.replaceState(null, "", location.pathname + location.search); });
  dlg.addEventListener("click", (e) => { if (e.target === dlg) closeDetail(); });
  $("#d-close").addEventListener("click", closeDetail);
  $("#q-min").addEventListener("click", () => { const p = ALL.find((x) => x.kode === CUR); if (!p) return; PILIH[p.kode] = Math.max(1, (PILIH[p.kode] || 1) - 1); fillDetail(p); });
  $("#q-plus").addEventListener("click", (e) => { const p = ALL.find((x) => x.kode === CUR); if (!p) return; PILIH[p.kode] = Math.min(+e.currentTarget.dataset.max || 10, (PILIH[p.kode] || 1) + 1); fillDetail(p); });

  // klik di grid & detail: buka detail atau pilih jumlah ekor paket
  document.addEventListener("click", (e) => {
    const o = e.target.closest("[data-opsi]");
    if (o) {
      const p = ALL.find((x) => x.kode === o.dataset.opsi);
      if (!p) return;
      PILIH[p.kode] = +o.dataset.n;
      const c = $(`#grid .card[data-kode="${CSS.escape(p.kode)}"]`);
      if (c) c.outerHTML = card(p);
      if (CUR === p.kode) fillDetail(p);
      const again = (CUR === p.kode ? $(`#d-opsi [data-n="${o.dataset.n}"]`) : $(`#grid .card[data-kode="${CSS.escape(p.kode)}"] [data-n="${o.dataset.n}"]`));
      if (again) again.focus();
      return;
    }
    const t = e.target.closest("#grid [data-open]");
    if (t) openDetail(t.dataset.open);
  });

  /* ---------- kontrol filter ---------- */
  const setKat = (k) => {
    F.kat = k;
    $$(".seg button").forEach((x) => x.setAttribute("aria-checked", String(x.dataset.kat === k)));
    render();
  };
  $$(".seg button").forEach((b) => b.addEventListener("click", () => {
    setKat(b.dataset.kat);
    b.scrollIntoView({ block: "nearest", inline: "center", behavior: "smooth" });
  }));
  const toggle = (id, key) => $(id).addEventListener("click", (e) => { F[key] = !F[key]; e.currentTarget.setAttribute("aria-pressed", String(F[key])); render(); });
  toggle("#chip-flash", "flash"); toggle("#chip-ada", "ada"); toggle("#chip-kurban", "kurban");
  $("#q").addEventListener("input", (e) => { F.q = e.target.value; render(); });
  $("#sort").addEventListener("change", (e) => { F.sort = e.target.value; render(); });
  $("#reset").addEventListener("click", () => {
    Object.assign(F, { flash: false, ada: false, kurban: false, q: "" }); $("#q").value = "";
    $$(".chip").forEach((x) => x.setAttribute("aria-pressed", "false"));
    setKat("");
  });

  /* ---------- isi teks statis dari config ---------- */
  const rek = C.rekening || {};
  const rekTxt = `${rek.bank} ${rek.nomor} a.n. ${rek.nama}`;
  $("#f-jam").textContent = C.jamBuka;
  $("#f-dp").textContent = rupiah(C.dpMinimal);
  $$(".js-jam").forEach((e) => (e.textContent = C.jamBuka));
  $$(".js-dp").forEach((e) => (e.textContent = rupiah(C.dpMinimal)));
  $$(".js-hari").forEach((e) => (e.textContent = `${C.batasPelunasanHari} hari`));
  $$(".js-rek").forEach((e) => (e.textContent = rekTxt));
  $("#rek-no").textContent = `${rek.bank} ${String(rek.nomor).replace(/(\d{4})(?=\d)/g, "$1 ")}`;
  $("#rek-nama").textContent = `a.n. ${rek.nama}`;
  $("#alamat").textContent = C.alamat;
  $("#foot-alamat").textContent = C.alamat;
  $("#foot-wa").textContent = "0" + String(C.waCS).replace(/^62/, "").replace(/(\d{3})(\d{4})(\d+)/, "$1-$2-$3");
  $("#yr").textContent = new Date().getFullYear();
  $$(".js-maps").forEach((a) => (a.href = C.mapsUrl));
  $$(".js-wa").forEach((a) => (a.href = wa(MSG[a.dataset.msg] || MSG.umum)));
  const SO = C.sosial || {};
  $$(".js-sos-ig").forEach((a) => (a.href = SO.instagram));
  $$(".js-sos-tt").forEach((a) => (a.href = SO.tiktok));
  $$(".js-sos-fb").forEach((a) => (a.href = SO.facebook));
  $$(".js-sos-handle").forEach((e) => (e.textContent = SO.handle || ""));
  const O = C.otomaya || {};
  $$(".js-oto-web").forEach((a) => (a.href = `${O.web}/?ref=barokahfarm`));
  $$(".js-oto-ig").forEach((a) => (a.href = O.instagram));
  $$(".js-oto-tt").forEach((a) => (a.href = O.tiktok));
  $$(".js-oto-ig-h").forEach((e) => (e.textContent = `Instagram ${O.igHandle}`));
  $$(".js-oto-tt-h").forEach((e) => (e.textContent = `TikTok ${O.tiktokHandle}`));
  if (C.iduladha) { $("#banner-kurban").hidden = false; $("#chip-kurban").hidden = false; }

  const toast = (t) => { const el = $("#toast"); el.textContent = t; el.classList.add("on"); clearTimeout(toast.t); toast.t = setTimeout(() => el.classList.remove("on"), 2200); };
  const copyBtn = $("#copy-rek");
  copyBtn.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(String(rek.nomor)); toast("Nomor rekening disalin"); }
    catch { toast(`${rek.nomor}`); }
    copyBtn.classList.add("done");
    copyBtn.querySelector("span").textContent = "Tersalin";
    setTimeout(() => { copyBtn.querySelector("span").textContent = "Salin nomor"; }, 2500);
  });
  // "Rekening resmi: lihat" → ke kotak rekening, lalu sorot sebentar
  $$('a[href="#rekening"]').forEach((a) => a.addEventListener("click", (e) => {
    e.preventDefault();
    const box = $("#rekening");
    box.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" });
    box.classList.remove("hl"); void box.offsetWidth; box.classList.add("hl");
    setTimeout(() => copyBtn.focus({ preventScroll: true }), 700);
  }));

  // watermark disembunyikan saat kredit di footer sudah terlihat
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(([e]) => $("#oto-badge").classList.toggle("hide", e.isIntersecting), { threshold: 0.2 }).observe($("#credit"));
  }

  /* ---------- tim, lokasi, galeri ---------- */
  const inisial = (n) => String(n).replace(/^(bpk|bapak|bu|ibu|bung|mas|mbak|pak)\.?\s+/i, "").trim().charAt(0).toUpperCase();
  $("#tim-grid").innerHTML = (C.tim || []).map((t) => `<li class="orang">
      <div class="orang-foto">${t.foto ? `<img src="${esc(t.foto)}" alt="Foto ${esc(t.nama)}" loading="lazy">`
        : `<span class="mono" aria-hidden="true">${esc(inisial(t.nama))}</span><span class="foto-nanti">foto menyusul</span>`}</div>
      <p class="orang-nama">${esc(t.nama)}</p>
      <p class="orang-peran">${esc(t.peran)}</p>
    </li>`).join("");
  $("#tim").hidden = !(C.tim || []).length;
  const ICON_LOK = { kantor: "ic-office", kandang: "ic-pen", dapur: "ic-pot" };
  $("#lok-isi").innerHTML = (C.lokasiIsi || []).map((x) => {
    const k = Object.keys(ICON_LOK).find((y) => x.toLowerCase().includes(y)) || "kandang";
    return `<li><svg aria-hidden="true"><use href="#${ICON_LOK[k]}"/></svg>${esc(x)}</li>`;
  }).join("");
  if (C.mapsEmbed) {
    // peta dimuat saat bagian lokasi hampir terlihat, supaya halaman tetap ringan
    const pasang = () => { if (!$("#map-frame iframe")) $("#map-frame").innerHTML = `<iframe src="${esc(C.mapsEmbed)}" title="Peta lokasi Barokah Farm" loading="lazy" tabindex="-1" aria-hidden="true" referrerpolicy="no-referrer-when-downgrade"></iframe>`; };
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { pasang(); io.disconnect(); } }, { rootMargin: "400px" });
      io.observe($("#lokasi"));
    } else pasang();
  }
  const lb = $("#lightbox");
  $("#lb-close").addEventListener("click", () => lb.close());
  lb.addEventListener("click", (e) => { if (e.target === lb) lb.close(); });
  $("#galeri-grid").addEventListener("click", (e) => {
    const b = e.target.closest("[data-src]");
    if (!b) return;
    $("#lb-img").src = b.dataset.src; $("#lb-img").alt = b.dataset.cap || "Foto kegiatan Barokah Farm";
    $("#lb-cap").textContent = b.dataset.cap || "";
    lb.showModal();
  });
  async function loadGaleri() {
    try {
      if (!SB) return [];
      const r = await fetch(`${C.supabaseUrl}/rest/v1/galeri_publik?select=*&order=created_at.desc&limit=24`, { headers: H() });
      return r.ok ? r.json() : [];
    } catch { return []; }
  }
  loadGaleri().then((g) => {
    $("#galeri-grid").innerHTML = g.map((x) => `<button type="button" class="gal-item" data-src="${esc(x.foto_url)}" data-cap="${esc(x.caption || "")}">
      <img src="${esc(x.foto_url)}" alt="${esc(x.caption || "Kegiatan Barokah Farm")}" loading="lazy">${x.caption ? `<span>${esc(x.caption)}</span>` : ""}</button>`).join("");
    $("#galeri-empty").hidden = g.length > 0;
    $("#galeri-note").hidden = g.length > 0;
  });

  /* ---------- hitung mundur flash sale ---------- */
  setInterval(() => {
    let lewat = false;
    $$("[data-sampai]").forEach((el) => {
      if (new Date(el.dataset.sampai) <= new Date()) lewat = true;
      el.textContent = sisaWaktu(el.dataset.sampai);
    });
    if (lewat && !dlg.open) { renderMeta(); render(); }
  }, 1000);

  /* ---------- muat ---------- */
  $("#grid").innerHTML = '<div class="skel"></div><div class="skel"></div><div class="skel"></div>';
  async function cekModeKurban() {
    if (!SB) return;
    try {
      const r = await fetch(`${C.supabaseUrl}/rest/v1/pengaturan_publik?select=iduladha`, { headers: H() });
      if (!r.ok) return;
      const [p] = await r.json();
      C.iduladha = !!(p && p.iduladha);
      $("#banner-kurban").hidden = !C.iduladha;
      $("#chip-kurban").hidden = !C.iduladha;
    } catch { /* tetap pakai config.js */ }
  }
  async function refresh(first) {
    try {
      if (first) await cekModeKurban();
      const [d, u] = await Promise.all([loadProduk(), loadUlasan()]);
      META = { contoh: !!d.contoh };
      ALL = d.produk || [];
      ULASAN = u || [];
      renderMeta(); render(); renderUlasan();
      if (first) {
        const h = decodeURIComponent(location.hash.slice(1));
        if (h && ALL.some((k) => k.kode.toLowerCase() === h.toLowerCase())) openDetail(h, false);
      }
    } catch (e) {
      console.error(e);
      if (first) {
        $("#grid").innerHTML = "";
        $("#empty").hidden = false;
        $("#empty p b").textContent = "Katalog belum bisa dimuat.";
        $("#empty p + p").textContent = "Cek koneksi internet lalu muat ulang halaman, atau tanya admin lewat WhatsApp.";
        $("#live-text").textContent = "Cek koneksi internet, lalu muat ulang halaman";
      }
    }
  }
  refresh(true);
  loadTesti().then(renderTesti);
  if (C.refreshDetik > 0) setInterval(() => { if (!document.hidden && !dlg.open) refresh(false); }, C.refreshDetik * 1000);
})();
