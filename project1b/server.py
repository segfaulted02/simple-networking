import socket
import struct
import random
import threading
from concurrent.futures import ThreadPoolExecutor
import time

GAME_ID_MASK = 0xFFFFFF0000000000 #24-bit
MSG_ID_MASK = 0x000000FF00000000 #8-bit
GAME_FLAGS_MASK = 0x00000000FFFC0000 #14-bit
GAME_STATE_MASK = 0x000000000003FFFF #18-bit
MAX_SIZE = 65000
EMPTY = 0b00
ERROR_FLAG = (1 << 8)
X = 0b01
O = 0b10
IP = ''
PORT = 5555

GAME_ID_INDEX = 0
GAME_STATE_INDEX = 1
MSG_ID_INDEX = 2
FLAGS_INDEX = 3
PLAYER_INDEX = 4
TEXT_INDEX = 5
TIME_INDEX = 6
ADDRESS_INDEX = 7

#Listens on all interfaces, on port 5555
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((IP, PORT))

games = {}
game_locks = {}
global_lock = threading.Lock()
flag_mapping = {'X': (1 << 11), 'O': (1 << 10), 'Tie!': (1 << 9)}

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

def update_game_state(move, game_state, player):
    if (player == X):
        game_state |= X << (move * 2)
    elif (player == O):
        game_state |= O << (move * 2)
    return game_state

def square_filled(game_state, user_input):
    square_value = (game_state >> (user_input * 2)) & 0b11
    return square_value != EMPTY

def calculate_move(game_state, player):
    moved = False
    while (not moved):
        num = random.randint(0,8)
        if (not square_filled(game_state, num)):
            game_state = update_game_state(num, game_state, player)
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
    
    if (game_state == 0):
        return False, ' '
    
    #check rows
    for i in range(0,9,3):
        if ((get_value(board[i]) == get_value(board[i+1]) == get_value(board[i+2]))
            and get_value(board[i]) != ' '):
            return True, get_value(board[i])
    #check columns
    for i in range(3):
        if ((get_value(board[i]) == get_value(board[i+3]) == get_value(board[i+6]))
            and get_value(board[i]) != ' '):
            return True, get_value(board[i])
    #check diagonals
    if ((get_value(board[0]) == get_value(board[4]) == get_value(board[8]))
        and get_value(board[0]) != ' '):
        return True, get_value(board[0])
    if ((get_value(board[2]) == get_value(board[4]) == get_value(board[6]))
        and get_value(board[2]) != ' '):
        return True, get_value(board[2])
    
    if ' ' not in [get_value(cell) for cell in board]:
        return True, "Tie!"
    
    return False, ' '

def check_valid_game_state(old_state, new_state):
    #check that player changed ONLY 1 bit (too many moves)
    changed_bits = old_state ^ new_state
    count = 0
    while changed_bits:
        count += changed_bits & 1
        changed_bits >>= 1
    if (count >= 2):
        return True
    
    #check if wrong player moved, I do this by comparing to see if there 
    #are 2 or more X's than O's, or vice versa
    count_01 = 0
    count_10 = 0
    for i in range(0, 18, 2):
        two_bits = (new_state >> i) & 0b11
        if (two_bits == 0b01):
            count_01 += 1
        elif (two_bits == 0b10):
            count_10 += 1
    if (abs(count_01 - count_10) >= 2):
        return True
    
    #check if client played move that was already filled (unavailable location)
    for i in range(9):
        old_square = (old_state >> (i * 2)) & 0b11
        new_square = (new_state >> (i * 2)) & 0b11
        if (old_square != new_square and new_square != EMPTY):
            return True
    return False

def check_errors(game_id, msg_id, flags, game_state, games):
    if ((game_id not in games) and (msg_id !=0) and (game_state !=0) and (flags != 0)):
        return True, "Error, something is amiss...Game ID not recognized!"
    elif (msg_id != games[game_id][MSG_ID_INDEX] + 1):
        return True, "Error, something is amiss...Msg ID is invalid!"
    elif (check_valid_game_state(game_state, games[game_id][GAME_STATE_INDEX])):
        return True, "Error, something is amiss...Game state is invalid!"
    else:
        return False, ""

