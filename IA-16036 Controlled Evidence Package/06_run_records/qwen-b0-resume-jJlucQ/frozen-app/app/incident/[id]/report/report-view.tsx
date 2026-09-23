'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import type { IncidentRecord } from '@/src/domain/types';

function markdownReport(incident: IncidentRecord, trackId: string, versionId: string) {
  const track = incident.tracks.find((item) => item.id === trackId) || incident.tracks[0];
  const version = track?.versions.find((item) => item.id === versionId) || track?.versions.at(-1);
  if (!track || !version) return '';
  const analysis = version.analysis;
  const lines = [
    `# RCA Investigation Report — ${incident.title}`,
    '', `**Model track:** ${track.modelName}`, `**Version:** V${version.number}`, `**Status:** ${analysis.status}`, `**Generated:** ${new Date().toISOString()}`, '',
    `**Execution:** ${analysis.stageErrors.length ? 'Incomplete — stage failures recorded' : 'Completed'}. Model execution is not proof of RCA correctness or human acceptance.`, '',
    '## Executive summary', '', analysis.structuredIncident.summary, '',
    '## Original incident account', '', incident.description, '',
    '## Established event', '', `**Focal event:** ${analysis.structuredIncident.focalEvent}`, '', `**Actual impact:** ${analysis.structuredIncident.actualImpact}`, '', `**Potential impact:** ${analysis.structuredIncident.potentialImpact}`, '',
    '## Normal state and event state', '', `**Normal:** ${analysis.structuredIncident.normalState}`, '', `**At event:** ${analysis.structuredIncident.eventState}`, '',
    '## Document and image observations', '',
    ...((analysis.documentIntelligence || []).length
      ? (analysis.documentIntelligence || []).flatMap((record) => [
          `### ${record.title}`,
          '', `${record.summary} _(${record.mode}; source: ${record.documentId})_`, '',
          ...record.observations.map((observation) => `- **${observation.status} · ${observation.kind}:** ${observation.text} _(location: ${observation.location || 'not isolated'}; confidence: ${Math.round(observation.confidence * 100)}%)_`),
          ...(record.limitations.length ? ['', `Limitations: ${record.limitations.join('; ')}`] : []), '',
        ])
      : ['No document or image observations are recorded in this version.', '']),
    '## Evidence claims', '',
    ...analysis.evidenceClaims.map((claim) => `- **${claim.review ? claim.status : 'not reviewed'} · ${claim.kind}:** ${claim.text} _(sources: ${claim.sourceIds.join(', ') || 'not established'})_${claim.review ? `\n  Review: ${claim.review.reason}\n${claim.review.citations.map(c => `  Source ${c.sourceId}: “${c.excerpt}”`).join('\n')}` : ''}`), '',
    '## Causal findings', '',
    ...analysis.causalBoard.nodes.map((node) => `- **${node.type} · ${node.status} · ${node.verified && !analysis.causalBoard.verificationFindings.some(f => f.targetId === node.id && f.severity === 'blocking') ? 'model evidence-reviewed' : 'not verified'}:** ${node.label} — ${node.detail}`), '',
    '### Causal links', '',
    ...analysis.causalBoard.edges.map((edge) => `- **${edge.type} · ${edge.status}:** ${edge.rationale} _(sources: ${edge.sourceIds.join(', ') || 'not established'})_`), '',
    '## Contradictions and unresolved evidence', '',
    ...analysis.causalBoard.verificationFindings.map(f => `- **${f.severity} · ${f.targetId}:** ${f.issue} Needed: ${f.evidenceNeeded}`), '',
    ...(analysis.conflicts.length ? analysis.conflicts.map((conflict) => `- **${conflict.status}:** ${conflict.summary} — ${conflict.resolutionNeeded}`) : ['No contradictions are recorded in this version.']), '',
    '## Human review decisions', '',
    ...((analysis.humanDecisions || []).length ? (analysis.humanDecisions || []).map((decision) => `- **${decision.action}:** ${decision.targetType} ${decision.targetId}${decision.notes ? ` — ${decision.notes}` : ''} (${decision.actor}, ${decision.createdAt})`) : ['No human review decisions are recorded in this version.']), '',
    '## Corrective actions', '',
    ...(analysis.correctiveActions.length ? analysis.correctiveActions.map((action) => `### ${action.title}\n\n- Status: ${action.status}\n- Control type: ${action.type}\n- Owner role: ${action.ownerRole}\n- Completion evidence: ${action.completionEvidence}\n- Effectiveness check: ${action.effectivenessCheck}\n\n${action.description}`) : ['No corrective actions have earned a place in this version.']), '',
    '## Open questions', '',
    ...[...analysis.baselineQuestions, ...analysis.questions].filter((question) => !['answered', 'screened', 'superseded'].includes(question.status)).map((question) => `- **${question.priority}:** ${question.text}`), '',
    '## Method and limitations', '',
    'This report preserves the state of one independent model track and version. Tags route specialist investigation; they are not causal conclusions. Proposed or unknown claims require supporting evidence and human review before closure.', '',
  ];
  return lines.join('\n');
}

