import threading
from functools import wraps
from select import select

import dns.resolver
import pytest

from dnsproxy.tcp import TCPServer
from dnsproxy.udp import UDPServer
from dnsproxy.resolver import Resolver


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


def get_proxy_resolver(server):
    address, port = server.socket.getsockname()
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = [address]
    resolver.port = port
    return resolver


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
    proxy_resolver = get_proxy_resolver(server)

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
    proxy_resolver = get_proxy_resolver(server)

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


@with_server(UDPServer, address="127.0.0.1", port=0)
def test_udp_resolve_override(server):
    class TestResolver(Resolver):
        def resolve_a(self, qname, ipv6=False):
            return "::1" if ipv6 else "127.0.0.1"

        def resolve_mx(self, qname):
            return "10 mail.%s" % qname

        def resolve(self, qname, rdtype, rdclass):
            if rdtype == "TXT" and rdclass == "IN":
                return "\"v=spf1 include:_spf.example.com -all\""
            return None

    class NoAnswerResolver(Resolver):
        def resolve(self, qname, rdtype, rdclass):
            raise dns.resolver.NoAnswer()

    class TimeoutResolver(Resolver):
        def resolve(self, qname, rdtype, rdclass):
            raise dns.resolver.Timeout()

    server.resolvers = [TestResolver()]

    proxy_resolver = get_proxy_resolver(server)

    response = proxy_resolver.query("example.com")
    assert str(response.rrset) == "example.com. 1 IN A 127.0.0.1"

    response = proxy_resolver.query("example.com", "AAAA")
    assert str(response.rrset) == "example.com. 1 IN AAAA ::1"

    response = proxy_resolver.query("example.com", "MX")
    assert str(response.rrset) == "example.com. 1 IN MX 10 mail.example.com."

    response = proxy_resolver.query("example.com", "TXT")
    assert str(response.rrset) == "example.com. 1 IN TXT " \
                                  "\"v=spf1 include:_spf.example.com -all\""

    server.resolvers = [NoAnswerResolver()]
    with pytest.raises(dns.resolver.NoAnswer):
        proxy_resolver.query("example.com", "A")

    server.resolvers = [TimeoutResolver()]
    proxy_resolver.lifetime = 4  # Otherwise this test takes too long
    with pytest.raises(dns.resolver.Timeout):
        proxy_resolver.query("example.com", "A")
