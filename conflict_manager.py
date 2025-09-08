#!/usr/bin/env python3
"""
conflict_manager.py

Priority-based conflict detection and arbitration for intents coming from AI apps.

Receives intents (PULL) from AI -> arbitrates -> forwards chosen command (PUSH) to node(s).
Logs conflicts and resolutions to conflict_log.jsonl.

Default topology (adjust addresses/ports as needed):
  - INPUT (from AI apps):   PULL  tcp://0.0.0.0:5560
  - OUTPUT (to nodes):      PUSH  tcp://192.168.0.178:5561
  - REGISTER (optional):    REQ   tcp://192.168.0.178:5558  (used only for optional priority lookup)
"""
import zmq
import time
import json
import threading
from collections import defaultdict, deque

# Configuration (edit if necessary)
INTENT_PULL_ADDR = "tcp://0.0.0.0:5560"      # binds here to receive intents
NODE_PUSH_ADDR = "tcp://192.168.0.178:5561"  # connect here to forward commands to nodes
REGISTER_REQ_ADDR = "tcp://192.168.0.178:5558"  # optional register lookup
INTENT_TTL_DEFAULT = 5.0   # seconds to keep intents active before expiry
COLLECT_WINDOW = 0.3       # short wait to collect multiple intents (seconds)
PRIORITY_LOOKUP_TIMEOUT_MS = 500  # timeout for register query

LOG_FILE = "conflict_log.jsonl"

# Local fallback priority map (app_id -> priority). Higher number => higher priority.
LOCAL_PRIORITY_MAP = {
    "APP1": 100,
    "APP2": 80,
    "APP3": 70,
    "APP4": 60,
    "APP5": 50,
}

# In-memory store: key -> deque of intents
# key = (target_node, param)
intent_store = defaultdict(deque)  # deque of intent dicts

store_lock = threading.Lock()

def now():
    return time.time()

def log_event(obj):
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(obj) + "\n")

