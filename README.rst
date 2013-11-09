zero_buffer
===========

.. image:: https://travis-ci.org/alex/zero_buffer.png?branch=master
    :target: https://travis-ci.org/alex/zero_buffer

``zero_buffer`` is a high-performance, zero-copy, implementation of a
byte-buffer for Python.

.. code-block:: python

    from zero_buffer import Buffer

    # Create a buffer which has space for 8192 bytes.
    b = Buffer.allocate(8192)
    with open(path, "rb") as f:
        # Read up to 8192 bytes from the file into the buffer
        b.read_from(f.fileno())
    # Create a read-only view of the buffer, this performs no copying.
    view = b.view()
    # Split the view on colons, this returns a generator which yields sub-views
    # of the view.
    for part in view.split(b":"):
        print(part)

``zero_buffer`` works on Python 2.6, 2.7, 3.2, 3.3, and PyPy.
