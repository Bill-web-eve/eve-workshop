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

    def test_release_lookup_includes_drafts_on_later_pages(self):
        draft = {'tag_name': 'v1', 'draft': True, 'assets': []}
        pages = [[{'tag_name': 'v2', 'draft': False}], [draft]]
        with patch.object(release, 'gh', return_value=json.dumps(pages)) as gh:
            self.assertEqual(release.release_info('owner/repo', 'v1'), draft)
            self.assertIn('--paginate', gh.call_args.args)
            self.assertIn('--slurp', gh.call_args.args)
            self.assertNotIn('/tags/', gh.call_args.args[-1])

    def test_api_errors_are_not_treated_as_missing_releases(self):
        for status in [401, 403, 404, 500]:
            with patch.object(release, 'gh', side_effect=RuntimeError('HTTP ' + str(status))):
                with self.assertRaisesRegex(RuntimeError, str(status)):
                    release.release_info('owner/repo', 'v1')
        with patch.object(release, 'gh', return_value='[[]]'):
            self.assertIsNone(release.release_info('owner/repo', 'v1'))

    def test_corrupt_remote_file_is_never_overwritten(self):
        bad = dict(self.asset, digest='sha256:' + '0' * 64)
        with patch.object(release, 'release_info', return_value={'draft': True, 'assets': [bad]}), patch.object(release, 'gh') as gh:
            with self.assertRaisesRegex(RuntimeError, 'Remote SHA-256 mismatch'):
                release.publish('owner/repo', 'main', self.data, self.files)
            gh.assert_not_called()

    def test_immutable_incomplete_release_is_not_modified(self):
        with patch.object(release, 'release_info', return_value={'draft': False, 'immutable': True, 'assets': []}), patch.object(release, 'gh') as gh:
            with self.assertRaisesRegex(RuntimeError, 'Immutable release is incomplete'):
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

    def test_published_empty_release_is_repaired_without_recreating_it(self):
        before = {'draft': False, 'immutable': False, 'assets': []}
        after = {'draft': False, 'immutable': False, 'assets': [self.asset]}
        with patch.object(release, 'release_info', side_effect=[before, after, after]), patch.object(release, 'gh') as gh:
            release.publish('owner/repo', 'main', self.data, self.files)
            self.assertEqual([c.args[1] for c in gh.call_args_list], ['upload'])
            self.assertNotIn('--clobber', gh.call_args.args)

    def test_download_links_preserve_owners_custom_notes(self):
        body = 'Download `installer.zip`\n\nCustom changelog: retained'
        info = {'draft': False, 'assets': [self.asset], 'body': body}
        with patch.object(release, 'release_info', return_value=info), patch.object(release, 'gh') as gh:
            release.publish('owner/repo', 'main', self.data, self.files)
            args = gh.call_args.args
            self.assertEqual(args[1], 'edit')
            new_body = args[args.index('--notes') + 1]
            self.assertIn('Custom changelog: retained', new_body)
            self.assertIn('[installer.zip](https://github.com/owner/repo/releases/download/v1.0.0/installer.zip)', new_body)

    def test_real_lookup_and_publishing_support_a_draft_with_no_public_tag(self):
        # Model GitHub's documented API semantics rather than mocking release_info:
        # a new draft appears in authenticated listings before publication.
        remote = []
        operations = []
        def fake_gh(*args):
            if args[0] == 'api':
                self.assertNotIn('/tags/', args[-1])
                return json.dumps([remote])
            operations.append(args[1])
            if args[1] == 'create':
                remote.append({'tag_name': self.data['tag'], 'draft': True, 'assets': []})
            elif args[1] == 'upload':
                remote[0]['assets'] = [self.asset]
            elif args[1] == 'edit':
                remote[0]['draft'] = False
            return ''
        with patch.object(release, 'gh', side_effect=fake_gh):
            release.publish('owner/repo', 'main', self.data, self.files)
        self.assertEqual(operations, ['create', 'upload', 'edit'])
        self.assertFalse(remote[0]['draft'])


if __name__ == '__main__':
    unittest.main()
