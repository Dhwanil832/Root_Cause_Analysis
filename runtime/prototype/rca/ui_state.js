/* Pure view policy: independent from DOM so lifecycle/graph feedback is testable. */
const RcaView = {
  appearance(item) {
    const rejected = item.review === 'human_rejected';
    const stale = !!item.stale;
    const approved = item.review === 'human_approved' && !stale;
    return {
      label: [item.record.status, stale ? 'STALE — reassessment needed' : '', rejected ? 'HUMAN REJECTED' : approved ? 'human approved' : 'model proposal'].filter(Boolean).join(' · '),
      fill: rejected ? '#f9dadd' : stale ? '#fff1cf' : item.record.status === 'supported' ? '#e3f4ed' : '#edf2f7',
      stroke: rejected ? '#b42338' : stale ? '#ad7600' : '#698092',
      dashed: stale || rejected || item.record.status !== 'supported'
    };
  },
  requestGroup(item) {
    if (item.superseded_by || ['answered','blocked','terminated'].includes(item.record.status)) return 'history';
    if (['awaiting_user','partial'].includes(item.record.status)) return 'actionable';
    return 'internal';
  },
  updateLabel(update) {
    if (!update) return 'No model output yet';
    if (update.accepted === false) return 'Rejected proposal — nothing committed';
    if (update.accepted === null) return 'Proposal awaiting lead review — not committed';
    return update.committed ? 'Accepted update — structural checks passed' : 'Model update';
  }
};
if (typeof module !== 'undefined') module.exports = RcaView;
