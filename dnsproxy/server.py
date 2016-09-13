import sys
from select import select

import dns.message
import dns.rrset
import dns.rdata
import dns.resolver
import dns.rdataclass
import dns.rdatatype
import dns.flags
import dns.exception


class Server(object):
    def __init__(self):
        super(Server, self).__init__()
        self.resolvers = []
        self.fallback = dns.resolver.Resolver()

    def read_sockets(self):
        return []

    def write_sockets(self):
        return []

    def do_read(self, socket):
        raise Exception("do_read not implemented")

    def do_write(self, socket):
        raise Exception("do_write not implemented")

    def resolve(self, qname, rdtype, rdclass):
        rdata = None
        # First try specific methods.
        if rdclass == "IN":
            for resolver in self.resolvers:
                if rdtype == "A":
                    rdata = resolver.resolve_a(qname)
                elif rdtype == "AAAA":
                    rdata = resolver.resolve_a(qname, True)
                elif rdtype == "MX":
                    rdata = resolver.resolve_mx(qname)

                if rdata is not None:
                    return rdata

        # If that fails, try the generic method.
        for resolver in self.resolvers:
            rdata = resolver.resolve(qname, rdtype, rdclass)
            if rdata is not None:
                return rdata

        # None of the resolvers matched. Try resolving using an
        # actual DNS server.
        answer = self.fallback.query(qname, rdtype, rdclass)
        return answer.rrset

    def respond(self, data):
        query = dns.message.from_wire(data)
        response = dns.message.make_response(query, recursion_available=True)


        for rrset in query.question:
            print >>sys.stderr, "<", rrset

            qname = rrset.name
            rdtype = dns.rdatatype.to_text(rrset.rdtype)
            rdclass = dns.rdataclass.to_text(rrset.rdclass)

            try:
                rdata = self.resolve(qname, rdtype, rdclass)
            except dns.resolver.NoAnswer:
                print >>sys.stderr, "> NoAnswer"
                continue
            except dns.resolver.NXDOMAIN:
                print >>sys.stderr, "> NXDOMAIN"
                response.set_rcode(dns.rcode.NXDOMAIN)
                break
            except dns.exception.Timeout:
                print >>sys.stderr, "> Timeout"
                # We just drop the query here, causing a timeout for the client
                return None

            if rdata is not None:
                print >>sys.stderr, ">", str(rdata).replace("\n", "\n  ")

                if isinstance(rdata, str):
                    rdata = dns.rdata.from_text(rrset.rdclass, rrset.rdtype,
                                                rdata)

                if isinstance(rdata, dns.rrset.RRset):
                    answer = rdata
                else:
                    answer = rrset._clone()
                    answer.add(rdata)

                # Reset TTL to break caching
                answer.ttl = 1
                response.answer.append(answer)

        return response.to_wire()


def mainloop(servers):
    timeout = 1.0

    while True:
        rdict = {}
        wdict = {}
        for server in servers:
            for socket in server.read_sockets():
                rdict[socket] = server
            for socket in server.write_sockets():
                wdict[socket] = server

        rlist, wlist, _ = select(rdict.keys(), wdict.keys(), [], timeout)

        for sock in rlist:
            rdict[sock].do_read(sock)
        for sock in wlist:
            wdict[sock].do_write(sock)
