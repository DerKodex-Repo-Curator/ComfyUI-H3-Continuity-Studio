import json
import os
import subprocess
import sys
import tempfile
import unittest

from tests.support import FixtureStudio


class CLITest(unittest.TestCase):
    def test_diagnostic_launcher_works_outside_the_checkout(self):
        host = FixtureStudio()
        self.addCleanup(host.close)
        host.routes[('GET', '/h3c/agent/catalog')] = (200, {'agent_api_version': 1, 'skills': [{}]})
        host.routes[('GET', '/h3c/api/v1/capabilities')] = (200, {'profiles': [], 'readiness': {'render': False}})
        with tempfile.TemporaryDirectory(prefix='h3c path with spaces ') as directory:
            result = subprocess.run([sys.executable, '-m', 'h3c_mcp', '--studio-url', host.url, '--check'],
                                    cwd=directory, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['skills'], 1)
        self.assertEqual(result.stderr, '')

    def test_import_and_help_require_no_host_dependencies(self):
        result = subprocess.run([sys.executable, '-c', "import sys,h3c_mcp; assert 'torch' not in sys.modules; assert 'folder_paths' not in sys.modules"], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([sys.executable, '-m', 'h3c_mcp', '--help'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--studio-url', result.stdout)
