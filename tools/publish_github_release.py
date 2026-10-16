#!/usr/bin/env python3
"""Publish reviewed installers by release ID; never overwrite existing assets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'release-assets/v0.11.0/manifest.json'


def checked_bundle(manifest_path):
    manifest_path = Path(manifest_path).resolve()
    data = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', data['tag']):
        raise RuntimeError('Invalid release tag')
    files = []
    names = set()
    for asset in data['assets']:
        name = asset['name']
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]+', name) or '..' in name or name in names:
            raise RuntimeError('Invalid or duplicate asset filename')
        names.add(name)
        path = manifest_path.parent / name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError('Missing or unsafe asset: ' + name)
        if not re.fullmatch(r'[a-f0-9]{64}', asset['sha256']):
            raise RuntimeError('Invalid SHA-256: ' + name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != asset['sha256']:
            raise RuntimeError('SHA-256 mismatch: ' + name)
        files.append((path, asset['sha256']))
    if not files:
        raise RuntimeError('No release assets')
    data['body'] = (manifest_path.parent / 'notes.md').read_text(encoding='utf-8')
    return data, files


def gh(*args):
    result = subprocess.run(['gh', *args], text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'GitHub CLI failed')
    return result.stdout


def api_json(endpoint, method='GET', data=None):
    args=['api','--method',method,'--header','Cache-Control: no-cache']
    if data is None:return json.loads(gh(*args,endpoint))
    # Keep JSON booleans, arbitrary notes and real newlines intact.
    with tempfile.TemporaryDirectory(prefix='eve-release-request-') as folder:
        payload=Path(folder)/'request.json'
        payload.write_text(json.dumps(data),encoding='utf-8')
        return json.loads(gh(*args,endpoint,'--input',str(payload)))


def release_info(repo, tag):
    pages = json.loads(gh('api', '--paginate', '--slurp', '--header','Cache-Control: no-cache',
                         'repos/' + repo + '/releases?per_page=100'))
    matches = [item for page in pages for item in page if item['tag_name'] == tag]
    if len(matches) > 1:
        raise RuntimeError('More than one release has tag ' + tag)
    return matches[0] if matches else None


def release_id(release, tag):
    value=release.get('id')
    if isinstance(value,bool) or not isinstance(value,int) or value<1 or release.get('tag_name')!=tag:
        raise RuntimeError('GitHub returned an invalid release identity for '+tag)
    return value


def verify_remote(repo, tag, path, expected, asset):
    if asset.get('state') != 'uploaded' or asset.get('size') != path.stat().st_size:
        raise RuntimeError('Incomplete remote asset: ' + path.name)
    digest = asset.get('digest')
    if digest is not None:
        if digest != 'sha256:' + expected:
            raise RuntimeError('Remote SHA-256 mismatch: ' + path.name)
        return
    # Legacy assets may omit digest. Download by asset ID, including drafts;
    # avoid all tag/list lookups and let gh handle authenticated redirects.
    aid=asset.get('id')
    if isinstance(aid,bool) or not isinstance(aid,int) or aid<1:raise RuntimeError('Missing asset ID: '+path.name)
    with tempfile.TemporaryDirectory(prefix='eve-release-check-') as folder:
        target=Path(folder)/'asset.bin'
        with target.open('wb') as stream:
            result=subprocess.run(['gh','api','--header','Accept: application/octet-stream',
                'repos/'+repo+'/releases/assets/'+str(aid)],stdout=stream,stderr=subprocess.PIPE)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace').strip() or 'Asset download failed')
        if hashlib.sha256(target.read_bytes()).hexdigest()!=expected:
            raise RuntimeError('Remote SHA-256 mismatch: '+path.name)


def upload_asset(repo, rid, path):
    endpoint='https://uploads.github.com/repos/'+repo+'/releases/'+str(rid)+'/assets?name='+quote(path.name,safe='')
    return json.loads(gh('api','--method','POST',endpoint,'--header','Content-Type: application/octet-stream','--input',str(path)))


def linked_notes(repo,tag,body,files):
    for path,_ in files:
        if path.suffix.lower() in {'.zip','.dmg'}:
            url='https://github.com/'+repo+'/releases/download/'+quote(tag,safe='')+'/'+quote(path.name)
            body=body.replace('`'+path.name+'`','['+path.name+']('+url+')')
    return body


def publish(repo, target, data, files):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise RuntimeError('GH_REPO must be OWNER/REPOSITORY')
    tag=data['tag']
    release=release_info(repo,tag)
    if release is None:
        # The POST response is authoritative. A just-created draft may not yet
        # be present in List releases; never rediscover it by tag or listing.
        release=api_json('repos/'+repo+'/releases','POST',{
            'tag_name':tag,'name':data['title'],'body':data['body'],
            'target_commitish':target,'draft':True})
    rid=release_id(release,tag)
    endpoint='repos/'+repo+'/releases/'+str(rid)
    print('Checking '+tag+' (release ID '+str(rid)+')',flush=True)
    assets={a['name']:a for a in release['assets']}
    missing=[]
    for path,expected in files:
        if path.name in assets:verify_remote(repo,tag,path,expected,assets[path.name])
        else:missing.append((path,expected))
    if missing and release.get('immutable',False):
        raise RuntimeError('Immutable release is incomplete. Use a new release tag; existing files were not changed.')
    for path,expected in missing:
        print('Uploading '+tag+': '+path.name,flush=True)
        uploaded=upload_asset(repo,rid,path)
        if uploaded.get('name')!=path.name:raise RuntimeError('Upload returned a different asset name')
        verify_remote(repo,tag,path,expected,uploaded)
        assets[path.name]=uploaded
    original_body=release.get('body') or data['body']
    body=linked_notes(repo,tag,original_body,files)
    patch={}
    if release['draft']:patch.update(draft=False,make_latest='true')
    if body!=original_body:patch['body']=body
    if patch:
        release=api_json(endpoint,'PATCH',patch)
        if release_id(release,tag)!=rid:raise RuntimeError('Release identity changed during publication')
    # Read the exact release directly, not the eventually indexed list. Retry
    # boundedly if GitHub's read view lags completed uploads/publication.
    last_error=None
    for delay in [0,.5,1,2]:
        if delay:time.sleep(delay)
        try:
            published=api_json(endpoint)
            if release_id(published,tag)!=rid or published['draft']:
                raise RuntimeError('Release has not been published')
            remote={a['name']:a for a in published['assets']}
            for path,expected in files:
                if path.name not in remote:raise RuntimeError('Upload missing: '+path.name)
                verify_remote(repo,tag,path,expected,remote[path.name])
            print('Published and verified: https://github.com/'+repo+'/releases/tag/'+tag,flush=True)
            return
        except RuntimeError as exc:last_error=exc
    raise last_error


def all_manifests(root=ROOT):
    def version(path):
        match=re.fullmatch(r'v(\d+)\.(\d+)\.(\d+)',path.parent.name)
        if not match:raise RuntimeError('Unsupported release folder: '+path.parent.name)
        return tuple(map(int,match.groups()))
    paths=sorted((root/'release-assets').glob('*/manifest.json'),key=version)
    if not paths:raise RuntimeError('No release manifests')
    return paths


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--manifest',type=Path)
    group.add_argument('--all',action='store_true',help='Verify and repair every reviewed release, oldest first')
    parser.add_argument('--check',action='store_true',help='Verify local files without credentials or network access')
    args=parser.parse_args()
    paths=all_manifests() if args.all else [args.manifest or MANIFEST]
    # Validate every local file before any network mutation.
    bundles=[checked_bundle(path) for path in paths]
    for data,files in bundles:print('Verified '+data['tag']+': '+str(len(files))+' local files.',flush=True)
    if args.check:return
    if not os.environ.get('GH_TOKEN') and not os.environ.get('GITHUB_TOKEN'):
        raise RuntimeError('Use GitHub Actions, or supply your own authenticated GH_TOKEN environment. Never commit tokens.')
    failures=[]
    for data,files in bundles:
        try:publish(os.environ.get('GH_REPO','Bill-web-eve/eve-workshop'),os.environ.get('RELEASE_TARGET','main'),data,files)
        except (RuntimeError,OSError,KeyError,ValueError) as exc:
            failures.append(data['tag']+': '+str(exc));print('FAILED '+failures[-1],flush=True)
    if failures:raise RuntimeError('\n'.join(failures))


if __name__=='__main__':
    try:main()
    except (RuntimeError,OSError,KeyError,ValueError) as exc:raise SystemExit(str(exc))
