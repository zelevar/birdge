import asyncio
import math
import os
from asyncio import AbstractEventLoop, DatagramTransport
from dataclasses import dataclass
from enum import Enum
from typing import Self

import aiofiles
from aiofiles.threadpool.binary import AsyncBufferedReader

from exceptions import HandshakeError
from protocol import PeerProtocol
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

    def __init__(
        self,
        transport: DatagramTransport,
        protocol: PeerProtocol
    ) -> None:
        self.transport = transport
        self.protocol = protocol

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
                peer.state = PeerState.CONNECTED
            case PacketType.ACCEPT:
                peer.state = PeerState.CONNECTED
            case _:
                raise HandshakeError(f"incorrect incoming packet during handshake ({packet.type.name})")

        return peer

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
    
    async def send_file(self, file: AsyncBufferedReader) -> None:
        # round up
        chunk_count = math.ceil(os.stat(file.name).st_size / MAX_CHUNK_SIZE)
        
        filename = str(file.name).replace('\\', '/').split('/')[-1] or 'unknown'

        await self.send(Packet(
            PacketType.TRANSFER_BEGIN,
            chunk_count.to_bytes(4) + filename[:256].encode()
        ))
        print("Transfer started!")

        index = 0
        async for chunk_data in chunkify_file(file, MAX_CHUNK_SIZE):
            index += 1
            chunk_index = index.to_bytes(4)

            await self.send(Packet(PacketType.TRANSFER_CHUNK, chunk_index + chunk_data))

    async def receive_file(self) -> AsyncBufferedReader:
        initial_packet = await self.receive()
        if initial_packet.type != PacketType.TRANSFER_BEGIN:
            raise ValueError(f"expected TRANSFER_BEGIN, got {initial_packet.type.name}")
        
        chunk_count = int.from_bytes(initial_packet.payload[:4])
        file_name = initial_packet.payload[4:260].decode()
        file_size = chunk_count * MAX_CHUNK_SIZE

        print(f"Receiving file `{file_name}` ({chunk_count} chunks, {round(file_size / 1024 / 1024)} MiB)")
        received_chunk_count = 0

        async with aiofiles.open(file_name, 'w+b') as f:
            await f.truncate(file_size)

            for _ in range(chunk_count):
                chunk_packet = await self.receive()
                if chunk_packet.type != PacketType.TRANSFER_CHUNK:
                    raise ValueError(f"expected TRANSFER_CHUNK, got {chunk_packet.type.name}")
                
                chunk_index = int.from_bytes(chunk_packet.payload[:4])
                chunk_data = chunk_packet.payload[4:]
                
                await save_chunk(f, chunk_index, MAX_CHUNK_SIZE, chunk_data)

                received_chunk_count += 1
                progress = round((received_chunk_count / chunk_count) * 100)
                if progress != 0 and progress % 5 == 0:
                    print(f"Progress: {progress}%")
        
        return f


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
            async with aiofiles.open("../Teardown 2024-08-07.zip", 'rb') as f:  # type: ignore[assignment]
                peer.send_file(f)
        case _:
            raise ValueError("unknown mode")
    

asyncio.run(main())
