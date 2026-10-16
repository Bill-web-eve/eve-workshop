import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('github_release',Path(__file__).resolve().parents[1]/'tools/publish_github_release.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)

class FakeGitHub:
    """Lists may stay stale forever; direct release-ID operations still work."""
    def __init__(self,test,existing=None):
        self.test=test;self.record=copy.deepcopy(existing);self.operations=[]
        self.list_calls=0;self.stale_listing=existing is None;self.upload_error=False;self.patch_error=False
        self.final_lag=0;self.file=None;self.asset=None
    def gh(self,*args):
        self.test.assertEqual(args[0],'api','Tag-based gh release commands must not be used')
        if '--paginate' in args:
            self.list_calls+=1
            return json.dumps([[] if self.stale_listing else [self.record]])
        method=args[args.index('--method')+1] if '--method' in args else 'GET'
        endpoint=next(a for a in args if a.startswith(('repos/','https://uploads.github.com/')))
        payload=json.loads(Path(args[args.index('--input')+1]).read_text()) if '--input' in args and not endpoint.startswith('https:') else None
        self.operations.append((method,endpoint,payload))
        if method=='POST' and endpoint=='repos/owner/repo/releases':
            self.test.assertEqual(payload['draft'],True);self.test.assertEqual(payload['target_commitish'],'main')
            self.record={'id':123,'tag_name':payload['tag_name'],'draft':True,'assets':[],'body':payload['body']}
        elif method=='POST' and endpoint.startswith('https://uploads.github.com/'):
            self.test.assertIn('/releases/123/assets?name=installer.zip',endpoint)
            self.test.assertEqual(Path(args[args.index('--input')+1]).read_bytes(),self.file.read_bytes())
            if self.upload_error:raise RuntimeError('HTTP 403 upload denied')
            self.record['assets'].append(copy.deepcopy(self.asset));return json.dumps(self.asset)
        elif method=='PATCH':
            self.test.assertEqual(endpoint,'repos/owner/repo/releases/123')
            if self.patch_error:raise RuntimeError('HTTP 403 edit denied')
            self.record.update(payload)
        elif method=='GET':
            self.test.assertEqual(endpoint,'repos/owner/repo/releases/123')
            if self.final_lag:
                self.final_lag-=1;return json.dumps({**self.record,'draft':True})
        return json.dumps(self.record)

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name)
        self.path=self.folder/'installer.zip';self.path.write_bytes(b'clean test installer')
        self.digest=hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.data={'tag':'v1.0.0','title':'Release','body':'Download `installer.zip`\n\nSecond line'}
        self.files=[(self.path,self.digest)]
        self.asset={'id':456,'name':self.path.name,'state':'uploaded','size':self.path.stat().st_size,'digest':'sha256:'+self.digest}
    def record(self,**kw):return {'id':123,'tag_name':'v1.0.0','draft':False,'assets':[self.asset],**kw}
    def fake(self,existing=None):
        f=FakeGitHub(self,existing);f.file=self.path;f.asset=self.asset;return f
    def run_publish(self,f):
        with patch.object(release,'gh',side_effect=f.gh),patch.object(release.time,'sleep'):
            release.publish('owner/repo','main',self.data,self.files)
    def test_fresh_draft_is_published_even_when_all_listings_remain_stale(self):
        f=self.fake();self.run_publish(f)
        self.assertEqual(f.list_calls,1)
        self.assertEqual([o[0] for o in f.operations],['POST','POST','PATCH','GET'])
        self.assertFalse(f.record['draft']);self.assertEqual(f.record['assets'],[self.asset])
        self.assertIn('[installer.zip](https://github.com/owner/repo/releases/download/v1.0.0/installer.zip)',f.record['body'])
        self.assertIn('\n\nSecond line',f.record['body'])
    def test_existing_empty_published_release_is_repaired_by_id_without_recreation(self):
        f=self.fake(self.record(assets=[],body='Owner notes: retained'));self.run_publish(f)
        self.assertEqual([o[0] for o in f.operations],['POST','GET'])
        self.assertEqual(f.record['body'],'Owner notes: retained')
    def test_existing_draft_resumes_without_overwriting_verified_asset(self):
        f=self.fake(self.record(draft=True));self.run_publish(f)
        self.assertEqual([o[0] for o in f.operations],['PATCH','GET'])
    def test_identical_published_release_is_idempotent(self):
        f=self.fake(self.record(body='Existing owner notes'));self.run_publish(f);self.assertEqual([o[0] for o in f.operations],['GET'])
    def test_corrupt_asset_is_never_overwritten(self):
        f=self.fake(self.record(assets=[dict(self.asset,digest='sha256:'+'0'*64)]))
        with self.assertRaisesRegex(RuntimeError,'Remote SHA-256 mismatch'):self.run_publish(f)
        self.assertFalse(f.operations)
    def test_immutable_incomplete_release_is_not_modified(self):
        f=self.fake(self.record(assets=[],immutable=True))
        with self.assertRaisesRegex(RuntimeError,'Immutable release'):self.run_publish(f)
        self.assertFalse(f.operations)
    def test_upload_failure_leaves_new_release_draft(self):
        f=self.fake();f.upload_error=True
        with self.assertRaisesRegex(RuntimeError,'upload denied'):self.run_publish(f)
        self.assertTrue(f.record['draft']);self.assertNotIn('PATCH',[o[0] for o in f.operations])
    def test_uploaded_response_must_have_expected_hash_before_publish(self):
        f=self.fake();f.asset={**self.asset,'digest':'sha256:'+'0'*64}
        with self.assertRaisesRegex(RuntimeError,'Remote SHA-256 mismatch'):self.run_publish(f)
        self.assertTrue(f.record['draft'])
    def test_publication_failure_not_reported_success(self):
        f=self.fake();f.patch_error=True
        with self.assertRaisesRegex(RuntimeError,'edit denied'):self.run_publish(f)
        self.assertTrue(f.record['draft'])
    def test_direct_read_lag_retried_without_any_extra_upload(self):
        f=self.fake();f.final_lag=2;self.run_publish(f)
        self.assertEqual([o[0] for o in f.operations],['POST','POST','PATCH','GET','GET','GET'])
    def test_lookup_includes_drafts_on_later_pages(self):
        draft=self.record(draft=True)
        with patch.object(release,'gh',return_value=json.dumps([[{'tag_name':'v2'}],[draft]])) as gh:
            self.assertEqual(release.release_info('owner/repo','v1.0.0'),draft)
            self.assertIn('--paginate',gh.call_args.args);self.assertIn('--slurp',gh.call_args.args)
            self.assertNotIn('/tags/',gh.call_args.args[-1])
    def test_lookup_errors_and_duplicate_releases_are_not_absence(self):
        with patch.object(release,'gh',side_effect=RuntimeError('HTTP 403')):
            with self.assertRaisesRegex(RuntimeError,'HTTP 403'):release.release_info('owner/repo','v1.0.0')
        with patch.object(release,'gh',return_value=json.dumps([[self.record(),self.record()]])):
            with self.assertRaisesRegex(RuntimeError,'More than one release'):release.release_info('owner/repo','v1.0.0')
    def test_bad_create_identity_prevents_upload(self):
        for record in [{'id':True,'tag_name':'v1.0.0'},{'id':123,'tag_name':'v2'},{}]:
            with self.subTest(record=record),patch.object(release,'release_info',return_value=None),patch.object(release,'api_json',return_value=record),patch.object(release,'upload_asset') as upload:
                with self.assertRaisesRegex(RuntimeError,'invalid release identity'):release.publish('owner/repo','main',self.data,self.files)
                upload.assert_not_called()
    def test_local_corruption_and_path_traversal_rejected(self):
        manifest=self.folder/'manifest.json'
        for name,digest,expected in [('installer.zip','0'*64,'SHA-256'),('../private.zip',self.digest,'filename')]:
            manifest.write_text(json.dumps({'tag':'v1','assets':[{'name':name,'sha256':digest}]}))
            with self.assertRaisesRegex(RuntimeError,expected):release.checked_bundle(manifest)
    def test_legacy_asset_download_uses_asset_id_not_release_tag(self):
        def download(args,stdout,stderr):
            self.assertEqual(args[-1],'repos/owner/repo/releases/assets/456')
            self.assertNotIn('release',args)
            stdout.write(self.path.read_bytes())
            from types import SimpleNamespace
            return SimpleNamespace(returncode=0)
        with patch.object(release.subprocess,'run',side_effect=download):
            release.verify_remote('owner/repo','v1.0.0',self.path,self.digest,{k:v for k,v in self.asset.items() if k!='digest'})

    def test_all_versions_numeric_order_nine_before_ten(self):
        for version in ['v0.10.0','v0.8.1','v0.9.0']:
            folder=self.folder/'release-assets'/version;folder.mkdir(parents=True);(folder/'manifest.json').write_text('{}')
        self.assertEqual([p.parent.name for p in release.all_manifests(self.folder)],['v0.8.1','v0.9.0','v0.10.0'])
    def test_all_manifests_checked_before_first_publication(self):
        with patch.object(release,'all_manifests',return_value=['first','second']),patch.object(release,'checked_bundle',side_effect=[(self.data,self.files),RuntimeError('corrupt second')]),patch.object(release,'publish') as publish,patch('sys.argv',['publish','--all']):
            with self.assertRaisesRegex(RuntimeError,'corrupt second'):release.main()
            publish.assert_not_called()
    def test_failure_of_older_version_does_not_skip_newer_repair(self):
        next_data={**self.data,'tag':'v2.0.0'}
        with patch.object(release,'all_manifests',return_value=['first','second']),patch.object(release,'checked_bundle',side_effect=[(self.data,self.files),(next_data,self.files)]),patch.object(release,'publish',side_effect=[RuntimeError('old immutable'),None]) as publish,patch.dict('os.environ',{'GH_TOKEN':'unit-test-only'}),patch('sys.argv',['publish','--all']):
            with self.assertRaisesRegex(RuntimeError,'v1.0.0: old immutable'):release.main()
            self.assertEqual(publish.call_count,2)

if __name__=='__main__':unittest.main()
