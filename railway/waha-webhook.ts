// Railway Function (Bun): pasang webhook WAHA -> n8n lalu cek status sesi.
// Variabel: WAHA_KEY, WEBHOOK_URL
const BASE = "http://devlikeaprowaha.railway.internal:8080";
const H = { "X-Api-Key": Bun.env.WAHA_KEY ?? "", "Content-Type": "application/json" };
async function j(path: string, init: any = {}) {
  const r = await fetch(BASE + path, { ...init, headers: H });
  return { status: r.status, body: await r.text() };
}
const url = Bun.env.WEBHOOK_URL ?? "";
const before = await j("/api/sessions/default");
console.log("SEBELUM", before.status, before.body.slice(0, 400));
const upd = await j("/api/sessions/default", {
  method: "PUT",
  body: JSON.stringify({
    name: "default",
    config: { webhooks: [{ url, events: ["message"], retries: { policy: "constant", delaySeconds: 3, attempts: 3 } }] }
  })
});
console.log("UPDATE", upd.status, upd.body.slice(0, 600));
for (let i = 0; i < 12; i++) {
  await Bun.sleep(5000);
  const s = await j("/api/sessions/default");
  let st = "";
  try { st = JSON.parse(s.body).status; } catch {}
  console.log("STATUS", st);
  if (st === "WORKING") { console.log("WEBHOOK_OK", url); break; }
}
console.log("DONE");
