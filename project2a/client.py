import json
import socket
import sys
import signal
import threading
import ast
from typing import List

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def signal_handler():
    disconnect_msg = json.dumps({"action": "disconnect"})
    connection.send(disconnect_msg.encode('utf-8'))
    print("\nKeyboard Interrupt, disconnecting\n")
    sys.exit(0)

#signal.signal(signal.SIGINT, signal_handler)

def connect_server(host, port, user_name, targets_list):
    connection.connect((host, port))
    
    formatted_targets = [f"#{target.lstrip('#')}" for target in targets_list]
    message = json.dumps({
        "action": "connect",
        "user_name": f"@{user_name}",
        "targets": formatted_targets
    })
    connection.send(message.encode('utf-8'))

def send_message(user_name, target, message):
    data = json.dumps({
        "action": "message",
        "user_name": f"@{user_name}",
        "target": target,
        "message": message[:3800]
        })
    connection.send(data.encode('utf-8'))
    
def listen():
    while True:
        response = connection.recv(4096).decode('utf-8')
        print("----------Server Message----------")
        if (response):
            response_data = json.loads(response)
            if (response_data["status"] == "disconnect"):
                print("Server is shutting down, disconnecting")
                return
            elif (response_data["status"] == "error"):
                print("Error from server: ", response_data["message"])
            elif (response_data["status"] == "chat"):
                for msg in response_data["history"]:
                    new_msg = ast.literal_eval(msg)
                    print("Message from: ", new_msg["from"], " to ", new_msg["target"], ": ", new_msg["message"])
            else:
                print("Unknown response: ", response_data)
        else:
            print("Server disconnected")
            print("----------------------------------\n")
            sys.exit(0)
        print("----------------------------------\n")
    
def main(ip, port):
    user_name = input("Enter your username: ").strip()[:60]
    initial_targets = input("Enter the chat room(s) to listen to, separated by spaces: ").strip().split()
        
    connect_server(ip, port, user_name, initial_targets)
    print("Connected to server\n")
    
    receive_thread = threading.Thread(target=listen, daemon=True)
    receive_thread.start()
        
    try:
        while True:
            try:
                print("To send a message, enter your message followed by the user or chat room")
                message = input().strip()
                split = message.rsplit(' ', 1)
                
                if (len(split) == 2 and (split[1].startswith('@') or split[1].startswith('#'))):
                    message, target = split
                    send_message(user_name, target, message)
                else:
                    print("Invalid input\n")
            except KeyboardInterrupt as e:
                raise
    except KeyboardInterrupt as e:
        signal_handler()
    finally:
        connection.close()
        sys.exit(0)
        
if __name__ == "__main__":
    if (len(sys.argv) != 3):
        print("Incorrect format")
    else:
        main(sys.argv[1], int(sys.argv[2]))