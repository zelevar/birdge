import enum
import socket
import struct
from typing import BinaryIO

import utils


class PacketType(enum.Enum):
	CONNECT = 0
	ACCEPT = 1
	FILE = 2


class ConnectionState(enum.Enum):
	DISCONNECTED = 0
	ESTABLISHED = 1


class HandshakeError(Exception):
	pass


class Session:
	def __init__(self, port: int = 2077) -> None:
		self.port = port
		self.state = ConnectionState.DISCONNECTED

		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.socket.bind(('0.0.0.0', self.port))
		self.socket.settimeout(30)

	def _send_packet(self, type: PacketType, content: bytes = b'') -> None:
		data = struct.pack('!cI', type.value.to_bytes(1, 'big'), len(content)) + content
		self.socket.sendto(data, self.peer_addr)

	def _receive_peer_bytes(self, size: int) -> bytes:
		# FIXME: fix the timeout troubles

		data, addr = self.socket.recvfrom(size)
		while addr != self.peer_addr:
			data, addr = self.socket.recvfrom(size)
		
		return data
	
	def _receive_packet(self) -> dict:  # TODO: dict to NamedTuple or smth
		data = self._receive_peer_bytes(5)
		raw_type, raw_length = struct.unpack('!cI', data)

		length = raw_length # length = int.from_bytes(raw_length, 'big')
		content = self._receive_peer_bytes(length) if length > 0 else None
		
		return {
			'type': PacketType(int.from_bytes(raw_type, 'big')),
			'content': content
		}
	
	def _establish(self) -> None:
		self.state = ConnectionState.ESTABLISHED
		print("🎉 connection established!")

	def connect(self, peer_addr: tuple[str, int]) -> None:  # -> bool:
		if self.state != ConnectionState.DISCONNECTED:
			raise NotImplementedError("must close connection before starting other (close isn't implemented)")
		
		self.peer_addr = peer_addr

		self._send_packet(PacketType.CONNECT)
		packet = self._receive_packet()
		if packet['type'] == PacketType.CONNECT:
			self._send_packet(PacketType.ACCEPT)
			self._establish()
		elif packet['type'] == PacketType.ACCEPT:
			self._establish()
		else:
			self.state = ConnectionState.DISCONNECTED
			raise HandshakeError("incorrect incoming packet during handshake")
	
	# TODO: is this type annotation right?
	def send_file(self, file: BinaryIO) -> None:
		filename = b'flnmenotimplmntd'
		data = file.read()  # ! read entire file
		self._send_packet(PacketType.FILE, filename + data)

	# TODO: pack this tuple to the class too
	def receive_file(self) -> tuple[str, bytes]:  # filename, data
		packet = self._receive_packet()
		if packet['type'] != PacketType.FILE:
			raise Exception(f"Expected FILE, got {packet['type']}")
		
		content = packet['content']  # TODO: remove this alias when Packet class is ready
		return content[:16], content[16:]  # TODO: move to constant (filename max length)
	
	def get_external_address(
		self, stun_host: str = 'stun.ekiga.net'
	) -> tuple[str, int]:
		stun_addr = (socket.gethostbyname(stun_host), 3478)
		
		self.socket.sendto(
			b"\x00\x01\x00\x00!\x12\xa4B\xd6\x85y\xb8\x11\x030\x06xi\xdfB",
			stun_addr
		)
		data, _ = self.socket.recvfrom(2048)
		
		return socket.inet_ntoa(data[28:32]), int.from_bytes(data[26:28], 'big')


if __name__ == '__main__':
	session = Session()

	my_address = session.get_external_address()
	my_code = utils.address_to_code(my_address)
	print(f"🔒 your code: {my_code} ({':'.join(map(str, my_address))})")

	peer_code = input("🌎 enter the peer's code: ")
	peer_addr = utils.code_to_address(peer_code)
	
	session.connect(peer_addr)
	mode = input('choose mode (a. send file; b. receive): ')
	if mode == 'a':
		session.send_file(open('../image.png', 'rb'))
	elif mode == 'b':
		file_data = session.receive_file()
		print("First 50 bytes of file:", file_data[1][:50])
		with open('testttt.png', 'wb') as f:
			f.write(file_data[1])
	else:
		print('wtf??? incorrect mode')
