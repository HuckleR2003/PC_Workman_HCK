// ─────────────────────────────────────────────────────────────────────────────
// PC Workman — anonymous telemetry sink (Cloudflare Worker)
// ─────────────────────────────────────────────────────────────────────────────
// Receives the opt-in anonymous snapshot from the desktop app and stores only an
// allow-listed set of fields. It never stores IP addresses or anything personal.
//
// DEPLOY (one time):
//   1. Cloudflare dashboard → Workers & Pages → Create → Worker. Paste this file.
//   2. Create a KV namespace (Storage & Databases → KV), e.g. "pcworkman_telemetry".
//   3. Worker → Settings → Variables → KV Namespace Bindings:
//        Variable name: TELEMETRY   →   your KV namespace.
//   4. Deploy. Copy the Worker URL (e.g. https://telemetry.pcworkman.dev/collect
//      via a custom route, or the workers.dev URL).
//   5. Put that URL in  core/telemetry.py → ENDPOINT.
//
// The app only ever calls this when the user turned Network Access + Telemetry on.
// ─────────────────────────────────────────────────────────────────────────────

const ALLOWED = [
  "install_id", "app_version", "ts", "session_min", "os", "country",
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
      const key = `${clean.install_id}:${clean.received}`;
      await env.TELEMETRY.put(key, JSON.stringify(clean), {
        expirationTtl: 60 * 60 * 24 * 400,   // auto-expire after ~13 months
      });
    } catch (e) {
      return new Response("store error", { status: 500 });
    }

    return new Response(null, { status: 204 });
  },
};
