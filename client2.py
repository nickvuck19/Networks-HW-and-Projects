import sys
import socket
import threading
import json
import time

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

def registration(sock, directory_addr, username, local_host, local_port):
    """
    Send the registration info to the directory service useing the following key_value pairs:
    UID, user IP, user PORT
    """
    registration_msg = {"UID": username, "user IP": local_host, "user PORT": local_port}
    sock.sendto(json.dumps(registration_msg).encode("utf-8"), directory_addr)

def lookup(sock, directory_addr, dest_username):
    request = {"target user": dest_username}

    while True:
        try:
            sock.sendto(json.dumps(request).encode("utf-8"), directory_addr)
            data, addr = sock.recvfrom(1024)
            response = json.loads(data.decode("utf-8"))

            # Only treat 400 as a valid lookup
            if response.get("error code") == 400:
                dest_ip = response.get("destination IP")
                dest_port = response.get("destination port")
                if dest_ip is None or dest_port is None:
                    print("Directory response missing IP/port. Retrying...")
                    time.sleep(1)
                    continue


                return dest_ip, int(dest_port)

            else:
                print(f"Destination '{dest_username}' not found. Retrying in 5 seconds...")
                time.sleep(5)

        except Exception as e:
            print(f"Failed to get response from directory: {e}. Retrying...")
            time.sleep(5)

def sender(sock, dest_tuple, username, dest_identifier):
    seq_num = 0
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
            sock.sendto(json_data, dest_tuple)
            print(f"{username}>>{message}")
            seq_num += 1

        except KeyboardInterrupt:
            print("\nExiting chat...")
            break

def receiver(sock, expected_seq_num, username):
    while True:
        try:
            data, addr = sock.recvfrom(2048)
            try:
                msg = json.loads(data.decode("utf-8"))
            except json.JSONDecodeError:
                print("Received invalid JSON")
                continue



            if msg.get("UID") == username:
                continue

            if "Message" not in msg or "Seq. num" not in msg:
                continue

            # Validate the expected sequence number
            if msg.get("Seq. num") == expected_seq_num[0]:
                print(f"{msg.get('UID')}>>{msg.get('Message')}", flush=True)
                expected_seq_num[0] += 1
            else:
                print("Out of order message received (ignored)")
        except KeyboardInterrupt:
            print("\nStopping receiver...")
            break

def main():
    if len(sys.argv) != 5:
        print("Usage: python3 client2.py <username> <local_host:local_port> <dest_username> <directory_host:directory_port>")
        sys.exit(1)

    username = sys.argv[1]
    local_host, local_port = parse_hostport(sys.argv[2])
    dest_username = sys.argv[3]
    directory_host, directory_port = parse_hostport(sys.argv[4])
    directory_addr = (directory_host, directory_port)

    # Separate socket for directory communication
    dir_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Chat socket for sending/receiving messages
    chat_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    chat_sock.bind((local_host, local_port))

    # Registration
    registration(dir_sock, directory_addr, username, local_host, local_port)

    # Lookup — will retry until target user registers
    dest_host, dest_port = lookup(dir_sock, directory_addr, dest_username)
    dest_identifier = f"{dest_host}:{dest_port}"
    print(f"Chatting with {dest_username} at {dest_identifier}")

    # Start receiver thread for chat messages only
    expected_seq_num = [0]
    recv_thread = threading.Thread(target=receiver, args=(chat_sock, expected_seq_num, username), daemon=True)
    recv_thread.start()

    # Chat sender uses chat socket
    dest_tuple = (dest_host, dest_port)
    sender(chat_sock, dest_tuple, username, dest_identifier)


if __name__ == "__main__":
    main()