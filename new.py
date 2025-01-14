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

        self.send(Packet(PacketType.CONNECT))
        packet = self.receive()
        print(packet)

    def _send(self, data: bytes) -> None:
        self.socket.sendto(data, self.address)
        
    def _receive(self, length: int) -> bytes:
        data, addr = self.socket.recvfrom(length)
        if addr != self.address:
            # TODO: log warning
            # FIXME: recursion limit vulnerability
            return self._receive(length)

        return data

    def send(self, packet: Packet) -> None:
        data = packet.pack()
        length = len(data).to_bytes(1)
        self._send(length + data)

    def receive(self) -> Packet:
        length = int.from_bytes(self._receive(1))
        data = self._receive(length)

        packet = Packet.unpack(data)
        
        # happens when NAT is already open so ACCEPT packets end up on both sides
        if (
            packet.type == PacketType.ACCEPT
            and self.state == PeerState.CONNECTED
        ):
            return self.receive()
        
        return packet        
        

my_addr = get_external_address()
my_code = address_to_code(my_addr)
print(f"Your code: {my_code}")

peer_code = input("Peer's code: ")
peer_addr = code_to_address(peer_code)

peer = Peer(peer_addr)
