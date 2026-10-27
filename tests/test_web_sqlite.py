"""Self-contained PHP/SQLite checks. No MySQL service or real records are used.

Run: python -m unittest discover -s tests -p test_web_sqlite.py -v
Set OSY_PHP to php.exe if it is not on PATH.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


class WebSQLiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        php = os.environ.get('OSY_PHP') or shutil.which('php')
        if not php:
            raise RuntimeError('Install PHP or set OSY_PHP to php.exe before running browser tests.')
        cls.php = [php, '-n']
        if sys.platform == 'win32':
            cls.php += ['-d', 'extension_dir=' + str(Path(php).parent / 'ext')]
        cls.php += ['-d', 'extension=pdo_sqlite', '-d', 'extension=fileinfo', '-d', 'extension=mbstring']
        cls.temporary = tempfile.TemporaryDirectory(prefix='osy-web-sqlite-')
        cls.folder = Path(cls.temporary.name)
        cls.environment = dict(os.environ, OSY_WEB_STORAGE=str(cls.folder / 'storage'))
        cls.server = None
        cls.log = open(cls.folder / 'php.log', 'w+', encoding='utf-8')
        try:
            cls.start_server()
        except Exception:
            cls.tearDownClass()
            raise

    @classmethod
    def start_server(cls):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        cls.base = f'http://127.0.0.1:{port}/'
        cls.server = subprocess.Popen(cls.php + ['-S', f'127.0.0.1:{port}', 'router.php'], cwd=ROOT,
                                      env=cls.environment, stdout=cls.log, stderr=cls.log)
        for _ in range(100):
            if cls.server.poll() is not None:
                cls.log.seek(0)
                raise RuntimeError('PHP server stopped: ' + cls.log.read())
            try:
                with urllib.request.urlopen(cls.base, timeout=1) as response:
                    if response.status == 200:
                        return
            except OSError:
                time.sleep(.1)
        raise RuntimeError('PHP server did not become ready.')

    @classmethod
    def stop_server(cls):
        if cls.server is not None and cls.server.poll() is None:
            cls.server.terminate()
            cls.server.wait(timeout=10)

    @classmethod
    def tearDownClass(cls):
        cls.stop_server()
        cls.log.close()
        cls.temporary.cleanup()

    def php_code(self, body, storage, *args):
        code = 'date_default_timezone_set("Asia/Manila"); require ' + json.dumps((ROOT / 'app/database.php').as_posix()) + '; ' + body
        result = subprocess.run(self.php + ['-r', code, *args], cwd=ROOT,
                                env=dict(os.environ, OSY_WEB_STORAGE=str(storage)),
                                capture_output=True, text=True, timeout=40)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_01_browser_workflow_without_mysql_driver(self):
        drivers = subprocess.check_output(self.php + ['-r', 'echo json_encode(PDO::getAvailableDrivers());'], text=True)
        self.assertEqual(json.loads(drivers), ['sqlite'])
        result = subprocess.run([sys.executable, str(ROOT / 'tests/integration.py')], cwd=ROOT,
                                env=dict(os.environ, OSY_TEST_URL=self.base),
                                capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('34 integration checks passed', result.stdout)

    def test_02_persists_after_server_restart(self):
        path = self.folder / 'storage/database/osy.sqlite3'
        with closing(sqlite3.connect(path)) as database:
            self.assertEqual(database.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(database.execute('SELECT COUNT(*) FROM admins').fetchone()[0], 1)
            before = database.execute('SELECT osy_id, full_name, photo FROM osy_records ORDER BY id').fetchall()
            self.assertEqual(len(before), 2)
            self.assertTrue((self.folder / 'storage/photos' / before[0][2]).is_file())
        self.stop_server()
        self.start_server()
        with urllib.request.urlopen(self.base, timeout=10) as response:
            self.assertIn('page=login', response.url)
        with closing(sqlite3.connect(path)) as database:
            self.assertEqual(database.execute('SELECT osy_id, full_name, photo FROM osy_records ORDER BY id').fetchall(), before)

    def test_parallel_counter_allocation(self):
        folder = self.folder / 'parallel-ids'
        body = '$ids=[]; for ($i=0;$i<10;$i++) { $ids[]=writeTransaction(db(), function($pdo) { $id=allocateOsyId($pdo); usleep(1000); return $id; }); } echo json_encode($ids);'
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: json.loads(self.php_code(body, folder)), range(8)))
        identifiers = [item for group in results for item in group]
        self.assertEqual(len(set(identifiers)), 80)
        self.assertEqual(sorted(int(item.rsplit('-', 1)[1]) for item in identifiers), list(range(1, 81)))



if __name__ == '__main__':
    unittest.main()
