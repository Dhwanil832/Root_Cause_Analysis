# Fixed scenario — IA-16036

Private. Design frozen 2026-09-22 before a run of this package. Historical anchor: instrument-air loss to RHOB during planned isolation of the 1SC dryer system on 2024-05-20. The row reports that one newly installed bypass valve was opened, the main isolation was closed, the other bypass valve remained closed, and opening it restored pressure. The recorded root factor is an ECP not updated for the bypass. These historical interpretations are not the raw evidence needed to verify them.

The exercise retains that sequence. Its synthetic identifiers and measurements extend the previously developed IA-16036 case; this is a redesigned three-release derivative, not an independent held-out incident. No previous outcome is an answer source in a fresh run.

## Fixed physical world

H-U is the common supply header. Normal path: H-U → M101 → D101 dryer → M102 → H-R → RHOB consumers. Added bypass B17: H-U → V201 → plain spool → V202 → H-R. Both bypass valves are in series. No third feed, intermediate receiver or cross-connection is present in the traced scope. Consumers continue drawing air; no pressure decay or flow rate is analytically calculated.

At 09:56 V201 is opened. At 10:00:03 ±5 s M101 is closed; M102 remains open. V202 is not opened at this time and is later directly seen closed. P-U remains about 7 bar gauge while P-R drops. At 10:06:18 ±5 s V202 is opened while M101 remains closed; P-R recovers by 10:07. These are synthetic observations making the row's sequence testable, not recovered historical telemetry. A later continuous controller journal records no compressor trip in its stated interval.

AL44's display label is COMP FAULT, but its configured input is low P-R, not a compressor-trip contact. The desk's initial trip message is an inference from that label. Its later revision corrects the inference; neither revision denies the low-pressure alarm. No pressure gauge is a physical isolation barrier.

## Fixed documentary world

WO527 was issued with ECP-1SC revision 3. Field B17 had been installed before this job. Revision 3 does not depict B17 or its valve identities. Revision 4-D mentions the new branch but is draft, lacks approval/effective date and was not in the issued packet. CH218's work-package-impact field was No; the routing system creates an ECP distribution task only when that field is Yes. The register shows no such task or issued revision replacing 3 before the event. This supports a specific change-to-document handoff gap, not a claim that the technician ignored an available updated procedure. Why the impact field was No, why the draft stayed unissued and who should be blamed remain unestablished.

## Alternatives and limits

Compressor trip, downstream rupture, closed flow path, faulty indication and an updated instruction ignored are initially live possibilities. Stable P-U samples weaken a sustained upstream loss but do not alone rule out all short transients. B1 topology/actions/pressure jointly support path interruption and restoration. B2 journal and issued-document history narrow alternatives further. No evidence proves worker incompetence, intentional noncompliance, pressure-vessel damage, financial loss, legal compliance, complete organizational root cause or effectiveness of a future corrective action.

Pressure taps, timing precision, topology names, controlled-document workflow, desk correction and journal coverage are synthetic. Row consequence remains instrument-air loss; no invented injury or quantified loss. The historical approval fields are not technical validation or unanimous agreement.
