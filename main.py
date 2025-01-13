from socket import AF_INET, SOCK_DGRAM, socket

from impl import Packet, PacketType
from utils import address_to_code, code_to_address, get_external_address

sock = socket(AF_INET, SOCK_DGRAM)

my_addr = get_external_address(sock)
my_code = address_to_code(my_addr)
print(f"Your code: {my_code}")

peer_code = input("Peer's code: ")
peer_addr = code_to_address(peer_code)

sock.sendto(Packet(PacketType.CONNECT).pack(), peer_addr)
test = sock.recvfrom(65507)
print(test[1], len(test[0]), test[0])
