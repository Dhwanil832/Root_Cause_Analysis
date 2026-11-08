from pathlib import Path
import pytest
from integrations.evidence_sources.local_folder import LocalEvidenceWorld
from integrations.utilities.file_reader import read_document

def test_local_evidence_route_does_not_leak_future_docs(tmp_path):
    incident=tmp_path/'incident.md';incident.write_text('An employee slipped beside F-2 at 10:05.')
    folder=tmp_path/'evidence';security=folder/'security';security.mkdir(parents=True)
    (security/'CAM-001.md').write_text('The incident camera record shows a 10:00 observation of the aisle floor.')
    w=LocalEvidenceWorld(incident,folder)
    assert w.initial_packet()['id']=='incident'
    assert 'CAM-001' not in str(w.public_routes())
    routes=w.discover('need security camera evidence','security')
    assert routes[0]['id']=='security'
    assert 'CAM-001' not in str(routes)
    reply=w.request('security','Please provide an incident camera record of the aisle')
    assert reply['document']['id']=='CAM-001'
    assert w.request('security','Please provide more incident camera evidence')['document'] is None

def test_unrequested_route_rejected(tmp_path):
    incident=tmp_path/'incident.md';incident.write_text('Incident occurred.')
    e=tmp_path/'evidence';(e/'security').mkdir(parents=True)
    w=LocalEvidenceWorld(incident,e);w.initial_packet()
    with pytest.raises(ValueError):w.request('security','Please provide camera evidence')

def test_opaque_file_fails_closed(tmp_path):
    p=tmp_path/'bad.pdf';p.write_bytes(b'%PDF-1.4\0')
    with pytest.raises(ValueError):read_document(p)

def test_unsolicited_arrival(tmp_path):
    incident=tmp_path/'incident.md';incident.write_text('A reported fall occurred.')
    e=tmp_path/'evidence';(e/'unsolicited').mkdir(parents=True)
    (e/'unsolicited/COR-20.md').write_text('The previous note was from another camera.')
    w=LocalEvidenceWorld(incident,e);w.initial_packet()
    assert w.maybe_unsolicited()['id']=='COR-20'
    assert w.maybe_unsolicited() is None
