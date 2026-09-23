import {NextResponse} from 'next/server';
import {database} from '@/src/server/repository';
import {exportExperiment} from '@/src/experiments/export';
import {exportArchive} from '@/src/experiments/archive';
import {readStoredDocument} from '@/src/server/document-media';
export async function GET(request:Request,context:{params:Promise<{trackId:string}>}) {
  try {
    const {trackId}=await context.params;
    if(new URL(request.url).searchParams.get('format')==='zip') {
      const archive=await exportArchive(database(),trackId,readStoredDocument);
      return new Response(new Uint8Array(archive.bytes),{headers:{'Content-Type':'application/zip',
        'Content-Disposition':`attachment; filename="rca-${trackId.replace(/[^a-zA-Z0-9-]/g,'')}.zip"`}});
    }
    return NextResponse.json(await exportExperiment(database(),trackId),{headers:{'Content-Disposition':`attachment; filename="rca-${trackId.replace(/[^a-zA-Z0-9-]/g,'')}.json"`}});
  }catch(error){return NextResponse.json({error:error instanceof Error?error.message:'Export failed.'},{status:400});}
}
