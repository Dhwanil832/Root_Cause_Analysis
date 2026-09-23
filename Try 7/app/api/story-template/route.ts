import {NextResponse} from 'next/server';
export async function GET(){return NextResponse.json({error:'Private scenario templates are not served by the Try 7 investigator.'},{status:410});}
