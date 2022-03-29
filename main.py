import json
import socket, glob

port = 53
ip = "127.0.0.1"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((ip, port))

def load_zones():
    json_zone = {}
    zone_files = glob.glob("zones/*.zone")

    for zone in zone_files:
        with open(zone) as zonedata:
            data = json.load(zonedata)
            zone_name = data["$origin"]
            json_zone[zone_name] = data

    return json_zone

zone_data = load_zones()


def parse_flags(flags):
    fs_byte = bytes(flags[:1])
    sc_byte = bytes(flags[1:])

    rflags = ""

    QR = '1'
    OPCODE = ''
    for bit in range(1, 5):
        OPCODE += str(ord(fs_byte) & (1 << bit))
    AA = '1'
    TC = '0'
    RD = '0'
    RA = '0'
    Z = '000'
    RCODE = '0000'
    return int(QR + OPCODE + AA + TC + RD + RCODE).to_bytes(1, byteorder='big') + int(RA + Z + RCODE).to_bytes(1,
                                                                                                               byteorder='big')


def get_question_domain(data):
    state = False
    expected_length = 0
    domain_string = ""
    domain_parts = []
    x = 0
    y = 0

    for byte in data:
        if state:
            domain_string += chr(byte)
            x += 1
            if x == expected_length:
                domain_parts.append(domain_string)
                domain_string = ""
                state = False
                x = 0
            if byte == 0:
                domain_parts.append(domain_string)
                break
        else:
            state = True
            expected_length = byte
        y += 1

    return get_recs('.'.join(domain_parts), data[y + 1:y + 3])


def get_zone(domain):
    global zone_data
    zone_name = domain + '.'
    return zone_data[zone_name]


def get_recs(domain, question_type):
    at = ''
    qt = ''
    if question_type == b'\x00\x01':
        qt = 'a'

    zone = get_zone(domain)

    return zone, qt, domain


def build_response(data):
    # Transaction ID
    TransactionID = data[:2]
    TID = ""
    for byte in TransactionID:
        TID += hex(byte)[2:]

    # Flags
    Flags = parse_flags(data[2:4])

    # Question Count
    QDCOUNT = b = '\x00\x01'

    # Answer Count
    get_question_domain(data[12:])


while True:
    data, addr = sock.recvfrom(512)
    response = build_response(data)
    sock.sendto(response, addr)
