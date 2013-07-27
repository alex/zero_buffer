import os

import cffi


ffi = cffi.FFI()
ffi.cdef("""
ssize_t read(int, void *, size_t);
""")
lib = ffi.verify("""
#include <sys/types.h>
#include <sys/uio.h>
#include <unistd.h>
""")


class BufferFull(Exception):
    pass


class BufferPool(object):
    def __init__(self, capacity, buffer_size):
        self.capacity = capacity
        self.buffer_size = buffer_size
        self._freelist = [self._create_buffer() for _ in xrange(capacity)]
        self._num_free = capacity

    def _create_buffer(self):
        return Buffer(self, self.buffer_size)

    def buffer(self):
        if self._num_free:
            self._num_free -= 1
            buf = self._freelist[self._num_free]
            self._freelist[self._num_free] = None
            return buf
        else:
            return self._create_buffer()

    def return_buffer(self, buffer):
        if self._num_free != self.capacity:
            self._freelist[self._num_free] = buffer
            self._num_free += 1


class Buffer(object):
    def __init__(self, pool, capacity):
        self.pool = pool
        self._data = ffi.new("uint8_t[]", capacity)
        self._writepos = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.release()

    @property
    def writepos(self):
        return self._writepos

    @property
    def capacity(self):
        return len(self._data)

    @property
    def free(self):
        return len(self._data) - self.writepos

    def release(self):
        self._writepos = 0
        self.pool.return_buffer(self)

    def read_from(self, fd):
        if not self.free:
            raise BufferFull
        res = lib.read(fd, self._data + self.writepos, len(self._data) - self.writepos)
        if res == -1:
            raise OSError(ffi.errno, os.strerror(ffi.errno))
        elif res == 0:
            raise EOFError
        self._writepos += res
        return res

    def add_bytes(self, b):
        if not self.free:
            raise BufferFull
        bytes_written = min(len(b), self.free)
        for i in xrange(bytes_written):
            self._data[self.writepos] = ord(b[i])
            self._writepos += 1
        return bytes_written

    def view(self, start, stop):
        return BufferView(self, start, stop)


class BufferView(object):
    def __init__(self, buf, start, stop):
        self._keepalive = buf
        self._data = buf._data + start
        self._length = stop - start
