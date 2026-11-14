"""Original read-only Sony PTP3 capability probe; run on the idle Pi over SSH.

Based on the owner's Sony Camera Remote Command 2.02 reference, pp. 43-49,
115-120. No third-party camera implementation used. No shutter or focus writes.
"""
import ctypes as C
import json
import struct
import time


class USB:
    def __init__(self):
        self.lib = C.CDLL('libusb-1.0.so.0')
        self.lib.libusb_init.argtypes = [C.POINTER(C.c_void_p)]
        self.lib.libusb_open_device_with_vid_pid.argtypes = [C.c_void_p,C.c_uint16,C.c_uint16]
        self.lib.libusb_open_device_with_vid_pid.restype = C.c_void_p
        self.lib.libusb_claim_interface.argtypes = [C.c_void_p,C.c_int]
        self.lib.libusb_release_interface.argtypes = [C.c_void_p,C.c_int]
        self.lib.libusb_close.argtypes = [C.c_void_p]
        self.lib.libusb_exit.argtypes = [C.c_void_p]
        self.lib.libusb_bulk_transfer.argtypes = [C.c_void_p,C.c_ubyte,C.c_void_p,C.c_int,C.POINTER(C.c_int),C.c_uint]
        self.context = C.c_void_p()
        assert self.lib.libusb_init(C.byref(self.context)) == 0
        self.handle = self.lib.libusb_open_device_with_vid_pid(self.context,0x054c,0x0e88)
        assert self.handle, 'A7CR not available'
        assert self.lib.libusb_claim_interface(self.handle,0) == 0,'USB interface busy'
        self.tx = 0
        self.pending = b''

    def transfer(self,ep,data=None):
        buf = C.create_string_buffer(data) if data is not None else C.create_string_buffer(1024*1024)
        size = len(data) if data is not None else len(buf)
        got = C.c_int()
        result = self.lib.libusb_bulk_transfer(self.handle,ep,buf,size,C.byref(got),5000)
        assert result == 0, ('USB error',result,got.value)
        if data is not None: assert got.value == len(data)
        return buf.raw[:got.value]

    def container(self):
        while len(self.pending)<12: self.pending += self.transfer(0x81)
        length,kind,code,tx = struct.unpack_from('<IHHI',self.pending)
        assert 12<=length<=32*1024*1024,(length,kind,code,tx)
        while len(self.pending)<length: self.pending += self.transfer(0x81)
        body,self.pending = self.pending[12:length],self.pending[length:]
        return kind,code,tx,body

    def command(self,op,args=(),data=None):
        tx=self.tx;self.tx+=1
        payload=struct.pack('<'+'I'*len(args),*args)
        self.transfer(2,struct.pack('<IHHI',12+len(payload),1,op,tx)+payload)
        if data is not None: self.transfer(2,struct.pack('<IHHI',12+len(data),2,op,tx)+data)
        body=b''
        while True:
            kind,code,received,chunk=self.container()
            assert received==tx,(received,tx)
            if kind==2:
                assert code==op
                body+=chunk
            else:
                assert kind==3 and code==0x2001,('PTP response',hex(op),hex(code))
                return body

    def close(self):
        try: self.command(0x1003)
        finally:
            self.lib.libusb_release_interface(self.handle,0)
            self.lib.libusb_close(self.handle)
            self.lib.libusb_exit(self.context)


class Reader:
    def __init__(self,b): self.b=b;self.i=0
    def n(self,n,signed=False):
        assert self.i+n<=len(self.b)
        v=int.from_bytes(self.b[self.i:self.i+n],'little',signed=signed);self.i+=n;return v
    def value(self,t):
        if t==0xffff:
            n=self.n(1)*2;s=self.b[self.i:self.i+n].decode('utf-16-le').rstrip('\0');self.i+=n;return s
        if t&0x4000:
            count=self.n(4);assert count<=100000;return [self.value(t&~0x4000) for _ in range(count)]
        assert 1<=t<=10,('type',hex(t),self.i)
        return self.n(1<<((t-1)//2),t%2==1)


def properties(b):
    r=Reader(b);count=r.n(8);assert count<=4096;out={}
    for _ in range(count):
        code,t,g,e=r.n(2),r.n(2),r.n(1),r.n(1)
        default,current=r.value(t),r.value(t);form=r.n(1)
        p={'type':t,'set':g,'enabled':e,'value':current,'form':form}
        if form==1:p['range']=[r.value(t) for _ in range(3)]
        elif form==2:
            p['allowed']=[r.value(t) for _ in range(r.n(2))]
            p['read_values']=[r.value(t) for _ in range(r.n(2))]
        else:assert form==0,(hex(code),form,r.i)
        out[f'{code:04x}']=p
    assert r.i==len(b),(r.i,len(b))
    return out


def main():
    u=USB()
    try:
        u.command(0x1002,[1])
        for phase in (1,2):u.command(0x9201,[phase,0,0])
        ext=u.command(0x9202,[0x12c,1]);assert ext
        u.command(0x9201,[3,0,0]);time.sleep(.5)
        p=properties(u.command(0x9209,[0,1]))
        print(json.dumps({'protocol':ext.hex(),'properties':p}))
    finally:u.close()


if __name__=='__main__': main()
