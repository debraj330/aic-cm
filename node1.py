# ------------------------------
# File: node1.py
# ------------------------------
import zmq
import time
import random

NODE_ID = "N001"
PARAMS = {
    "X": random.randint(1, 10),
    "Y": random.randint(1, 10),
    "Z": random.randint(1, 10)
}

def register_node():
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://192.168.0.178:5558")

    print("[Node] Registering to Register...")
    socket.send_json({"type": "NODE_REGISTER", "node_id": NODE_ID, "params": PARAMS})
    reply = socket.recv_json()
    print("[Node] Register reply:", reply)
    if reply.get("status") != "NODE_REGISTRATION_SUCCESS":
        print("[Node] ERROR: Node registration failed.")
        return None
    return context

def run_rapps():
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    socket.connect("tcp://192.168.0.178:5561")

    print("[Node] Listening for broker instructions...")

    while True:
        msg = socket.recv_json()
        cmd = msg.get("command")
        print(f"[Node] Received command: {cmd}")

        if cmd == "add":
            result = PARAMS["X"] + PARAMS["Y"] + PARAMS["Z"]
            print(f"[Node] add(X,Y,Z) = {result}")
        elif cmd == "multiply":
            result = PARAMS["X"] * PARAMS["Y"] * PARAMS["Z"]
            print(f"[Node] multiply(X,Y,Z) = {result}")
        else:
            print("[Node] Unknown command")

if __name__ == "__main__":
    ctx = register_node()
    if ctx:
        run_rapps()
