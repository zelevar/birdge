from impl import Packet, PacketType, Session
from utils import address_to_code, chunkify, code_to_address, get_external_address

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
        # session.send_packet(Packet(PacketType.FILE, b"p"*10100))
        with open('../image.png', 'rb') as f:
            # TODO: read only part of file (because it can be larger than available RAM) 
            payload = f.read()  

        chunks = chunkify(payload, 1468)
        chunk_count = len(chunks).to_bytes(4)
        session.send_packet(Packet(PacketType.TRANSFER_BEGIN, ))

        # TODO: make it asynchronous
        for chunk_index, chunk in enumerate(chunks):
            payload = chunk_index.to_bytes(4) + chunk
            session.send_packet(Packet(PacketType.TRANSFER_CHUNK, payload))
    case 'recv':
        begin_packet = session.receive_packet()
        if begin_packet.type == PacketType.TRANSFER_BEGIN:
            # FIXME: conflict with prev (match)case block - move to the function
            chunk_count: int = int.from_bytes(begin_packet.payload[:4])  # type: ignore

            with open(f'{peer_code}.png', 'wb') as f:
                # FIXME: chunk sequence isn't checked (and it's unneccessary when you're working with sync send)
                for _ in range(chunk_count):
                    chunk_packet = session.receive_packet()
                    if chunk_packet.type != PacketType.TRANSFER_CHUNK:
                        raise Exception(f'got {chunk_packet.type} while transfering chunks')
                    f.write(chunk_packet.payload[4:])
        else:
            raise ValueError(f"expected TRANSFER_BEGIN, got {begin_packet.type.name}")
    case _:
        raise ValueError("unknown mode")
