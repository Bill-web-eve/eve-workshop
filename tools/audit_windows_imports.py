"""Check PE import names against bundled binaries and Windows system libraries."""
import json
from pathlib import Path
import struct
import sys

SYSTEM_DLLS=set('advapi32.dll bcrypt.dll bcryptprimitives.dll crypt32.dll iphlpapi.dll kernel32.dll kernelbase.dll ntdll.dll ole32.dll oleaut32.dll propsys.dll rpcrt4.dll shell32.dll user32.dll version.dll winmm.dll ws2_32.dll ucrtbase.dll msvcrt.dll mscoree.dll shlwapi.dll gdi32.dll comdlg32.dll comctl32.dll'.split())


def imports(path):
    data=Path(path).read_bytes();pe=struct.unpack_from('<I',data,0x3c)[0];optional=pe+24
    sections=optional+struct.unpack_from('<H',data,pe+20)[0];count=struct.unpack_from('<H',data,pe+6)[0]
    def offset(rva):
        if rva<struct.unpack_from('<I',data,optional+60)[0]:return rva
        for i in range(count):
            size,va,rawsize,raw=struct.unpack_from('<IIII',data,sections+i*40+8)
            if va<=rva<va+max(size,rawsize):return raw+rva-va
        raise ValueError('Invalid PE import RVA.')
    magic=struct.unpack_from('<H',data,optional)[0]
    directory=112 if magic==0x20b else 96 if magic==0x10b else None
    if directory is None:raise ValueError('Invalid PE optional header')
    rva,size=struct.unpack_from('<II',data,optional+directory+8)
    if not rva:return []
    cursor=offset(rva);result=[]
    for _ in range(4096):
        record=struct.unpack_from('<IIIII',data,cursor)
        if not any(record):return result
        name=offset(record[3]);result.append(data[name:data.index(b'\0',name)].decode('ascii').lower());cursor+=20
    raise ValueError('Invalid PE import table.')


def audit(root):
    root=Path(root);files=[p for p in root.rglob('*') if p.suffix.lower() in ['.exe','.dll','.pyd']]
    shipped={p.name.lower() for p in files};external=set();records={}
    if not files:raise ValueError('No Windows binaries.')
    for path in files:
        names=imports(path);records[path.relative_to(root).as_posix()]=names;external.update(set(names)-shipped)
    missing={n for n in external if n not in SYSTEM_DLLS and not n.startswith(('api-ms-win-','ext-ms-win-'))}
    if missing:raise ValueError('Unbundled DLL dependencies: '+', '.join(sorted(missing)))
    return {'binaries':len(files),'system_dlls':sorted(external),'imports':records}


if __name__=='__main__':print(json.dumps(audit(sys.argv[1]),indent=2))
