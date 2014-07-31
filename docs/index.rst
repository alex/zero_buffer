Welcome to Zero Buffer
======================

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

Installation
------------

Install it with ``pip``:

.. code-block:: console

    $ pip install zero_buffer

If you are installing ``zero_buffer`` on Ubuntu, you may need to run the
following before installing it with ``pip``.

.. code-block:: console

    $ sudo apt-get install build-essential libffi-dev python-dev

Contents
--------

.. toctree::
    :maxdepth: 2

    api-reference
