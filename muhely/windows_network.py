"""Read the local Windows IPv4 listener table without making a TCP connection."""
import ctypes
import socket
import struct


def listener_present(port):
    # GetTcpTable / MIB_TCPTABLE: DWORD count followed by five-DWORD rows.
    # Inspect LISTEN only; established and TIME_WAIT sockets are not servers.
    query=ctypes.WinDLL('iphlpapi').GetTcpTable
    query.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32),ctypes.c_int]
    query.restype=ctypes.c_uint32
    size=ctypes.c_uint32(0)
    status=query(None,ctypes.byref(size),False)
    if status not in {0,122}:raise OSError(status,'GetTcpTable failed')
    for _ in range(4):
        if not 4<=size.value<=16*1024*1024:raise OSError('Invalid TCP table size')
        buffer=ctypes.create_string_buffer(size.value)
        status=query(buffer,ctypes.byref(size),False)
        if status==122:continue  # Other processes may open connections meanwhile.
        if status:raise OSError(status,'GetTcpTable failed')
        return table_has_listener(buffer.raw,port)
    raise OSError('TCP table changed repeatedly')


def table_has_listener(data,port):
    if len(data)<4:raise OSError('Incomplete TCP table')
    count=struct.unpack_from('<I',data)[0]
    if count>(len(data)-4)//20:raise OSError('Incomplete TCP table rows')
    for offset in range(4,4+count*20,20):
        state,address,local_port,_,_=struct.unpack_from('<5I',data,offset)
        if state==2 and address in {0,0x0100007f} and socket.ntohs(local_port&0xffff)==port:return True
    return False
