# register1.py
import zmq
import threading

VALID_NODE_ID = "N001"
VALID_AI_ID = "AI001"
registered_node = None
registered_ai = None
node_metrics = {}

# Setup PUB socket to notify broker (inter_ai_broker.py)
# context_pub = zmq.Context()
# pub_socket = context_pub.socket(zmq.PUB)
# pub_socket.bind("tcp://192.168.0.178:5562")  # <-- Added line


def handle_node_registration():
    global registered_node, node_metrics
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://192.168.0.178:5558")

    while True:
        message = socket.recv_json()
        print(f"[Register] Received node registration: {message}")
        if message.get("node_id") == VALID_NODE_ID:
            registered_node = VALID_NODE_ID
            node_metrics = message.get("metrics", {})
            socket.send_json({"status": "REGISTRATION_SUCCESS"})
            print(f"[Register] Node {VALID_NODE_ID} registered with metrics: {node_metrics}")
            # Notify broker about APP1 after successful node registration
            # pub_socket.send_string("APP1")
        else:
            socket.send_json({"status": "REGISTRATION_FAILED"})
            print("[Register] Invalid node ID!")

def handle_ai_registration():
    global registered_ai
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://192.168.0.178:5559")

    while True:
        message = socket.recv_json()
        print(f"[Register] Received AI registration: {message}")
        if message.get("ai_id") == VALID_AI_ID and registered_node:
            registered_ai = VALID_AI_ID
            socket.send_json({"status": "AI_REGISTRATION_SUCCESS", "node_metrics": node_metrics})
            print("[Register] AI registered and node is available.")
        else:
            socket.send_json({"status": "AI_REGISTRATION_FAILED"})
            print("[Register] Invalid AI ID or node not present!")

if __name__ == "__main__":
    print("[Register] Register service started.")
    threading.Thread(target=handle_node_registration).start()
    threading.Thread(target=handle_ai_registration).start()
