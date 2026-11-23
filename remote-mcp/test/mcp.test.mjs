import {test} from "node:test";
import assert from "node:assert/strict";
import {createServer} from "node:http";
import {generateKeyPair, SignJWT} from "jose";
import {Client} from "@modelcontextprotocol/sdk/client/index.js";
import {StreamableHTTPClientTransport} from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import {handlerFor} from "../api/mcp.mjs";
import {resource} from "../lib/config.mjs";

test("authenticated SDK session has two read tools and isolates project credentials",async()=>{
  const {privateKey,publicKey}=await generateKeyPair("RS256");
  const env={MCP_OAUTH_ISSUER:"https://auth.example.org",MCP_OAUTH_JWKS:"https://auth.example.org/keys",
    MCP_ALLOWED_SUBJECT:"owner",MCP_CLAUDE_CLIENT_ID:"claude",HUB_BRIDGE_ORIGIN:"https://pc.example.org",HUB_WEB_READER:"web-only"};
  const sign=(sub,aud=resource)=>new SignJWT({client_id:"claude",scope:"hub.read"}).setSubject(sub)
    .setIssuer(env.MCP_OAUTH_ISSUER).setAudience(aud).setIssuedAt().setExpirationTime("5m")
    .setProtectedHeader({alg:"RS256"}).sign(privateKey);
  let calls=0;
  const handler=handlerFor(env,()=>publicKey,async(url,opts)=>{
    calls++;assert.equal(url.pathname,"/projects/vanillate-web/context");
    assert.equal(opts.headers.Authorization,"Bearer web-only");
    return Response.json({project:"vanillate-web",resources:[]});
  });
  const http=createServer((req,res)=>{
    res.status=n=>{res.statusCode=n;return res};res.json=obj=>res.end(JSON.stringify(obj));
    handler(req,res).catch(()=>{res.statusCode=500;res.end()});
  });
  await new Promise(done=>http.listen(0,"127.0.0.1",done));
  const url=new URL("http://127.0.0.1:"+http.address().port+"/mcp");
  const client=new Client({name:"test",version:"1"});
  try{
    assert.equal((await fetch(url)).status,401);
    for(const [sub,aud,status] of [["other",resource,403],["owner","other",401]]){
      assert.equal((await fetch(url,{headers:{Authorization:"Bearer "+await sign(sub,aud)}})).status,status);
    }
    await client.connect(new StreamableHTTPClientTransport(url,{requestInit:{headers:{Authorization:"Bearer "+await sign("owner")}}}));
    assert.deepEqual((await client.listTools()).tools.map(t=>t.name).sort(),["get_project_context","list_projects"]);
    const call=project=>client.callTool({name:"get_project_context",arguments:{project,query:"docs"}});
    assert.ok(!(await call("vanillate-web")).isError);
    assert.ok((await call("private-project")).isError);
    assert.ok((await call("vanillate-bot")).isError);
    assert.equal(calls,1);
  }finally{await client.close();http.closeAllConnections();await new Promise(done=>http.close(done));}
});
