"use strict";
const $ = id => document.getElementById(id);
const ns = "http://www.w3.org/2000/svg";
const groups = {
  mint: {color:"#72e2c0", name:"Komponen", icon:"layers"},
  blue: {color:"#8dbbff", name:"Repositori", icon:"repo"},
  amber: {color:"#efc47f", name:"Dokumen", icon:"doc"},
  purple: {color:"#c8a7ed", name:"Lainnya", icon:"box"}
};
const paths = {
  layers:"M3 7l9-5 9 5-9 5z M3 12l9 5 9-5 M3 17l9 5 9-5",
  link:"M9 15l6-6 M8 17l-1 1a4 4 0 01-6-6l5-5a4 4 0 016 0 M16 7l1-1a4 4 0 016 6l-5 5a4 4 0 01-6 0",
  doc:"M6 2h8l4 4v16H6z M14 2v5h4 M9 12h6 M9 16h6",
  repo:"M5 4h14v16H6a2 2 0 010-4h13 M8 7h7",
  box:"M3 7l9-5 9 5v10l-9 5-9-5z M3 7l9 5 9-5 M12 12v10"
};
function svg(tag, attrs={}, content) {
  const item=document.createElementNS(ns,tag);
  Object.entries(attrs).forEach(([k,v])=>item.setAttribute(k,v));
  if(content!==undefined) item.textContent=content;
  return item;
}
function icon(key) {
  const art=svg("svg",{viewBox:"0 0 24 24",width:21,height:21,fill:"none",stroke:"currentColor","stroke-width":1.6,"stroke-linejoin":"round","stroke-linecap":"round","aria-hidden":"true"});
  art.append(svg("path",{d:paths[key]})); return art;
}
document.querySelectorAll("[data-icon]").forEach(el=>el.append(icon(el.dataset.icon)));
function html(tag, value, cls) {
  const el=document.createElement(tag);
  if(value!==undefined) el.textContent=value;
  if(cls) el.className=cls;
  return el;
}
function group(kind) {
  if(/document|specification/i.test(kind)) return "amber";
  if(/repo/i.test(kind)) return "blue";
  if(/component|api|worker/i.test(kind)) return "mint";
  return "purple";
}
const entries=[
  ["api","Hub API","component","hub/api.py","API mengatur akses proyek, event, dan tinjauan Founder."],
  ["repo","Repositori Hub","repository","github.com/Ndyspleasure/vanillate-agent-hub","Repositori implementasi dan dokumentasi Hub."],
  ["db","Database Hub","database","hub/schema.sql","Penyimpanan khusus untuk peta, pekerjaan, dan riwayat."],
  ["brief","Project Brief","document","docs/PROJECT_BRIEF.md","Arahan proyek dan kewenangan Founder."],
  ["mcp","MCP Server","component","hub/mcp_server.py","Antarmuka baca untuk klien MCP."],
  ["worker","Worker Ollama","component","hub/worker.py","Worker lokal mengirim usulan ringkasan untuk ditinjau."],
  ["adr","Keputusan teknis","document","docs/adr/0001-initial-slice.md","Pertimbangan arsitektur untuk implementasi awal."]
];
const demo={name:"Vanillate Agent Hub",nodes:entries.map(([id,name,kind,locator,summary])=>({id,name,kind,locator,summary,source:"docs/ARCHITECTURE.md",authority:id==="brief"?"APPROVED_SPECIFICATION":"TECHNICAL_OBSERVATION"})),
links:[["api","repo","implemented_in"],["api","db","uses"],["api","brief","documented_by"],["mcp","api","calls"],["worker","api","calls"],["api","adr","documented_by"]].map(([origin,target,kind])=>({origin,target,kind,evidence:"brief"}))};
let data=demo, selection="api", asList=false, token="", revision=0, center="api";
function connected(id){return data.links.filter(l=>l.origin===id||l.target===id)}
function selectNode(id){selection=id;render()}
function renderGraph(){
  const graph=$("graph"); graph.replaceChildren();
  if(!data.nodes.length){graph.setAttribute("viewBox","0 0 720 320");graph.append(svg("text",{x:30,y:80,fill:"#a6b8c9"},"Belum ada sumber daya."));return}
  const byId=new Map(data.nodes.map(n=>[n.id,n]));
  const neighbors=[...new Set(connected(center).map(l=>l.origin===center?l.target:l.origin))].filter(id=>id!==center);
  const others=[...neighbors,...data.nodes.map(n=>n.id).filter(id=>id!==center&&!neighbors.includes(id))].slice(0,6);
  const left=others.slice(0,Math.ceil(others.length/2)), right=others.slice(left.length);
  const positions=new Map([[center,[360,171]]]);
  [left,right].forEach((side,i)=>side.forEach((id,k)=>positions.set(id,[i?596:124,171+(k-(side.length-1)/2)*105])));
  graph.setAttribute("viewBox","0 0 720 342");
  const defs=svg("defs");const marker=svg("marker",{id:"arrow",viewBox:"0 0 10 10",refX:9,refY:5,markerWidth:6,markerHeight:6,orient:"auto-start-reverse"});
  marker.append(svg("path",{d:"M0 0 L10 5 L0 10",fill:"#7892a4"}));defs.append(marker);graph.append(defs);
  data.links.forEach(l=>{
    const a=positions.get(l.origin), b=positions.get(l.target);if(!a||!b)return;
    const dx=b[0]-a[0],dy=b[1]-a[1];
    let path;
    if(!dx && !dy) path='M '+a[0]+' '+(a[1]-24)+' c -50 -47 50 -47 20 0';
    else if(!dx) path='M '+a[0]+' '+(a[1]+24*Math.sign(dy))+' L '+b[0]+' '+(b[1]-24*Math.sign(dy));
    else {const x=a[0]+89*Math.sign(dx),end=b[0]-89*Math.sign(dx),mid=(x+end)/2;
      path='M '+x+' '+a[1]+' C '+mid+' '+a[1]+' '+mid+' '+b[1]+' '+end+' '+b[1];}
    const line=svg("path",{d:path,class:"edge","marker-end":"url(#arrow)"});line.append(svg("title",{},l.origin+" · "+l.kind+" · "+l.target));graph.append(line);
  });
  positions.forEach(([x,y],id)=>{
    const n=byId.get(id), g=groups[group(n.kind)], active=selection===id;
    const v=svg("g",{class:"vertex",role:"button",tabindex:"0","aria-label":n.name,"aria-pressed":active,transform:"translate("+x+" "+y+")"});
    v.append(svg("title",{},n.name),svg("rect",{x:-88,y:-23,width:176,height:46,rx:9,fill:active?"#193b3b":"#142334",stroke:active?"#72e2c0":"#3a5164","stroke-width":active?2:1.2}));
    const image=icon(g.icon); image.setAttribute("x",-75);image.setAttribute("y",-10);image.style.color=g.color;
    v.append(image,svg("text",{x:-46,y:5},n.name.length>15?n.name.slice(0,14)+"…":n.name));
    v.onclick=()=>selectNode(id);v.onkeydown=e=>{if(["Enter"," "].includes(e.key)){e.preventDefault();selectNode(id);$("detail").scrollIntoView({block:"nearest"})}};graph.append(v);
  });
}
function renderDetail(){
  const panel=$("detail");panel.replaceChildren();const n=data.nodes.find(n=>n.id===selection);
  if(!n){panel.append(html("p","Belum ada sumber daya untuk ditampilkan."));return}
  const key=group(n.kind), title=html("div",undefined,"resource-title"), avatar=html("div",undefined,"avatar "+key);
  avatar.append(icon(groups[key].icon));title.append(avatar,html("strong",n.name));panel.append(title,html("p",n.summary,"summary"));
  const meta=html("dl",undefined,"meta");
  const fields=[["Jenis",n.kind],["Lokasi",n.locator],["Sumber",n.source],["Kewenangan",n.authority]];
  if(n.observed)fields.push(["Dicatat",new Date(n.observed*1000).toLocaleString("id-ID")],["Kesegaran",n.changed?"Perlu ditinjau":"Sesuai registrasi"]);
  for(const [k,v] of fields){
    const dd=html("dd",v);
    if((k==="Lokasi"||k==="Sumber") && /^https:\/\//.test(v)){
      const a=html("a",v);a.href=v;a.target="_blank";a.rel="noopener noreferrer";dd.replaceChildren(a);
    }
    meta.append(html("dt",k),dd);
  }
  panel.append(meta);
  const links=connected(n.id);panel.append(html("small","RELASI ("+links.length+")"));
  links.forEach(l=>{const target=l.origin===n.id?l.target:l.origin, peer=data.nodes.find(item=>item.id===target);
    const btn=html("button",undefined,"linkrow");btn.append(html("b",peer?.name||target),html("span",l.kind));btn.title="Bukti: "+l.evidence;
    btn.onclick=()=>{center=target;selectNode(target)};panel.append(btn)});
}
function render(){
  $("ncount").textContent=data.nodes.length;$("lcount").textContent=data.links.length;$("dcount").textContent=data.nodes.filter(n=>group(n.kind)==="amber").length;
  $("mapTab").setAttribute("aria-pressed",!asList);$("listTab").setAttribute("aria-pressed",asList);
  $("filterWrap").hidden=!asList;$("list").hidden=!asList;$("plot").hidden=asList;
  if(asList){const list=$("list");list.replaceChildren();const term=$("filter").value.trim().toLowerCase();data.nodes.filter(n=>[n.name,n.id,n.summary,n.locator].some(v=>v.toLowerCase().includes(term))).forEach(n=>{const btn=html("button",n.name);btn.append(html("span",n.kind));btn.onclick=()=>{selection=center=n.id;asList=false;render()};list.append(btn)});
    if(!list.childElementCount)list.append(html("p","Tidak ada sumber daya yang cocok."));}
  else renderGraph();
  renderDetail();
  $("status").textContent=!asList&&data.nodes.length>7?"Graf menampilkan maksimal tujuh sumber daya. Pilih sumber daya lain melalui Daftar.":"";
}
function setMap(map){
  $("filter").value="";data=map;const degrees=new Map(data.nodes.map(n=>[n.id,0]));
  data.links.forEach(l=>{degrees.set(l.origin,degrees.get(l.origin)+1);degrees.set(l.target,degrees.get(l.target)+1)});
  center=selection=[...degrees].sort((a,b)=>b[1]-a[1])[0]?.[0];render();
}
function options(projects){$("projects").replaceChildren(...projects.map(p=>new Option(p.name,p.id)))}
let offlineMaps=[{...demo,id:"demo"}];
function reset(){revision++;token="";options(offlineMaps);$("mode").textContent=offlineMaps.length>1?"Snapshot repositori":"Data contoh";$("connect").textContent="Hubungkan Hub";setMap(offlineMaps[0]);checkComputer()}
async function api(path,credential){
  const res=await fetch(path,{headers:{Authorization:"Bearer "+credential},cache:"no-store",redirect:"error"});
  if(!res.ok)throw Error(res.status===401?"Token tidak berlaku.":res.status===403?"Token tidak memiliki akses baca.":"Hub gagal memuat data ("+res.status+").");
  return res.json();
}
$("connect").hidden=document.body.dataset.live!=="true";
$("connect").onclick=()=>{if(token){reset();return}$("error").textContent="";$("login").showModal();$("token").focus()};
$("cancel").onclick=()=>$("login").close();
$("login").onclose=()=>{$("token").value="";revision++};
$("form").onsubmit=async e=>{
  e.preventDefault();const key=$("token").value.trim(), rev=++revision;
  try{const projects=await api("/projects",key);const map=projects.length?await api("/projects/"+encodeURIComponent(projects[0].id)+"/map",key):{nodes:[],links:[]};
    if(rev!==revision)return;token=key;checkComputer();options(projects);setMap(map);$("mode").textContent="Hub terhubung";$("connect").textContent="Putuskan";$("login").close();
    if(!projects.length)$("status").textContent="Belum ada proyek yang dapat diakses.";
  }catch(err){if(rev===revision)$("error").textContent=err.message}
};
$("projects").onchange=async()=>{if(!token){setMap(offlineMaps.find(m=>m.id===$("projects").value));return}const rev=++revision;setMap({nodes:[],links:[]});
  try{const map=await api("/projects/"+encodeURIComponent($("projects").value)+"/map",token);if(rev===revision)setMap(map)}
  catch(err){if(rev===revision)$("status").textContent=err.message}};
