# ------------------------------
# File: m_broker.py
# ------------------------------
import zmq

def start_broker():
    context = zmq.Context()

    # Input from AI Control Engine
    pull_socket = context.socket(zmq.PULL)
    pull_socket.bind("tcp://192.168.0.178:5560")

    # Output to Node
    push_socket = context.socket(zmq.PUSH)
    push_socket.bind("tcp://192.168.0.178:5561")

    print("[Broker] Broker started. Waiting for AI instructions...")

    while True:
        msg = pull_socket.recv_json()
        print("[Broker] Received instruction:", msg)
        push_socket.send_json(msg)
        print("[Broker] Forwarded to Node.")

if __name__ == "__main__":
    start_broker()
