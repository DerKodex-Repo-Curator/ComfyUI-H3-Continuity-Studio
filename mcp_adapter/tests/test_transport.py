import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.support import FixtureStudio
try:
    from h3c_mcp import transport
except ImportError:
    transport = None


class TransportTest(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(transport, 'Standalone transport must not depend on ComfyUI')
        self.host = FixtureStudio()
        self.addCleanup(self.host.close)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.client = transport.StudioClient(self.host.url + '/comfy', token='secret-token', roots=[self.root])
        self.addCleanup(self.client.close)

    def test_proxy_prefix_auth_and_idempotency(self):
        self.host.routes[('POST', '/comfy/create')] = (200, {'ok': True})
        self.client.json('/create', method='POST', body={'seed': 18446744073709551615}, key='saved-key')
        request = self.host.requests[-1]
        self.assertEqual(request['headers']['Authorization'], 'Bearer secret-token')
        self.assertEqual(request['headers']['Idempotency-Key'], 'saved-key')
        self.assertEqual(json.loads(request['body'])['seed'], 18446744073709551615)

    def test_errors_preserve_code_and_redact_credentials(self):
        self.host.routes[('GET', '/comfy/error')] = (409, {'error': {'code': 'revision_conflict', 'message': 'secret-token rejected', 'details': {'token': 'secret-token'}}})
        with self.assertRaises(transport.StudioError) as raised:
            self.client.json('/error')
        self.assertEqual(raised.exception.code, 'revision_conflict')
        self.assertNotIn('secret-token', str(raised.exception))
        self.assertNotIn('secret-token', repr(raised.exception.details))

    def test_native_http_200_failure_is_an_error(self):
        self.host.routes[('GET', '/comfy/native')] = (200, {'ok': False, 'error': 'no snapshot'})
        with self.assertRaisesRegex(transport.StudioError, 'no snapshot'):
            self.client.json('/native')

    def test_failed_job_status_keeps_its_recovery_evidence(self):
        job = {'state': 'failed', 'id': 'job1', 'error': {'code': 'execution_failed', 'message': 'inspect attempt'}, 'attempts': ['evidence']}
        self.host.routes[('GET', '/comfy/job')] = (200, job)
        self.assertEqual(self.client.json('/job'), job)

    def test_redirect_is_not_followed(self):
        other = FixtureStudio()
        self.addCleanup(other.close)
        self.host.routes[('GET', '/comfy/redirect')] = (302, {}, {'Location': other.url + '/stolen'})
        with self.assertRaises(transport.StudioError):
            self.client.json('/redirect')
        self.assertEqual(other.requests, [])

    def test_unsafe_origins_and_paths_are_rejected(self):
        for url in ('file:///tmp', 'https://user:pass@example.com', self.host.url + '/?secret=1'):
            with self.subTest(url=url), self.assertRaises(transport.StudioError):
                transport.StudioClient(url)
        for path in ('https://example.com/data', '//example.com', '/../private', '/%2e%2e/private', '/a\\b', '/ok#fragment'):
            with self.subTest(path=path), self.assertRaises(transport.StudioError):
                self.client.json(path)

    def test_bad_json_and_response_limits(self):
        for content in (b'{"n": NaN}', b'[]', b'not json'):
            self.host.routes[('GET', '/comfy/bad')] = (200, content)
            with self.assertRaises(transport.StudioError):
                self.client.json('/bad')
        self.host.routes[('GET', '/comfy/big')] = (200, b'x' * 64)
        with mock.patch.object(transport, 'MAX_JSON', 32), self.assertRaises(transport.StudioError):
            self.client.json('/big')

    def test_failed_download_preserves_destination(self):
        output = self.root / 'film.mp4'
        output.write_bytes(b'previous-output')
        self.host.routes[('GET', '/comfy/artifact')] = (200, b'changed')
        descriptor = dict(download_url='/artifact', size=7, sha256=hashlib.sha256(b'correct').hexdigest())
        with self.assertRaises(transport.StudioError):
            self.client.download(descriptor, output)
        self.assertEqual(output.read_bytes(), b'previous-output')
        descriptor['sha256'] = hashlib.sha256(b'changed').hexdigest()
        self.client.download(descriptor, output)
        self.assertEqual(output.read_bytes(), b'changed')

    def test_local_files_stay_inside_roots(self):
        with self.assertRaises(transport.StudioError):
            self.client.download({}, self.root.parent / 'outside.mp4')

    def test_upload_sends_original_bytes_not_adapter_path(self):
        source = self.root / 'private-name.wav'
        source.write_bytes(b'original-media')
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        self.host.routes[('POST', '/comfy/h3c/api/v1/assets')] = (201, {'sha256': digest, 'id': 'asset'})
        self.assertEqual(self.client.upload(source, 'audio')['id'], 'asset')
        body = self.host.requests[-1]['body']
        self.assertIn(b'original-media', body)
        self.assertNotIn(str(source).encode(), body)


if __name__ == '__main__':
    unittest.main()
