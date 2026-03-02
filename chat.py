import sys
import socket
import threading
import json

def parse_hostport(arg):
    """
    Parse a string with the form host:port and return it as (host, port)
    Example: 192.168.1.5:2000 returns as (192.168.1.5, 5000)
    """
    try:
        host, portstr = arg.split(":")
        port = int(portstr)
        return host, port
    except ValueError:
        print(f"Error: invalid host:port format '{arg}'. Expected host:port")
        sys.exit(1)

def sender(sock, dest, username, dest_identifier):
    seq_num = 0;
    while True:
        try:
            message = input()
            if len(message) > 1024:
                print("Error: message is too long (max 1024 characters).")
                continue
            data = {
                "Version": "v1",
                "Seq. num": seq_num,
                "UID": username,
                "DID": dest_identifier,
                "Message": message
            }

            json_data = json.dumps(data).encode("utf-8")
            sock.sendto(json_data, dest)
            seq_num += 1
        except KeyboardInterrupt:
            print("\nExisting chat...")
            break

def receiver(sock, expected_seq_num):
    while True:
        try:
            data, addr = sock.recvfrom(2048)
            try:
                msg = json.loads(data.decode("utf-8"))
            except json.JSONDecodeError:
                print("Received invalid JSON")
                continue

            # Validate the expected sequence number
            if msg.get("Seq. num") == expected_seq_num[0]:
                print(f"{msg.get('UID')}>>{msg.get('Message')}")
                expected_seq_num[0] += 1
            else:
                print("Out of order message received (ignored)")
        except KeyboardInterrupt:
            print("\nStopping receiver...")
            break

def main():
    if len(sys.argv) != 4:
        print("Usage: python3 chat.py <username> <dest_host:dest_port> <local_host:local_port>")
        sys.exit(1)

    username = sys.argv[1]
    dest_host, dest_port = parse_hostport(sys.argv[2])
    local_host, local_port = parse_hostport(sys.argv[3])
    dest_identifier = sys.argv[2]

    # Create the UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((local_host, local_port))

    print(f"Chat started as {username}. Type messages below:")

    expected_seq_num = [0]

    # Start the receiver thread
    recv_thread = threading.Thread(target=receiver, args=(sock, expected_seq_num), daemon=True)
    recv_thread.start()

    # Run sender in the main thread
    sender(sock, (dest_host, dest_port), username, dest_identifier)


if __name__ == "__main__":
    main()