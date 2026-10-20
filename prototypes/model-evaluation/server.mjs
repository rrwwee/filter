import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
const root=process.cwd(), dir=path.join(root,'local-results');await fs.mkdir(dir,{recursive:true});
const types={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.wasm':'application/wasm','.css':'text/css'};
http.createServer(async(req,res)=>{res.setHeader('Cross-Origin-Opener-Policy','same-origin');res.setHeader('Cross-Origin-Embedder-Policy','require-corp');res.setHeader('Cache-Control','no-store');try{
 if(req.method==='POST'&&req.url==='/labels'){let chunks=[];for await(const c of req)chunks.push(c);const data=JSON.parse(Buffer.concat(chunks));await fs.writeFile(path.join(dir,'latest-labels.json'),JSON.stringify(data,null,2));res.end('{}');return;}
 if(req.method==='POST'&&req.url==='/save'){let chunks=[];for await(const c of req)chunks.push(c);let data=JSON.parse(Buffer.concat(chunks));let name=`run-${Date.now()}.json`;await fs.writeFile(path.join(dir,name),JSON.stringify(data,null,2));res.end(JSON.stringify({name}));return;}
 let url=new URL(req.url,'http://localhost'), p=path.resolve(root,'.'+decodeURIComponent(url.pathname==='/'?'/prototypes/model-evaluation/index.html':url.pathname));if(!p.startsWith(root+path.sep))throw Error('Bad path');let b=await fs.readFile(p);res.setHeader('Content-Type',types[path.extname(p)]||'application/octet-stream');res.end(b);
}catch(e){res.statusCode=404;res.end(String(e));}}).listen(8766,'127.0.0.1',()=>console.log('Local-only evaluation: http://127.0.0.1:8766'));
