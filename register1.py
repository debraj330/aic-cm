# ------------------------------
# File: register1.py
# ------------------------------
import zmq

VALID_AI_ID = "AI001"
VALID_APP_ID = "APP1"
VALID_NODE_ID = "N001"

registered_ai = None
registered_app = None
registered_node = None
node_params = {}

def start_register():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://192.168.0.178:5558")

    print("[Register] Service started on tcp://192.168.0.178:5558")

    while True:
        msg = socket.recv_json()
        print("[Register] Received:", msg)

        if msg.get("type") == "AI_REGISTER":
            ai_id = msg.get("ai_id")
            if ai_id == VALID_AI_ID:
                global registered_ai
                registered_ai = ai_id
                socket.send_json({"status": "AI_REGISTRATION_SUCCESS"})
            else:
                socket.send_json({"status": "AI_REGISTRATION_FAILED"})

        elif msg.get("type") == "APP_REGISTER":
            app_id = msg.get("app_id")
            if app_id == VALID_APP_ID:
                global registered_app
                registered_app = app_id
                socket.send_json({"status": "APP_REGISTRATION_SUCCESS"})
            else:
                socket.send_json({"status": "APP_REGISTRATION_FAILED"})

        elif msg.get("type") == "NODE_REGISTER":
            node_id = msg.get("node_id")
            if node_id == VALID_NODE_ID:
                global registered_node, node_params
                registered_node = node_id
                node_params = msg.get("params", {})
                socket.send_json({"status": "NODE_REGISTRATION_SUCCESS"})
                print(f"[Register] Node registered: {node_id} with params {node_params}")
            else:
                socket.send_json({"status": "NODE_REGISTRATION_FAILED"})

if __name__ == "__main__":
    start_register()
