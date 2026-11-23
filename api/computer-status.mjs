// Vercel Node function. Protect the dashboard and /api/* with the same access policy.
export async function probe(env, request = fetch) {
  if (!env.HUB_STATUS_ORIGIN || !env.HUB_STATUS_TOKEN) return "unknown";
  let url;
  try {
    url = new URL(env.HUB_STATUS_ORIGIN);
    if (url.protocol !== "https:" || url.username || url.password ||
        url.pathname !== "/" || url.search || url.hash) return "unknown";
  } catch {
    return "unknown";
  }
  try {
    const response = await request(new URL("/api/computer-status", url), {
      headers: {Authorization: "Bearer " + env.HUB_STATUS_TOKEN},
      cache: "no-store", redirect: "error", signal: AbortSignal.timeout(4000)
    });
    if ([502, 503, 504].includes(response.status)) return "offline";
    if (!response.ok) return "unknown";
    const result = await response.json();
    return result.service === "vanillate-local-hub" && result.status === "online"
      ? "online" : "unknown";
  } catch (error) {
    // A broken TLS configuration or malformed response leaves presence uncertain.
    return error.name === "TimeoutError" ? "offline" : "unknown";
  }
}

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "private, no-store");
  if (req.method !== "GET") return res.status(405).end();
  const status = await probe(process.env);
  return res.status(200).json({service: "vanillate-status", status,
    checked_at: new Date().toISOString()});
}
