"""Exercise the exact pinned embedded Windows runtime on an isolated CI machine."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from tools.build_windows_release import stage,fetch,extract,stage_source_package,trim_other_architectures



def run_check(command,timeout):
    try:
        result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        output=(result.stdout or '')+(result.stderr or '')
        print(output,flush=True)
        if result.returncode:
            detail=output[-6000:] or 'Windows check exited with code '+str(result.returncode)
            escaped=detail.replace('%','%25').replace('\r','%0D').replace('\n','%0A')
            print('::error title=Native Windows check::'+escaped,flush=True)
            raise SystemExit(result.returncode)
    except subprocess.TimeoutExpired as error:
        raw=error.output or b''
        if isinstance(raw,bytes):raw=raw.decode('utf-8',errors='replace')
        diagnostic=error.stderr or b''
        if isinstance(diagnostic,bytes):diagnostic=diagnostic.decode('utf-8',errors='replace')
        raw+='\n'+diagnostic
        detail=('Native Windows check timed out. '+raw[-5000:]).replace('%','%25').replace('\r','%0D').replace('\n','%0A')
        print('::error title=Native Windows check::'+detail,flush=True)
        raise SystemExit(1)


def main():
    if sys.platform!='win32':raise RuntimeError('Windows CI runner required')
    source=Path(__file__).resolve().parents[1]
    lock=json.loads((source/'tools/windows-runtime-lock.json').read_text())
    with tempfile.TemporaryDirectory(prefix='eve-webview2-runtime-') as folder:
        root=Path(folder);downloads=root/'downloads';downloads.mkdir()
        package=root/'EVE Muhely';stage(package,{'client_id':'synthetic-ci-client'})
        runtime=package/'runtime';runtime.mkdir();extract(fetch(lock['python'],downloads),runtime)
        packages=runtime/'Lib/site-packages';packages.mkdir(parents=True)
        for wheel in lock['wheels']:extract(fetch(wheel,downloads),packages)
        for record in lock.get('sources',[]):stage_source_package(record,downloads,packages)
        trim_other_architectures(packages)
        (runtime/'python313._pth').write_text('python313.zip\n.\nLib\\site-packages\n..\\app\n',encoding='ascii')
        run_check([str(runtime/'python.exe'),'-I','-X','utf8',str(package/'app/windows_smoke_test.py')],90)
        run_check([str(runtime/'python.exe'),'-I','-X','utf8',str(package/'app/windows_window_smoke.py')],120)

if __name__=='__main__':main()
