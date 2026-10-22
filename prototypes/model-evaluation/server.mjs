import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {validateLabelSnapshot} from './label-state.mjs';

const assets = new Set(['index.html','app.mjs','contracts.mjs','label.html','labeling.mjs','label-state.mjs','autosave.mjs','report.html']);
const dataFiles = new Set(['labeling-cases.json','latest-labels.json','bullet-cases.json']);
const dependencyRoots = ['@opendecider/web/dist/','@opendecider/client/dist/','@huggingface/tokenizers/dist/','onnxruntime-web/dist/','@r4ai/laya-web/dist/'];
const types = {'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.wasm':'application/wasm','.css':'text/css'};
const fail = (status, message) => Object.assign(new Error(message), {status});

export function serializedWrites() {
  let tail = Promise.resolve();
  return task => { const job = tail.then(task); tail = job.catch(() => {}); return job; };
}

async function safePath(root, relative) {
  const target = path.resolve(root, relative);
  if (!target.startsWith(root+path.sep)) throw fail(404,'Not found');
  let current = root;
  for (const part of path.relative(root,target).split(path.sep)) {
    current = path.join(current,part);
    const stat = await fs.lstat(current);
    if (stat.isSymbolicLink()) throw fail(404,'Not found');
  }
  return target;
}

async function atomicWrite(target, content, replace) {
  const temporary = path.join(path.dirname(target), '.pending-'+randomUUID());
  let handle;
  try {
    handle = await fs.open(temporary, 'wx', 0o600);
    await handle.writeFile(content); await handle.sync(); await handle.close(); handle = null;
    if (replace) {
      try { if ((await fs.lstat(target)).isSymbolicLink()) throw fail(400,'Invalid destination'); }
      catch (error) { if (error.code !== 'ENOENT') throw error; }
      await fs.rename(temporary,target);
    } else {
      // Hard link provides atomic create-without-overwrite; the temp file is complete.
      await fs.link(temporary,target);
    }
  } finally {
    if (handle) await handle.close();
    await fs.unlink(temporary).catch(error => { if (error.code !== 'ENOENT') throw error; });
  }
}

function allowedRequest(req, port) {
  const host = req.headers.host;
  if (!host || /[\s/@\\]/.test(host)) throw fail(403,'Loopback host required');
  let url; try { url = new URL('http://'+host); } catch { throw fail(403,'Loopback host required'); }
  if (url.host.toLowerCase() !== host.toLowerCase() || !['localhost','127.0.0.1','[::1]'].includes(url.hostname) || Number(url.port || 80) !== port) throw fail(403,'Loopback host required');
  if (req.headers.origin && req.headers.origin !== url.origin) throw fail(403,'Same origin required');
  if (req.headers['sec-fetch-site'] && !['same-origin','none'].includes(req.headers['sec-fetch-site'])) throw fail(403,'Same origin required');
}

async function readJson(req, maxBytes) {
  if (req.headers['content-type']?.split(';')[0].trim().toLowerCase() !== 'application/json') throw fail(415,'JSON required');
  const declared = req.headers['content-length'];
  if (declared && (!/^\d+$/.test(declared) || Number(declared)>maxBytes)) { req.resume(); throw fail(413,'Body too large'); }
  const buffer = await new Promise((resolve,reject) => {
    let size=0, chunks=[], rejected=false;
    req.on('data',chunk => {
      if (rejected) return;
      size+=chunk.length;
      if (size>maxBytes) { rejected=true; chunks=[]; reject(fail(413,'Body too large')); return; }
      chunks.push(chunk);
    });
    req.on('end',()=>{if(!rejected)resolve(Buffer.concat(chunks));});
    req.on('error',reject);
    req.on('aborted',()=>reject(fail(400,'Incomplete body')));
  });
  try { return JSON.parse(buffer.toString('utf8')); } catch { throw fail(400,'Invalid JSON'); }
}

export function createEvaluationServer({root=process.cwd(), maxBodyBytes=8*1024*1024}={}) {
  const rootReady = fs.realpath(root);
  const enqueue = serializedWrites();
  const server = http.createServer(async(req,res) => {
    res.setHeader('Cross-Origin-Opener-Policy','same-origin');
    res.setHeader('Cross-Origin-Embedder-Policy','require-corp');
    res.setHeader('Cache-Control','no-store');
    res.setHeader('X-Content-Type-Options','nosniff');
    try {
      allowedRequest(req, server.address().port);
      if (!req.url.startsWith('/') || req.url.includes('\\')) throw fail(404,'Not found');
      const url = new URL(req.url,'http://localhost');
      let route; try { route=decodeURIComponent(url.pathname); } catch { throw fail(400,'Invalid path'); }
      if (route.includes('\0') || route.split('/').includes('..') || route.includes('\\')) throw fail(404,'Not found');
      const base = await rootReady;
      if (req.method==='POST' && ['/labels','/save'].includes(route)) {
        const data = await readJson(req,maxBodyBytes);
        if (route==='/save' && (!data || data.schema!==1 || !Array.isArray(data.cases) || !Array.isArray(data.rows))) throw fail(400,'Invalid run snapshot');
        const result = await enqueue(async() => {
          if (route==='/labels') {
            const source = JSON.parse(await fs.readFile(await safePath(base,'local-results/labeling-cases.json'),'utf8'));
            try { validateLabelSnapshot(data,source); } catch { throw fail(400,'Invalid label snapshot'); }
          }
          const directory = path.join(base,'local-results');
          try { await fs.mkdir(directory); } catch(error) { if(error.code!=='EEXIST')throw error; }
          await safePath(base,'local-results');
          const name = route==='/labels' ? 'latest-labels.json' : `run-${Date.now()}-${randomUUID()}.json`;
          await atomicWrite(path.join(directory,name),JSON.stringify(data,null,2),route==='/labels');
          return route==='/labels' ? {} : {name};
        });
        res.setHeader('Content-Type','application/json'); res.end(JSON.stringify(result)); return;
      }
      if (!['GET','HEAD'].includes(req.method)) throw fail(405,'Method not allowed');
      let relative;
      if (route==='/') relative='prototypes/model-evaluation/index.html';
      else if (route.startsWith('/prototypes/model-evaluation/') && assets.has(route.slice('/prototypes/model-evaluation/'.length))) relative=route.slice(1);
      else if (route.startsWith('/local-results/') && dataFiles.has(route.slice('/local-results/'.length))) relative=route.slice(1);
      else if (route.startsWith('/node_modules/') && dependencyRoots.some(prefix=>route.slice('/node_modules/'.length).startsWith(prefix)) && types[path.extname(route)]) relative=route.slice(1);
      else throw fail(404,'Not found');
      const file = await safePath(base,relative);
      const content = await fs.readFile(file);
      res.setHeader('Content-Type',types[path.extname(file)] || 'application/octet-stream');
      res.end(req.method==='HEAD' ? undefined : content);
    } catch(error) {
      res.statusCode = error.status || (error.code==='ENOENT' ? 404 : 500);
      res.setHeader('Content-Type','application/json');
      res.end(JSON.stringify({error:res.statusCode===500 ? 'Local save or read failed' : error.status ? error.message : 'Not found'}));
    }
  });
  server.requestTimeout=30_000; server.headersTimeout=10_000;
  return server;
}

if (process.argv[1] && import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href) {
  createEvaluationServer().listen(8766,'127.0.0.1',()=>console.log('Local-only evaluation: http://127.0.0.1:8766'));
}
