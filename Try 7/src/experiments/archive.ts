import {strToU8,zipSync} from 'fflate';
import type {DocumentRecord} from '@/src/domain/types';
import {exportExperiment} from './export';

/** Resolve only file keys from already-admitted frozen investigator inputs. */
export async function exportArchive(db:D1Database,trackId:string,
  load:(key:string)=>Promise<{arrayBuffer:()=>Promise<ArrayBuffer>}|null>) {
  const experiment=await exportExperiment(db,trackId) as {versions:Array<{input:{documents:DocumentRecord[]}}>;[key:string]:unknown};
  const originals:Record<string,Uint8Array>={};
  const records:Array<{sourceId:string;revision:string;sha256:string;archivePath:string|null;limitation?:string}>=[];
  const seen=new Set<string>();
  for(const version of experiment.versions)for(const doc of version.input.documents) {
    const identity=JSON.stringify([doc.id,doc.revision,doc.sha256,doc.fileKey]);
    if(seen.has(identity))continue;seen.add(identity);
    const record={sourceId:doc.id,revision:doc.revision,sha256:doc.sha256};
    const source=await load(doc.fileKey);
    if(!source){records.push({...record,archivePath:null,limitation:'Original file is not accessible; extracted text and prior identifiers remain in the experiment.'});continue;}
    const bytes=new Uint8Array(await source.arrayBuffer());
    if(/^[a-f0-9]{64}$/i.test(doc.sha256)) {
      const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(n=>n.toString(16).padStart(2,'0')).join('');
      if(hash!==doc.sha256.toLowerCase())throw Error('Original file digest differs from the frozen release; refusing an apparently complete archive.');
    }
    const safe=(value:string)=>value.replace(/[^a-zA-Z0-9._-]/g,'_');
    const name=`originals/${safe(doc.id)}-${safe(doc.revision)}-${safe(doc.sha256)}-${safe(doc.fileName)}`;
    originals[name]=bytes;records.push({...record,archivePath:name});
  }
  const manifest={...experiment,originalFiles:{status:records.some(r=>!r.archivePath)?'partial':'complete',records}};
  return {bytes:zipSync({...originals,'experiment.json':strToU8(JSON.stringify(manifest,null,2))}),manifest};
}
