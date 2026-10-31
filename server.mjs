import http from 'node:http';
import path from 'node:path';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {randomBytes} from 'node:crypto';
import {Store,AppError} from './src/store.mjs';
import {syncOne,syncAll} from './src/registry.mjs';
import {rulesMatch} from './src/matching.mjs';
const root=path.dirname(fileURLToPath(import.meta.url));
export function createApp({dataDir=process.env.LINKTRIAL_DATA_DIR||path.join(root,'runtime'),seed=true}={}){
 const store=new Store(dataDir,{seed,recoverSync:true}),sessions=new Map();let syncJob=null;
 const server=http.createServer(async(req,res)=>{
 res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Referrer-Policy','no-referrer');res.setHeader('Cache-Control','no-store');res.setHeader('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'");
 const json=(value,status=200)=>{res.writeHead(status,{'Content-Type':'application/json; charset=utf-8'});res.end(JSON.stringify(value));};
 try{const port=server.address().port;if(![`127.0.0.1:${port}`,`localhost:${port}`].includes(req.headers.host))throw new AppError('Host não permitido.',403);const url=new URL(req.url,'http://'+req.headers.host),route=url.pathname,method=req.method;
 if(!route.startsWith('/api/')){const allowed={'/':'index.html','/app.js':'app.js','/style.css':'style.css','/logo.svg':'logo.svg'};const file=allowed[route];if(!file)throw new AppError('Não encontrado.',404);const bytes=await readFile(path.join(root,'public',file));res.writeHead(200,{'Content-Type':file.endsWith('.js')?'text/javascript; charset=utf-8':file.endsWith('.css')?'text/css; charset=utf-8':file.endsWith('.svg')?'image/svg+xml':'text/html; charset=utf-8'});return res.end(bytes);}
 const sid=req.headers.cookie?.split(';').map(x=>x.trim()).find(x=>x.startsWith('lt_session='))?.slice(11);let session=sessions.get(sid);if(session&&session.expires<Date.now()){sessions.delete(sid);session=null;}
 if(route==='/api/bootstrap'&&method==='GET'){if(!session){const token=randomBytes(32).toString('hex');session={role:'doctor',csrf:randomBytes(24).toString('hex'),expires:Date.now()+8*3600000};sessions.set(token,session);res.setHeader('Set-Cookie',`lt_session=${token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800`);}return json({role:session.role,csrf:session.csrf,mode:'synthetic-only',matching:{rules:true,jev:'adapter-ready-not-connected',llm:'adapter-required'},privacy:{pseudonymized:true,encryptedAtRest:true,productionReady:false}});}
 if(!session)throw new AppError('Sessão expirada. Recarregue a página.',401);const role=session.role;
 let body={};if(!['GET','HEAD'].includes(method)){if(req.headers.origin!=='http://'+req.headers.host||req.headers['x-csrf-token']!==session.csrf)throw new AppError('Origem ou token da sessão inválido.',403);let size=0,chunks=[];for await(const chunk of req){size+=chunk.length;if(size>65536)throw new AppError('Solicitação muito grande.',413);chunks.push(chunk);}try{body=chunks.length?JSON.parse(Buffer.concat(chunks)):{};}catch{throw new AppError('JSON inválido.');}}
 if(route==='/api/session'&&method==='POST'){if(!['doctor','center','admin','sponsor'].includes(body.role))throw new AppError('Papel inválido.');session.role=body.role;store.audit(body.role,'demo.role_changed','session');return json({role:session.role});}
 if(route==='/api/patients'&&method==='GET')return json(store.patients(role));
 if(route==='/api/patients'&&method==='POST')return json(store.createPatient(body,role),201);
 let m=route.match(/^\/api\/patients\/([^/]+)(?:\/(identity|consent|archive|export))?$/);
 if(m){const [,pid,action]=m;if(action==='identity'&&method==='GET')return json(store.identity(pid,role));if(action==='export'&&method==='GET'){const p=store.patient(pid,role);store.audit(role,'patient.exported','patient',pid);return json(p);}if(action==='consent'&&method==='POST'){store.consent(pid,body.purpose,body.granted,role);return json({ok:true});}if(action==='archive'&&method==='POST'){store.archivePatient(pid,role);return json({ok:true});}if(!action&&method==='GET')return json(store.patient(pid,role));if(!action&&method==='PATCH')return json(store.updatePatient(pid,body,role));if(!action&&method==='DELETE'){store.erasePatient(pid,role);return json({ok:true});}}
 if(route==='/api/studies'&&method==='GET')return json(store.studies({all:url.searchParams.get('all')==='1',q:url.searchParams.get('q')||'',source:url.searchParams.get('source')||''},role));
 if(route==='/api/studies'&&method==='POST')return json(store.createStudy(body,role),201);
 if(route==='/api/studies/import'&&method==='POST'){store.allow(role,['admin']);return json(await syncOne(store,body.nct));}
 m=route.match(/^\/api\/studies\/([^/]+)(?:\/(sync))?$/);if(m){const [,studyId,action]=m;if(action==='sync'&&method==='POST'){store.allow(role,['admin']);return json(await syncOne(store,studyId));}if(!action&&method==='PATCH')return json(store.updateStudy(studyId,body,role));if(!action&&method==='DELETE')return json(store.archiveStudy(studyId,role));if(!action&&method==='GET'){const s=store.study(studyId);if(!s.visible&&role!=='admin')throw new AppError('Estudo indisponível.',404);return json(s);}}
 if(route==='/api/sync'&&method==='POST'){store.allow(role,['admin']);if(syncJob)throw new AppError('Sincronização já iniciada.',409);syncJob=syncAll(store).catch(()=>null).finally(()=>syncJob=null);return json({started:true},202);}
 if(route==='/api/sync'&&method==='GET'){store.allow(role,['admin']);return json(store.db.prepare('SELECT * FROM sync_runs ORDER BY started_at DESC LIMIT 1').get()||null);}
 if(route==='/api/candidates'&&method==='GET'){store.allow(role,['doctor']);const p=store.patient(url.searchParams.get('patient'),role);if(p.archived||!p.consents.matching)throw new AppError('Paciente arquivado ou autorização de pré-triagem revogada.');return json(store.studies({},role).map(s=>{const r=rulesMatch(p.clinical,s);return {...s,match:{status:r.status,label:r.label,counts:r.counts}};}).sort((a,b)=>({high:0,possible:1,review:2,barrier:3}[a.match.status]-{high:0,possible:1,review:2,barrier:3}[b.match.status])));}
 if(route==='/api/matches'&&method==='POST')return json(store.match(body.patientId,body.studyId,role),201);
 if(route==='/api/reviews'&&method==='POST')return json(store.review(body.matchId,body,role),201);
 if(route==='/api/referrals'&&method==='POST')return json(store.refer(body.reviewId,body.centerId,role),201);
 if(route==='/api/referrals'&&method==='GET')return json(store.referrals(role));
 m=route.match(/^\/api\/referrals\/([^/]+)\/actions$/);if(m&&method==='POST')return json(store.actReferral(m[1],body,role));
 if(route==='/api/metrics'&&method==='GET')return json(store.metrics(role));
 if(route==='/api/audit'&&method==='GET'){store.allow(role,['admin']);return json(store.db.prepare('SELECT * FROM audit ORDER BY at DESC LIMIT 100').all());}
 throw new AppError('Rota não encontrada.',404);
 }catch(err){json({error:err instanceof AppError?err.message:'Não foi possível concluir a operação. Nenhuma elegibilidade foi inferida.'},err.status||500);}
 });
 const timer=setInterval(()=>{if(process.env.LINKTRIAL_AUTO_SYNC==='1'&&!syncJob)syncJob=syncAll(store).catch(()=>null).finally(()=>syncJob=null);},24*3600000);timer.unref();
 server.on('close',()=>{clearInterval(timer);if(!syncJob)store.close();});return {server,store};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){const {server}=createApp();server.listen(Number(process.env.PORT||4175),'127.0.0.1',()=>console.log('LinkTrial local: http://127.0.0.1:'+server.address().port+' · somente dados fictícios'));}
