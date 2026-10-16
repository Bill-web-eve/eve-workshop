#!/usr/bin/env python3
"""Publish the reviewed installers with GitHub CLI; never rebuild or overwrite them."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'release-assets/v0.8.1/manifest.json'


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


def release_info(repo, tag):
    try:
        return json.loads(gh('api', 'repos/' + repo + '/releases/tags/' + quote(tag, safe='')))
    except RuntimeError as exc:
        if 'HTTP 404' in str(exc):
            return None
        raise


def verify_remote(repo, tag, path, expected, asset):
    if asset.get('state') != 'uploaded' or asset.get('size') != path.stat().st_size:
        raise RuntimeError('Incomplete remote asset: ' + path.name)
    digest = asset.get('digest')
    if digest is not None:
        if digest != 'sha256:' + expected:
            raise RuntimeError('Remote SHA-256 mismatch: ' + path.name)
        return
    # Older GitHub responses may omit digest; let gh handle authenticated redirects.
    with tempfile.TemporaryDirectory(prefix='eve-release-check-') as folder:
        gh('release', 'download', tag, '--repo', repo, '--pattern', path.name, '--dir', folder)
        if hashlib.sha256((Path(folder) / path.name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Remote SHA-256 mismatch: ' + path.name)


def publish(repo, target, data, files):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise RuntimeError('GH_REPO must be OWNER/REPOSITORY')
    tag = data['tag']
    release = release_info(repo, tag)
    if release is None:
        gh('release', 'create', tag, '--repo', repo, '--title', data['title'],
           '--notes', data['body'], '--target', target, '--draft')
        release = release_info(repo, tag)
        if release is None:
            raise RuntimeError('Draft release was not created')
    assets = {a['name']: a for a in release['assets']}
    missing = []
    for path, expected in files:
        if path.name in assets:
            verify_remote(repo, tag, path, expected, assets[path.name])
        else:
            missing.append(path)
    if missing and not release['draft']:
        raise RuntimeError('Published release is incomplete. Use a new release tag; existing files were not changed.')
    if missing:
        gh('release', 'upload', tag, '--repo', repo, *map(str, missing))
        release = release_info(repo, tag)
        assets = {a['name']: a for a in release['assets']}
        for path, expected in files:
            if path.name not in assets:
                raise RuntimeError('Upload missing: ' + path.name)
            verify_remote(repo, tag, path, expected, assets[path.name])
    if release['draft']:
        gh('release', 'edit', tag, '--repo', repo, '--draft=false', '--latest')
    published = release_info(repo, tag)
    if not published or published['draft']:
        raise RuntimeError('Release has not been published')
    print('Published: https://github.com/' + repo + '/releases/tag/' + tag)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=MANIFEST)
    parser.add_argument('--check', action='store_true', help='Verify local files without credentials or network access')
    args = parser.parse_args()
    data, files = checked_bundle(args.manifest)
    print('Verified %d installer, checksum and instruction files.' % len(files))
    if args.check:
        return
    if not os.environ.get('GH_TOKEN') and not os.environ.get('GITHUB_TOKEN'):
        raise RuntimeError('Use GitHub Actions, or supply your own authenticated GH_TOKEN environment. Never commit tokens.')
    publish(os.environ.get('GH_REPO', 'Bill-web-eve/eve-workshop'),
            os.environ.get('RELEASE_TARGET', 'main'), data, files)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, KeyError, ValueError) as exc:
        raise SystemExit(str(exc))
