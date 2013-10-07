import errno

import pytest

from zero_buffer import Buffer, BufferView, BufferCollator, BufferFull


@pytest.fixture
def buf():
    return Buffer.allocate(16)


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

    def test_capacity(self, buf):
        assert buf.capacity == 16
        buf.add_bytes(b"abc")
        assert buf.capacity == 16

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
    def test_bytes(self, buf):
        buf.add_bytes(b"abc")
        assert bytes(buf.view()) == b"abc"

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

    def test_contains(self, buf):
        buf.add_bytes(b"abc")
        view = buf.view()
        assert b"a" in view
        assert b"d" not in view

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

    def test_find_empty_bytes(self, buf):
        buf.add_bytes(b"abc")
        view = buf.view()
        assert view.find(b"") == 0
        assert view.find(b"", 2) == 2

    def test_find_bytes(self, buf):
        buf.add_bytes(b"abc123")
        view = buf.view()
        assert view.find(b"cc") == -1
        assert view.find(b"ab") == 0
        assert view.find(b"c1") == 2
        buf.add_bytes(b"aabbcc")
        view = buf.view()
        assert view.find(b"aa") == 6
        assert view.find(b"abb") == 7

    def test_index(self, buf):
        buf.add_bytes(b"abc123")
        view = buf.view()
        assert view.index(b"b") == 1
        with pytest.raises(ValueError):
            view.index(b"d")

    def test_rfind_empty(self, buf):
        view = buf.view()
        assert view.rfind(b"") == 0

    def test_rfind_char(self, buf):
        buf.add_bytes(b"abc123")
        view = buf.view()
        assert view.rfind(b"c") == 2
        assert view.rfind(b"3") == 5
        assert view.rfind(b"4") == -1
        assert view.rfind(b"3", -2) == 5
        assert view.rfind(b"2", 0, 10) == 4
        assert view.rfind(b"2", 10, 0) == -1

    def test_rfind_bytes(self, buf):
        buf.add_bytes(b"123abc123")
        view = buf.view()
        assert view.rfind(b"cc") == -1
        assert view.rfind(b"23") == 7
        assert view.rfind(b"124") == -1

    def test_rindex(self, buf):
        buf.add_bytes(b"abc")
        view = buf.view()
        assert view.rindex(b"c") == 2
        with pytest.raises(ValueError):
            view.rindex(b"d")

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
        assert view[0] == ord(b"a")
        assert view[-1] == ord(b"3")
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
        assert list(view.split(b"-", 1)) == [b"a", b"b-c"]

    def test_split_empty(self, buf):
        view = buf.view()
        with pytest.raises(ValueError):
            view.split(b"")

    def test_split_bytes(self, buf):
        buf.add_bytes(b"a::b::c")
        view = buf.view()
        assert list(view.split(b"::")) == [b"a", b"b", b"c"]

    def test_split_bytes_maxsplit(self, buf):
        buf.add_bytes(b"a::b::c")
        view = buf.view()
        assert list(view.split(b"::", 1)) == [b"a", b"b::c"]

    def test_splitlines(self):
        b = Buffer.allocate(32)
        b.add_bytes(b"abc\ndef\n\rghi")
        assert list(b.view().splitlines()) == [b"abc", b"def", b"", b"ghi"]

        b = Buffer.allocate(32)
        b.add_bytes(b"abc\ndef\r\nghi")
        assert list(b.view().splitlines()) == [b"abc", b"def", b"ghi"]

        b = Buffer.allocate(32)
        b.add_bytes(b"\nabc\ndef\r\nghi\n\r")
        assert list(b.view().splitlines(True)) == [
            b"\n", b"abc\n", b"def\r\n", b"ghi\n", b"\r"
        ]

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
        assert not view[:1].isspace()
        assert view[1:].isspace()
        assert not buf.view(0, 0).isspace()
        assert not buf.view(0, 2).isspace()

    def test_iteration(self, buf):
        buf.add_bytes(b"abc")
        view = buf.view()
        assert list(view) == [ord(b"a"), ord(b"b"), ord(b"c")]

    def test_isdigit(self, buf):
        buf.add_bytes(b"123abc")
        assert not buf.view().isdigit()
        assert buf.view(0, 3).isdigit()
        assert not buf.view(0, 0).isdigit()

    def test_isalpha(self, buf):
        buf.add_bytes(b"abc123")
        assert not buf.view().isalpha()
        assert buf.view(0, 3).isalpha()
        assert not buf.view(0, 0).isalpha()

    def test_add_contigious(self, buf):
        buf.add_bytes(b"abc123")
        assert (buf.view(0, 3) + buf.view(3, 6)) == buf.view()

    def test_add_discontigious(self, buf):
        buf.add_bytes(b"abc123")
        bg = buf.view(0, 2) + buf.view(3, 6)
        assert bg == b"ab123"

    def test_add_typeerror(self, buf):
        view = buf.view()
        with pytest.raises(TypeError):
            view + 3


class TestBufferCollator(object):
    def test_single_item(self, buf):
        view = buf.view()
        collator = BufferCollator()
        collator.append(view)
        assert collator.collapse() is view

    def test_collapse_clears(self, buf):
        buf.add_bytes(b"abc")
        view = buf.view()
        collator = BufferCollator()
        collator.append(view)
        collator.collapse()
        view = collator.collapse()
        assert len(view) == 0
