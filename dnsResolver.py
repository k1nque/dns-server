import socket

ROOT_DNS_IP = ("198.41.0.4", 53)
resolve_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)



def send_dns_request(dns_request, server_addr):
    resolve_sock.sendto(dns_request, server_addr)
    resolve_sock.recv(512)