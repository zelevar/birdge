from impl import Packet, PacketType, Session
from utils import address_to_code, code_to_address, get_external_address

session = Session()

my_addr = get_external_address(session.socket)
my_code = address_to_code(my_addr)
print(f"Your code: {my_code}")

peer_code = input("Peer's code: ")
peer_addr = code_to_address(peer_code)

session.connect(peer_addr)
print("Connected!")

mode = input("Select mode (send/recv): ")
match mode:
    case 'send':
        with open('../image.png', 'rb') as f:
            packet = Packet(PacketType.FILE, f.read())
        session.send_packet(packet)
    case 'recv':
        packet = session.receive_packet()
        with open(f'{peer_code}.png', 'wb') as f:
            f.write(packet.payload)
    case _:
        raise ValueError("unknown mode")
