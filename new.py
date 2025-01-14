from dataclasses import dataclass
from enum import Enum
from socket import AF_INET, SOCK_DGRAM, socket
from typing import BinaryIO, Self

from exceptions import HandshakeError
from utils import (
    Address,
    address_to_code,
    chunkify,
    code_to_address,
    get_external_address,
)

MAX_PACKET_SIZE = 1472


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
        data, addr = self.socket.recvfrom(MAX_PACKET_SIZE)
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
                self.send(Packet(PacketType.ACCEPT))
                self._establish()
            case PacketType.ACCEPT:
                self._establish()
            case _:
                raise HandshakeError(f"incorrect incoming packet during handshake ({packet.type.name})")

    def send_file(self, file: BinaryIO) -> None:
        data = file.read()
        chunks = chunkify(data, MAX_PACKET_SIZE - 4)
        chunk_count = len(chunks).to_bytes(4)

        peer.send(Packet(PacketType.TRANSFER_BEGIN, chunk_count))
        for index, chunk_data in enumerate(chunks):
            chunk_index = index.to_bytes(4)
            peer.send(Packet(PacketType.TRANSFER_CHUNK, chunk_index + chunk_data))

    def receive_file(self) -> dict[int, bytes]:
        initial_packet = self.receive()
        if initial_packet.type != PacketType.TRANSFER_BEGIN:
            raise ValueError(f"expected TRANSFER_BEGIN, got {initial_packet.type.name}")
        
        chunks = {}
        chunk_count = int.from_bytes(initial_packet.payload[:4])
        for _ in range(chunk_count):
            chunk_packet = self.receive()
            if chunk_packet.type != PacketType.TRANSFER_CHUNK:
                raise ValueError(f"expected TRANSFER_CHUNK, got {chunk_packet.type.name}")
            
            chunk_index = int.from_bytes(chunk_packet.payload[:4])
            chunk_data = chunk_packet.payload[4:]
            chunks[chunk_index] = chunk_data
        
        return chunks
        

my_addr = get_external_address()
my_code = address_to_code(my_addr)
print(f"Your code: {my_code}")

peer_code = input("Peer's code: ")
peer_addr = code_to_address(peer_code)

peer = Peer(peer_addr)
print("Connected!")

mode = input("Select mode (recv, send): ")
match mode:
    case 'recv':
        chunks = peer.receive_file()
        with open(f'{peer_code}.png', 'wb') as f:
            for chunk_index in sorted(chunks.keys()):
                f.write(chunks[chunk_index])
    case 'send':
        with open('../image.png', 'rb') as f:  # type: ignore[assignment]
            peer.send_file(f)
    case _:
        raise ValueError("unknown mode")
