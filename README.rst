zero_buffer
===========

.. image:: https://travis-ci.org/alex/zero-buffer.png?branch=master
    :target: https://travis-ci.org/alex/zero-buffer

``zero_buffer`` is a high-performance, zero-copy, implementation of a
byte-buffer for Python.

.. code-block:: python

    from zero_buffer import Buffer

    b = Buffer.allocate(8192)
    with open(path, "rb") as f:
        b.read_from(f.fileno())
    view = b.view()
    for part in view.split(":"):
        print(part)
