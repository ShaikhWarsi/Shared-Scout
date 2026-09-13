# AgentScout: Pre-Ship CI/CD Firewall Gate & Adversarial Attack Engine for AI Agents

> **"Don't ask an agent to trust itself. Challenge it with independent adversarial verification."**

**The Standard CI/CD Safety Primitive for Autonomous Agents on SharedOS** (`Agent -> AgentScout Firewall -> World`)

---

## 🎯 Executive Summary & Core Proposition

Any AI agent can research and reason, but neither guarantees that its answer is correct. When an agent attempts to self-verify its conclusions, it suffers from **circular confirmation bias**—affirming the very hallucinations it generated.

**AgentScout** is an independent, evidence-backed Pre-Ship CI/CD Firewall Gate and Adversarial Attack Engine. Calling agents route draft outputs through AgentScout before shipping to human users or external systems (`POST /firewall/gate` or `POST /attack`):

1. **⚔️ Adversarial Attack Probes (`POST /attack`):** Actively attacks candidate propositions, hunting for numeric discrepancies, outdated claims, and ungrounded marketing superlatives.
2. **👥 Multi-Perspective Deliberation Pipeline:** Convenes 3 independent verification perspectives:
   - **Researcher-Perspective:** Evaluates primary evidence coverage, named entity overlap, and citation availability.
   - **Skeptic-Perspective:** Runs adversarial stress-tests for temporal obsolescence, spec boundaries, and price volatility.
   - **SourceJudge-Perspective:** Classifies domain trust tiers (Gov/Edu = 1.0, Official = 0.95, Wikipedia = 0.90) and resolves conflicting citations.
3. **🚨 Pre-Ship CI/CD Firewall Gate (`POST /firewall/gate`):** Evaluates reliability against safety thresholds (e.g. $\ge 80$). Drafts with contradictions are flagged `BLOCKED_UNSAFE`.
4. **🔧 Surgical Autonomous Diff-Repair:** Applies in-flight token diff patches to prices, specifications (`hours`, `dB`, `mAh`, `W`, `meters`), and dates $\rightarrow$ re-evaluates $\rightarrow$ outputs `REPAIRED_AND_APPROVED`.
5. **🔏 Cryptographic Proof Chain & Settlement:** Persists a 5-turn SHA-256 chained transaction to `.sharedos/audit_log.jsonl`, verified via `GET /api/audit-trail/{audit_id}/verify`. Deducts 5 Arena Credits with CSV ledger export.


---

## ⚙️ System Architecture

```
+-------------------------------------------------------------------------------+
|                                Calling AI Agent                               |
|                  (e.g., ShoppingBot-Node-71, ResearchAgent)                   |
+-------------------------------------------------------------------------------+
                                        |
                                        | 1. Signed A2A Call: POST /repair
                                        |    Headers: x-sharedos-agent-id, x-sharedos-signature
                                        v
+-------------------------------------------------------------------------------+
|                       SharedNet HTTP Node / Gateway Router                    |
|                (HMAC-SHA256 Auth, Rate Limiter: 60 req/min)                   |
+-------------------------------------------------------------------------------+
                                        |
                                        | 2. Initiates 5-Turn Audit Task
                                        v
+-------------------------------------------------------------------------------+
|                           AgentScout Core Service Runtime                     |
|  - Purpose: "Independent multi-source factual verification for AI agents"     |
|  - Grants: network:http_client, tools:web_search, storage:audit_log           |
+-------------------------------------------------------------------------------+
         |                                                 ^
         | 3. Deconstruct Propositions                     | 7. Structured Autopsy &
         v                                                 |    Repaired Output
+----------------------+                                   |
|   Claim Extractor    |                                   |
| (Decimal-safe regex) |                                   |
+----------------------+                                   |
         |                                                 |
         | 4. Parallel Query Formulation                   |
         v                                                 |
+----------------------+                                   |
| Multi-Engine Search  |                                   |
| - Wikipedia REST API |                                   |
| - DuckDuckGo Live    |                                   |
+----------------------+                                   |
         |                                                 |
         | 5. Evidence Snippets & Domain Scores            |
         v                                                 |
+----------------------+                                   |
| NLI Verifier Engine  |                                   |
| - Numeric/Spec Match |                                   |
| - Optional GPT-4o    |                                   |
+----------------------+                                   |
         |                                                 |
         +----------------- 6. Scorer & Auto-Repair -------+
```

---

## 🛡️ Technical Implementation Realities

To ensure complete transparency and credibility during judging:

- **Verification Engine:** Uses deterministic regex pattern matching, numeric unit normalization, and semantic keyword overlap for fast, reproducible evaluation ($<1$s latency); optional GPT-4o-mini reasoning is invoked when `OPENAI_API_KEY` is provided.
- **SharedOS Compliance & Peer Federation:** Operates as a SharedNet-compliant HTTP server enforcing HMAC-SHA256 turn authorization by default. Dials SharedNet peers via signed HMAC-SHA256 handshakes (`POST /sharednet/peers/dial`) and maintains active peer routing tables (`GET /sharednet/peers`).
- **Cryptographic Audit Trail:** Logs 5 distinct turns (`TURN_1_INGRESS` to `TURN_5_EGRESS`) with linked SHA-256 event hashes permanently saved to `.sharedos/audit_log.jsonl`.
- **Search Engine:** All searches query live public REST APIs (Wikipedia REST API) and DuckDuckGo HTML parser, complemented by an authoritative multi-domain verification corpus fallback (`AUTHORITATIVE_CORPUS`) for offline or throttled sandbox execution to prevent unhandled network drops.
- **Arena Credits Ledger:** Enforces real balance tracking in `.sharedos/ledger.json` (100 credits initial grant, 5 credits billed per audit/repair, HTTP 403 on insufficient balance, and full CSV export at `GET /ledger/export`).

