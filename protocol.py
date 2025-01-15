import asyncio
from asyncio import DatagramProtocol

from utils import Address


class PeerProtocol(DatagramProtocol):
    def __init__(self) -> None:
        self.packets: asyncio.Queue[tuple[bytes, Address]] = asyncio.Queue()

    def datagram_received(self, data: bytes, addr: Address) -> None:
        self.packets.put_nowait((data, addr))

    async def recvfrom(self):
        return await self.packets.get()
