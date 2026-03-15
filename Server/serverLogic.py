import threading
import queue
from serverComm import serverComm
from random import choice
from string import ascii_uppercase

db = DB()
commands = {}
# [ip] = [username, call_id]
open_clients = {}
#[call_id] = [call_key, list_of_clients]
meetings = {"123": ["Matan's Meeting",["username"]]}

def log_in(comm, username, password):
    """
    Return if successfully logged to account
    :param username:
    :param password:
    :return:
    """
    if db.verify_user(username, password):
        msg2send = serverProtocol.build_msg("1")
    else:
        msg2send = serverProtocol.build_msg("0")
    comm.send_msg(msg2send)


def sign_up(comm, username, password):
    """
    Return if successfully signed up account
    :param username:
    :param password:
    :return:
    """
    if db.add_user(username, password):
        msg2send = serverProtocol.build_msg("1")
    else:
        msg2send = serverProtocol.build_msg("0")
    comm.send_msg(msg2send)

def generate_shared_key():
    """
    generate random 5 char string for meeting key
    :return: the key
    """
    return ''.join(choice(ascii_uppercase) for i in range(5))
def generate_call_id()
    """
    generate random 5 char string for meeting id
    :return: 
    """
    return ''.join(choice(ascii_uppercase) for i in range(5))

def close_call(comm, call_id):
    """

    :param call_id:
    :return:
    """
    if call_id in meetings.keys():
        for i in meetings[call_id][1]:
            comm.send_msg(serverProtocol.close_meeting())
    else:
        print("call id is incorrect")
def handle_disconnect(comm, a):
    """
    Disconnect the clients safely
    :return:
    """


def main():
    """
    Create comm objects queues and starts handle_msgs
    :return:
    """
    msgsQ = queue.Queue()
    myServer = ServerComm(1231, msgsQ)
    threading.Thread(target=handle_msgs, args=(myServer, msgsQ)).start()

def handle_msgs(comm, msgQ):
    """
    Handle incoming messages from clients.
    :param comm: Server communication object
    :param msgQ: Queue to receive messages
    :return: None
    """
    ip, msg = msgQ.get()
    opcode, data = serverProtocol.unpack(msg)
    if opcode in commands.keys():
        commands[opcode](comm, data)
    else:
        print(f"Unknown opcode received: {opcode}")

