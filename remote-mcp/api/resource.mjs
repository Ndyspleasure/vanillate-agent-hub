import {authConfig, resource, scope} from "../lib/config.mjs";
export default function handler(req, res) {
  res.setHeader("Cache-Control","no-store");
  if (req.method !== "GET") return res.status(405).end();
  try {
    const {issuer} = authConfig(process.env);
    return res.status(200).json({resource, authorization_servers:[issuer],
      scopes_supported:[scope], bearer_methods_supported:["header"]});
  } catch {
    return res.status(503).json({error:"oauth_not_configured"});
  }
}