---

## 📡 A2A Service Contracts

### 1. Endpoint: `POST /repair` (Challenge & Repair)
- **Node Target:** `agentscout.sharedos.net/repair`
- **Fee:** `5 Arena Credits`

#### Input Schema
```json
{
  "question": "Find the best noise cancelling headphones under Rs 3,000 in India.",
  "answer": "The boAt Rockerz 450 is a top choice at Rs. 1,499. For ANC, the Realme Buds Air 5 Pro provides 50dB ANC and costs Rs. 2,499 with quick charging."
}
```

#### Output Schema (The Answer Autopsy + Repaired Text)
```json
{
  "audit_id": "as-audit-c0854398",
  "reliability": 50,
  "verdict_summary": "CONTRADICTED",
  "stats": {
    "total_claims": 2,
    "supported": 1,
    "contradicted": 1,
    "unverified": 0,
    "outdated": 0
  },
  "claims": [
    {
      "claim_id": 1,
      "claim_text": "The boAt Rockerz 450 is a top choice at Rs. 1,499",
      "verdict": "SUPPORTED",
      "confidence": 0.86,
      "evidence": [
        {
          "source_url": "https://www.boat-lifestyle.com/products/rockerz-450",
          "source_title": "boAt Lifestyle Official Catalog",
          "snippet": "boAt Rockerz 450 wireless on-ear headphones feature up to 15 hours battery backup, priced at Rs. 1,499."
        }
      ]
    },
    {
      "claim_id": 2,
      "claim_text": "Realme Buds Air 5 Pro provides 50dB ANC and costs Rs. 2,499 with quick charging.",
      "verdict": "CONTRADICTED",
      "confidence": 0.96,
      "contradiction_details": "Claim states price Rs. 2,499, but verified manufacturer/retailer catalog confirms Rs. 4,999.",
      "correction": "Actual verified price is Rs. 4,999",
      "evidence": [
        {
          "source_url": "https://buy.realme.com/in/goods/realme-buds-air-5-pro",
          "source_title": "Realme Official Store",
          "snippet": "Realme Buds Air 5 Pro official launch price is Rs. 4,999. Includes 50dB Active Noise Cancellation."
        }
      ]
    }
  ],
  "recommendation": "Found 1 factual contradiction(s). Autopsy generated repaired answer below with verified values.",
  "repaired_answer": "The boAt Rockerz 450 is a top choice at Rs. 1,499. For ANC, the Realme Buds Air 5 Pro provides 50dB ANC and costs Rs. 4,999 with quick charging.",
  "execution_latency_ms": 412,
  "sharedos_purpose": "Independent multi-source factual verification and hallucination auditing for AI agent responses.",
  "credits_billed": 5,
  "remaining_credits": 95
}
```

---

## 🚀 Quickstart & Reproduction

### 1. 🎬 Run the 90-Second Cinematic Mega-Demo (Single Command)
Demonstrates the full autonomous lifecycle: Upstream Draft $\rightarrow$ ⚔️ Adversarial Attack $\rightarrow$ 3-Agent Committee $\rightarrow$ 🚨 Pre-Ship Gate Interception $\rightarrow$ 🔧 Surgical Diff-Repair $\rightarrow$ 🔏 SHA-256 Provenance & Arena Settlement.
```bash
python demo/run_megademo.py
```

### 2. Run Full Automated Test Suite (46 Tests, 100% Green)
```bash
python -m pytest tests/
```
Covers API endpoints, Native SharedNet Room Watcher, 3-Agent Committee, In-Flight Diff-Repair, 2-Node Federation, Ed25519 Signing, and 14 Hostile Blackbox Torture cases.

### 3. Launch Native SharedNet Arena Room Watcher
Connects AgentScout directly to the SharedNet Arena room to receive messages via stdin and post replies via stdout:
```bash
npx -y sharednet@latest watch --on message --run "python agentscout_arena_watcher.py" --reply
```

### 4. Model Context Protocol (MCP) Server
Run the stdio JSON-RPC 2.0 MCP server for Claude Code / Cursor / Codex:
```bash
python mcp_server.py
```

### 5. Run 2-Node Peer Federation & Dial Handshake
```bash
python demo/run_2node_federation.py
```

### 6. Run Live Performance & Hallucination Benchmark
```bash
python benchmarks/benchmark_live.py
```

### 7. Launch Node Server & Neo-Brutalist Mission Control
```bash
python server.py --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser. Inspect machine-readable discovery interfaces:
- **Agent Card:** `GET /.well-known/agent.json`
- **Service Catalog:** `GET /api/v1/listing`
- **Verification Public Key:** `GET /api/v1/public-key`
- **Remote MCP Endpoint:** `POST /api/mcp`
- **Live CSV Ledger:** `GET /ledger/export`


