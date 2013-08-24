import sys
from collections import defaultdict

from fast_buffer import BufferPool, BufferCollator, BufferFull


N = 100


def run_py_bench():
    d = defaultdict(int)
    with open("/usr/share/dict/words") as f:
        for line in f:
            d[line[0]] += 1


def run_fast_buffer_bench():
    d = defaultdict(int)
    pool = BufferPool(capacity=4, buffer_size=8192)
    cur_buffer = pool.buffer()
    last_pos = 0
    collator = BufferCollator()
    with open("/usr/share/dict/words") as f:
        while True:
            try:
                read = cur_buffer.read_from(f.fileno())
            except BufferFull:
                cur_buffer = pool.buffer()
                last_pos = 0
                continue
            except EOFError:
                break
            view = cur_buffer.view(last_pos, last_pos + read)
            last_pos += read
            collator.append(view)
            if "\n" in view:
                data = collator.collapse()
                last_newline_pos = data.rfind("\n")
                for line in data[:last_newline_pos].split("\n"):
                    d[chr(line[0])] += 1
                collator.append(data[last_newline_pos + 1:])


def main(argv):
    name = argv[1]
    if name == "py":
        for i in xrange(N):
            run_py_bench()
    elif name == "fast_buffer":
        for i in xrange(N):
            run_fast_buffer_bench()
    else:
        raise SystemExit("You're a moron")

if __name__ == "__main__":
    main(sys.argv)
