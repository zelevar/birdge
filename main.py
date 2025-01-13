import enum
import socket
import struct

import utils


class PacketType(enum.Enum):
	CONNECT = 0
	ACCEPT = 1
	MESSAGE = 2


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

	def _send_packet(self, type: PacketType, content: str = '') -> None:
		data = struct.pack('!cc', type.value.to_bytes(1, 'big'), len(content).to_bytes(1, 'big')) + content.encode()
		self.socket.sendto(data, self.peer_addr)

	def _receive_peer_bytes(self, size: int) -> bytes:
		# FIXME: fix the timeout troubles

		data, addr = self.socket.recvfrom(size)
		while addr != self.peer_addr:
			data, addr = self.socket.recvfrom(size)
		
		return data
	
	def _receive_packet(self) -> dict:
		data = self._receive_peer_bytes(2)
		raw_type, raw_length = struct.unpack('!cc', data)

		length = int.from_bytes(raw_length, 'big')
		content = self._receive_peer_bytes(length) if length > 0 else None
		
		return {
			'type': PacketType(int.from_bytes(raw_type, 'big')),
			'content': content
		}

	def connect(self, peer_addr: tuple[str, int]) -> bool:
		if self.state != ConnectionState.DISCONNECTED:
			raise NotImplementedError("must close connection before starting other (close isn't implemented)")
		
		self.peer_addr = peer_addr

		self._send_packet(PacketType.CONNECT)
		packet = self._receive_packet()
		if packet['type'] == PacketType.CONNECT:
			self._send_packet(PacketType.ACCEPT)
			self.state = ConnectionState.ESTABLISHED
			print("🎉 connection established!")
		elif packet['type'] == PacketType.ACCEPT:
			self.state = ConnectionState.ESTABLISHED
			print("🎉 connection established!")
		else:
			self.state = ConnectionState.DISCONNECTED
			raise HandshakeError("incorrect incoming packet during handshake")
	
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

	my_code = utils.address_to_code(session.get_external_address())
	print(f"🔒 your code: {my_code}")

	peer_code = input("🌎 enter the peer's code: ")
	peer_addr = utils.code_to_address(peer_code)
	
	session.connect(peer_addr)
