dnsproxy
========

This thing I hacked together when I needed a DNS server that could intercept/log/spoof some queries and was unable to find exactly that using Google.

Example
-------

    $ sudo python example.py
    < test.google.com. IN A
    > 127.0.0.1
    < test.google.com. IN AAAA
    > ::1

From another terminal:

    $ dig +ttlid a test.google.com @localhost | grep -A1 "ANSWER SECTION"
    ;; ANSWER SECTION:
    test.google.com.    1   IN  A     127.0.0.1
    $ dig +ttlid aaaa test.google.com @localhost | grep -A1 "ANSWER SECTION"
    ;; ANSWER SECTION:
    test.google.com.    1   IN  AAAA  ::1
