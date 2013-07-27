import errno

import pytest

from fast_buffer import BufferPool, Buffer, BufferView, BufferFull


@pytest.fixture
def buf(request):
    return BufferPool(capacity=1, buffer_size=16).buffer()


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

    def test_return_buffer_freelist_full(self):
        p = BufferPool(capacity=1, buffer_size=16)
        buf1 = p.buffer()
        buf2 = p.buffer()
        buf1.release()
        buf2.release()

    def test_return_used_buffer(self):
        p = BufferPool(capacity=1, buffer_size=16)
        with p.buffer() as buf:
            buf.add_bytes(b"abc")
        with p.buffer() as buf:
            assert buf.writepos == 0


class TestBuffer(object):
    def test_read_from(self, buf, tmpdir):
        t = tmpdir.join("t.txt")
        t.write("abc123")
        with t.open() as f:
            res = buf.read_from(f.fileno())
            assert res == 6
        assert buf.writepos == 6

    def test_read_from_error(self, buf):
        with pytest.raises(OSError) as exc_info:
            buf.read_from(-1)
        assert exc_info.value.errno == errno.EBADF

    def test_read_from_eof(self, buf, tmpdir):
        t = tmpdir.join("t.txt")
        t.write("")
        with t.open() as f:
            with pytest.raises(EOFError):
                buf.read_from(f.fileno())

    def test_read_from_end_of_buffer(self, buf, tmpdir):
        t = tmpdir.join("t.txt")
        t.write("a" * 16)
        with t.open() as f:
            buf.read_from(f.fileno())
        with t.open() as f:
            with pytest.raises(BufferFull):
                buf.read_from(f.fileno())

    def test_free(self, buf, tmpdir):
        t = tmpdir.join("t.txt")
        t.write("abc")
        assert buf.free == 16
        with t.open() as f:
            buf.read_from(f.fileno())
            assert buf.free == 13

    def test_add_bytes(self, buf):
        res = buf.add_bytes(b"abc")
        assert res == 3
        assert buf.writepos == 3

    def test_add_bytes_longer_than_buffer(self, buf):
        res = buf.add_bytes(b"a" * 20)
        assert res == 16
        assert buf.writepos == 16

    def test_add_bytes_buffer_full(self, buf):
        buf.add_bytes(b"a" * 16)
        with pytest.raises(BufferFull):
            buf.add_bytes(b"abc")

    def test_view(self, buf):
        buf.add_bytes(b"abc")
        view = buf.view(0, 3)
        assert isinstance(view, BufferView)
        view = buf.view()
        assert isinstance(view, BufferView)

    @pytest.mark.parametrize(("start", "stop"), [
        (3, 0),
        (10, 11),
        (0, 11),
        (-2, 0),
        (0, -2),
    ])
    def test_invalid_views(self, buf, start, stop):
        buf.add_bytes(b"abc123")
        with pytest.raises(ValueError):
            buf.view(start, stop)

    def test_writepos_assign(self, buf):
        with pytest.raises(AttributeError):
            buf.writepos = 12


