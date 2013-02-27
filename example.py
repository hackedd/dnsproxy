"""Example script that makes all .google.com addresses resolve to localhost.
"""
import dnsproxy

# Set this to the address you want the server to bind on
ADDRESS = "192.168.1.14"

class GoogleResolver(dnsproxy.Resolver):
    def resolve_a(self, qname, ipv6=False):
        if str(qname).rstrip(".").endswith("google.com"):
            return "::1" if ipv6 else "127.0.0.1"

server = dnsproxy.UDPServer(ADDRESS)
server.resolvers = [GoogleResolver()]

try:
    dnsproxy.mainloop([server])
except KeyboardInterrupt:
    server.cleanup()
