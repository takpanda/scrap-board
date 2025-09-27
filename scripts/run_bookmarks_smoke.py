from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
res = client.get('/bookmarks')
print('STATUS:', res.status_code)
# print a short snippet to confirm template content
print('HAS_TITLE:', 'ブックマーク' in res.text)
print(res.text[:400])
