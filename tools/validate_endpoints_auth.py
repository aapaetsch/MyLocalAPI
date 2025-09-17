import re
import json

server_path = 'c:/Users/aapae/Documents/Projects/MyLocalAPI/src/server.py'
endpoints_path = 'c:/Users/aapae/Documents/Projects/MyLocalAPI/static/endpoints.json'

with open(server_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

auth_paths = []
for i, line in enumerate(lines):
    m = re.search(r"@self\.app\.route\(['\"]([^'\"]+)['\"]", line)
    if m:
        path = m.group(1)
        # look ahead a few lines to see if @self._require_auth appears
        lookahead = ''.join(lines[i+1:i+4])
        if '@self._require_auth' in lookahead:
            auth_paths.append(path)

# load endpoints.json
with open(endpoints_path, 'r', encoding='utf-8') as f:
    endpoints = json.load(f)

# create mapping path->params
path_to_params = {}
for group in endpoints:
    for ep in group.get('endpoints', []):
        path_to_params[ep.get('path')] = ep.get('params','')

missing_in_json = []
missing_token = []

for p in auth_paths:
    if p not in path_to_params:
        missing_in_json.append(p)
    else:
        params = path_to_params[p] or ''
        if 'token' not in params:
            missing_token.append((p, params))

print('Auth-protected paths found in server.py:')
for p in auth_paths:
    print('  ', p)
print('\n')
if missing_in_json:
    print('Paths missing in endpoints.json:')
    for p in missing_in_json:
        print('  ', p)
else:
    print('All auth-protected paths are present in endpoints.json')

if missing_token:
    print('\nAuth-protected paths missing token in endpoints.json:')
    for p, params in missing_token:
        print('  ', p, '-> params:', params)
else:
    print('All auth-protected endpoints include token in endpoints.json')
