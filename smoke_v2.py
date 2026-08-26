from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app)

analysis = client.post('/v2/risk/analyze', json={'severity': 96, 'exploit_likelihood': 89, 'asset_criticality': 96, 'exposure': 100})
assert analysis.status_code == 200, analysis.text
body = analysis.json()
assert body['policy_version'] == 'RP-2.4'
assert body['action'] == 'block'
assert len(body['contributions']) == 4

abstain = client.post('/v2/risk/analyze', json={'severity': 90, 'exploit_likelihood': 80, 'asset_criticality': 80, 'exposure': 90, 'evidence_count': 0})
assert abstain.status_code == 200
assert abstain.json()['action'] == 'abstain'

invalid_review = client.post('/v2/governance/review', json={'case_id': 'RP-1', 'decision': 'approve', 'rationale': 'short'})
assert invalid_review.status_code == 422

review = client.post('/v2/governance/review', json={'case_id': 'RP-1', 'decision': 'approve', 'rationale': 'Evidence and analyst review support approval.'})
assert review.status_code == 200
assert client.get('/v2/audit').json()[-1]['event_type'] == 'ANALYST_REVIEW'
print('RiskPilot v2 smoke tests passed')
