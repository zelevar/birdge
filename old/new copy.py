import math
import os
from dataclasses import dataclass
from enum import Enum
from socket import AF_INET, SOCK_DGRAM, socket
from typing import BinaryIO, Self

from exceptions import HandshakeError
from utils import (
    Address,
    address_to_code,
    chunkify_file,
    code_to_address,
    get_external_address,
    save_chunk,
)

MAX_PACKET_SIZE = 1472
MAX_CHUNK_SIZE = MAX_PACKET_SIZE - 4


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
        data, addr = self.socket.recvfrom(65507)
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
        chunks = chunkify_file(file, MAX_CHUNK_SIZE)
        # round up
        chunk_count = math.ceil(os.stat(file.name).st_size / MAX_CHUNK_SIZE)
        
        filename = file.name.replace('\\', '/').split('/')[-1] or 'unknown'

        self.send(Packet(
            PacketType.TRANSFER_BEGIN,
            chunk_count.to_bytes(4) + filename[:256].encode()
        ))
        print("Transfer started!")
        for index, chunk_data in enumerate(chunks):
            chunk_index = index.to_bytes(4)
            self.send(Packet(PacketType.TRANSFER_CHUNK, chunk_index + chunk_data))

    def receive_file(self) -> BinaryIO:
        initial_packet = self.receive()
        if initial_packet.type != PacketType.TRANSFER_BEGIN:
            raise ValueError(f"expected TRANSFER_BEGIN, got {initial_packet.type.name}")
        
        chunk_count = int.from_bytes(initial_packet.payload[:4])
        file_name = initial_packet.payload[4:260].decode()
        file_size = chunk_count * MAX_CHUNK_SIZE

        print(f"Receiving file `{file_name}` ({chunk_count} chunks, {round(file_size / 1024 / 1024)} MiB)")
        received_chunk_count = 0

        with open(file_name, 'w+b') as f:
            f.truncate(file_size)

            for _ in range(chunk_count):
                chunk_packet = self.receive()
                if chunk_packet.type != PacketType.TRANSFER_CHUNK:
                    raise ValueError(f"expected TRANSFER_CHUNK, got {chunk_packet.type.name}")
                
                chunk_index = int.from_bytes(chunk_packet.payload[:4])
                chunk_data = chunk_packet.payload[4:]
                
                save_chunk(f, chunk_index, MAX_CHUNK_SIZE, chunk_data)

                received_chunk_count += 1
                progress = round((received_chunk_count / chunk_count) * 100)
                if progress != 0 and progress % 5 == 0:
                    print(f"Progress: {progress}%")
        
        return f
        

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
        file = peer.receive_file()
    case 'send':
        with open("../Teardown 2024-08-07.zip", 'rb') as f:  # type: ignore[assignment]
            peer.send_file(f)
    case _:
        raise ValueError("unknown mode")
