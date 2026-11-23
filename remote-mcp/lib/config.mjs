export const resource = "https://mcp.vanillate.id/mcp";
export const scope = "hub.read";
// CMS advertises OIDC scopes. The API permission is a separate signed token claim.
export function consentScope(issuer) {
  return issuer === "https://lvfwopnvvqncopvathop.supabase.co/auth/v1" ? "openid" : scope;
}
export function grantsHubRead(payload, issuer) {
  if (consentScope(issuer) === "openid") return payload.hub_permission === scope;
  return typeof payload.scope === "string" && payload.scope.split(" ").includes(scope);
}
export const projects = Object.freeze({
  "vanillate-bot": {name:"Bot utama · Vanillate.ID", credential:"HUB_BOT_READER"},
  "vanillate-web": {name:"Website · vanillate.id", credential:"HUB_WEB_READER"}
});

export function httpsUrl(value) {
  const url = new URL(value);
  if (url.protocol !== "https:" || url.username || url.password || url.search || url.hash) {
    throw new Error("Expected an HTTPS service URL");
  }
  return url;
}

export function authConfig(env) {
  httpsUrl(env.MCP_OAUTH_ISSUER);
  const keys = httpsUrl(env.MCP_OAUTH_JWKS);
  if (!env.MCP_ALLOWED_SUBJECT || !env.MCP_CLAUDE_CLIENT_ID) throw new Error("OAuth setup incomplete");
  return {issuer:env.MCP_OAUTH_ISSUER, keys, subject:env.MCP_ALLOWED_SUBJECT, client:env.MCP_CLAUDE_CLIENT_ID};
}
