import threading
from functools import wraps
from select import select

import dns.resolver
import pytest

from dnsproxy.tcp import TCPServer
from dnsproxy.udp import UDPServer


def server_loop(server, flag, timeout=0.5):
    while not flag.is_set():
        rlist, wlist, _ = select(server.read_sockets(),
                                 server.write_sockets(), [], timeout)

        for sock in rlist:
            server.do_read(sock)
        for sock in wlist:
            server.do_write(sock)


def with_server(server_class, *server_args, **server_kwargs):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            server = None
            thread = None
            quit = threading.Event()

            try:
                server = server_class(*server_args, **server_kwargs)

                thread = threading.Thread(target=server_loop,
                                          args=(server, quit))
                thread.daemon = True
                thread.start()

                return f(server, *args, **kwargs)

            finally:
                quit.set()
                if thread:
                    thread.join(5.0)
                if server:
                    server.cleanup()
        return wrapped
    return wrapper


def compare_responses(resolver_a, resolver_b, name, **query_options):
    answer_a = resolver_a.query(name, **query_options)
    answer_b = resolver_b.query(name, **query_options)

    assert isinstance(answer_a, dns.resolver.Answer)
    assert isinstance(answer_b, dns.resolver.Answer)

    assert len(answer_a.rrset) == len(answer_b.rrset)
    for rd_a, rd_b in zip(answer_a.rrset, answer_b.rrset):
        assert rd_a == rd_b

    return answer_a, answer_b


@with_server(UDPServer, address="127.0.0.1", port=0)
def test_udp_communication(server):
    # Create a resolver that uses the system's DNS servers
    default_resolver = dns.resolver.Resolver()

    # Create a resolver that uses our own proxy server
    address, port = server.socket.getsockname()
    proxy_resolver = dns.resolver.Resolver(configure=False)
    proxy_resolver.nameservers = [address]
    proxy_resolver.port = port

    # Resolve example.com against the system DNS and against the proxy server,
    # and assert that the responses match.
    response, proxy_response = compare_responses(default_resolver,
                                                 proxy_resolver,
                                                 "example.com")

    # Check if the TTL is reset, to prevent caching of responses
    assert proxy_response.ttl == 1

    # Try resolving a domain name that does not exist against the system DNS
    # and the proxy server, and assert both raise NXDOMAIN.
    with pytest.raises(dns.resolver.NXDOMAIN):
        default_resolver.query("nxdomain.example.com")

    with pytest.raises(dns.resolver.NXDOMAIN):
        proxy_resolver.query("nxdomain.example.com")


@with_server(TCPServer, address="127.0.0.1", port=0)
def test_tcp_communication(server):
    # Create a resolver that uses the system's DNS servers
    default_resolver = dns.resolver.Resolver()

    # Create a resolver that uses our own proxy server
    address, port = server.socket.getsockname()
    proxy_resolver = dns.resolver.Resolver(configure=False)
    proxy_resolver.nameservers = [address]
    proxy_resolver.port = port

    # Resolve example.com against the system DNS and against the proxy server,
    # and assert that the responses match.
    response, proxy_response = compare_responses(default_resolver,
                                                 proxy_resolver,
                                                 "example.com", tcp=True)

    # Check if the TTL is reset, to prevent caching of responses
    assert proxy_response.ttl == 1

    # Try resolving a domain name that does not exist against the system DNS
    # and the proxy server, and assert both raise NXDOMAIN.
    with pytest.raises(dns.resolver.NXDOMAIN):
        default_resolver.query("nxdomain.example.com", tcp=True)

    with pytest.raises(dns.resolver.NXDOMAIN):
        proxy_resolver.query("nxdomain.example.com", tcp=True)
