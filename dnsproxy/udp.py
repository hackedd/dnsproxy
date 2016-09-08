import sys
import socket

from .server import Server


class UDPServer(Server):
    def __init__(self, address="", port=53):
        Server.__init__(self)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((address, port))

    def read_sockets(self):
        return [self.socket]

    def cleanup(self):
        self.socket.close()

    def do_read(self, socket):
        packet, address = socket.recvfrom(4096)
        response = self.respond(packet)
        if response:
            socket.sendto(response, address)
        else:
            print >>sys.stderr, "Query from %s:%d not resolved" % address
            print >>sys.stderr, " ", repr(packet)
