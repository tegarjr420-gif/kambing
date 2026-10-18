(() => {
  "use strict";
  const C = window.BF_CONFIG || {};
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));

  /* ---------- format ---------- */
  const rupiah = (n) => "Rp" + Math.round(Number(n) || 0).toLocaleString("id-ID");
  const umur = (bln) => {
    bln = Number(bln) || 0;
    if (!bln) return "–";
    if (bln < 12) return `${bln} bulan`;
    const y = Math.floor(bln / 12), m = bln % 12;
    return m ? `${y} th ${m} bln` : `${y} tahun`;
  };
  const berat = (kg) => (kg ? `${String(kg).replace(".", ",")} kg` : "–");
  const relTime = (iso) => {
    const t = new Date(iso).getTime();
    if (!t) return "";
    const d = Math.max(0, (Date.now() - t) / 1000);
    if (d < 90) return "baru saja";
    if (d < 3600) return `${Math.round(d / 60)} menit lalu`;
    if (d < 86400) return `${Math.round(d / 3600)} jam lalu`;
    return new Date(t).toLocaleDateString("id-ID", { day: "numeric", month: "long" });
  };
  const STATUS = {
    tersedia: { label: "Tersedia", cls: "" },
    ditahan: { label: "Sedang dipesan", cls: "ditahan" },
    dp: { label: "Sudah di-DP", cls: "dp" },
  };
  const isOpen = (k) => k.status === "tersedia";

  /* ---------- WhatsApp ---------- */
  const wa = (text) => `https://wa.me/${C.waCS}?text=${encodeURIComponent(text)}`;
  const nama = (k) => `${k.jenis} ${k.ras || ""} ${String(k.kelamin || "").toLowerCase()}`.replace(/\s+/g, " ").trim();
  const MSG = {
    umum: `Halo ${C.namaToko}, saya mau tanya kambing/domba yang tersedia.`,
    stok: `Halo ${C.namaToko}, saya cari kambing/domba dengan kriteria: `,
    kunjung: `Halo ${C.namaToko}, saya mau datang ke kandang hari … sekitar jam …`,
  };
  const msgPesan = (k) => `Halo ${C.namaToko}, saya mau pesan *${k.kode}* (${nama(k)}, ${berat(k.berat_kg)}, ${rupiah(k.harga)}). Masih tersedia?`;
  const msgAntre = (k) => `Halo ${C.namaToko}, kalau *${k.kode}* (${nama(k)}) tersedia lagi, tolong kabari saya ya.`;

  /* ---------- ilustrasi pengganti foto ---------- */
  // Ilustrasi kambing/domba berdiri menghadap kanan, dipakai selama foto asli belum ada.
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
  const hash = (s) => [...String(s)].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7);
  function goatSVG(k) {
    const h = hash(k.kode);
    const s = SCENE[h % SCENE.length];
    const id = "c" + h.toString(36) + Math.random().toString(36).slice(2, 6);
    const jantan = String(k.kelamin).toLowerCase() === "jantan";
    const domba = String(k.jenis).toLowerCase() === "domba";
    const bg = `<rect width="400" height="300" fill="${s.sky}"/>
      <path d="M0 178C70 150 150 146 220 164S350 150 400 140V300H0Z" fill="${s.hill}"/>
      <path d="M0 246C90 232 210 232 300 240S380 246 400 244V300H0Z" fill="${s.ground}"/>
      <ellipse cx="214" cy="257" rx="112" ry="9" fill="#000" opacity=".09"/>`;
    let animal;
    if (domba) {
      const p = SHEEP[(h >> 3) % SHEEP.length];
      const puffs = [[150, 168, 30], [178, 146, 30], [214, 140, 31], [250, 146, 30], [276, 166, 28], [270, 194, 27], [238, 206, 28], [200, 208, 29], [164, 200, 28], [144, 186, 24]];
      const horn = jantan ? `<path d="M304 112C288 96 266 106 268 126C270 144 292 148 298 134C302 124 292 118 284 124" fill="none" stroke="${p.horn}" stroke-width="10" stroke-linecap="round"/>` : "";
      animal = `
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
    } else {
      const p = GOAT[(h >> 3) % GOAT.length];
      const body = "M132 170C130 146 156 136 196 136C236 136 262 134 280 146C296 157 298 192 286 206C266 224 176 226 146 212C134 205 132 188 132 170Z";
      const patch = p.patch
        ? `<g clip-path="url(#${id})"><ellipse cx="170" cy="160" rx="34" ry="24" fill="${p.patch}"/><ellipse cx="258" cy="190" rx="26" ry="20" fill="${p.patch}"/></g>`
        : "";
      const legs = [[148, 196], [170, 200], [250, 200], [270, 196]]
        .map(([x, y]) => `<rect x="${x}" y="${y}" width="13" height="${254 - y}" rx="6" fill="${p.coat}" stroke="${p.shade}" stroke-width="2"/><rect x="${x}" y="248" width="13" height="8" rx="3" fill="${p.hoof}"/>`).join("");
      const beard = jantan ? `<path d="M336 130C336 144 332 156 326 162C322 152 322 140 326 130Z" fill="${p.shade}"/>` : "";
      const horns = jantan
        ? `<path d="M310 82C306 58 290 46 270 50" fill="none" stroke="${p.horn}" stroke-width="9" stroke-linecap="round"/><path d="M318 80C318 60 306 48 290 46" fill="none" stroke="${p.horn}" stroke-width="7" stroke-linecap="round"/>`
        : `<path d="M312 82C310 68 302 60 292 58" fill="none" stroke="${p.horn}" stroke-width="7" stroke-linecap="round"/>`;
      animal = `
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
    return `<svg class="goat" viewBox="0 0 400 300" role="img" aria-label="Ilustrasi ${esc(k.jenis)}, foto menyusul" preserveAspectRatio="xMidYMid slice">
      ${bg}${animal}
      <text x="200" y="286" text-anchor="middle" font-family="Plus Jakarta Sans, sans-serif" font-size="12.5" font-weight="700" fill="#1E4A2C" opacity=".5">foto menyusul</text>
    </svg>`;
  }
  const media = (k, i = 0) =>
    k.foto && k.foto[i]
      ? `<img src="${esc(k.foto[i])}" alt="Foto ${esc(k.kode)}, ${esc(nama(k))}" loading="lazy" decoding="async">`
      : goatSVG(k);

  /* ---------- data ---------- */
  let ALL = [], META = { contoh: false };
  async function loadKambing() {
    if (C.supabaseUrl && C.supabaseAnonKey) {
      const u = `${C.supabaseUrl}/rest/v1/katalog?select=*&order=kode.asc`;
      const r = await fetch(u, { headers: { apikey: C.supabaseAnonKey, Authorization: `Bearer ${C.supabaseAnonKey}` } });
      if (!r.ok) throw new Error("supabase " + r.status);
      return { contoh: false, kambing: await r.json() };
    }
    const r = await fetch(`data/kambing.json?v=${Date.now()}`);
    if (!r.ok) throw new Error("json " + r.status);
    return r.json();
  }
  async function loadTesti() {
    try {
      if (C.supabaseUrl && C.supabaseAnonKey) {
        const u = `${C.supabaseUrl}/rest/v1/testimoni_publik?select=*&order=tanggal.desc&limit=24`;
        const r = await fetch(u, { headers: { apikey: C.supabaseAnonKey, Authorization: `Bearer ${C.supabaseAnonKey}` } });
        return r.ok ? r.json() : [];
      }
      const r = await fetch(`data/testimoni.json?v=${Date.now()}`);
      return r.ok ? (await r.json()).testimoni || [] : [];
    } catch { return []; }
  }

  /* ---------- filter ---------- */
  const F = { jenis: "", kelamin: new Set(), kurban: false, q: "", sort: "murah" };
  function visible() {
    const q = F.q.trim().toLowerCase().replace(/\s+/g, "");
    let list = ALL.filter((k) =>
      (!F.jenis || k.jenis === F.jenis) &&
      (!F.kelamin.size || F.kelamin.has(k.kelamin)) &&
      (!F.kurban || k.layak_kurban) &&
      (!q || String(k.kode).toLowerCase().replace(/[\s-]/g, "").includes(q.replace(/-/g, "")) ||
        `${k.jenis} ${k.ras}`.toLowerCase().replace(/\s+/g, "").includes(q))
    );
    const by = { murah: (a, b) => a.harga - b.harga, mahal: (a, b) => b.harga - a.harga, berat: (a, b) => (b.berat_kg || 0) - (a.berat_kg || 0) }[F.sort];
    return list.sort((a, b) => (isOpen(b) - isOpen(a)) || by(a, b));
  }

  /* ---------- render ---------- */
  function card(k) {
    const st = STATUS[k.status] || STATUS.tersedia;
    const open = isOpen(k);
    const n = (k.foto || []).length;
    return `<article class="card${open ? "" : " is-off"}" data-kode="${esc(k.kode)}">
      <button class="media" type="button" data-open="${esc(k.kode)}" aria-label="Lihat detail ${esc(k.kode)}">
        ${media(k)}
        <span class="tag">${esc(k.kode)}</span>
        <span class="pill ${st.cls}">${st.label}</span>
        ${n > 1 ? `<span class="count">${n} foto</span>` : ""}
      </button>
      <div class="c-body">
        <div class="c-head">
          <h3 class="c-title">${esc(k.jenis)} ${esc(k.ras || "")}</h3>
          <span class="sex sex-${String(k.kelamin || "").toLowerCase()}">${esc(k.kelamin || "")}</span>
        </div>
        ${C.iduladha && k.layak_kurban ? `<span class="kurban-lbl">Layak kurban</span>` : ""}
        <dl class="stats">
          <div><svg aria-hidden="true"><use href="#ic-scale"/></svg><dt>Berat</dt><dd>${berat(k.berat_kg)}</dd></div>
          <div><svg aria-hidden="true"><use href="#ic-cal"/></svg><dt>Umur</dt><dd>${umur(k.umur_bulan)}</dd></div>
        </dl>
        <p class="price"><span class="price-lbl">Harga</span>${rupiah(k.harga)}</p>
        ${open
          ? `<a class="btn btn-wa btn-block" href="${wa(msgPesan(k))}" target="_blank" rel="noopener"><svg aria-hidden="true"><use href="#ic-wa"/></svg>Pesan lewat WhatsApp</a>`
          : `<a class="btn btn-ghost btn-block" href="${wa(msgAntre(k))}" target="_blank" rel="noopener">Kabari saya kalau batal</a>`}
      </div>
    </article>`;
  }
  function render() {
    const list = visible();
    $("#grid").innerHTML = list.map(card).join("");
    $("#empty").hidden = list.length > 0;
    const kosong = ALL.length === 0;
    $("#empty p b").textContent = kosong ? "Stok sedang diperbarui." : "Belum ada yang cocok dengan pilihanmu.";
    $("#empty p + p").textContent = kosong ? "Kambing dan domba baru akan tampil di sini. Tanya admin untuk stok terbaru, atau datang langsung ke kandang." : "Coba hapus saringan, atau tanya admin untuk stok lainnya.";
    $("#reset").hidden = kosong;
  }
  function renderMeta() {
    const n = ALL.filter(isOpen).length;
    $("#live-text").textContent = n ? `${n} ekor siap dibawa pulang hari ini` : "Stok sedang kosong, tanya admin untuk stok berikutnya";
    const last = ALL.map((k) => k.updated_at).filter(Boolean).sort().pop();
    $("#updated").textContent = last ? `Diperbarui ${relTime(last)}` : "";
    $("#notice-contoh").hidden = !META.contoh;
  }
  function renderTesti(t) {
    $("#testi").innerHTML = t.map((x) => `<figure>
      <img src="${esc(x.foto_url)}" alt="Serah terima ${esc(x.kode_kambing || "kambing")}" loading="lazy">
      <figcaption>${esc(x.caption || "Terima kasih sudah percaya Barokah Farm")}<small>${[x.kota, x.tanggal && new Date(x.tanggal).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" })].filter(Boolean).map(esc).join(", ")}</small></figcaption>
    </figure>`).join("");
    $("#testi-empty").hidden = t.length > 0;
  }

  /* ---------- detail ---------- */
  const dlg = $("#detail");
  function openDetail(kode, push = true) {
    const k = ALL.find((x) => String(x.kode).toLowerCase() === String(kode).toLowerCase());
    if (!k) return;
    const st = STATUS[k.status] || STATUS.tersedia;
    const n = Math.max(1, (k.foto || []).length);
    $("#d-media").innerHTML = Array.from({ length: n }, (_, i) => media(k, i)).join("");
    $("#d-tag").textContent = k.kode;
    $("#d-pill").className = `pill ${st.cls}`;
    $("#d-pill").textContent = st.label;
    $("#d-title").textContent = `${k.jenis} ${k.ras || ""} ${String(k.kelamin || "").toLowerCase()}`.trim();
    $("#d-specs").innerHTML = [["Berat", berat(k.berat_kg)], ["Umur", umur(k.umur_bulan)], ["Jenis kelamin", k.kelamin || "–"], ["Ras", k.ras || "–"]]
      .concat(C.iduladha ? [["Kurban", k.layak_kurban ? "Layak kurban" : "Belum cukup umur"]] : [])
      .map(([a, b]) => `<div><dt>${a}</dt><dd>${esc(b)}</dd></div>`).join("");
    $("#d-note").hidden = !k.catatan;
    $("#d-note").textContent = k.catatan || "";
    $("#d-price").textContent = rupiah(k.harga);
    const b = $("#d-wa");
    if (isOpen(k)) {
      b.href = wa(msgPesan(k)); b.className = "btn btn-wa btn-block";
      b.querySelector("span").textContent = "Pesan lewat WhatsApp";
      $("#d-fine").textContent = `DP minimal ${rupiah(C.dpMinimal)}, pelunasan paling lambat ${C.batasPelunasanHari} hari setelah DP dikonfirmasi. Atau datang langsung ke kandang jam ${C.jamBuka}.`;
    } else {
      b.href = wa(msgAntre(k)); b.className = "btn btn-ghost btn-block";
      b.querySelector("span").textContent = "Kabari saya kalau batal";
      $("#d-fine").textContent = `Kambing ini sedang dipesan pembeli lain. Kalau tidak dilunasi dalam ${C.batasPelunasanHari} hari, kambing kembali tersedia.`;
    }
    if (!dlg.open) dlg.showModal();
    if (push) history.replaceState(null, "", `#${k.kode}`);
  }
  function closeDetail() {
    if (dlg.open) dlg.close();
  }
  dlg.addEventListener("close", () => { if (/^#BF/i.test(location.hash) || ALL.some((k) => `#${k.kode}` === location.hash)) history.replaceState(null, "", location.pathname + location.search); });
  dlg.addEventListener("click", (e) => { if (e.target === dlg) closeDetail(); });
  $("#d-close").addEventListener("click", closeDetail);
  $("#grid").addEventListener("click", (e) => { const t = e.target.closest("[data-open]"); if (t) openDetail(t.dataset.open); });

  /* ---------- kontrol filter ---------- */
  $$(".seg button").forEach((b) => b.addEventListener("click", () => {
    $$(".seg button").forEach((x) => x.setAttribute("aria-checked", String(x === b)));
    F.jenis = b.dataset.jenis; render();
  }));
  $$(".chip[data-kelamin]").forEach((b) => b.addEventListener("click", () => {
    const on = b.getAttribute("aria-pressed") !== "true";
    b.setAttribute("aria-pressed", String(on));
    on ? F.kelamin.add(b.dataset.kelamin) : F.kelamin.delete(b.dataset.kelamin); render();
  }));
  $("#chip-kurban").addEventListener("click", (e) => {
    F.kurban = !F.kurban; e.currentTarget.setAttribute("aria-pressed", String(F.kurban)); render();
  });
  $("#q").addEventListener("input", (e) => { F.q = e.target.value; render(); });
  $("#sort").addEventListener("change", (e) => { F.sort = e.target.value; render(); });
  $("#reset").addEventListener("click", () => {
    F.jenis = ""; F.kelamin.clear(); F.kurban = false; F.q = ""; $("#q").value = "";
    $$(".seg button").forEach((x, i) => x.setAttribute("aria-checked", String(i === 0)));
    $$(".chip").forEach((x) => x.setAttribute("aria-pressed", "false")); render();
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
  const O = C.otomaya || {};
  $$(".js-oto-web").forEach((a) => (a.href = `${O.web}/?ref=barokahfarm`));
  $$(".js-oto-ig").forEach((a) => (a.href = O.instagram));
  $$(".js-oto-tt").forEach((a) => (a.href = O.tiktok));
  $$(".js-oto-ig-h").forEach((e) => (e.textContent = `Instagram ${O.igHandle}`));
  $$(".js-oto-tt-h").forEach((e) => (e.textContent = `TikTok ${O.tiktokHandle}`));
  if (C.iduladha) { $("#banner-kurban").hidden = false; $("#chip-kurban").hidden = false; }

  const toast = (t) => { const el = $("#toast"); el.textContent = t; el.classList.add("on"); clearTimeout(toast.t); toast.t = setTimeout(() => el.classList.remove("on"), 2200); };
  $("#copy-rek").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(String(rek.nomor)); toast("Nomor rekening disalin"); }
    catch { toast(`${rek.nomor}`); }
  });

  // watermark disembunyikan saat kredit di footer sudah terlihat
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(([e]) => $("#oto-badge").classList.toggle("hide", e.isIntersecting), { threshold: 0.2 }).observe($("#credit"));
  }

  /* ---------- muat ---------- */
  $("#grid").innerHTML = '<div class="skel"></div><div class="skel"></div><div class="skel"></div>';
  async function cekModeKurban() {
    if (!(C.supabaseUrl && C.supabaseAnonKey)) return;
    try {
      const r = await fetch(`${C.supabaseUrl}/rest/v1/pengaturan_publik?select=iduladha`, { headers: { apikey: C.supabaseAnonKey, Authorization: `Bearer ${C.supabaseAnonKey}` } });
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
      const d = await loadKambing();
      META = { contoh: !!d.contoh };
      ALL = (d.kambing || []).filter((k) => STATUS[k.status]);
      renderMeta(); render();
      if (first) {
        const h = decodeURIComponent(location.hash.slice(1));
        if (h && ALL.some((k) => k.kode.toLowerCase() === h.toLowerCase())) openDetail(h, false);
      }
    } catch (e) {
      if (first) {
        $("#grid").innerHTML = "";
        $("#empty").hidden = false;
        $("#empty p b").textContent = "Katalog belum bisa dimuat.";
        $("#live-text").textContent = "Cek koneksi internet, lalu muat ulang halaman";
      }
    }
  }
  refresh(true);
  loadTesti().then(renderTesti);
  if (C.refreshDetik > 0) setInterval(() => { if (!document.hidden && !dlg.open) refresh(false); }, C.refreshDetik * 1000);
})();
