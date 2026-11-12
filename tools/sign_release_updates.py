#!/usr/bin/env python3
"""Create an Ed25519-authenticated update descriptor after both packages build.
Private keys are LOCAL inputs, never copied into release files or the repository.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
if str(Path(__file__).resolve().parents[1]) not in sys.path:sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from muhely.updates import REPO, canonical, trust_key, verify_document, version

def sign(manifest_path, key_file):
    manifest_path=Path(manifest_path);manifest=json.loads(manifest_path.read_text());v=manifest['tag'].removeprefix('v');version(v)
    folder=manifest_path.parent
    key=serialization.load_pem_private_key(Path(key_file).read_bytes(),password=None)
    if not isinstance(key,Ed25519PrivateKey):raise ValueError('An Ed25519 signing key is required')
    assets={}
    for platform,suffix in [('macos-arm64','macOS-AppleSilicon-update.zip'),('windows-x64','Windows11-x64.zip')]:
        name=f'EVE_Muhely-{v}-{suffix}';p=folder/name
        if p.is_symlink() or not p.is_file():raise ValueError('Missing update archive: '+name)
        assets[platform]={'name':name,'url':REPO+'/releases/download/v'+v+'/'+name,'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    payload={'schema':1,'version':v,'notes_url':REPO+'/releases/tag/v'+v,'assets':assets}
    document={'payload':payload,'signature':base64.b64encode(key.sign(canonical(payload))).decode()}
    verify_document(document,trust_key()) # refuse signing with a different local key
    (folder/'update.json').write_text(json.dumps(document,indent=2)+'\n')
    for name in [assets['macos-arm64']['name'],'update.json']:
        p=folder/name;record={'name':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        manifest['assets']=[a for a in manifest['assets'] if a['name']!=name]+[record]
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    print('Signed update descriptor prepared and verified; no private key was exported.')
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--key-file',type=Path,required=True)
    args=parser.parse_args();sign(args.manifest,args.key_file)