class TestBufferView(object):
    def test_equality(self, buf):
        buf.add_bytes(b"abc")
        assert buf.view() == buf.view()
        assert buf.view() != buf.view(0, 2)
        assert not (buf.view() == buf.view(0, 2))
        assert not (buf.view(0, 2) == buf.view(1, 3))
        assert not (buf.view(0, 2) != buf.view(0, 2))

    def test_equality_bytes(self, buf):
        buf.add_bytes(b"abc")
        assert buf.view() == b"abc"
        assert buf.view() != b"abd"
        assert not (buf.view() != b"abc")
        assert not (buf.view() == b"abd")
        assert buf.view() != b"ab"
        assert not (buf.view() == b"ab")

    def test_equality_other(self, buf):
        assert buf.view() != []

    def test_find_char(self, buf):
        buf.add_bytes(b"abc")
        view = buf.view()
        assert view.find(b"a") == 0
        assert view.find(b"c") == 2
        assert view.find(b"d") == -1

    def test_find_char_offsets(self, buf):
        buf.add_bytes(b"abcdefghijklm")
        view = buf.view()
        assert view.find(b"a", 1) == -1
        assert view.find(b"c", 2) == 2
        assert view.find(b"d", 2, 4) == 3
        assert view.find(b"e", 2, 3) == -1
        assert view.find(b"m", 0, 20) == 12
        assert view.find(b"a", -1) == 0
        assert view.find(b"a", 3, 2) == -1

    def test_find_empty_string(self, buf):
        buf.add_bytes(b"abc")
        view = buf.view()
        assert view.find(b"") == 0
        assert view.find(b"", 2) == 2

    def test_find_str(self, buf):
        buf.add_bytes(b"abc123")
        view = buf.view()
        assert view.find(b"cc") == -1
        assert view.find(b"ab") == 0
        assert view.find(b"c1") == 2
        buf.add_bytes("aabbcc")
        view = buf.view()
        assert view.find(b"aa") == 6
        assert view.find(b"abb") == 7

    def test_subscript_slice(self, buf):
        buf.add_bytes(b"abc123")
        view = buf.view()
        assert view[:3] == b"abc"
        assert view[3:] == b"123"
        assert view[2:3] == b"c"
        with pytest.raises(ValueError):
            view[2:2:2]
        with pytest.raises(ValueError):
            view[3:2]

    def test_subscript(self, buf):
        buf.add_bytes(b"abc123")
        view = buf.view()
        assert view[0] == b"a"
        assert view[-1] == b"3"
        with pytest.raises(IndexError):
            view[7]
        with pytest.raises(IndexError):
            view[-7]

    def test_split_char(self, buf):
        buf.add_bytes(b"a-b-c")
        view = buf.view()
        assert list(view.split(b"-")) == [b"a", b"b", b"c"]

    def test_split_char_maxsplit(self, buf):
        buf.add_bytes(b"a-b-c")
        view = buf.view()
        assert list(view.split(b"-", 1)) == [b"a", "b-c"]

    def test_split_empty(self, buf):
        view = buf.view()
        with pytest.raises(ValueError):
            view.split(b"")

    def test_split_str(self, buf):
        buf.add_bytes(b"a::b::c")
        view = buf.view()
        assert list(view.split(b"::")) == [b"a", b"b", b"c"]

    def test_split_str_maxsplit(self, buf):
        buf.add_bytes(b"a::b::c")
        view = buf.view()
        assert list(view.split(b"::", 1)) == [b"a", b"b::c"]

    def test_strip_default_chars(self, buf):
        buf.add_bytes(b" \t\r\n\f\vabc\t\r\n\f\v ")
        view = buf.view()
        assert view.strip() == b"abc"

    def test_strip(self, buf):
        buf.add_bytes(b"abc123")
        view = buf.view()
        assert view.strip(b"ab3") == b"c12"

    def test_rstrip_default_chars(self, buf):
        buf.add_bytes(b" \t\r\n\f\vabc\t\r\n\f\v ")
        view = buf.view()
        assert view.rstrip() == b" \t\r\n\f\vabc"

    def test_lstrip_default_chars(self, buf):
        buf.add_bytes(b" \t\r\n\f\vabc\t\r\n\f\v ")
        view = buf.view()
        assert view.lstrip() == b"abc\t\r\n\f\v "

    def test_lstrip(self, buf):
        buf.add_bytes(b"abc123")
        view = buf.view()
        assert view.lstrip(b"ab3") == b"c123"

    def test_rstrip(self, buf):
        buf.add_bytes(b"abc123")
        view = buf.view()
        assert view.rstrip(b"ab3") == b"abc12"

    def test_isspace(self, buf):
        buf.add_bytes(b"a\t\r\n\f\v ")
        view = buf.view()
        assert not view[0].isspace()
        assert view[1:].isspace()
        assert not buf.view(0, 0).isspace()
        assert not buf.view(0, 2).isspace()

    def test_iteration(self, buf):
        buf.add_bytes(b"abc")
        view = buf.view()
        assert list(view) == [b"a", b"b", b"c"]

    def test_isdigit(self, buf):
        buf.add_bytes(b"123abc")
        assert not buf.view().isdigit()
        assert buf.view(0, 3).isdigit()
        assert not buf.view(0, 0).isdigit()
