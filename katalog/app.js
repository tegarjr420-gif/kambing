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
  const PAL = [
    { bg: "#E3ECD9", body: "#FFFFFF", dark: "#3A3A34" },
    { bg: "#F1E7D2", body: "#B07A4A", dark: "#3B2A1C" },
    { bg: "#E2E9E6", body: "#2F2E2B", dark: "#1A1917" },
    { bg: "#EFE9DD", body: "#E8DCC4", dark: "#6B5536" },
  ];
  const hash = (s) => [...String(s)].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7);
  function goatSVG(k) {
    const p = PAL[hash(k.kode) % PAL.length];
    const domba = String(k.jenis).toLowerCase() === "domba";
    const wool = domba
      ? [[130, 150], [165, 128], [205, 124], [245, 132], [270, 160], [250, 192], [205, 200], [160, 198], [128, 180]]
          .map(([x, y]) => `<circle cx="${x}" cy="${y}" r="30" fill="${p.body}" stroke="${p.dark}" stroke-opacity=".18" stroke-width="3"/>`).join("")
      : `<ellipse cx="200" cy="163" rx="96" ry="50" fill="${p.body}" stroke="${p.dark}" stroke-opacity=".2" stroke-width="3"/>`;
    const horn = domba
      ? `<path d="M286 92c-14-12-30-4-28 10 2 10 14 12 18 4" fill="none" stroke="${p.dark}" stroke-width="9" stroke-linecap="round" opacity=".75"/>`
      : `<path d="M292 86c-6-22-24-34-40-30" fill="none" stroke="${p.dark}" stroke-width="8" stroke-linecap="round" opacity=".75"/>`;
    const beard = domba || String(k.kelamin).toLowerCase() !== "jantan" ? "" : `<path d="M318 132l-6 26-10-22z" fill="${p.dark}" opacity=".7"/>`;
    return `<svg class="goat" viewBox="0 0 400 300" role="img" aria-label="Ilustrasi ${esc(k.jenis)}, foto menyusul" preserveAspectRatio="xMidYMid slice">
      <rect width="400" height="300" fill="${p.bg}"/>
      <ellipse cx="200" cy="272" rx="190" ry="40" fill="#000" opacity=".05"/>
      <g fill="${p.dark}" opacity=".85">
        <rect x="134" y="190" width="15" height="70" rx="7"/><rect x="162" y="194" width="15" height="66" rx="7"/>
        <rect x="232" y="194" width="15" height="66" rx="7"/><rect x="258" y="190" width="15" height="70" rx="7"/>
      </g>
      <path d="M108 140l-16-22 26 8z" fill="${p.body}" stroke="${p.dark}" stroke-opacity=".2" stroke-width="3"/>
      ${wool}
      <path d="M262 150c4-34 14-52 30-58l20 34c-8 14-22 28-40 34z" fill="${p.body}" stroke="${p.dark}" stroke-opacity=".2" stroke-width="3"/>
      ${horn}
      <ellipse cx="308" cy="112" rx="30" ry="22" transform="rotate(28 308 112)" fill="${p.body}" stroke="${p.dark}" stroke-opacity=".2" stroke-width="3"/>
      <ellipse cx="282" cy="108" rx="18" ry="8" transform="rotate(-30 282 108)" fill="${p.dark}" opacity=".55"/>
      <circle cx="308" cy="104" r="4" fill="${p.dark}"/>
      ${beard}
      <text x="200" y="292" text-anchor="middle" font-family="Plus Jakarta Sans, sans-serif" font-size="13" font-weight="600" fill="${p.dark}" opacity=".45">foto menyusul</text>
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
        <h3 class="c-title">${esc(k.jenis)} ${esc(k.ras || "")}<small>${esc(k.kelamin || "")}</small></h3>
        ${C.iduladha && k.layak_kurban ? `<span class="kurban-lbl">Layak kurban</span>` : ""}
        <dl class="stats"><div><dt>Berat</dt><dd>${berat(k.berat_kg)}</dd></div><div><dt>Umur</dt><dd>${umur(k.umur_bulan)}</dd></div></dl>
        <p class="price">${rupiah(k.harga)}</p>
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
  async function refresh(first) {
    try {
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
