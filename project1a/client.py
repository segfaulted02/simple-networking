import socket
import sys
import struct
import random

GAME_ID_MASK = 0xFFFFFF0000000000 #24-bit
MSG_ID_MASK = 0x000000FF00000000 #8-bit
GAME_FLAGS_MASK = 0x00000000FFFC0000 #14-bit
GAME_STATE_MASK = 0x000000000003FFFF #18-bit 
MAX_SIZE = 65000
EMPTY = 0b00
X = 0b01
O = 0b10

def encode_message(game_id, msg_id, flags, game_state, text=""):
    message = (game_id << 40) | (msg_id << 32) | (flags << 18) | game_state
    return struct.pack('!Q', message) + text.encode('utf-8')

def decode_message(received_message):
    message = struct.unpack('!Q', received_message[:8])
    
    text = received_message[8:].decode('utf-8')
    game_id = (message[0] & GAME_ID_MASK) >> 40
    msg_id = (message[0] & MSG_ID_MASK) >> 32
    flags = (message[0] & GAME_FLAGS_MASK) >> 18
    game_state = (message[0]) & GAME_STATE_MASK
    
    return game_id, msg_id, flags, game_state, text

def msg_id_increment(id_msg):
    if (id_msg == 0xFF):
        id_msg = 0x00
        return id_msg
    else:
        return id_msg + 1

def create_game_board(game_state):
    board_array = []
    
    r1c1 = game_state & 0b000000000000000011
    board_array.append(r1c1)
    
    r1c2 = (game_state & 0b000000000000001100) >> 2
    board_array.append(r1c2)
    
    r1c3 = (game_state & 0b000000000000110000) >> 4
    board_array.append(r1c3)
    
    r2c1 = (game_state & 0b000000000011000000) >> 6
    board_array.append(r2c1)
    
    r2c2 = (game_state & 0b000000001100000000) >> 8
    board_array.append(r2c2)
    
    r2c3 = (game_state & 0b000000110000000000) >> 10
    board_array.append(r2c3)
    
    r3c1 = (game_state & 0b000011000000000000) >> 12
    board_array.append(r3c1)
    
    r3c2 = (game_state & 0b001100000000000000) >> 14
    board_array.append(r3c2)
    
    r3c3 = (game_state & 0b110000000000000000) >> 16
    board_array.append(r3c3)
    
    row1: str = get_value(board_array[0]) + " | " + get_value(board_array[1]) + " | " + get_value(board_array[2])
    row2: str = get_value(board_array[3]) + " | " + get_value(board_array[4]) + " | " + get_value(board_array[5])
    row3: str = get_value(board_array[6]) + " | " + get_value(board_array[7]) + " | " + get_value(board_array[8])
    
    print(row1 + "\n----------\n" + row2 + "\n----------\n" + row3)
 
def get_value(val):
    if ((val & 0b11) == 0b01):
        return "X"
    elif ((val & 0b11) == 0b10):
        return "O"
    else:
        return " "

def update_game_state(move, game_state, flags):
    if (flags == 8192):
        game_state |= X << (move * 2)
    elif (flags == 4096):
        game_state |= O << (move * 2)
    return game_state

def main():
    ip_address = "10.10.1.249"
    port = 7775
    addr = (ip_address, port)
    name = str(input("Enter your name: "))
    
    tictactoe = True
    while(tictactoe):
        #get user name and ask if they want to play
        run_game = True
        new_game = input("Hello " + name + ". Would you like to play? (y or n): ")
        if (new_game == 'n'):
            run_game = False
            tictactoe = False
            break
        
        #generate random game id
        game_id = random.randint(0, 0xFFFFFF)
        print("Game ID:", game_id)
        
        #create socket and send initial message
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        init_msg = encode_message(game_id, 0, 0, 0, name)
        client_socket.sendto(init_msg, addr)
            
        #receive initial data from server
        raw_data, _ = client_socket.recvfrom(MAX_SIZE)
        #gather the data and create variables
        game_id, msg_id, flags, game_state, text = decode_message(raw_data)
        print("Server message:")
        print(text)
        
        while run_game:
            print("\nGame Board:")
            create_game_board(game_state)
            
            #check win
            if (flags == 2048):
                print("\nX has won, ending current game")
                break
            elif (flags == 1024):
                print("\nO has won, ending current game")
                break
            elif (flags == 512):
                print("\nTie, ending current game")
                break
            elif (flags == 256):
                print("\nError, stopping current game")
                break
            #bits 6-13 are filled, reserved for future use
            
            print("Diagram:")
            print("0" + " | " + "1" + " | " + "2" + "\n----------\n" + 
                "3" + " | " + "4" + " | " + "5" + "\n----------\n" + 
                "6" + " | " + "7" + " | " + "8\n")
            
            move = int(input("See diagram for board map\nEnter box to play move (0-8): "))
            
            #update game state
            game_state = update_game_state(move, game_state, flags)
            #print board
            create_game_board(game_state)
            
            #increment serial msg id
            msg_id = msg_id_increment(msg_id)
            
            #send data to server
            msg2 = encode_message(game_id,msg_id,0,game_state,name)
            client_socket.sendto(msg2, addr)
            
            #get data from server
            raw_data, _ = client_socket.recvfrom(MAX_SIZE)
            #gather the data and create variables
            game_id, msg_id, flags, game_state, text = decode_message(raw_data)

            print("\nServer message: "+text)
        
    client_socket.close()

if __name__ == "__main__":
    main()