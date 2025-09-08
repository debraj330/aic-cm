#!/usr/bin/env python3
# node_listener.py
import zmq
import json

PULL_ADDR = "tcp://192.168.0.178:5561"   # conflict_manager PUSH -> nodes' PULL

def main():
    ctx = zmq.Context()
    pull = ctx.socket(zmq.PULL)
    pull.bind(PULL_ADDR)
    print("[NodeListener] Listening for commands on", PULL_ADDR)
    try:
        while True:
            msg = pull.recv_json()
            print("[NodeListener] Received command:", json.dumps(msg))
    except KeyboardInterrupt:
        print("Interrupted, exiting.")
    finally:
        pull.close()
        ctx.term()

if __name__ == "__main__":
    main()
