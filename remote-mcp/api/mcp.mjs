import {createRemoteJWKSet,jwtVerify} from "jose";
import {StreamableHTTPServerTransport} from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import {authConfig,resource,scope} from "../lib/config.mjs";
import {makeServer} from "../lib/server.mjs";

const metadata="https://mcp.vanillate.id/.well-known/oauth-protected-resource/mcp";
const keysets=new Map();
function remoteKeys(url) {
  if(!keysets.has(url.href))keysets.set(url.href,createRemoteJWKSet(url));
  return keysets.get(url.href);
}

export function handlerFor(env, keys=remoteKeys, upstream=fetch) {
  return async function handler(req,res) {
    res.setHeader("Cache-Control","private, no-store");
    if(req.headers.origin && req.headers.origin!==new URL(resource).origin) return res.status(403).end();
    let cfg;
    try { cfg=authConfig(env); }
    catch {return res.status(503).json({error:"oauth_not_configured"});}
    const challenge='Bearer resource_metadata="'+metadata+'", scope="'+scope+'"';
    const token=/^Bearer ([^\s]+)$/i.exec(req.headers.authorization||"")?.[1];
    if(!token){res.setHeader("WWW-Authenticate",challenge);return res.status(401).end();}
    try{
      const {payload}=await jwtVerify(token,keys(cfg.keys),{algorithms:["RS256","ES256"],
        issuer:cfg.issuer,audience:resource,requiredClaims:["exp","sub","iat"]});
      if(payload.sub!==cfg.subject || (payload.client_id??payload.azp)!==cfg.client ||
        typeof payload.scope!=="string" || !payload.scope.split(" ").includes(scope))return res.status(403).end();
    }catch{res.setHeader("WWW-Authenticate",challenge);return res.status(401).end();}
    if(req.method!=="POST"){res.setHeader("Allow","POST");return res.status(405).end();}
    const server=makeServer(env,upstream);
    const transport=new StreamableHTTPServerTransport({sessionIdGenerator:undefined,enableJsonResponse:true});
    try{
      await server.connect(transport);
      await transport.handleRequest(req,res,req.body);
    }finally{await server.close();}
  };
}

export default handlerFor(process.env);
