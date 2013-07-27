import errno

import pytest

from fast_buffer import BufferPool, Buffer, BufferView, BufferFull


class TestBufferPool(object):
    def test_create(self):
        p = BufferPool(capacity=5, buffer_size=1024)
        assert p.capacity == 5
        assert p.buffer_size == 1024

    def test_buffer(self):
        p = BufferPool(capacity=5, buffer_size=16)
        b = p.buffer()
        assert isinstance(b, Buffer)
        assert b.capacity == 16

    def test_buffer_empty_freelist(self):
        p = BufferPool(capacity=1, buffer_size=16)
        p.buffer()
        p.buffer()

    def test_return_buffer_to_freelist(self):
        p = BufferPool(capacity=1, buffer_size=16)
        orig_buffer = p.buffer()
        orig_buffer.release()
        new_buffer = p.buffer()
        assert orig_buffer is new_buffer

    def test_return_buffer_with_context_manager(self):
        p = BufferPool(capacity=1, buffer_size=16)
        with p.buffer() as orig_buffer:
            assert isinstance(orig_buffer, Buffer)
        new_buffer = p.buffer()
        assert orig_buffer is new_buffer

    def test_return_used_buffer(self):
        p = BufferPool(capacity=1, buffer_size=16)
        with p.buffer() as buf:
            buf.add_bytes(b"abc")
        with p.buffer() as buf:
            assert buf.writepos == 0


class TestBuffer(object):
    def test_read_from(self, tmpdir):
        t = tmpdir.join("t.txt")
        t.write("abc123")
        p = BufferPool(capacity=1, buffer_size=16)
        with p.buffer() as buf:
            with t.open() as f:
                res = buf.read_from(f.fileno())
                assert res == 6
            assert buf.writepos == 6

    def test_read_from_error(self):
        p = BufferPool(capacity=1, buffer_size=16)
        with p.buffer() as buf:
            with pytest.raises(OSError) as exc_info:
                buf.read_from(-1)
            assert exc_info.value.errno == errno.EBADF

    def test_read_from_eof(self, tmpdir):
        t = tmpdir.join("t.txt")
        t.write("")
        p = BufferPool(capacity=1, buffer_size=16)
        with p.buffer() as buf:
            with t.open() as f:
                with pytest.raises(EOFError):
                    buf.read_from(f.fileno())

    def test_read_from_end_of_buffer(self, tmpdir):
        t = tmpdir.join("t.txt")
        t.write("a" * 16)
        p = BufferPool(capacity=1, buffer_size=16)
        with p.buffer() as buf:
            with t.open() as f:
                buf.read_from(f.fileno())
            with t.open() as f:
                with pytest.raises(BufferFull):
                    buf.read_from(f.fileno())

    def test_free(self, tmpdir):
        p = BufferPool(capacity=1, buffer_size=16)
        t = tmpdir.join("t.txt")
        t.write("abc")
        with p.buffer() as buf:
            assert buf.free == 16
            with t.open() as f:
                buf.read_from(f.fileno())
                assert buf.free == 13

    def test_add_bytes(self):
        p = BufferPool(capacity=1, buffer_size=16)
        with p.buffer() as buf:
            res = buf.add_bytes(b"abc")
            assert res == 3
            assert buf.writepos == 3

    def test_add_bytes_longer_than_buffer(self):
        p = BufferPool(capacity=1, buffer_size=16)
        with p.buffer() as buf:
            res = buf.add_bytes(b"a" * 20)
            assert res == 16
            assert buf.writepos == 16

    def test_view(self):
        p = BufferPool(capacity=1, buffer_size=16)
        with p.buffer() as buf:
            buf.add_bytes(b"abc")
            view = buf.view(0, 3)
            assert isinstance(view, BufferView)

    def test_writepos_assign(self):
        p = BufferPool(capacity=1, buffer_size=16)
        with p.buffer() as buf:
            with pytest.raises(AttributeError):
                buf.writepos = 12
