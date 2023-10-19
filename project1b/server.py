import socket
import struct
import random
import threading
from concurrent.futures import ThreadPoolExecutor

GAME_ID_MASK = 0xFFFFFF0000000000 #24-bit
MSG_ID_MASK = 0x000000FF00000000 #8-bit
GAME_FLAGS_MASK = 0x00000000FFFC0000 #14-bit
GAME_STATE_MASK = 0x000000000003FFFF #18-bit 
MAX_SIZE = 65000
EMPTY = 0b00
ERROR_FLAG = 0b100000
X = 0b01
O = 0b10
IP = "127.0.0.1"
PORT = 5555

games = {}
threads = ThreadPoolExecutor(max_workers=10)

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

def get_value(val):
    if ((val & 0b11) == 0b01):
        return "X"
    elif ((val & 0b11) == 0b10):
        return "O"
    else:
        return " "

def update_game_state(move, game_state, flags):
    if (flags == (1 << 13)):
        game_state |= X << (move * 2)
    elif (flags == (1 << 12)):
        game_state |= O << (move * 2)
    return game_state

def square_filled(game_state, user_input):
    square_value = (game_state >> (user_input * 2)) & 0b11
    return square_value != EMPTY

def calculate_move(game_state, flags):
    moved = False
    while (not moved):
        num = random.randint(0,8)
        if (not square_filled(game_state, num)):
            update_game_state(num, game_state, flags)
            moved = True
    return game_state
     
def create_game_board(game_state):
    board_array = []
    
    masks_shifts = [
        (0b000000000000000011, 0),
        (0b000000000000001100, 2),
        (0b000000000000110000, 4),
        (0b000000000011000000, 6),
        (0b000000001100000000, 8),
        (0b000000110000000000, 10),
        (0b000011000000000011, 12),
        (0b001100000000000011, 14),
        (0b110000000000000011, 16),
    ]
    
    for mask, shift, in masks_shifts:
        board_array.append((game_state & mask) >> shift)
    
    #for use if you want to print the board
    row1: str = get_value(board_array[0]) + " | " + get_value(board_array[1]) + " | " + get_value(board_array[2])
    row2: str = get_value(board_array[3]) + " | " + get_value(board_array[4]) + " | " + get_value(board_array[5])
    row3: str = get_value(board_array[6]) + " | " + get_value(board_array[7]) + " | " + get_value(board_array[8])
    
    return board_array
    
def check_win(game_state):
    board = create_game_board(game_state)
    #check rows
    for i in range(0,9,3):
        if ((get_value(board[i]) == get_value(board[i+1]) == get_value(board[i+2]))
            & get_value(board[i]) != " "):
            return True, get_value(board[i])
    #check columns
    for i in range(3):
        if ((get_value(board[i]) == get_value(board[i+3]) == get_value(board[i+6]))
            & get_value(board[i]) != " "):
            return True, get_value(board[i])
    #check diagonals
    if ((get_value(board[0]) == get_value(board[4]) == get_value(board[8]))
        & get_value(board[0]) != " "):
        return True, get_value(board[0])
    if ((get_value(board[2]) == get_value(board[4]) == get_value(board[6]))
        & get_value(board[0]) != " "):
        return True, get_value(board[2])
    #update flags???
    
    return False, " "

def check_valid_game_state(old_state, new_state):
    #check that player changed ONLY 1 bit (too many moves)
    changed_bits = old_state ^ new_state
    count = 0
    while changed_bits:
        count += changed_bits & 1
        changed_bits >>= 1
    if (count != 1):
        return False
    
    #check if wrong player moved, I do this by comparing to see if there 
    #are 2 or more X's than O's, or vice versa
    count_01 = 0
    count_10 = 0
    for i in range(0, new_state.length(), 2):
        two_bits = (new_state >> i) & 0b11
        if (two_bits == 0b01):
            count_01 += 1
        elif (two_bits == 0b10):
            count_10 += 1
    if (abs(count_01 - count_10) >= 2):
        return False
    
    #check if client played move that was already filled (unavailable location)
    for i in range(9):
        old_square = (old_state >> (i * 2)) & 0b11
        new_square = (new_state >> (i * 2)) & 0b11
        if (old_square != new_square):
            if (old_square != EMPTY):
                return False
    
    return True

