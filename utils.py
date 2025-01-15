import base64
import socket
from typing import BinaryIO

Address = tuple[str, int]


def parse_address(addr: str) -> tuple[str, int]:
	ip, port = addr.split(':', 1)
	return ip, int(port)


def address_to_code(addr: tuple[str, int]) -> str:
	addr_bytes = socket.inet_aton(addr[0]) + addr[1].to_bytes(2, 'big')
	return base64.urlsafe_b64encode(addr_bytes).decode()


def code_to_address(code: str) -> tuple[str, int]:
	addr_bytes = base64.urlsafe_b64decode(code)
	ip, port = addr_bytes[:4], addr_bytes[4:]
	return socket.inet_ntoa(ip), int.from_bytes(port)


def get_external_address(
	*,
	timeout: float = 30.0,
	source_host: str = '0.0.0.0',
	source_port: int = 2025,  # TODO: remove this default
	stun_host: str = 'stun.ekiga.net',
	stun_port: int = 3478
) -> tuple[str, int]:
	source_addr = (socket.gethostbyname(source_host), source_port)
	stun_addr = (socket.gethostbyname(stun_host), stun_port)

	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.settimeout(timeout)
	sock.bind(source_addr)
	
	sock.sendto(
		b"\x00\x01\x00\x00!\x12\xa4B\xd6\x85y\xb8\x11\x030\x06xi\xdfB",
		stun_addr
	)
	data, _ = sock.recvfrom(2048)
	sock.close()
	
	return socket.inet_ntoa(data[28:32]), int.from_bytes(data[26:28], 'big')


def chunkify(data: bytes, chunk_size: int) -> list[bytes]:
	return [
		data[chunk_position:chunk_position + chunk_size]
		for chunk_position in range(0, len(data), chunk_size)
	]


def save_chunk(
	file: BinaryIO,
	chunk_index: int,
	chunk_size: int,
	chunk_data: bytes
) -> None:
    file.seek(chunk_index * chunk_size)
    file.write(chunk_data)