$("mapTab").onclick=()=>{asList=false;render()};$("listTab").onclick=()=>{asList=true;render()};
let probeSequence=0;
let lastOnline=null;
async function checkComputer(){
  const sequence=++probeSequence;
  const local=document.body.dataset.live==="true";
  let state="unknown";
  if(!local || token){
    try{
      const response=await fetch("/api/computer-status",{
        headers:local?{Authorization:"Bearer "+token}:{},cache:"no-store",
        redirect:"error",signal:AbortSignal.timeout(6000)
      });
      if(response.ok){
        const result=await response.json();
        const expected=local?"vanillate-local-hub":"vanillate-status";
        if(result.service===expected && ["online","offline","unknown"].includes(result.status))state=result.status;
      }else if(local && [502,503,504].includes(response.status))state="offline";
    }catch(error){
      if(local && (error.name==="TypeError" || error.name==="TimeoutError"))state="offline";
    }
  }
  if(sequence!==probeSequence)return;
  if(state==="online")lastOnline=new Date();
  const label={online:"Online",offline:"Offline · Hub tidak terjangkau",unknown:"Belum diketahui"};
  $("pcState").textContent="Komputer Hub · "+label[state]+
    (lastOnline && state!=="online"?" · terakhir online "+lastOnline.toLocaleTimeString("id-ID"):"");
  $("gitGuide").hidden=state==="online";
}
setInterval(()=>{if(!document.hidden)checkComputer()},30000);
document.addEventListener("visibilitychange",()=>{if(!document.hidden)checkComputer()});

reset();

$("filter").oninput=render;
if(document.body.dataset.catalog==="true"){
  fetch("./vanillate.json").then(r=>{if(!r.ok)throw Error();return r.json()}).then(maps=>{
    offlineMaps=maps;reset();
  }).catch(()=>{$("status").textContent="Snapshot repositori gagal dimuat. Muat ulang halaman untuk mencoba lagi."});
}
