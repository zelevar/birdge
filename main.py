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
        # session.send_packet(Packet(PacketType.CONNECT))
        session.send_packet(Packet(PacketType.FILE, b"p"*15000))
        # with open('../image.png', 'rb') as f:
        #     payload = f.read()
        #     print(len(payload))
        #     packet = Packet(PacketType.FILE, payload)
        # session.send_packet(packet)
    case 'recv':
        packet = session.receive_packet()
        print(packet)
        if packet.type == PacketType.FILE:
            with open(f'{peer_code}.png', 'wb') as f:
                f.write(packet.payload)
        else:
            raise ValueError(f"expected FILE, got {packet.type.name}")
    case _:
        raise ValueError("unknown mode")
