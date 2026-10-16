"""Windows per-user DPAPI protection for the vault key; no machine-wide key."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path


ENTROPY=b'hu.eve.muhely.tokens.v1'


def transform(data, decrypt=False):
    if os.name!='nt':raise OSError('Windows DPAPI is only available on Windows.')
    class Blob(ctypes.Structure):
        _fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_ubyte))]
    def blob(value):
        buffer=ctypes.create_string_buffer(value)
        return Blob(len(value),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte))),buffer
    incoming,source=blob(data);entropy,entropy_buffer=blob(ENTROPY);outgoing=Blob()
    crypt=ctypes.WinDLL('crypt32',use_last_error=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.LocalFree.argtypes=[wintypes.HLOCAL];kernel.LocalFree.restype=wintypes.HLOCAL
    if decrypt:
        call=crypt.CryptUnprotectData
        call.argtypes=[ctypes.POINTER(Blob),ctypes.POINTER(wintypes.LPWSTR),ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
        description=None
    else:
        call=crypt.CryptProtectData
        call.argtypes=[ctypes.POINTER(Blob),wintypes.LPCWSTR,ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
        description='EVE Muhely token key'
    call.restype=wintypes.BOOL
    if not call(ctypes.byref(incoming),description,ctypes.byref(entropy),None,None,1,ctypes.byref(outgoing)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:return ctypes.string_at(outgoing.pbData,outgoing.cbData)
    finally:kernel.LocalFree(ctypes.cast(outgoing.pbData,wintypes.HLOCAL))


def vault_key(folder, generate, validate):
    folder=Path(folder);protected=folder/'vault.key.dpapi';legacy=folder/'vault.key'
    if protected.exists():return transform(protected.read_bytes(),decrypt=True)
    if legacy.exists():
        key=legacy.read_bytes();validate(key)
    else:
        if (folder/'characters.enc').exists():raise OSError('Missing Windows vault key; saved logins were preserved.')
        key=generate()
    encrypted=transform(key)
    if transform(encrypted,decrypt=True)!=key:raise OSError('Windows key protection failed.')
    try:
        with protected.open('xb') as output:output.write(encrypted)
    except FileExistsError:return transform(protected.read_bytes(),decrypt=True)
    if legacy.exists():legacy.unlink()
    return key
