import sys

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

        # return "%s 123 IN %s %s" % (qname, "AAAA" if ipv6 else "A", self.overrides[key])
        return self.overrides.get(key)

if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("--tcp", help="start TCP listener (default: no)", action="store_true")
    parser.add_option("--bind", help="address to bind to", default="")
    parser.add_option("-o", "--override", help="override dns record (name addr)", action="append", default=[])

    options, args = parser.parse_args()
    if args: options.override.extend(args)

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

    print >>sys.stderr, "Starting UDP%sserver on %s:53" % (" and TCP" if options.tcp else "", options.bind)

    servers = [UDPServer(options.bind)]
    if options.tcp:
        servers.append(TCPServer(options.bind))

    for srv in servers:
        srv.resolvers.append(override)

    try:
        mainloop(servers)
    except KeyboardInterrupt:
        print "Ctrl+C"
        for server in servers:
            server.cleanup()
