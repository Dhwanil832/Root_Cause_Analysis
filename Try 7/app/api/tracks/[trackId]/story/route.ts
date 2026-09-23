import {NextResponse} from 'next/server';
// Private controller storage must not be imported into investigator routes.
function controllerOnly() {
  return NextResponse.json({error:'Private scenarios are not hosted in the Try 7 investigator. Supply an approved answer/document release from a separate controller.'},{status:410});
}
export const GET=controllerOnly;
export const POST=controllerOnly;