function download(name: string, type: string, content: string) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ReportView({ incidentId, trackId, versionId }: { incidentId: string; trackId: string; versionId: string }) {
  const [incident, setIncident] = useState<IncidentRecord | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let cancelled = false;
    fetch(`/api/incidents/${incidentId}`, { cache: 'no-store' })
      .then((response) => response.json().then((payload) => ({ response, payload: payload as { incident?: IncidentRecord; error?: string } })))
      .then(({ response, payload }) => {
        if (!response.ok || !payload.incident) throw new Error(payload.error || 'Unable to load the report.');
        if (!cancelled) setIncident(payload.incident);
      })
      .catch((caught: unknown) => { if (!cancelled) setError(caught instanceof Error ? caught.message : 'Unable to load the report.'); });
    return () => { cancelled = true; };
  }, [incidentId]);

  const selection = useMemo(() => {
    const track = incident?.tracks.find((item) => item.id === trackId) || incident?.tracks[0];
    const version = track?.versions.find((item) => item.id === versionId) || track?.versions.at(-1);
    return { track, version };
  }, [incident, trackId, versionId]);

  if (error) return <main className="center-page"><div className="processing-card"><h1>{error}</h1></div></main>;
  if (!incident || !selection.track || !selection.version) return <main className="center-page"><div className="processing-card"><p>Preparing report…</p></div></main>;
  const { track, version } = selection;
  const analysis = version.analysis;
  const report = markdownReport(incident, track.id, version.id);
  const fileStem = `rca-${incident.id}-v${version.number}`;
  const ready = (analysis.humanDecisions || []).length > 0;
  const reviewState = (id: string, verified: boolean, status: string) => status === 'rejected' ? 'Rejected'
    : analysis.causalBoard.verificationFindings.some(f => f.targetId === id && f.severity === 'blocking') ? 'Unresolved verification'
    : verified ? 'Model evidence-reviewed' : 'Not verified';

  return <main className="report-shell">
    <nav className="report-toolbar"><Link href={`/incident/${incident.id}`}>← Investigation</Link><div><button type="button" onClick={() => download(`${fileStem}.md`, 'text/markdown', report)}>Download Markdown</button><button type="button" onClick={() => download(`${fileStem}.json`, 'application/json', JSON.stringify({ incident, trackId: track.id, version }, null, 2))}>Evidence package</button><button type="button" onClick={() => window.print()}>Print / Save PDF</button></div></nav>
    <article className="report-page">
      <header><span className={`report-state ${ready ? 'ready' : 'draft'}`}>{ready ? 'Human decisions recorded — see open findings' : 'Investigation draft'}</span><p>RCA FIELDWORK · TRY 4</p><h1>{incident.title}</h1><dl><dt>Model track</dt><dd>{track.modelName}</dd><dt>Version</dt><dd>V{version.number}</dd><dt>Investigation status</dt><dd>{analysis.status.replaceAll('-', ' ')}</dd><dt>Execution</dt><dd>{analysis.stageErrors.length ? 'Incomplete' : 'Completed — not proof of RCA correctness'}</dd><dt>Generated</dt><dd>{new Date().toLocaleString()}</dd></dl></header>
      <section><h2>Executive summary</h2><p>{analysis.structuredIncident.summary}</p></section>
      <section><h2>Original incident account</h2><p className="verbatim-account">{incident.description}</p></section>
      <section className="report-columns"><div><h2>Focal event</h2><p>{analysis.structuredIncident.focalEvent}</p><h3>Actual impact</h3><p>{analysis.structuredIncident.actualImpact}</p></div><div><h2>State comparison</h2><h3>Normal</h3><p>{analysis.structuredIncident.normalState}</p><h3>At event</h3><p>{analysis.structuredIncident.eventState}</p></div></section>
      <section><h2>Document and image observations</h2>{(analysis.documentIntelligence || []).length === 0 && <p>No document or image observations are recorded in this version.</p>}{(analysis.documentIntelligence || []).map((record) => <article className="report-action" key={record.documentId}><span>{record.mode} · source {record.documentId}</span><h3>{record.title}</h3><p>{record.summary}</p>{record.observations.length > 0 && <ul>{record.observations.map((observation) => <li key={observation.id}><strong>{observation.status} · {observation.kind}</strong> — {observation.text} <em>({observation.location || 'location not isolated'}, {Math.round(observation.confidence * 100)}%)</em></li>)}</ul>}{record.limitations.length > 0 && <p><strong>Limitations:</strong> {record.limitations.join('; ')}</p>}</article>)}</section>
      <section><h2>Causal findings</h2><table><thead><tr><th>Type</th><th>Finding</th><th>Evidence review</th><th>Sources</th></tr></thead><tbody>{analysis.causalBoard.nodes.map((node) => <tr key={node.id}><td>{node.type.replaceAll('-', ' ')}</td><td><strong>{node.label}</strong><br />{node.detail}</td><td>{reviewState(node.id, node.verified, node.status)}<br />Recorded status: {node.status}</td><td>{node.sourceIds.join(', ') || 'Required'}</td></tr>)}</tbody></table></section>
      <section><h2>Evidence ledger</h2><table><thead><tr><th>Kind</th><th>Claim and review</th><th>Status</th><th>Sources</th></tr></thead><tbody>{analysis.evidenceClaims.map((claim) => <tr key={claim.id}><td>{claim.kind.replaceAll('-', ' ')}</td><td>{claim.text}{claim.review && <><p>{claim.review.reason}</p>{claim.review.citations.map((c, i) => <blockquote key={i}>{c.excerpt} — {c.sourceId}</blockquote>)}</>}</td><td>{claim.review ? claim.status : 'Not reviewed'}</td><td>{claim.sourceIds.join(', ') || 'Required'}</td></tr>)}</tbody></table></section>
      <section><h2>Contradictions and verification gaps</h2>{analysis.conflicts.length === 0 && <p>No contradictions are recorded in this version.</p>}{analysis.conflicts.map((conflict) => <article className="report-callout" key={conflict.id}><strong>{conflict.summary}</strong><p>{conflict.resolutionNeeded}</p></article>)}{analysis.causalBoard.verificationFindings.map((finding) => <article className="report-callout" key={finding.id}><strong>{finding.issue}</strong><p>{finding.evidenceNeeded}</p></article>)}</section>
      <section><h2>Corrective actions</h2>{analysis.correctiveActions.length === 0 && <p>No corrective actions have earned a place in this version.</p>}{analysis.correctiveActions.map((action) => <article className="report-action" key={action.id}><span>{action.type} · {action.status}</span><h3>{action.title}</h3><p>{action.description}</p><dl><dt>Owner</dt><dd>{action.ownerRole}</dd><dt>Completion evidence</dt><dd>{action.completionEvidence}</dd><dt>Effectiveness check</dt><dd>{action.effectivenessCheck}</dd></dl></article>)}</section>
      <section><h2>Human review record</h2>{(analysis.humanDecisions || []).length === 0 && <p>No human review decisions are recorded in this version.</p>}{(analysis.humanDecisions || []).map((decision) => <p key={decision.id}><strong>{decision.action.replaceAll('-', ' ')}</strong> — {decision.targetType.replaceAll('-', ' ')} · {decision.actor} · {new Date(decision.createdAt).toLocaleString()}{decision.notes ? ` — ${decision.notes}` : ''}</p>)}</section>
      <footer>Tags are investigation routes, not causal conclusions. This report represents one model track and one preserved version.</footer>
    </article>
  </main>;
}
