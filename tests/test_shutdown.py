import socket
import tempfile
import threading
import subprocess
import unittest
from unittest.mock import patch
from pathlib import Path

from desktop import stop_backend
from muhely.server import App,Server


class ShutdownTests(unittest.TestCase):
    def test_separate_production_backend_starts_and_stops(self):
        from muhely.windows_window import ensure_backend
        with tempfile.TemporaryDirectory() as folder:
            with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
            processes=[];popen=subprocess.Popen
            def spawn(*args,**kwargs):
                process=popen(*args,**kwargs);processes.append(process);return process
            with patch('muhely.windows_window.subprocess.Popen',side_effect=spawn):origin=ensure_backend(port,folder)
            try:self.assertTrue(stop_backend(origin,timeout=10))
            finally:
                stop_backend(origin,timeout=1)
                for process in processes:process.wait(timeout=5)
            self.assertTrue(all(p.returncode==0 for p in processes))
            with self.assertRaises(ConnectionRefusedError):socket.create_connection(('127.0.0.1',port),timeout=.5)

    def test_native_quit_stops_monitoring_and_releases_port_without_external_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            app=App(folder,Path(__file__).resolve().parents[1]/'data/catalog.sqlite3',0)
            server=Server(app);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            app.fleet.start()
            try:
                self.assertTrue(stop_backend(app.origin,timeout=10))
                thread.join(timeout=2);self.assertFalse(thread.is_alive())
                self.assertTrue(app.fleet.stop_event.is_set());self.assertTrue(app.intel.stop_event.is_set())
                self.assertTrue(app.asset_locations.closed)
                with self.assertRaises(ConnectionRefusedError):socket.create_connection(('127.0.0.1',app.port),timeout=.5)
                self.assertTrue(stop_backend(app.origin,timeout=.1))
            finally:server.shutdown();server.server_close();thread.join(timeout=2)


if __name__=='__main__':unittest.main()