def handle_client(data, client_address, server_socket):
    print("Client found and accepted")
    game_id, msg_id, flags, game_state, text = decode_message(data)
    
    #check if game_id doesn't exist in server, then create a new game
    if ((game_id not in games) & (msg_id == 0) & (game_state == 0) & (flags == 0)):  
        text = "Hello " + text + ", a pleasure to play with you.\n"
        games[game_id] = {
            'game_state': game_state,
            'msg_id': msg_id,
            'flags': flags,
            'player': X if (random.randint(0,1) == 1) else O,
            'text': text,
        }
    #check if game_id doesn't exist in server, if values are not initially 0, return error
    elif ((game_id not in games) & (msg_id !=0) & (game_state !=0) & (flags != 0)):
        text = "Error, something is amiss...Game ID not recognized!"
        flags &= ERROR_FLAG
        updated_message = encode_message(game_id, 0, flags, 0, text)
        server_socket.sendto(updated_message, client_address)
        return
    #check if msg_id is incorrect
    elif (msg_id != games[game_id]['msg_id'] + 1):
        text = "Error, something is amiss...Msg ID is invalid!"
        flags &= ERROR_FLAG
        updated_message = encode_message(game_id, 0, flags, 0, text)
        server_socket.sendto(updated_message, client_address)
        return
    #check if game_state is invalid
    elif (check_valid_game_state(game_state, games[game_id]['game_state'])):
        text = "Error, something is amiss...Game state is invalid!"
        flags &= ERROR_FLAG
        updated_message = encode_message(game_id, 0, flags, 0, text)
        server_socket.sendto(updated_message, client_address)
        return
    #update dictionary with values
    else:
        games[game_id]['game_state'] = game_state
        games[game_id]['msg_id'] = msg_id
        games[game_id]['flags'] = 0
        games[game_id]['text'] = text
    
    current_game = games[game_id]
    print("got here!1")
    
    #check wins
    if (check_win(current_game['game_state']) == True, "X"):
        current_game['text'] = "X has won! Ending game"
        print("X has won! Ending game")
        current_game['flags'] &= 0b100
        updated_message = encode_message(current_game['game_id'], current_game['msg_id'], 
                                         current_game['flags'], current_game['game_state'], current_game['text'])
        server_socket.sendto(updated_message, client_address)
        return
    elif (check_win(current_game['game_state']) == True, "O"):
        current_game['text'] = "O has won! Ending game"
        print("O has won! Ending game")
        current_game['flags'] &= 0b1000
        updated_message = encode_message(current_game['game_id'], current_game['msg_id'], 
                                         current_game['flags'], current_game['game_state'], current_game['text'])
        server_socket.sendto(updated_message, client_address)
        return
    elif (check_win(current_game['game_state']) == True, " "):
        current_game['text'] = "Tie! Ending game"
        print("Tie! Ending game")
        current_game['flags'] &= 0b10000
        updated_message = encode_message(current_game['game_id'], current_game['msg_id'], 
                                         current_game['flags'], current_game['game_state'], current_game['text'])
        server_socket.sendto(updated_message, client_address)
        return

    print("got here!2")
    
    #adjust flags for SERVER, then play move
    if (current_game['player'] == X):
        current_game['flags'] &= X
    elif (current_game['player'] == O):
        current_game['flags'] &= O
    current_game['game_state'] = calculate_move(current_game['game_state'], current_game['flags'])
    print("got here!3")
    
    #adjust flags and text for PLAYER to send back
    if (current_game['player'] == X):
        current_game['flags'] &= O
        current_game['text'] = "You are O! Play your O!"
    elif (current_game['player'] == O):
        current_game['flags'] &= X
        current_game['text'] = "You are X! Play your X!"
    
    #update msg_id
    current_game['msg_id'] += 1
    
    print("got here!4")
    
    updated_message = encode_message(current_game['game_id'], current_game['msg_id'], 
                                     current_game['flags'], current_game['game_state'], current_game['text'])
    server_socket.sendto(updated_message, client_address)
    print("got here!5")

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((IP, PORT))
        print("Server started on 127.0.0.1:5555")
        while True:
            data, address = sock.recvfrom(MAX_SIZE)
            threads.submit(handle_client, data, address, sock)

if __name__ == "__main__":
    main()