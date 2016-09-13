import sys
import socket
import struct

from .server import Server


class TCPServer(Server):
    def __init__(self, address="", port=53):
        super(TCPServer, self).__init__()
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

    def unpack_message(self, buf):
        length, = struct.unpack("!H", buf[:2])
        return length, buf[2:]

    def pack_message(self, buf):
        return struct.pack("!H", len(buf)) + buf

    def complete(self, buffer):
        length, message = self.unpack_message(buffer)
        return len(message) >= length

    def do_read(self, socket):
        if socket == self.socket:
            client, address = socket.accept()
            self.clients.append(client)
            self.buffers.append("")
            return

        i = self.clients.index(socket)
        self.buffers[i] += socket.recv(4096)
        buf = self.buffers[i]

        if self.complete(buf):
            length, message = self.unpack_message(buf)

            response = self.respond(message)
            if response:
                socket.sendall(self.pack_message(response))
            else:
                print >>sys.stderr, "Query from %s:%d (TCP) not resolved" % \
                                    socket.getpeername()
                print >>sys.stderr, " ", repr(buf)

            buf = buf[length + 2:]

        # TODO: Detect socket close
        if buf:
            self.buffers[i] = buf
        else:
            del self.clients[i]
            del self.buffers[i]

    # XXX: We should probably buffer outgoing data as well?
    # def do_write(self, socket):
    #     pass
