import {McpServer} from "@modelcontextprotocol/sdk/server/mcp.js";
import {z} from "zod";
import {httpsUrl, projects} from "./config.mjs";

export function makeServer(env, request=fetch) {
  const server = new McpServer({name:"Vanillate Agent Hub",version:"1.0.0"});
  const annotations={readOnlyHint:true,destructiveHint:false,idempotentHint:true};
  const result=data=>({content:[{type:"text",text:JSON.stringify(data)}]});
  server.registerTool("list_projects",{description:"Daftar proyek yang disetujui untuk konektor ini.",annotations},
    async()=>result(Object.entries(projects).map(([id,{name}])=>({id,name}))));
  server.registerTool("get_project_context",{
    description:"Baca konteks terkini dari Hub lokal untuk bot utama atau website.",
    annotations, inputSchema:{project:z.enum(["vanillate-bot","vanillate-web"]),query:z.string().trim().min(1).max(100)}
  },async({project,query})=>{
    try {
      const origin=httpsUrl(env.HUB_BRIDGE_ORIGIN);
      if (origin.pathname!=="/") throw new Error();
      const token=env[projects[project].credential];
      if (!token) throw new Error();
      const url=new URL("/projects/"+project+"/context",origin);
      url.searchParams.set("q",query);
      const response=await request(url,{headers:{Authorization:"Bearer "+token},cache:"no-store",
        redirect:"error",signal:AbortSignal.timeout(5000)});
      if(!response.ok) throw new Error();
      const data=await response.json();
      if(data.project!==project||!Array.isArray(data.resources)) throw new Error();
      return result(data);
    } catch {
      return {isError:true,content:[{type:"text",text:"Konteks live tidak tersedia. Periksa koneksi Hub atau gunakan konektor GitHub Anda untuk membaca peta pada main."}]};
    }
  });
  return server;
}
