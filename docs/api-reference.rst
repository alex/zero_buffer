API Reference
=============

.. currentmodule:: zero_buffer

.. class:: Buffer

    A buffer is a fixed-size, append only, contigious region of memory. Once
    data is in it, that data cannot be mutated, however data can be read into
    the buffer with multiple calls.

    .. classmethod:: allocate(size)

        :param int size: Number of bytes.
        :return Buffer: The new buffer.

        Allocates a new buffer of ``size`` bytes.

    .. attribute:: capacity

        Returns the size of the underlying buffer. This is the same as what it
        was allocated with.

    .. attribute:: writepos

        Returns the current, internal writing position, this increases on calls
        to :meth:`read_from` and :meth:`add_bytes`.

    .. attribute:: free

        Returns the remaining space in the :class:`Buffer`.

    .. method:: read_from(fd)

        :param int fd: A file descriptor.
        :return int: Number of bytes read.
        :raises OSError: on an error reading from the file descriptor.
        :raises EOFError: when the read position of the file is at the end.
        :raises BufferFull: when the buffer has no remaining space when called

        Reads from the file descriptor into the :class:`Buffer`. Note that the
        number of bytes copied may be less than the number of bytes in the
        file.

    .. method:: add_bytes(b)

        :param bytes b: Bytes to copy into the buffer.
        :return int: Number of bytes copied into the buffer.
        :raises BufferFull: when the buffer has no remaining space when called

        Copies the bytes into the :class:`Buffer`. Note that the number of
        bytes copied may be less than ``len(b)`` if there isn't space in the
        :class:`Buffer`.

    .. method:: view(start=0, stop=None)

        :param int start: The byte-offset from the beggining of the buffer.
        :param int stop: The byte-offset from start.
        :return BufferView:
        :raises ValueError: If the stop is before the start, if the start is
                            negative or after the writepos, or if the stop is
                            after the writepos.

        Returns a view of the buffer's data. This does not perform any copying.


.. class:: BufferView

    A buffer view is an immutable, fixed-size, view over a contigious region of
    memory. It exposes much of the same API as :class:`bytes`, except most
    methods return BufferViews and do not make copies of the data. A buffer
    view is either a view into a :class:`Buffer` or into another
    :class:`BufferView`.

    .. method:: __bytes__()

        Returns a copy of the contents of the view as a :class:`bytes`.

    .. method:: __len__()

        Returns the length of the view.

    .. method:: __eq__(other)

        Checks whether the contents of the view are equal to ``other``, which
        can be either a :class:`bytes` or a :class:`BufferView`.

    .. method:: __contains__(needle)

        Returns whether or not the ``needle`` exists in the view as a
        contigious series of bytes.

    .. method:: __getitem__(idx)

        If ``idx`` is a :class:`slice`, returns a :class:`BufferView` over that
        data, it does not perform a copy. If ``idx`` is an integer, it returns
        the ordinal value of the byte at that index.

        Unlike other containers in Python, this does not support slices with
        steps (``view[::2]``).

    .. method:: __add__(other)

        :param BufferView other:

        Returns a :class:`BufferView` over the concatenated contents. If
        ``other`` is contigious with ``self`` in memory, no copying is
        performed, otherwise both views are copied into a new one.

    .. method:: find(needle, start=0, stop=None)

        The same as :meth:`bytes.find`.

    .. method:: index(needle, start=0, stop=None)

        The same as :meth:`bytes.index`.

    .. method:: rfind(needle, start=0, stop=None)

        The same as :meth:`bytes.rfind`.

    .. method:: rindex(needle, start=0, stop=None)

        The same as :meth:`bytes.rindex`.

    .. method:: split(by, maxsplit=-1)

        Similar to :meth:`bytes.split`, except it returns an iterator (not a
        :class:`list`) over the results, and each result is a
        :class:`BufferView` (not a :class:`bytes`).

    .. method:: splitlines(keepends=False)

        Similar to :meth:`bytes.splitlines`, except it returns an iterator (not
        a :class:`list`) over the results, and each result is a
        :class:`BufferView` (not a :class:`bytes`).

    .. method:: isspace()

        The same as :meth:`bytes.isspace`.

    .. method:: isdigit()

        The same as :meth:`bytes.isdigit`.

    .. method:: isalpha()

        The same as :meth:`bytes.isalpha`.

    .. method:: strip(chars=None)

        The same as :meth:`bytes.strip` except it returns a :class:`BufferView`
        (and not a :class:`bytes`).

    .. method:: lstrip(chars=None)

        The same as :meth:`bytes.lstrip` except it returns a
        :class:`BufferView` (and not a :class:`bytes`).

    .. method:: rstrip(chars=None)

        The same as :meth:`bytes.rstrip` except it returns a
        :class:`BufferView` (and not a :class:`bytes`).

.. class:: BufferCollator

    A buffer collator is a collection of :class:`BufferView` objects which can
    be collapsed into a single :class:`BufferView`.

    .. method:: append(view)

        :param BufferView view:

        Adds the contents of a view to the collator.

    .. method:: collapse()

        Collapses the contents of the collator into a single
        :class:`BufferView`. Also resets the internal state of the collator, so
        if you call it twice successively, the second call will return an empty
        :class:`BufferView`.
