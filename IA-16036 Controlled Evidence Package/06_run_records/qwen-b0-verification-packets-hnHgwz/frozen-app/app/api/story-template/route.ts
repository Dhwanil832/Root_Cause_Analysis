import {NextResponse} from 'next/server';
import {r3Template} from '@/src/story-agent/r3-template';
export async function GET(){return NextResponse.json(r3Template);}