class ConflictManager:
    def __init__(self,
                 intent_pull_addr=INTENT_PULL_ADDR,
                 node_push_addr=NODE_PUSH_ADDR,
                 register_req_addr=REGISTER_REQ_ADDR):
        self.ctx = zmq.Context()
        # receive intents
        self.pull = self.ctx.socket(zmq.PULL)
        self.pull.bind(intent_pull_addr)
        # forward to node
        self.push = self.ctx.socket(zmq.PUSH)
        self.push.connect(node_push_addr)
        # optional register client to query priority / policy
        self.register_client = self.ctx.socket(zmq.REQ)
        try:
            self.register_client.connect(register_req_addr)
            self.register_connected = True
            # set timeout for replies
            self.register_client.RCVTIMEO = PRIORITY_LOOKUP_TIMEOUT_MS
        except Exception:
            self.register_connected = False

        self.running = True

        # start cleaner thread
        t = threading.Thread(target=self._cleanup_loop, daemon=True)
        t.start()

    def _cleanup_loop(self):
        while self.running:
            with store_lock:
                expired_keys = []
                for key, dq in list(intent_store.items()):
                    # remove expired intents
                    new_dq = deque([it for it in dq if now() - it["_recv_ts"] <= it.get("ttl", INTENT_TTL_DEFAULT)])
                    intent_store[key] = new_dq
                    if not new_dq:
                        expired_keys.append(key)
                for k in expired_keys:
                    del intent_store[k]
            time.sleep(1.0)

    def _lookup_priority(self, app_id):
        # 1) try priority provided in local map
        if app_id in LOCAL_PRIORITY_MAP:
            return LOCAL_PRIORITY_MAP[app_id]
        # 2) try to query register for priority (non-standard; may fail)
        if self.register_connected:
            try:
                self.register_client.send_json({"type": "GET_APP_PRIORITY", "app_id": app_id})
                reply = self.register_client.recv_json()
                if isinstance(reply, dict) and "priority" in reply:
                    return int(reply["priority"])
            except Exception:
                # timeout or unsupported: fallthrough to default
                pass
        # 3) default fallback
        return 10

    def _choose_winner(self, intents):
        """
        intents: list of intent dicts (with fields app_id, value, priority if present)
        Selection policy:
          - prefer higher priority
          - if tie, prefer newer intent (higher timestamp or _recv_ts)
        """
        best = None
        best_score = None
        for it in intents:
            prio = it.get("priority")
            if prio is None:
                prio = self._lookup_priority(it.get("app_id"))
                it["priority"] = prio
            # tie-breaker: newer gets advantage
            timestamp = it.get("timestamp", it.get("_recv_ts", now()))
            score = (prio, timestamp)
            if best is None or score > best_score:
                best = it
                best_score = score
        return best

    def _forward_command(self, chosen_intent):
        """
        Forward chosen intent to node via push socket.
        We'll build a command envelope and send as JSON.
        """
        cmd = {
            "intent_id": chosen_intent.get("intent_id"),
            "app_id": chosen_intent.get("app_id"),
            "target_node": chosen_intent.get("target_node"),
            "param": chosen_intent.get("param"),
            "value": chosen_intent.get("value"),
            "resolved_by": "conflict_manager",
            "ts": now()
        }
        try:
            self.push.send_json(cmd)
        except Exception as e:
            print("[ConflictManager] ERROR forwarding to node:", e)

    def process_intent_batch(self, key):
        """
        Called with a (node,param) key while holding store_lock.
        Gathers active intents for that key and resolves if conflict exists.
        """
        dq = intent_store.get(key, deque())
        active_intents = [it for it in dq if now() - it["_recv_ts"] <= it.get("ttl", INTENT_TTL_DEFAULT)]
        if not active_intents:
            return

        # If only one intent, just forward it
        if len(active_intents) == 1:
            winner = active_intents[0]
            # forward and remove
            self._forward_command(winner)
            # log
            log_event({
                "event": "single_intent_forwarded",
                "key": key,
                "chosen": winner,
                "time": now()
            })
            # clear the queue for this key
            intent_store.pop(key, None)
            return

        # multiple intents -> conflict detection
        # simple detection: if any two values differ -> conflict
        values = [it.get("value") for it in active_intents]
        conflict_detected = len(set(json.dumps(v, sort_keys=True) for v in values)) > 1

        if not conflict_detected:
            # identical intents -> forward one and drop rest
            winner = active_intents[-1]  # newest
            self._forward_command(winner)
            log_event({
                "event": "identical_intents",
                "key": key,
                "chosen": winner,
                "fork": [it for it in active_intents],
                "time": now()
            })
            intent_store.pop(key, None)
            return

        # Arbitration by priority
        winner = self._choose_winner(active_intents)
        losers = [it for it in active_intents if it is not winner]

        # forward winner
        self._forward_command(winner)

        # log conflict and resolution
        log_event({
            "event": "conflict_resolved",
            "key": key,
            "chosen": winner,
            "losers": losers,
            "all_intents": active_intents,
            "time": now()
        })

        # remove intents for this key
        intent_store.pop(key, None)

    def run(self):
        print("[ConflictManager] Listening for intents on", INTENT_PULL_ADDR)
        while self.running:
            try:
                msg = self.pull.recv_json()
            except Exception as e:
                print("[ConflictManager] Error receiving message:", e)
                continue

            recv_ts = now()
            # normalize intent
            intent = dict(msg)  # copy
            intent.setdefault("intent_id", f"intent-{int(recv_ts*1000)}")
            intent.setdefault("timestamp", intent.get("timestamp", recv_ts))
            intent.setdefault("ttl", intent.get("ttl", INTENT_TTL_DEFAULT))
            intent["_recv_ts"] = recv_ts

            node = intent.get("target_node")
            param = intent.get("param")
            if not node or not param:
                print("[ConflictManager] Ignoring malformed intent (missing target_node or param):", intent)
                continue

            key = (node, param)
            with store_lock:
                intent_store[key].append(intent)

            # small collect window to allow multiple intents to arrive
            time.sleep(COLLECT_WINDOW)

            # process this key
            with store_lock:
                # re-check exists (might have been removed by cleanup)
                if key in intent_store:
                    self.process_intent_batch(key)

    def stop(self):
        self.running = False
        try:
            self.pull.close()
            self.push.close()
            self.register_client.close()
            self.ctx.term()
        except Exception:
            pass

if __name__ == "__main__":
    cm = ConflictManager()
    try:
        cm.run()
    except KeyboardInterrupt:
        print("Interrupted, shutting down...")
        cm.stop()
