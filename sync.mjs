import path from 'node:path';import {fileURLToPath} from 'node:url';import {Store} from './src/store.mjs';import {syncAll} from './src/registry.mjs';
const root=path.dirname(fileURLToPath(import.meta.url));const s=new Store(process.env.LINKTRIAL_DATA_DIR||path.join(root,'runtime'));try{console.log(await syncAll(s,{limit:Number(process.env.SYNC_LIMIT)||Infinity}));}finally{s.close();}
