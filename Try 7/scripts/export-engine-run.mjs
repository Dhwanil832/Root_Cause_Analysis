// Read-only selected-track export. Does not start inference or invoke a grader.
const [incidentId,trackId]=process.argv.slice(2);
if(!incidentId||!trackId)throw new Error('Usage: node scripts/export-engine-run.mjs INCIDENT_ID TRACK_ID');
const base=process.env.RCA_APP_URL||'http://127.0.0.1:3015';
const response=await fetch(base+'/api/incidents/'+encodeURIComponent(incidentId));
const data=await response.json();
if(!response.ok||!data.incident)throw Error(data.error||'Incident unavailable');
const incident=data.incident,track=incident.tracks.find(t=>t.id===trackId);
if(!track)throw Error('Selected model track does not belong to this incident');
const metrics=track.versions.map(v=>{
  const p=v.analysis.engineProgress,t=p?.tasks||[];
  return {version:v.number,execution:v.executionStatus||'historical',model:p?.model,
    completed:t.filter(t=>t.status==='completed').length,failed:t.filter(t=>['failed','blocked'].includes(t.status)).length,
    reused:t.filter(t=>t.reused).length,quarantined:p?.quarantineCount||0,
    inputTokens:t.reduce((n,t)=>n+t.inputTokens,0),outputTokens:t.reduce((n,t)=>n+t.outputTokens,0),
    taskDurationMs:t.reduce((n,t)=>n+t.durationMs,0),sourceCoverage:p?.sourceCoverage,
    scientificAssessment:'NOT GRADED — inspect claims and links against the private rubric and original sources'};
});
console.log(JSON.stringify({incident:{id:incident.id,title:incident.title,description:incident.description},track,metrics},null,2));
