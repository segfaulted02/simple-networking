import socket
import sys
import struct
import random

game_id_mask = 0xFFFFFF
msg_id_mask = 0xFF
game_flags_mask = 0xFFFC
game_state_mask = 0xFFFFC
max_size = 65000

def encode_message(game_id, msg_id, flags, game_state, text=""):
    message = (game_id << 40) | (msg_id << 32) | (flags << 18) | game_state
    return struct.pack('!Q', message) + text.encode('utf-8')

def decode_message(received_message):
    message = struct.unpack('!Q', received_message[:8])
    
    text = received_message[8:].decode('utf-8')
    game_id = (message[0] >> 40) & game_id_mask
    msg_id = (message[0] >> 32) & msg_id_mask
    game_flags = (message[0] >> 18) & game_flags_mask
    game_state = (message[0]) & game_state_mask
    
    return game_id, msg_id, game_flags, game_state, text

def msg_id_increment(id_msg):
    if (id_msg == 0xFF):
        id_msg = 0x00
    else:
        id_msg + 1
    
def map_board(game_state):
    r1c1 = game_state & 0x000000000000000011 #0x3
    r1c2 = game_state & 0x000000000000001100 #0xC
    r1c2 >> 2
    r1c3 = game_state & 0x000000000000110000 #0x30
    r1c3 >> 4
    r2c1 = game_state & 0x000000000011000000 #0xC0
    r1c3 >> 6
    r2c2 = game_state & 0x000000001100000000 #0x300
    r1c3 >> 8
    r2c3 = game_state & 0x000000110000000000 #0xC00
    r1c3 >> 10
    r3c1 = game_state & 0x000011000000000000 #0x3000
    r1c3 >> 12
    r3c2 = game_state & 0x001100000000000000 #0xC000
    r1c3 >> 14
    r3c3 = game_state & 0x110000000000000000 #0x30000
    r1c3 >> 16
    
    return [r1c1,r1c2,r1c3,r2c1,r2c2,r2c3,r3c1,r3c2,r3c3]

def create_game_board(board):
    row1: str = get_value(board[0]) + " | " + get_value(board[1]) + " | " + get_value(board[2])
    row2: str = get_value(board[3]) + " | " + get_value(board[4]) + " | " + get_value(board[5])
    row3: str = get_value(board[6]) + " | " + get_value(board[7]) + " | " + get_value(board[8])
    
    print(row1 + "\n----------\n" + row2 + "\n----------\n" + row3)
    
def get_value(val):
    if (val == 0x01):
        return "X"
    elif (val == 0x10):
        return "O"
    elif (val == 0x00):
        return " "
    
def main():
    ip_address = "44.218.223.102"
    port = 7775
    addr = (ip_address, port)
    
    run_game = True
    while run_game:
        new_game = input("Would you like to play? (y or n) ")
        if (new_game == 'n'):
            run_game = False
            break
        
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
        game_id = random.randint(0, 0xFFFFFF)
        print("Game ID:", game_id)
        name = input("Enter your name ")
    
        msg = encode_message(game_id, 0, 0, 0, name)
        client_socket.sendto(msg, addr)
        
        print("Waiting for server...")

        #get data from server
        raw_data, _ = client_socket.recvfrom(max_size)
        #gather the data and create variables
        game_id, msg_id, flags, game_state, text = decode_message(raw_data)
        
        print("Established connection with server")
        
        #establish team and which letter to fill squares
        team = ""
        if (flags & 0x10):
            team = "X"
        elif (flags & 0x01):
            team = "O"
        
        #print the server message
        print(text)
        
        if (flags & 0x100):
            print ("X has won!")
            break
        elif (flags & 0x1000):
            print ("O has won!")
            break
        
        print("0" + " | " + "1" + " | " + "2" + "\n----------\n" + 
              "3" + " | " + "4" + " | " + "5" + "\n----------\n" + 
              "6" + " | " + "7" + " | " + "8")
        move = input("Enter box to play move (0-8)\nSee diagram for board map")
        if ((game_state >> (move * 2)) != 0x00):
            print("Invalid move")
            
        if (flags & (1 << 0)):
            game_state |= "X" << (move * 2)
        else:
            game_state |= "O" << (move * 2)
        
        #update game state
        
        
        #increment serial msg id
        msg_id_increment(msg_id)
        
        msg2 = encode_message(game_id,msg_id,0,game_state)
        client_socket.sendto(msg2, addr)
        
    client_socket.close()
    
if __name__ == "__main__":
    main()
    #test_msg = encode_message(111,0,0,0,"hello, world!")
    #print(test_msg)
    #test_data = decode_message(test_msg)
    #print("returned")
    #print(test_data)