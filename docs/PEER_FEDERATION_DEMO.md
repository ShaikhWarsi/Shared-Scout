# SharedNet Multi-Node Peer Federation & Dial Handshake Guide

AgentScout nodes can discover, authenticate, and federate with each other across the SharedNet network using cryptographic HMAC-SHA256 signatures.

---

## 1. Running a Live 2-Node Cluster

To spin up two independent AgentScout peer nodes locally:

### Terminal 1: Node Alpha (Port 8000)
```bash
python server.py --port 8000 --node-id node-alpha.sharedos.net
```

### Terminal 2: Node Beta (Port 8001)
```bash
python server.py --port 8001 --node-id node-beta.sharedos.net
```

---

## 2. Dialing & Establishing Federation

### Active Handshake via CLI:
```bash
# Instruct Node Alpha to dial Node Beta:
curl -X POST "http://localhost:8000/sharednet/peers/dial?peer_url=http://localhost:8001"
```

### Handshake Sequence:
```
Node Alpha (8000)                             Node Beta (8001)
       |                                             |
       |------- POST /purpose (HMAC Signed) -------->|
       |                                             | [Verifies HMAC-SHA256]
       |<------ 200 OK + Manifest Payload -----------|
       |                                             |
[Registers Node Beta]                         [Registers Node Alpha]
```

---

## 3. Automated Demonstration Runner

Run the full end-to-end automated 2-node handshake simulation:

```bash
python demo/run_2node_federation.py
```

### Verified Output:
```text
=====================================================================================
  🌐 SHAREDNET 2-NODE PEER FEDERATION & CRYPTOGRAPHIC DIAL HANDSHAKE
=====================================================================================

[STEP 1] INITIALIZED 2 SHAREDNET PEER NODES:
  Node Alpha (Primary Verifier) : node-alpha.agentscout.net (HMAC Enforced: True)
  Node Beta  (Federated Peer)   : node-beta.agentscout.net (HMAC Enforced: True)

[STEP 2] NODE ALPHA INITIATES SIGNED DIAL HANDSHAKE TO NODE BETA:
  Dial Target     : node-beta.agentscout.net/purpose
  Auth Header     : x-sharedos-agent-id = node-alpha.agentscout.net
  HMAC-SHA256 Sig : dda4ef1afb7e04f01859d241496731ef...

[STEP 3] NODE BETA VERIFIES CRYPTOGRAPHIC TURN AUTHORIZATION:
  Authorized      : True
  HMAC Verified   : True
  Kernel Turn Idx : 1

[STEP 4] MUTUAL PEER FEDERATION ESTABLISHED:
  Node Alpha Registered Peers : ['node-beta.agentscout.net']
  Node Beta Registered Peers  : ['node-alpha.agentscout.net']

[STEP 5] NODE ALPHA DISPATCHES AUDIT PAYLOAD TO NODE BETA:
  Audit Execution : PARTIALLY_SUPPORTED (Reliability: 40 / 100)
  Billed To Caller: 5 Arena Credits
  Node Alpha Bal  : 95 Arena Credits remaining on Node Beta Ledger

=====================================================================================
  [SUCCESS] 2-Node SharedNet Federation & Authenticated Handshake Verified!
=====================================================================================
```
