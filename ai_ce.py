# ------------------------------
# File: ai_ce.py
# ------------------------------
import zmq
import time

AI_ID = "AI001"
APP_ID = "APP1"
VALID_AI_ID = "AI001"
VALID_APP_ID = "APP1"

def register_ai_and_app():
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://192.168.0.178:5558")  # register1.py REQ/REP

    # Step 1: Register AI
    print("[AI_CE] Registering AI Control Engine...")
    socket.send_json({"type": "AI_REGISTER", "ai_id": AI_ID})
    reply = socket.recv_json()
    print("[AI_CE] Received:", reply)
    if reply.get("status") != "AI_REGISTRATION_SUCCESS":
        print("[AI_CE] ERROR: AI registration failed.")
        return None, None

    # Step 2: Register Application
    print(f"[AI_CE] Registering Application: {APP_ID}")
    socket.send_json({"type": "APP_REGISTER", "app_id": APP_ID})
    reply = socket.recv_json()
    print("[AI_CE] Received:", reply)
    if reply.get("status") != "APP_REGISTRATION_SUCCESS":
        print("[AI_CE] ERROR: App registration failed.")
        return None, None

    return context

def send_instructions():
    context = zmq.Context()
    broker_socket = context.socket(zmq.PUSH)
    broker_socket.connect("tcp://192.168.0.178:5560")  # m_broker.py PULL

    while True:
        cmd = input("Enter instruction for node (add/multiply/exit): ")
        if cmd.lower() == "exit":
            break
        broker_socket.send_json({"command": cmd})
        print(f"[AI_CE] Sent instruction: {cmd}")

if __name__ == "__main__":
    ctx = register_ai_and_app()
    if ctx:
        print("[AI_CE] Ready to send instructions via broker...")
        send_instructions()
