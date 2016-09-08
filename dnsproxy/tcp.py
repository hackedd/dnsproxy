import sys
import socket

from .server import Server


class TCPServer(Server):
    def __init__(self, address="", port=53):
        Server.__init__(self)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((address, port))

        self.clients = []
        self.buffers = []

        self.socket.listen(1)

    def cleanup(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()

        for client in self.clients:
            client.close()

    def read_sockets(self):
        return [self.socket] + self.clients

    def write_sockets(self):
        return []

    def complete(self, buffer):
        # TODO: Determine if TCP DNS Message is complete
        return True

    def do_read(self, socket):
        if socket == self.socket:
            client, address = socket.accept()
            self.clients.append(client)
            self.buffers.append("")
        else:
            i = self.clients.index(socket)
            self.buffers[i] += socket.recv(4096)
            if not self.complete(self.buffers[i]):
                return

            response = self.respond(self.buffers[i])
            if response:
                self.socket.sendall(response)
            else:
                print >>sys.stderr, "Query from %s:%d (TCP) not resolved" % \
                                    socket.getpeername()
                print >>sys.stderr, " ", repr(self.buffers[i])

            del self.clients[i]
            del self.buffers[i]

    # XXX: We should probably buffer outgoing data as well?
    # def do_write(self, socket):
    #     pass
