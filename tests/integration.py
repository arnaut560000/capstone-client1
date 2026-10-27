"""Run against a NEW, disposable SQLite browser store. Never production.
Uses only Python's standard library. Leaves two clearly fictional test records.
"""
import base64
import datetime
import http.cookiejar
import os
import re
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get('OSY_TEST_URL', 'http://127.0.0.1:8080/').rstrip('/') + '/'
client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
checks = 0

def request(path='', data=None, upload=None, session=client):
    headers = {}
    if upload:
        boundary = 'osy-test-boundary'
        parts = []
        for key, value in data.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        name, content, mime = upload
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; filename="{name}"\r\nContent-Type: {mime}\r\n\r\n'.encode() + content + b'\r\n')
        parts.append(f'--{boundary}--\r\n'.encode())
        body = b''.join(parts)
        headers['Content-Type'] = 'multipart/form-data; boundary=' + boundary
    else:
        body = urllib.parse.urlencode(data).encode() if data is not None else None
    try:
        result = session.open(urllib.request.Request(BASE + path, data=body, headers=headers))
    except urllib.error.HTTPError as error:
        result = error
    raw = result.read()
    return result.status, result.url, raw.decode('utf-8', errors='replace'), raw

def check(condition, message):
    global checks
    assert condition, message
    checks += 1
    print('PASS:', message)

def token(html):
    return re.search(r'name="csrf" value="([a-f0-9]+)"', html).group(1)

status, location, html, _ = request()
check('page=setup' in location, 'Fresh database opens setup')
csrf = token(html)
_, location, html, _ = request('index.php?page=setup', dict(csrf=csrf, username='test_admin', password='CapstoneTest2026!', confirm_password='CapstoneTest2026!'))
check('page=login' in location and 'Setup complete' in html, 'Setup creates database and admin')
_, location, _, _ = request('index.php?page=reports')
check('page=login' in location, 'Reports require login')
_, _, html, _ = request('index.php?page=login', dict(csrf=csrf, username='test_admin', password='wrong'))
check('incorrect' in html, 'Wrong credentials rejected')
_, location, html, _ = request('index.php?page=login', dict(csrf=csrf, username='test_admin', password='CapstoneTest2026!'))
check('page=dashboard' in location and 'No OSY records yet' in html, 'Login and empty dashboard')
csrf = token(html)
_, location, _, _ = request('index.php?page=setup')
check('page=dashboard' in location, 'Setup disabled after first admin')
today = datetime.date.today()
data = dict(csrf=csrf, full_name='Juan Demo Youth', birthdate=f'{today.year-19}-01-15', sex='Male', address='Barangay A, Demo Municipality', contact_number='09123456789', educational_attainment='Junior high school level', last_school='Demo High School', reason_stopped='Fictional demonstration record', employment_status='Unemployed', date_registered=today.isoformat(), status='Active')
_, _, html, _ = request('index.php?page=register', dict(data, birthdate='2099-01-01'))
check('Enter a valid birthdate' in html and 'Save registration' in html, 'Future birthdate rejected with form preserved')
_, _, html, _ = request('index.php?page=register', dict(data, employment_status='Invalid'))
check('Choose a valid employment status' in html, 'Invalid enum rejected')
_, _, html, _ = request('index.php?page=register', data, ('bad.php', b'<?php echo 1; ?>', 'image/png'))
check('valid JPG' in html or 'could not be uploaded' in html, 'Fake image rejected')
photo = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
_, location, html, _ = request('index.php?page=register', data, ('photo.png', photo, 'image/png'))
check('page=profile' in location and f'OSY-{today.year}-0001' in html, 'Registration assigns first ID and saves real photo')
first_id = urllib.parse.parse_qs(urllib.parse.urlparse(location).query)['id'][0]
_, _, _, received = request('index.php?page=photo&id=' + first_id)
check(received == photo, 'Authenticated photo serving')
anonymous = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
_, location, _, _ = request('index.php?page=photo&id=' + first_id, session=anonymous)
check('page=login' in location, 'Anonymous photo requests require login')
second = dict(data, full_name='Maria Demo Youth', birthdate=f'{today.year-21}-04-20', sex='Female', employment_status='Employed', status='Inactive')
_, location, html, _ = request('index.php?page=register', second)
check(f'OSY-{today.year}-0002' in html, 'Second registration increments ID')
second_id = urllib.parse.parse_qs(urllib.parse.urlparse(location).query)['id'][0]
_, _, html, _ = request('index.php?page=records&q=Maria')
check('Maria Demo Youth' in html and 'Juan Demo Youth' not in html, 'Search by name')
_, _, html, _ = request(f'index.php?page=records&q=OSY-{today.year}-0001')
check('Juan Demo Youth' in html and 'Maria Demo Youth' not in html, 'Search by OSY ID')
_, _, html, _ = request('index.php?page=reports&sex=Female&status=Inactive&employment_status=Employed')
check('Maria Demo Youth' in html and 'Juan Demo Youth' not in html and '1 record' in html, 'Combined report filters and print list')
_, _, html, _ = request('index.php?page=edit&id=' + first_id, dict(data, full_name='Juan Demo Updated <script>alert(1)</script>'))
check('&lt;script&gt;' in html and '<script>alert(1)</script>' not in html and f'OSY-{today.year}-0001' in html, 'Editing keeps ID and escapes HTML')
request('index.php?page=edit&id=' + first_id, dict(data, full_name='Juan Demo Youth'))
status, _, _, _ = request('index.php?page=archive&id=' + first_id, {'csrf': 'bad'})
check(status == 403, 'Invalid CSRF prevents mutation')
_, _, html, _ = request('index.php?page=archive&id=' + first_id, {'csrf': csrf})
check('Juan Demo Youth' not in html and 'Record archived' in html, 'Archived record excluded from records')
_, _, html, _ = request('index.php?page=dashboard')
check('Juan Demo Youth' not in html and 'class="stat-number">1</strong>' in html, 'Dashboard excludes archived record')
_, _, html, _ = request('index.php?page=records&archived=1')
check('Juan Demo Youth' in html, 'Archived records remain available')
request('index.php?page=restore&id=' + first_id, {'csrf': csrf})
_, _, html, _ = request('index.php?page=records')
check('Juan Demo Youth' in html and 'Maria Demo Youth' in html, 'Restore returns record to directory')
_, _, html, _ = request('index.php?page=card&id=' + first_id)
check('IDENTIFICATION CARD' in html and 'Juan Demo Youth' in html and 'Authorized signature' in html, 'ID preview contains saved details')
status, _, html, _ = request('index.php?page=profile&id=999999')
check(status == 404 and 'not found' in html, 'Missing record has friendly 404')
for path in ['config.php', 'database.sql', 'storage/test-processes.json', 'app/bootstrap.php']:
    status, _, _, _ = request(path)
    check(status == 404, 'Private path blocked: ' + path)
_, _, html, _ = request('index.php?page=dashboard')
check('Warning' not in html and 'Fatal error' not in html, 'Dashboard renders without PHP errors')
_, location, _, _ = request('index.php?page=logout', {'csrf': csrf})
check('page=login' in location, 'Logout returns to login')
_, location, _, _ = request('index.php?page=profile&id=' + first_id)
check('page=login' in location, 'Logout revokes access')
print(f'\n{checks} integration checks passed.')
