import os
import struct

import cffi

from six import int2byte
from six.moves import xrange, zip


ffi = cffi.FFI()
ffi.cdef("""
int memcmp(const void *, const void *, size_t);
void *memchr(const void *, int, size_t);

ssize_t read(int, void *, size_t);
ssize_t write(int, const void *, size_t);

ssize_t writev(int, const struct iovec *, int);

struct iovec {
    char *iov_base;
    size_t iov_len;
};
""")
lib = ffi.verify("""
#include <string.h>
#include <sys/uio.h>
#include <unistd.h>
""")

BLOOM_WIDTH = struct.calcsize("l") * 8


def maybe_int2byte(c):
    return int2byte(c) if isinstance(c, int) else c


def maybe_bytes2int(c):
    return ord(c) if isinstance(c, bytes) else c


class Buffer(object):
    def __init__(self, data, length, keepalive=None):
        super(Buffer, self).__init__()
        self._data = data
        self._length = length
        self._keepalive = keepalive

    @classmethod
    def from_bytes(cls, bytes):
        return cls(ffi.new("uint8_t[]", bytes), len(bytes))

    @classmethod
    def from_fd_read(cls, fd, length):
        data = ffi.new("uint8_t[]", length)
        res = lib.read(fd, data, length)
        if res == -1:
            raise OSError(ffi.errno, os.strerror(ffi.errno))
        elif res == 0:
            raise EOFError
        return cls(data, res)

    def __len__(self):
        return self._length

    def __eq__(self, other):
        if isinstance(other, bytes):
            if len(self) != len(other):
                return False
            for c1, c2 in zip(self, other):
                if c1 != maybe_int2byte(c2):
                    return False
            return True
        elif isinstance(other, Buffer):
            if len(self) != len(other):
                return False
            return lib.memcmp(self._data, other._data, len(self)) == 0
        else:
            return NotImplemented

    def __ne__(self, other):
        return not (self == other)

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            (start, stop, step) = idx.indices(len(self))
            if step != 1:
                raise ValueError("Can't slice with non-1 step.")
            if start > stop:
                raise ValueError("Can't slice backwards.")
            return type(self)(self._data + start, stop - start, self._keepalive or self)
        else:
            if idx < 0:
                idx += len(self)
            if not (0 <= idx < len(self)):
                raise IndexError(idx)
            return int2byte(self._data[idx])

    def find(self, sub, start=0, end=None):
        end = end or self._length
        if start < 0:
            start = 0
        if end > len(self):
            end = len(self)
        if end - start < 0:
            return -1

        if len(sub) == 0:
            return start
        elif len(sub) == 1:
            pos = lib.memchr(self._data + start, ord(sub), end)
            if pos == ffi.NULL:
                return -1
            else:
                return ffi.cast("uint8_t *", pos) - self._data
        else:
            mask, skip = self._make_find_mask(sub)
            return self._multi_char_find(sub, start, end, mask, skip)

    def _multi_char_find(self, sub, start, end, mask, skip):
        i = start - 1
        w = (end - start) - len(sub)
        while i + 1 <= start + w:
            i += 1
            if self[i + len(sub) - 1] == maybe_int2byte(sub[-1]):
                for j in xrange(len(sub) - 1):
                    if self[i + j] != maybe_int2byte(sub[j]):
                        break
                else:
                    return i
                if i + len(sub) < len(self) and not self._bloom(mask, self[i + len(sub)]):
                    i += len(sub)
                else:
                    i += skip
            else:
                if i + len(sub) < len(self) and not self._bloom(mask, self[i + len(sub)]):
                    i += len(sub)
        return -1

    def _make_find_mask(self, sub):
        mlast = len(sub) - 1
        mask = 0
        skip = mlast - 1
        for i in xrange(mlast):
            mask = self._bloom_add(mask, sub[i])
            if sub[i] == sub[mlast]:
                skip = mlast - i - 1
        mask = self._bloom_add(mask, sub[mlast])
        return mask, skip

    def _bloom_add(self, mask, c):
        return mask | (1 << (maybe_bytes2int(c) & (BLOOM_WIDTH - 1)))

    def _bloom(self, mask, c):
        return mask & (1 << (maybe_bytes2int(c) & (BLOOM_WIDTH - 1)))

    def split(self, by, maxsplit=-1):
        if len(by) == 0:
            raise ValueError("empty separator")
        elif len(by) == 1:
            start = 0
            while maxsplit != 0:
                pos = lib.memchr(self._data + start, ord(by), len(self) - start)
                if pos == ffi.NULL:
                    break
                next = ffi.cast("uint8_t *", pos) - self._data
                yield self[start:next]
                start = next + 1
                maxsplit -= 1
            yield self[start:]
        else:
            start = 0
            mask, skip = self._make_find_mask(by)
            while maxsplit != 0:
                next = self._multi_char_find(by, start, len(self), mask, skip)
                if next < 0:
                    break
                yield self[start:next]
                start = next + len(by)
                maxsplit -= 1
            yield self[start:]

    def write_to_fd(self, fd):
        res = lib.write(fd, self._data, len(self))
        if res == -1:
            raise OSError(ffi.errno, os.strerror(ffi.errno))
        return res


class BufferGroup(object):
    def __init__(self, buffers):
        super(BufferGroup, self).__init__()
        self._buffers = buffers

    def __getitem__(self, idx):
        orig_idx = idx
        if idx < 0:
            for b in reversed(self._buffers):
                if -idx < len(b):
                    return b[idx]
                idx += len(b)
        else:
            for b in self._buffers:
                if idx < len(b):
                    return b[idx]
                idx -= len(b)
        raise IndexError(orig_idx)

    def write_to_fd(self, fd):
        iovecs = ffi.new("struct iovec[]", len(self._buffers))
        for i, buf in enumerate(self._buffers):
            iovecs[i].iov_len = len(buf)
            iovecs[i].iov_base = buf._data
        res = lib.writev(fd, iovecs, len(self._buffers))
        if res == -1:
            raise OSError(ffi.errno, os.strerror(ffi.errno))
        return res
