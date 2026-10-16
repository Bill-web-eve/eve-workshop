import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('github_release', Path(__file__).resolve().parents[1] / 'tools/publish_github_release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.path = self.folder / 'installer.zip'
        self.path.write_bytes(b'clean test installer')
        self.digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.data = {'tag': 'v1.0.0', 'title': 'Test release', 'body': 'Test notes'}
        self.files = [(self.path, self.digest)]
        self.asset = {'name': self.path.name, 'state': 'uploaded', 'size': self.path.stat().st_size, 'digest': 'sha256:' + self.digest}

    def test_corrupt_local_file_and_path_traversal_are_rejected(self):
        manifest = self.folder / 'manifest.json'
        manifest.write_text(json.dumps({'tag': 'v1', 'assets': [{'name': self.path.name, 'sha256': '0' * 64}]}))
        with self.assertRaisesRegex(RuntimeError, 'SHA-256 mismatch'):
            release.checked_bundle(manifest)
        manifest.write_text(json.dumps({'tag': 'v1', 'assets': [{'name': '../private.zip', 'sha256': self.digest}]}))
        with self.assertRaisesRegex(RuntimeError, 'filename'):
            release.checked_bundle(manifest)

    def test_only_http_404_is_treated_as_missing(self):
        with patch.object(release, 'gh', side_effect=RuntimeError('HTTP 403 Forbidden')):
            with self.assertRaisesRegex(RuntimeError, '403'):
                release.release_info('owner/repo', 'v1')
        with patch.object(release, 'gh', side_effect=RuntimeError('HTTP 404 Not Found')):
            self.assertIsNone(release.release_info('owner/repo', 'v1'))

    def test_corrupt_remote_file_is_never_overwritten(self):
        bad = dict(self.asset, digest='sha256:' + '0' * 64)
        with patch.object(release, 'release_info', return_value={'draft': True, 'assets': [bad]}), patch.object(release, 'gh') as gh:
            with self.assertRaisesRegex(RuntimeError, 'Remote SHA-256 mismatch'):
                release.publish('owner/repo', 'main', self.data, self.files)
            gh.assert_not_called()

    def test_published_incomplete_release_is_not_modified(self):
        with patch.object(release, 'release_info', return_value={'draft': False, 'assets': []}), patch.object(release, 'gh') as gh:
            with self.assertRaisesRegex(RuntimeError, 'Published release is incomplete'):
                release.publish('owner/repo', 'main', self.data, self.files)
            gh.assert_not_called()

    def test_identical_published_release_is_idempotent(self):
        with patch.object(release, 'release_info', return_value={'draft': False, 'assets': [self.asset]}), patch.object(release, 'gh') as gh:
            release.publish('owner/repo', 'main', self.data, self.files)
            gh.assert_not_called()

    def test_interrupted_draft_upload_resumes_before_publishing(self):
        before = {'draft': True, 'assets': []}
        after = {'draft': True, 'assets': [self.asset]}
        public = {'draft': False, 'assets': [self.asset]}
        with patch.object(release, 'release_info', side_effect=[before, after, public]), patch.object(release, 'gh') as gh:
            release.publish('owner/repo', 'main', self.data, self.files)
            self.assertEqual([c.args[1] for c in gh.call_args_list], ['upload', 'edit'])
            self.assertFalse(any('--clobber' in c.args for c in gh.call_args_list))

    def test_missing_release_is_draft_until_upload_verified(self):
        draft = {'draft': True, 'assets': []}
        uploaded = {'draft': True, 'assets': [self.asset]}
        public = {'draft': False, 'assets': [self.asset]}
        with patch.object(release, 'release_info', side_effect=[None, draft, uploaded, public]), patch.object(release, 'gh') as gh:
            release.publish('owner/repo', 'main', self.data, self.files)
            self.assertEqual([c.args[1] for c in gh.call_args_list], ['create', 'upload', 'edit'])
            self.assertIn('--draft', gh.call_args_list[0].args)

    def test_upload_failure_does_not_publish_draft(self):
        with patch.object(release, 'release_info', return_value={'draft': True, 'assets': []}), patch.object(release, 'gh', side_effect=RuntimeError('upload failed')) as gh:
            with self.assertRaisesRegex(RuntimeError, 'upload failed'):
                release.publish('owner/repo', 'main', self.data, self.files)
            self.assertEqual(gh.call_count, 1)
            self.assertEqual(gh.call_args.args[1], 'upload')


if __name__ == '__main__':
    unittest.main()
