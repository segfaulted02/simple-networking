#!/usr/bin/env python

import socket
import sys
import argparse
import random

ip_address = '127.0.0.1'
port = 7777

client_game_id = random.getrandbits(24)
serial_message_id = 0 #8-bit
game_flags = 0 #14-bit
game_state = 0 #18-bit

def check_game_id(server_game_id):
    if (serial_message_id and game_flags and game_state):
        if (client_game_id != server_game_id):
            return ValueError

def check_message_id():
    return True

def check_game_state():
    #check that no bits have value 11
    return True