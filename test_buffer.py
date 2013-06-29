import errno

import pytest

from buffer import Buffer


class TestBuffer(object):
    def test_from_bytes(self):
        buf = Buffer.from_bytes(b"abc... easy as 123...")
        assert buf is not None

    def test_from_fd_read(self, tmpdir):
        t = tmpdir.join("t.txt")
        t.write(b"""some text""")
        with t.open() as f:
            buf = Buffer.from_fd_read(f.fileno(), 9)
        # Technically no guarantee this is correct...
        assert len(buf) == 9

    def test_from_fd_read_bad_fd(self):
        with pytest.raises(OSError) as exc_info:
            Buffer.from_fd_read(-1, 10)
        assert exc_info.value.errno == errno.EBADF

    def test_from_fd_read_eof(self, tmpdir):
        t = tmpdir.join("t.txt")
        t.write(b"")
        with t.open() as f:
            with pytest.raises(EOFError):
                Buffer.from_fd_read(f.fileno(), 10)

    def test_from_fd_read_value_greater_than_127(self, tmpdir):
        t = tmpdir.join("t.txt")
        t.write("""\xFF""", "wb")
        with t.open() as f:
            buf = Buffer.from_fd_read(f.fileno(), 1)
        assert buf[0] == "\xFF"

    def test_len(self):
        buf = Buffer.from_bytes(b"abc... easy as 123...")
        assert len(buf) == 21

    def test_eq_bytes(self):
        buf = Buffer.from_bytes(b"abc")
        assert buf == b"abc"
        assert not (buf == b"abd")
        assert buf != b"ab"
        assert not (buf != b"abc")

    def test_eq_buffer(self):
        buf1 = Buffer.from_bytes(b"abc")
        buf2 = Buffer.from_bytes(b"abc")
        buf3 = Buffer.from_bytes(b"ad")
        buf4 = Buffer.from_bytes(b"abd")

        assert buf1 == buf1
        assert buf1 == buf2
        assert buf1 != buf3
        assert buf1 != buf4

    def test_eq_random(self):
        buf = Buffer.from_bytes(b"")
        assert buf != 3

    def test_getitem(self):
        buf = Buffer.from_bytes(b"abc...")
        assert buf[0] == b"a"
        assert buf[3] == "."
        assert buf[-1] == b"."
        assert buf[-4] == b"c"
        with pytest.raises(IndexError):
            buf[10]
        with pytest.raises(IndexError):
            buf[-10]

    def test_getitem_slice(self):
        buf = Buffer.from_bytes(b"abc...")
        assert buf[:3] == b"abc"

        with pytest.raises(ValueError):
            buf[::-1]

    def test_find_empty_string(self):
        buf = Buffer.from_bytes(b"abc")
        assert buf.find(b"") == 0
        assert buf.find(b"", 1) == 1
        assert buf.find(b"", 4) == -1

    def test_find_char(self):
        buf = Buffer.from_bytes(b"abc...")
        assert buf.find(b"a") == 0
        assert buf.find(b".") == 3
        assert buf.find(b"d") == -1
        assert buf.find(b".", 5) == 5
        assert buf.find(b"a", 2) == -1
        assert buf.find(b".", 0, 2) == -1
        assert buf.find(b".", -1, 10) == 3

    def test_find_multichar(self):
        buf = Buffer.from_bytes(b"abc...")
        assert buf.find("bc") == 1
        assert buf.find("..") == 3
        assert buf.find("bcd") == -1
        assert buf.find("....") == -1
        assert buf.find("ac") == -1
