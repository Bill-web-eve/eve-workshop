"""Windowless Windows entry point with persistent startup diagnostics."""
from pathlib import Path
import sys
import traceback
from contextlib import redirect_stdout,redirect_stderr


def main():
    from muhely.store import default_data_dir
    folder=default_data_dir();folder.mkdir(parents=True,exist_ok=True)
    with (folder/'launcher.log').open('a',encoding='utf-8') as output,redirect_stdout(output),redirect_stderr(output):
        try:
            from desktop import main as launch
            launch()
        except Exception:
            traceback.print_exc();return 1
    return 0


if __name__=='__main__':sys.exit(main())
