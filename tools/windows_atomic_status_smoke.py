"""Verify JSON replacement against a real Windows sharing lock, not a mock."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
from muhely.updates import atomic_json


def check():
    if sys.platform!='win32':raise RuntimeError('Windows is required')
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    kernel.CreateFileW.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
    with tempfile.TemporaryDirectory(prefix='eve-status-sharing-') as folder:
        path=Path(folder)/'status.json';atomic_json(path,{'phase':'old'})
        # Grant read sharing, deliberately deny delete/replace until released.
        handle=kernel.CreateFileW(str(path),0x80000000,1,None,3,0x80,None)
        if handle in (None,ctypes.c_void_p(-1).value):raise ctypes.WinError(ctypes.get_last_error())
        errors=[];started=threading.Event()
        def write():
            started.set()
            try:atomic_json(path,{'phase':'installed'})
            except Exception as e:errors.append(e)
        worker=threading.Thread(target=write)
        try:
            worker.start();assert started.wait(2)
            time.sleep(.12)
            assert worker.is_alive(),'Status writer did not retry the held sharing lock: '+repr(errors)
            assert json.loads(path.read_text())=={'phase':'old'},'Original status was truncated'
        finally:kernel.CloseHandle(handle)
        worker.join(3);assert not worker.is_alive(),'Status retry did not finish'
        if errors:raise errors[0]
        assert json.loads(path.read_text())=={'phase':'installed'}
        assert not list(Path(folder).glob('*.tmp'))
    return {'real_windows_sharing_lock':True,'atomic_status_retry':True,'original_preserved':True,'cleanup':True}

if __name__=='__main__':print(json.dumps(check()),flush=True)
