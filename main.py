from impl import Session
from utils import address_to_code, code_to_address, get_external_address

session = Session()

my_addr = get_external_address(session.socket)
my_code = address_to_code(my_addr)
print(f"Your code: {my_code}")

peer_code = input("Peer's code: ")
peer_addr = code_to_address(peer_code)

session.connect(peer_addr)
print("Connected!")
