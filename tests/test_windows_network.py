import ctypes
import socket
import struct
import unittest
from unittest.mock import Mock,patch

from muhely.windows_network import listener_present,table_has_listener
import desktop


def table(*rows):
    return struct.pack('<I',len(rows))+b''.join(struct.pack('<5I',*row,0,0) for row in rows)


class WindowsListenerTests(unittest.TestCase):
    def test_only_listening_loopback_or_wildcard_port_counts(self):
        port=socket.htons(8765)
        self.assertTrue(table_has_listener(table((2,0x0100007f,port)),8765))
        self.assertTrue(table_has_listener(table((2,0,port|0xabcd0000)),8765))
        for row in [(11,0x0100007f,port),(5,0x0100007f,port),(2,0x0200007f,port),(2,0x0100007f,socket.htons(8766))]:
            self.assertFalse(table_has_listener(table(row),8765))

    def test_partial_tables_fail_instead_of_reporting_service_stopped(self):
        for raw in [b'',b'abc',struct.pack('<I',2)+b'\0'*20]:
            with self.assertRaises(OSError):table_has_listener(raw,8765)

    def test_native_table_can_grow_between_size_and_read(self):
        raw=table((2,0x0100007f,socket.htons(8765)))
        calls=[]
        def query(buffer,size,_ordered):
            calls.append(buffer is None)
            required=ctypes.cast(size,ctypes.POINTER(ctypes.c_uint32))
            required.contents.value=len(raw)
            if len(calls)<=2:return 122
            ctypes.memmove(buffer,raw,len(raw));return 0
        dll=Mock();dll.GetTcpTable=Mock(side_effect=query)
        with patch('ctypes.WinDLL',return_value=dll,create=True):self.assertTrue(listener_present(8765))
        self.assertEqual(calls,[True,False,False])

    def test_native_failure_is_not_a_closed_port(self):
        dll=Mock();dll.GetTcpTable.return_value=5
        with patch('ctypes.WinDLL',return_value=dll,create=True):
            with self.assertRaises(OSError):listener_present(8765)

    def test_already_stopped_windows_service_needs_no_http_or_connect_probe(self):
        with patch.object(desktop.sys,'platform','win32'),patch('muhely.windows_network.listener_present',return_value=False),patch('desktop.urllib.request.build_opener') as http,patch('socket.create_connection') as connect:
            self.assertTrue(desktop.stop_backend('http://127.0.0.1:8765'))
        http.assert_not_called();connect.assert_not_called()

    def test_shutdown_waits_for_listener_to_close_even_if_connections_time_out(self):
        import urllib.error
        opener=Mock();opener.open.side_effect=urllib.error.URLError(TimeoutError())
        with patch.object(desktop.sys,'platform','win32'),patch('muhely.windows_network.listener_present',side_effect=[True,True,False]),patch('desktop.urllib.request.build_opener',return_value=opener),patch('socket.create_connection') as connect,patch('desktop.time.sleep'):
            self.assertTrue(desktop.stop_backend('http://127.0.0.1:8765',timeout=1))
        connect.assert_not_called()

    def test_still_listening_service_is_not_reported_stopped(self):
        import urllib.error
        opener=Mock();opener.open.side_effect=urllib.error.URLError(TimeoutError())
        with patch.object(desktop.sys,'platform','win32'),patch('muhely.windows_network.listener_present',return_value=True),patch('desktop.urllib.request.build_opener',return_value=opener),patch('desktop.time.monotonic',side_effect=[0,0,2]),patch('desktop.time.sleep'),self.assertLogs('desktop',level='WARNING'):
            self.assertFalse(desktop.stop_backend('http://127.0.0.1:8765',timeout=1))

    def test_native_query_failure_falls_back_to_confirmed_connection_refusal(self):
        import urllib.error
        opener=Mock();opener.open.side_effect=urllib.error.URLError(TimeoutError())
        with patch.object(desktop.sys,'platform','win32'),patch('muhely.windows_network.listener_present',side_effect=OSError('unavailable')),patch('desktop.urllib.request.build_opener',return_value=opener),patch('socket.create_connection',side_effect=ConnectionRefusedError()):
            self.assertTrue(desktop.stop_backend('http://127.0.0.1:8765',timeout=1))


if __name__=='__main__':unittest.main()
