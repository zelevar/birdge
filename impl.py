from dataclasses import dataclass
from enum import IntEnum


class PacketType(IntEnum):
    CONNECT = 0
    ACCEPT = 1


@dataclass
class Packet:
    type: PacketType
    payload: bytes = b''

    # TODO: find a ready-made lib that would do the following out of the box
    def pack(self) -> bytes:
        return self.type.value.to_bytes(1) + self.payload
