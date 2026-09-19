"""Timeouts for network access.

Without a timeout a stalled server blocks an import forever. The read timeout is the time to wait for the next bytes,
not for the whole response.
"""

CONNECT_TIMEOUT = 10.0
READ_TIMEOUT = 60.0

# for requests: (connect, read) in seconds
REQUEST_TIMEOUT = (CONNECT_TIMEOUT, READ_TIMEOUT)