def handle_client(data, client_address, server_socket):
    game_id, msg_id, flags, game_state, text = decode_message(data)
    print("Received data from client with game ID:", game_id)
    
    with global_lock:
        #check if game_id doesn't exist in server, then create a new game
        if ((game_id not in games) and (msg_id == 0) and (game_state == 0) and (flags == 0)):
            text = "Hello " + text + ", a pleasure to play with you.\n"
            games[game_id] = [
                game_id, #game_id
                game_state, #game_state
                random.randint(0,100), #msg_id, created by server
                flags, #flags to send to client
                X if (random.randint(0,1) == 1) else O, #SERVER player
                text, #text to send/receive
                time.time(),
                client_address
            ]
        else:
            #check for errors in the data, if not new data
            has_error, error_msg = check_errors(game_id, msg_id, flags, game_state, games)
            if (has_error):
                flags = ERROR_FLAG
                updated_message = encode_message(game_id, msg_id, flags, game_state, error_msg)
                server_socket.sendto(updated_message, client_address)
                return
            #update dictionary with values
            else:
                games[game_id][GAME_STATE_INDEX] = game_state
                games[game_id][MSG_ID_INDEX] = msg_id
                games[game_id][FLAGS_INDEX] = 0
                games[game_id][TEXT_INDEX] = text
                games[game_id][TIME_INDEX] = time.time()
        
    with game_locks.setdefault(game_id, threading.Lock()):
        current_game = games[game_id]
        
        #check wins after player moves
        did_win, win_player = check_win(current_game[GAME_STATE_INDEX])
        if (did_win):
            current_game[TEXT_INDEX] = f"{win_player} has won! Ending game" if "Tie!" else f"{win_player} Ending game"
            current_game[FLAGS_INDEX] = flag_mapping[win_player]
            updated_message = encode_message(current_game[GAME_ID_INDEX], current_game[MSG_ID_INDEX], current_game[FLAGS_INDEX], current_game[GAME_STATE_INDEX], current_game[TEXT_INDEX])
            server_socket.sendto(updated_message, client_address)
            print("Concluded game with ID:", game_id)
            return
        
        #play move, checks if server plays as X or O, and if initial move and O, doesnt move
        if (not (current_game[GAME_STATE_INDEX] == 0 and current_game[PLAYER_INDEX] == O)):
            current_game[GAME_STATE_INDEX] = calculate_move(current_game[GAME_STATE_INDEX], current_game[PLAYER_INDEX])
        
        #adjust flags and text for PLAYER to send back
        if (current_game[PLAYER_INDEX] == X):
            current_game[FLAGS_INDEX] = (1 << 12)
            current_game[TEXT_INDEX] = "You are O! Play your O!"
        elif (current_game[PLAYER_INDEX] == O):
            current_game[FLAGS_INDEX] = (1 << 13)
            current_game[TEXT_INDEX] = "You are X! Play your X!"
        
        #update msg_id
        current_game[MSG_ID_INDEX] += 1
        
        #check wins after server moves
        did_win, win_player = check_win(current_game[GAME_STATE_INDEX])
        if (did_win):
            current_game[TEXT_INDEX] = f"{win_player} has won! Ending game" if "Tie!" else f"{win_player} Ending game"
            current_game[FLAGS_INDEX] = flag_mapping[win_player]
            updated_message = encode_message(current_game[GAME_ID_INDEX], current_game[MSG_ID_INDEX], current_game[FLAGS_INDEX], current_game[GAME_STATE_INDEX], current_game[TEXT_INDEX])
            server_socket.sendto(updated_message, client_address)
            print("Concluded game with ID:", game_id)
            return

        updated_message = encode_message(current_game[GAME_ID_INDEX], current_game[MSG_ID_INDEX], current_game[FLAGS_INDEX], current_game[GAME_STATE_INDEX], current_game[TEXT_INDEX])
        server_socket.sendto(updated_message, client_address)
        
        print("Sent data to client with game ID:", game_id)

def check_timeout():
    while True:
        with global_lock:
            #checks to see if game has been inactive for at least 5 minutes
            old_games = [x for x, game in games.items() if time.time() - game[TIME_INDEX] >= 300]
            for x in old_games:
                with game_locks.get(x, threading.Lock()):
                    print("Timout for game with ID, removing game:", x)
                    message = encode_message(games[x][GAME_ID_INDEX], games[x][MSG_ID_INDEX], ERROR_FLAG, games[x][GAME_STATE_INDEX], "Your game has timed out!")
                    sock.sendto(message, games[x][ADDRESS_INDEX])
                    
                    games.pop(x)
                    game_locks.pop(x)
        #checks every 30 seconds to see if a thread has been inactive for over 5 minutes
        time.sleep(30)

def main():
    print("Server started on port 5555")
    
    threads = ThreadPoolExecutor(max_workers=10)
    cleanup_thread = threading.Thread(target=check_timeout, daemon=True)
    cleanup_thread.start()
    
    while True:
        data, address = sock.recvfrom(MAX_SIZE)
        #handle_client(data, address, sock)
        threads.submit(handle_client, data, address, sock)
        
if __name__ == "__main__":
    main()