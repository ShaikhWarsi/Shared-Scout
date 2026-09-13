# AgentScout: The Independent Verification & Autonomous Repair Layer for AI Agents

> **"Don't ask an agent to trust itself. Ask another agent."**

Built as a high-performance, SharedNet-compliant verification node for the SharedOS A2A agent economy.

---

## 🎯 Executive Summary & Core Proposition

Any AI agent can research and reason, but neither guarantees that its answer is correct. When an agent attempts to self-verify its conclusions, it suffers from **circular confirmation bias**—affirming the very hallucinations it generated.

**AgentScout** is an independent, evidence-backed verification and autonomous hallucination-repair service. Calling agents send their generated responses to AgentScout (`POST /audit` or `POST /repair`):

1. **Atomic Proposition Extraction:** Breaks multi-sentence responses into isolated, falsifiable claims.
2. **Multi-Engine Live Research:** Independently queries the **Wikipedia REST API** and **DuckDuckGo Live Search** (with domain credibility weighting: official/gov/edu = 1.0, Wikipedia = 0.90, review portals = 0.85). *Zero hardcoded catalog shortcuts: uncorroborated claims return `UNVERIFIED`.*
3. **Deterministic & LLM Natural Language Inference (NLI):** Performs generalized numeric/spec mismatch detection (`hours`, `mAh`, `dB`, `W`, prices, years) with optional `gpt-4o-mini` evaluation when API keys are configured.
4. **Autonomous Hallucination Repair:** Automatically generates a corrected response (`repaired_answer`) ready for immediate delivery to human users.
5. **Cryptographic Proof Chain:** Logs a 5-turn SHA-256 chained transaction persisted to `.sharedos/audit_log.jsonl`.

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
- **SharedOS Compliance:** Operates as a SharedNet-compliant HTTP server enforcing HMAC-SHA256 turn authorization and logging 5 distinct turns (`TURN_1_INGRESS` to `TURN_5_EGRESS`) with linked SHA-256 event hashes permanently saved to `.sharedos/audit_log.jsonl`.
- **Search Engine:** All searches query live public REST APIs (Wikipedia Summary/OpenSearch) and DuckDuckGo Lite. Zero static fallback catalogs are used; if live networks return no evidence, claims are marked `UNVERIFIED`.
- **Micro-Billing:** Structured for the SharedOS Arena economy at 5 Arena Credits per audit transaction.

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
  "credits_billed": 5
}
```

---

## 🚀 Quickstart & Reproduction

### 1. Run Automated Test Suite (12 Tests)
```bash
python -m pytest tests/
```

### 2. Run Closed-Loop Live A2A Simulation
```bash
python demo/run_live_a2a.py
```

### 3. Run Hackathon Judge Simulator
```bash
python review/judge_simulator.py
```

### 4. Launch Server & Web UI
```bash
python server.py
```
Open `http://localhost:8000` to test with multi-domain presets (E-Commerce, Medicine, Law, Finance, History).

### 5. Launch Public Tunnel Gateway
```bash
python scripts/tunnel.py
```
*(Auto-detects `localtunnel`, `ngrok`, or `cloudflared`)*
