#!/usr/bin/env python3
# test_intents.py
import zmq
import time
import uuid
import random
import json

PUSH_ADDR = "tcp://192.168.0.178:5560"   # conflict_manager PULL address

def make_intent(app_id, node, param, value, priority=None, ttl=5):
    return {
        "intent_id": str(uuid.uuid4()),
        "app_id": app_id,
        "target_node": node,
        "param": param,
        "value": value,
        "priority": priority,   # conflict_manager may ignore and lookup
        "timestamp": time.time(),
        "ttl": ttl
    }

def main():
    ctx = zmq.Context()
    push = ctx.socket(zmq.PUSH)
    push.connect(PUSH_ADDR)
    print("[Test] Connected to conflict manager at", PUSH_ADDR)

    node = "N001"
    param = "tx_power"

    # Scenario: three apps send conflicting intents quickly
    intents = [
        make_intent("APP1", node, param, {"power_dbm": 20}, priority=100),
        make_intent("APP2", node, param, {"power_dbm": 10}, priority=80),
        make_intent("APP3", node, param, {"power_dbm": 25}, priority=70),
    ]

    # Send them with small gaps to exercise collect window
    for it in intents:
        push.send_json(it)
        print("[Test] Sent intent:", json.dumps(it))
        time.sleep(0.1)

    # Also send a later higher-priority intent to see replace behavior
    time.sleep(1.0)
    hi = make_intent("APP1", node, param, {"power_dbm": 30}, priority=120)
    push.send_json(hi)
    print("[Test] Sent late/high-priority intent:", json.dumps(hi))

    # Additional unrelated intent (different param) should be forwarded alongside
    other = make_intent("APP2", node, "scheduling_weight", {"weight": 0.8}, priority=80)
    push.send_json(other)
    print("[Test] Sent unrelated intent:", json.dumps(other))

    # Keep alive briefly to ensure manager processes
    time.sleep(2)
    push.close()
    ctx.term()
    print("[Test] Done.")

if __name__ == "__main__":
    main()
