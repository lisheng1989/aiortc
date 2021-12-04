Janus video room client
=======================

This example illustrates how to connect to the Janus WebRTC server's video room.

By default it simply sends green video frames, but you can instead specify a
video file to stream to the room.

First install the required packages:

.. code-block:: console

    $ pip3 install aiohttp aiortc

When you run the example, it will connect to Janus and join the '1234' room:

.. code-block:: console

   $ python3 janus.py --room 1234 https://ws.ychzp.top/janus


