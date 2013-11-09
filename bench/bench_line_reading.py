import sys
from collections import defaultdict

from six.moves import xrange

from zero_buffer import Buffer, BufferCollator, BufferFull


N = 100


def run_py_bench():
    d = defaultdict(int)
    with open("/usr/share/dict/words") as f:
        for line in f:
            d[line[0]] += 1


def run_zero_buffer_bench():
    d = defaultdict(int)
    cur_buffer = Buffer.alloc(8192)
    last_pos = 0
    collator = BufferCollator()
    with open("/usr/share/dict/words") as f:
        done = False
        while not done:
            try:
                read = cur_buffer.read_from(f.fileno())
            except BufferFull:
                cur_buffer = Buffer.alloc(8192)
                last_pos = 0
                continue
            except EOFError:
                read = 0
                done = True
            view = cur_buffer.view(last_pos, last_pos + read)
            last_pos += read
            collator.append(view)
            if b"\n" in view:
                data = collator.collapse()
                last_newline_pos = data.rfind(b"\n")
                for line in data[:last_newline_pos].split(b"\n"):
                    d[chr(line[0])] += 1
                collator.append(data[last_newline_pos + 1:])


def main(argv):
    name = argv[1]
    if name == "py":
        for i in xrange(N):
            run_py_bench()
    elif name == "zero_buffer":
        for i in xrange(N):
            run_fast_buffer_bench()
    else:
        raise SystemExit("argv[1] should be either py or zero_buffer")

if __name__ == "__main__":
    main(sys.argv)
