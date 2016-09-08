import sys
from optparse import OptionParser

from .resolver import Resolver
from .server import mainloop
from .udp import UDPServer
from .tcp import TCPServer


class OverrideResolver(Resolver):
    def __init__(self, overrides=None, ipv6=False):
        self.overrides = overrides or dict()
        self.ipv6 = ipv6

    def resolve_a(self, qname, ipv6=False):
        if ipv6 != self.ipv6:
            return None

        key = str(qname).lower().rstrip(".")

        # if key not in self.overrides:
        #     return None

        # return "%s 123 IN %s %s" % (qname, "AAAA" if ipv6 else "A",
        #                             self.overrides[key])
        return self.overrides.get(key)


def main():
    parser = OptionParser()
    parser.add_option("--tcp", action="store_true",
                      help="start TCP listener (default: no)")
    parser.add_option("--bind", default="", help="address to bind to")
    parser.add_option("--port", default="53", help="port to listen on")
    parser.add_option("-o", "--override", action="append", default=[],
                      help="override dns record (name addr)")

    options, args = parser.parse_args()
    if args:
        options.override.extend(args)

    override = OverrideResolver()
    for o in options.override:
        parts = o.split()
        if len(parts) < 2:
            parser.error("Override should be in NAME ADDR format")

        addr = parts[-1]
        for name in parts[:-1]:
            key = name.lower().rstrip(".")
            print >>sys.stderr, "Adding override %s => %s" % (key, addr)
            override.overrides[key] = addr

    server_name = "UDP and TCP" if options.tcp else "UDP"
    address, port = options.bind, int(options.port)
    print >>sys.stderr, "Starting %s server on %s:%s" % (server_name,
                                                         address, port)

    servers = [UDPServer(address, port)]
    if options.tcp:
        servers.append(TCPServer(address, port))

    for srv in servers:
        srv.resolvers.append(override)

    try:
        mainloop(servers)
    except KeyboardInterrupt:
        print "Ctrl+C"
        for server in servers:
            server.cleanup()
