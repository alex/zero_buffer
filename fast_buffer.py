import os
from itertools import izip

import cffi


ffi = cffi.FFI()
ffi.cdef("""
ssize_t read(int, void *, size_t);

int memcmp(const void *, const void *, size_t);
void *memchr(const void *, int, size_t);
""")
lib = ffi.verify("""
#include <sys/types.h>
#include <sys/uio.h>
#include <unistd.h>
""")

BLOOM_WIDTH = ffi.sizeof("long") * 8


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
        if stop < start or not (0 <= start <= self.writepos) or stop > self.writepos:
            raise ValueError
        return BufferView(self, start, stop)


class BufferView(object):
    def __init__(self, buf, start, stop):
        self._keepalive = buf
        self._data = buf._data + start
        self._length = stop - start

    def __len__(self):
        return self._length

    def __eq__(self, other):
        if len(self) != len(other):
            return False
        if isinstance(other, BufferView):
            return lib.memcmp(self._data, other._data, len(self)) == 0
        elif isinstance(other, bytes):
            for i in xrange(len(self)):
                if self._data[i] != ord(other[i]):
                    return False
            return True
        else:
            return NotImplemented

    def __ne__(self, other):
        return not (self == other)

    def find(self, needle, start=0, stop=None):
        stop = stop or len(self)
        if start < 0:
            start = 0
        if stop > len(self):
            stop = len(self)
        if stop - start < 0:
            return -1

        if len(needle) == 0:
            return start
        elif len(needle) == 1:
            res = lib.memchr(self._data + start, ord(needle), stop - start)
            if res == ffi.NULL:
                return -1
            else:
                return ffi.cast("uint8_t *", res) - self._data
        else:
            mask, skip = self._make_find_mask(needle)
            return self._multi_char_find(needle, start, stop, mask, skip)

    def _bloom_add(self, mask, c):
        return mask | (1 << (c & (BLOOM_WIDTH - 1)))

    def _bloom(self, mask, c):
        return mask & (1 << (c & (BLOOM_WIDTH - 1)))

    def _make_find_mask(self, needle):
        mlast = len(needle) - 1
        mask = 0
        skip = mlast - 1
        for i in xrange(mlast):
            mask = self._bloom_add(mask, ord(needle[i]))
            if needle[i] == needle[mlast]:
                skip = mlast - i - 1
        mask = self._bloom_add(mask, ord(needle[mlast]))
        return mask, skip

    def _multi_char_find(self, needle, start, stop, mask, skip):
        i = start - 1
        w = (stop - start) - len(needle)
        while i + 1 <= start + w:
            i += 1
            if self._data[i + len(needle) - 1] == ord(needle[-1]):
                for j in xrange(len(needle) - 1):
                    if self._data[i + j] != ord(needle[j]):
                        break
                else:
                    return i
                if i + len(needle) < len(self) and not self._bloom(mask, self._data[i + len(needle)]):
                    i += len(needle)
                else:
                    i += skip
            else:
                if i + len(needle) < len(self) and not self._bloom(mask, self._data[i + len(needle)]):
                    i += len(needle)
        return -1
