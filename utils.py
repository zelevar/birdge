import base64
import socket


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
