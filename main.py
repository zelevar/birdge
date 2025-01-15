from asyncio import AbstractEventLoop, DatagramTransport
import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Self

from exceptions import HandshakeError
from protocol import PeerProtocol
from utils import Address, address_to_code, code_to_address, get_external_address


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
        print("PacketType opcode:", data[:1])
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

    def __init__(
        self,
        transport: DatagramTransport,
        protocol: PeerProtocol
    ) -> None:
        self.transport = transport
        self.protocol = protocol

    async def send(self, packet: Packet) -> None:
        self.transport.sendto(packet.pack())

    async def receive(self) -> Packet:
        data, _ = await self.protocol.recvfrom()
        packet = Packet.unpack(data)

        # happens when NAT is already open so ACCEPT packets end up on both sides
        if (
            packet.type == PacketType.ACCEPT
            and self.state == PeerState.CONNECTED
        ):
            return await self.receive()
        
        return packet
    
    def _establish(self) -> None:
        self.state = PeerState.CONNECTED

    @classmethod
    async def connect(
        cls,
        address: Address,
        loop: AbstractEventLoop | None = None
    ) -> Self:
        loop = loop or asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            PeerProtocol, ('0.0.0.0', 2025), address
        )

        peer = cls(transport, protocol)
        await peer.send(Packet(PacketType.CONNECT))

        packet = await peer.receive()
        match packet.type:
            case PacketType.CONNECT:
                await peer.send(Packet(PacketType.ACCEPT))
                peer._establish()
            case PacketType.ACCEPT:
                peer._establish()
            case _:
                raise HandshakeError(f"incorrect incoming packet during handshake ({packet.type.name})")

        return peer


async def main():
    my_addr = get_external_address()  # ! synchronous I/O
    my_code = address_to_code(my_addr)
    print(f"Your code: {my_code}")

    peer_code = input("Peer's code: ")
    peer_addr = code_to_address(peer_code)

    peer = await Peer.connect(peer_addr)
    print("Connected!")

    mode = input("Select mode (recv, send): ")
    match mode:
        case 'recv':
            peer.receive_file()
        case 'send':
            with open("../Teardown 2024-08-07.zip", 'rb') as f:  # type: ignore[assignment]
                peer.send_file(f)
        case _:
            raise ValueError("unknown mode")
    

asyncio.run(main())
