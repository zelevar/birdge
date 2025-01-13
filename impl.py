from dataclasses import dataclass
from enum import Enum
from socket import AF_INET, SOCK_DGRAM, socket
from typing import Self

Address = tuple[str, int]
SOURCE_PORT = 2025
MAX_PACKET_SIZE = 65507
TIMEOUT = 30.0


class PacketType(Enum):
    CONNECT = 0
    ACCEPT = 1
    FILE = 2


@dataclass
class Packet:
    type: PacketType
    payload: bytes = b''

    # TODO: find a ready-made lib that would do the following out of the box
    def pack(self) -> bytes:
        return self.type.value.to_bytes(1) + self.payload
    
    @classmethod
    def unpack(cls, data: bytes) -> Self:
        return cls(
            type=PacketType(int.from_bytes(data[:1])),
            payload=data[1:],
        )
    

# TODO: split this to the files
    

class SessionState(Enum):
    DISCONNECTED = 0
    CONNECTED = 1


class MissingPeerError(Exception):
    ...


class HandshakeError(Exception):
    ...


# TODO: add debug logs about every action
class Session:
    state: SessionState = SessionState.DISCONNECTED
    peer: Address | None = None
    
    def __init__(self, port: int = 2025) -> None:
        self.port = port

        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', self.port))
        self.socket.settimeout(TIMEOUT)

    def send_packet(self, packet: Packet) -> None:
        if not self.peer:
            raise MissingPeerError()
    
        data = packet.pack()
        self.socket.sendto(data, self.peer)
    
    def receive_packet(self) -> Packet:
        if not self.peer:
            raise MissingPeerError()

        data, addr = self.socket.recvfrom(MAX_PACKET_SIZE)
        if addr != self.peer:
            # TODO: add warning
            # FIXME: recursion limit vulnerability
            print("warning")
            return self.receive_packet()
        
        packet = Packet.unpack(data)

        # happens when p2p channel is already open
        # and ACCEPT packets end up on both sides
        if (
            packet.type == PacketType.ACCEPT
            and self.state == SessionState.CONNECTED
        ):
            return self.receive_packet()
        
        return packet
    
    def _establish(self) -> None:
        self.state = SessionState.CONNECTED
    
    def connect(self, peer: Address) -> None:
        if self.state == SessionState.CONNECTED:
            # TODO: raise an exception
            pass
        
        self.peer = peer
        self.send_packet(Packet(PacketType.CONNECT))

        packet = self.receive_packet()
        if packet.type == PacketType.CONNECT:
            self.send_packet(Packet(PacketType.ACCEPT))
            self._establish()
        elif packet.type == PacketType.ACCEPT:
            self._establish()
        else:
            raise HandshakeError(f"incorrect incoming packet during handshake ({packet.type})")
