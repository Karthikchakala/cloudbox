import requests

login_res = requests.post('http://localhost:5000/api/auth/login', json={'email': 'karthik@cloudbox.local', 'password': 'password123'})
token = login_res.json()['access_token']

files_res = requests.get('http://localhost:5000/api/files', headers={'Authorization': f'Bearer {token}'})
files = files_res.json()['files']
file_id = files[0]['id']
filename = files[0]['original_filename']

share_res = requests.post(f'http://localhost:5000/api/files/{file_id}/shares', headers={'Authorization': f'Bearer {token}'}, json={'permission': 'download'})
raw_token = share_res.json()['token']
print(f"FILE: {filename} (ID: {file_id})")
print(f"SHARE_URL: http://localhost/shared/{raw_token}")
