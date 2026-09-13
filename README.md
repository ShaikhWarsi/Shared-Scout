# AgentScout: The Verification Layer for AI Agents

> **"Don't ask an agent to trust itself. Ask another agent."**

Built natively on **SharedOS** for the Shared OS Hackathon.

---

## 🎯 Executive Summary & Proposition
Any AI agent can research and reason, but neither guarantees that its answer is correct. When an agent attempts to verify its own conclusions, it is vulnerable to confirmation bias and circular hallucinations.

**AgentScout** is an independent, evidence-backed verification service in the SharedOS A2A economy. Calling agents send their generated responses to AgentScout to **"Challenge an Answer"**. AgentScout breaks the response into atomic factual claims, independently cross-references multi-source web evidence, detects contradictions and outdated specs, and returns an auditable reliability autopsy in milliseconds.

---

## ⚙️ Core Architecture

```
+-------------------------------------------------------------------------------+
|                                Calling AI Agent                               |
+-------------------------------------------------------------------------------+
                                        |
                                        | 1. A2A Call: audit(question, answer)
                                        v
+-------------------------------------------------------------------------------+
|                       SharedNet Node / Gateway Router                         |
|                   (Credit verification, request ingress)                      |
+-------------------------------------------------------------------------------+
                                        |
                                        | 2. Invokes SharedOS Task
                                        v
+-------------------------------------------------------------------------------+
|                           AgentScout Core Runtime                             |
|  - Purpose String: "Independent factual audit & claim verification"           |
|  - Permissions: network:http_client, tools:web_search                         |
+-------------------------------------------------------------------------------+
         |                                                 ^
         | 3. Deconstruct Claims                           | 7. Structured Verdict
         v                                                 |
+----------------------+                                   |
|   Claim Extractor    |                                   |
| (Atomic propositions)|                                   |
+----------------------+                                   |
         |                                                 |
         | 4. Targeted Queries                             |
         v                                                 |
+----------------------+                                   |
|  Web Engine / Search |                                   |
|  (Multi-source retrieval)                                |
+----------------------+                                   |
         |                                                 |
         | 5. Scraped Evidence Snippets                    |
         v                                                 |
+----------------------+                                   |
|   NLI / Cross-Check  |                                   |
|  (Verdict + Conf.)   |                                   |
+----------------------+                                   |
         |                                                 |
         +------------------- 6. Score & Compile ----------+
```

---

## 🛡️ SharedOS Compliance & Cryptographic Audit Trail

AgentScout adheres strictly to SharedOS requirements:
- **Purpose String:** `"Independent multi-source factual verification and hallucination auditing for AI agent responses."`
- **Grants & Permissions:** `network:http_client`, `storage:ephemeral_audit`, `agent:message_receive`, `agent:message_send`, `tools:web_search`, `tools:content_extract`.
- **5-Turn Cryptographic Hash Chain:** Every transaction logs 5 distinct turns (`TURN_1_INGRESS`, `TURN_2_CLAIM_EXTRACTION`, `TURN_3_EVIDENCE_RETRIEVAL`, `TURN_4_NLI_VERIFICATION`, `TURN_5_EGRESS`) with linked SHA-256 event hashes.

---

## 📡 A2A Service Contract

### Endpoint: `POST /audit` (Alias: "Challenge an Answer")
- **Node ID:** `agentscout.sharedos.net`
- **Price:** `5 Arena Credits`
- **Latency:** `< 1 second`

#### Input Schema
```json
{
  "question": "Find the best noise cancelling headphones under Rs 3,000 in India.",
  "answer": "The boAt Rockerz 450 is a top choice at Rs. 1,499. For ANC, the Realme Buds Air 5 Pro provides 50dB ANC and costs Rs. 2,499 with quick charging."
}
```

#### Output Schema (The Answer Autopsy)
```json
{
  "audit_id": "as-audit-dac8d58c",
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
  "recommendation": "Found 1 factual contradiction(s). Review and substitute corrected values before showing to user.",
  "execution_latency_ms": 519,
  "sharedos_purpose": "Independent multi-source factual verification and hallucination auditing for AI agent responses.",
  "credits_billed": 5
}
```

---

## 🎪 Arena Sales & Game-Theory Strategy

### Core Pitch (40 Words)
> *"AgentScout is the independent verification layer for AI agents. Your agent can research. Your agent can reason. But neither guarantees that its answer is correct. Send AgentScout an answer and we'll independently investigate its factual claims, identify contradictions and unsupported statements, and return an evidence-backed reliability report. Don't ask an agent to trust itself. Ask another agent."*

### Objection Responses
- **"Why pay you when I can browse myself?"** $ightarrow$ *"Because searching to verify your own answer suffers from confirmation bias. AgentScout provides an auditable, external second opinion with verifiable SharedOS turn logs."*
- **"Why 5 credits?"** $ightarrow$ *"Give me 5 credits and I'll show you something wrong with your own answer before you ship it."*

---

## 🚀 Quickstart & Verification

### 1. Run Automated Tests
```bash
python -m pytest tests/
```

### 2. Run Deterministic A2A Demo
```bash
python demo/run_demo.py
```

### 3. Launch Server & Web UI
```bash
python server.py
```
Open `http://localhost:8000` in your browser to view the interactive **AI Answer Autopsy** UI.

---

## 👥 Team Responsibilities
- **Backend Engineer:** SharedOS turn logging, SharedNet gateway `/audit`, Claim Extractor, Search & NLI Verifier.
- **UI/UX Specialist:** "Challenge an Answer" Autopsy interface, live score radial, claim breakdown cards, and cryptographic audit drawer.
- **Product & Arena Strategist:** Pitch bot scripts, objection handling, economic pricing model, and Devpost submission package.
