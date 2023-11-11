import json
import socket
import select
import sys

clients = {}
messages = []

def send_message(client, message):
    if (message['target'] == clients[client]['user_name']):
        data = json.dumps({
            "status": "chat",
            "history": [
                {
                    "target": message['target'],
                    "from": message['user_name'],
                    "message": message['message']
                }
            ]
        })
        client.send(data.encode('utf-8'))
    elif (message['target'] in clients[client]['targets']):
        data = json.dumps({
            "status": "chat",
            "history": [
                {
                    "target": message['target'],
                    "from": message['user_name'],
                    "message": message['message']
                }
            ]
        })
        client.send(data.encode('utf-8'))
        
def receive(connection):
    data = connection.recv(4096).decode('utf-8')
    return json.loads(data)
    
def main(ip, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #ip, port = "127.0.0.1", 5555
    server_socket.bind((ip, port))
    server_socket.listen()
    
    inputs = [server_socket]
    
    try:
        while True:
            sockets, _, _ = select.select(inputs, [], [])
            
            for sock in sockets:
                if (sock is server_socket):
                    client_socket, client_addr = server_socket.accept()
                    inputs.append(client_socket)
                else:
                    try:
                        data = receive(sock)
                        if (data['action'] == 'connect'):
                            clients[sock] = data
                        elif (data['action'] == 'message'):
                            messages.append(data)
                        elif (data['action'] == 'disconnect'):
                            if sock in clients:
                                del clients[sock]
                            inputs.remove(sock)
                            sock.close()
                        
                        for message in messages:
                            for client in clients:
                                send_message(client, message)
                        messages.clear()
                    except json.JSONDecodeError:
                        error_message = {"status": "error", "message": "Malformed JSON"}
                        send_message(sock, error_message)
                    except UnicodeDecodeError:
                        error_message = {"status": "error", "message": "UTF-8 Error"}
                        send_message(sock, error_message)
                    except KeyError:
                        error_message = {"status": "error", "message": "KeyError"}
                        send_message(sock, error_message)
                    except ValueError:
                        error_message = {"status": "error", "message": "ValueError"}
                        send_message(sock, error_message)
    except KeyboardInterrupt:
        print("Shutting down server")
    finally:
        server_socket.close()

if __name__ == "__main__":
    if (len(sys.argv) != 3):
            print("Incorrect format")
    else:
        main(sys.argv[1], int(sys.argv[2]))