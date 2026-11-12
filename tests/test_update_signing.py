import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from muhely.updates import verify_document
from tools.sign_release_updates import sign

class SigningTests(unittest.TestCase):
    def test_signed_descriptor_and_both_archives_are_in_manifest_without_private_material(self):
        key=Ed25519PrivateKey.generate()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder=root/'release';folder.mkdir();secret=root/'private.pem'
            secret.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
            windows='EVE_Muhely-1.9.0-Windows11-x64.zip';mac='EVE_Muhely-1.9.0-macOS-AppleSilicon-update.zip'
            (folder/windows).write_bytes(b'windows');(folder/mac).write_bytes(b'mac')
            manifest=folder/'manifest.json';manifest.write_text(json.dumps({'tag':'v1.9.0','assets':[{'name':windows,'sha256':hashlib.sha256(b'windows').hexdigest()}]}))
            with patch('tools.sign_release_updates.trust_key',return_value=key.public_key()):sign(manifest,secret)
            payload=verify_document(json.loads((folder/'update.json').read_text()),key.public_key());self.assertEqual(payload['version'],'1.9.0')
            assets=json.loads(manifest.read_text())['assets'];self.assertEqual({a['name'] for a in assets},{windows,mac,'update.json'})
            (folder/'notes.md').write_text('Test release')
            from tools.publish_github_release import checked_bundle
            with patch('muhely.updates.trust_key',return_value=key.public_key()):
                self.assertEqual(len(checked_bundle(manifest)[1]),3)
            with self.assertRaises(ValueError):checked_bundle(manifest)
            self.assertNotIn(b'PRIVATE KEY',(folder/'update.json').read_bytes());self.assertNotIn(secret.name,{p.name for p in folder.iterdir()})
    def test_wrong_local_key_cannot_create_a_descriptor(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);key=Ed25519PrivateKey.generate();secret=root/'private.pem';secret.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
            for name in ['EVE_Muhely-1.9.0-Windows11-x64.zip','EVE_Muhely-1.9.0-macOS-AppleSilicon-update.zip']:(root/name).write_bytes(b'archive')
            manifest=root/'manifest.json';manifest.write_text(json.dumps({'tag':'v1.9.0','assets':[]}))
            with patch('tools.sign_release_updates.trust_key',return_value=Ed25519PrivateKey.generate().public_key()),self.assertRaises(ValueError):sign(manifest,secret)
            self.assertFalse((root/'update.json').exists())

    def test_future_release_requires_signed_metadata(self):
        from tools.publish_github_release import checked_bundle
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'installer.zip').write_bytes(b'archive')
            manifest=root/'manifest.json';manifest.write_text(json.dumps({'tag':'v1.9.0','assets':[{'name':'installer.zip','sha256':hashlib.sha256(b'archive').hexdigest()}]}))
            with self.assertRaisesRegex(RuntimeError,'signed update'):checked_bundle(manifest)
