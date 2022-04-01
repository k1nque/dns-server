import json
import socket
import glob
import dnsResolver

port = 53
ip = "127.0.0.1"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((ip, port))


def load_zones():
    json_zone = dict()
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
    return int(QR + OPCODE + AA + TC + RD, 2).to_bytes(1, byteorder='big') \
           + int(RA + Z + RCODE, 2).to_bytes(1, byteorder='big')


def get_question_domain(data):
    state = False
    expected_length = 0
    domain_string = ""
    domain_parts = []
    x = 0
    qti = 0

    for byte in data:
        if state:
            if byte != 0:
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
        qti += 1

    return domain_parts, data[qti:qti + 2]


def get_zone(domain):
    global zone_data
    zone_name = '.'.join(domain)
    return zone_data[zone_name]


def get_recs(data):
    domain, question_type = get_question_domain(data)
    qt = ''
    if question_type == b'\x00\x01':
        qt = 'a'

    zone = get_zone(domain)

    return zone[qt], qt, domain


def build_question(domain_parts, rectype):
    qbytes = b''

    for part in domain_parts:
        length = len(part)
        qbytes += bytes([length])

        for char in part:
            qbytes += ord(char).to_bytes(1, byteorder="big")

    if rectype == 'a':
        qbytes += (1).to_bytes(2, byteorder="big")

    qbytes += (1).to_bytes(2, byteorder="big")

    return qbytes


def rec2bytes(rectype, recttl, recvalue):
    rbytes = b'\xc0\x0c'

    if rectype == 'a':
        rbytes = rbytes + bytes([0]) + bytes([1])
    rbytes = rbytes + bytes([0]) + bytes([1])
    rbytes += int(recttl).to_bytes(4, byteorder="big")

    if rectype == 'a':
        rbytes = rbytes + bytes([0]) + bytes([4])

        for part in recvalue.split('.'):
            rbytes += bytes([int(part)])

    return rbytes


def build_response(data):
    # Transaction ID
    TransactionID = data[:2]

    # Flags
    Flags = parse_flags(data[2:4])

    # Question Count
    QDCOUNT = b'\x00\x01'

    # Answer Count
    ANCOUNT = (len(get_recs(data[12:])[0])).to_bytes(2, byteorder='big')

    # Nameserver Count
    NSCOUNT = (0).to_bytes(2, byteorder="big")

    # Additional Count
    ARCOUNT = (0).to_bytes(2, byteorder="big")
    # print(type(TransactionID), type(Flags), type(QDCOUNT), type(ANCOUNT), type(NSCOUNT), type(ARCOUNT))
    dns_header = TransactionID + Flags + QDCOUNT + ANCOUNT + NSCOUNT + ARCOUNT
    dns_body = b''

    records, rectype, domain_name = get_recs(data[12:])

    dns_question = build_question(domain_name, rectype)

    for record in records:
        dns_body += rec2bytes(rectype, record["ttl"], record["value"])

    return dns_header + dns_question + dns_body

while True:
    data, addr = sock.recvfrom(512)
    response = build_response(data)
    sock.sendto(response, addr)
