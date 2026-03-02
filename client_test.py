import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(b"Hello server", ("127.0.0.1", 5000))
print("Message sent", flush=True)