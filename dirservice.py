import socket
import json

def main():
    server_host = "0.0.0.0"
    server_port = 5000
    server_addr = (server_host, server_port)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(server_addr)
    print(f"Directory server listening on {server_host}:{server_port}")

    user_table = {}  # maps username -> (ip, port)

    while True:
        data, addr = sock.recvfrom(1024)
        try:
            msg = json.loads(data.decode("utf-8"))
        except json.JSONDecodeError:
            print("Received invalid JSON")
            continue

        # Registration
        if "UID" in msg and "user IP" in msg and "user PORT" in msg:
            try:
                username = msg["UID"]
                ip = msg["user IP"]
                port = int(msg["user PORT"])
                user_table[username] = (ip, port)
                print(f"Registered {username} -> {ip}:{port}")

                # Send registration ACK
                response = {
                    "error code": 400,  # Registration ACK (changed to 400, orginally put 200)
                    "destination IP": ip,
                    "destination port": port
                }
            except Exception as e:
                print(f"Registration failed: {e}")
                response = {
                    "error code": 600,
                    "destination IP": "",
                    "destination port": 0
                }
            sock.sendto(json.dumps(response).encode("utf-8"), addr)

        # Lookup
        elif "target user" in msg:
            target = msg["target user"]
            if target in user_table:
                dest_ip, dest_port = user_table[target]
                response = {
                    "error code": 400,  # Successful lookup
                    "destination IP": dest_ip,
                    "destination port": dest_port
                }
            else:
                response = {
                    "error code": 600,  # Lookup failed
                    "destination IP": "",
                    "destination port": 0
                }
            sock.sendto(json.dumps(response).encode("utf-8"), addr)
            print(f"Lookup for {target} -> {response}")

        else:
            print("Received unknown message format")

if __name__ == "__main__":
    main()