// ─────────────────────────────────────────────────────────────────────────────
// PC Workman - basic telemetry sink (Cloudflare Worker)
// ─────────────────────────────────────────────────────────────────────────────
const ALLOWED = [
  "install_id", "app_version", "ts", "kind", "session_id", "session_min",
  "os", "country",
  "cpu", "cpu_cores", "gpu", "ram_gb", "ram_mhz", "disks", "motherboard",
];

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("PC Workman telemetry", { status: 405 });
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return new Response("bad json", { status: 400 });
    }
    if (!body || typeof body !== "object" || !body.install_id) {
      return new Response("missing fields", { status: 400 });
    }

    // Server-side allow-list: keep ONLY known fields, drop anything unexpected.
    const clean = {};
    for (const k of ALLOWED) if (k in body) clean[k] = body[k];
    clean.received = Date.now();   // server time only — no IP, no headers stored

    try {
      const day = new Date(clean.received).toISOString().slice(0, 10);
      const key = `${day}:${clean.install_id}:${clean.received}`;
      await env.TELEMETRY.put(key, JSON.stringify(clean), {
        expirationTtl: 60 * 60 * 24 * 400,   // auto-expire after ~13 months
      });
    } catch (e) {
      return new Response("store error", { status: 500 });
    }

    return new Response(null, { status: 204 });
  },
};
