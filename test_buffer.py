import errno

import pytest

from buffer import Buffer, BufferGroup


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
        with pytest.raises(ValueError):
            buf[100:3]

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

    def test_split(self):
        buf = Buffer.from_bytes(b"abc-def-123")
        assert list(buf.split("-")) == ["abc", "def", "123"]
        assert list(buf.split("-", 1)) == ["abc", "def-123"]

        buf = Buffer.from_bytes(b"abc::def::123")
        assert list(buf.split("::")) == ["abc", "def", "123"]
        assert list(buf.split("::", 1)) == ["abc", "def::123"]

        with pytest.raises(ValueError):
            next(buf.split(""))

    def test_write_to_fd(self, tmpdir):
        t = tmpdir.join("t.txt")
        buf = Buffer.from_bytes(b"abc, 123!")
        with t.open("wb") as f:
            buf.write_to_fd(f.fileno())
        assert t.read() == b"abc, 123!"

    def test_write_to_fd_error(self):
        buf = Buffer.from_bytes(b"abc")
        with pytest.raises(OSError) as exc_info:
            buf.write_to_fd(-1)
        assert exc_info.value.errno == errno.EBADF


class TestBufferGroup(object):
    def test_write_to_fd(self, tmpdir):
        t = tmpdir.join("t.txt")
        buf = Buffer.from_bytes(b"abc, 123!\n")
        buf_group = BufferGroup([buf, buf, buf])
        with t.open("wb") as f:
            buf_group.write_to_fd(f.fileno())
        assert t.read() == b"abc, 123!\nabc, 123!\nabc, 123!\n"

    def test_write_to_fd_error(self):
        buf = Buffer.from_bytes(b"abc, 123!\n")
        buf_group = BufferGroup([buf])
        with pytest.raises(OSError) as exc_info:
            buf_group.write_to_fd(-1)
        assert exc_info.value.errno == errno.EBADF

    def test_getitem(self):
        buf_group = BufferGroup([
            Buffer.from_bytes(b"abc"),
            Buffer.from_bytes(b"def"),
            Buffer.from_bytes(b"123"),
        ])
        assert buf_group[0] == b"a"
        assert buf_group[3] == b"d"
        assert buf_group[6] == b"1"
        assert buf_group[-1] == b"3"
        assert buf_group[-5] == b"e"
        with pytest.raises(IndexError):
            buf_group[10]
        with pytest.raises(IndexError):
            buf_group[-10]
