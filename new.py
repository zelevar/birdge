from dataclasses import dataclass
from enum import Enum
from socket import socket, AF_INET, SOCK_DGRAM
from typing import Self

from utils import address_to_code, code_to_address, get_external_address, Address


class PacketType(Enum):
    CONNECT = 0
    ACCEPT = 1
    TRANSFER_BEGIN = 2
    TRANSFER_CHUNK = 3


@dataclass
class Packet:
    type: PacketType
    payload: bytes = b''

    def pack(self) -> bytes:
        return self.type.value.to_bytes(1) + self.payload
    
    @classmethod
    def unpack(cls, data: bytes) -> Self:
        type = PacketType(int.from_bytes(data[:1]))
        payload = data[1:]

        return cls(type, payload)
    

class PeerState(Enum):
    DISCONNECTED = 0
    CONNECTED = 1
    TRANSFER_BEGIN = 2
    TRANSFER_CHUNK = 3
    

class Peer:
    state: PeerState = PeerState.DISCONNECTED

    def __init__(self, address: Address):
        self.address = address

        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', 2025))
        self.socket.settimeout(30.0)

        self._connect()

    def _send(self, data: bytes) -> None:
        self.socket.sendto(data, self.address)
        
    def _receive(self) -> bytes:
        data, addr = self.socket.recvfrom(1472)
        if addr != self.address:
            # TODO: log warning
            # FIXME: recursion limit vulnerability
            return self._receive()

        return data

    def send(self, packet: Packet) -> None:
        self._send(packet.pack())

    def receive(self) -> Packet:
        data = self._receive()
        packet = Packet.unpack(data)
        
        # happens when NAT is already open so ACCEPT packets end up on both sides
        if (
            packet.type == PacketType.ACCEPT
            and self.state == PeerState.CONNECTED
        ):
            return self.receive()
        
        return packet
    
    def _establish(self) -> None:
        self.state = PeerState.CONNECTED
    
    def _connect(self) -> None:
        self.send(Packet(PacketType.CONNECT))

        packet = self.receive()
        match packet.type:
            case PacketType.CONNECT:
                self.send(Packet(PacketType.CONNECT))
                self._establish()
            case PacketType.ACCEPT:
                self._establish()
        

my_addr = get_external_address()
my_code = address_to_code(my_addr)
print(f"Your code: {my_code}")

peer_code = input("Peer's code: ")
peer_addr = code_to_address(peer_code)

peer = Peer(peer_addr)
packet = peer.receive()
print(packet)
