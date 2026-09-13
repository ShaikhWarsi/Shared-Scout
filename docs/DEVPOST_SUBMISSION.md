# AgentScout — Devpost Submission Package

## Project Title
**AgentScout: The Independent Verification Layer for AI Agents**

## Tagline
*Don't ask an agent to trust itself. Ask another agent.*

---

## 💡 Inspiration
In an autonomous agent economy, every agent generates conclusions, searches information, and reasons over answers. However, when an agent attempts to verify its own output, it inevitably falls prey to circular confirmation bias. Circular hallucinations are expensive and damaging in high-stakes workflows.

We built **AgentScout** on **SharedOS** as the first independent verification layer for AI agents. Rather than competing as another generic research assistant, AgentScout provides a modular second-opinion service where any agent can send an answer for 5 Arena credits and receive an evidence-backed reliability autopsy in milliseconds.

---

## ⚙️ What It Does
1. **Challenge an Answer:** Any calling agent sends an input payload `{"question": "...", "answer": "..."}` over SharedNet.
2. **Atomic Claim Isolation:** AgentScout isolates distinct factual propositions without breaking on abbreviations, currencies, or markdown structures.
3. **Multi-Source Real-Time Research:** Concurrently queries live web sources, scrapes citations, and weights domains across 3 credibility tiers (Tier 1: Official/Gov/Brand, Tier 2: Reputable media/Retail, Tier 3: General web).
4. **NLI Contradiction Engine:** Applies Natural Language Inference (NLI) to classify each claim as `SUPPORTED`, `CONTRADICTED`, `UNVERIFIED`, or `OUTDATED` with citations and factual corrections.
5. **Reliability Autopsy & Actionable Advisory:** Computes an aggregate reliability score (0–100) and supplies an advisory recommendation before the calling agent presents the answer to end-users.
6. **SharedOS Audit Trail:** Emits a 5-turn cryptographically hashed audit log (`TURN_1_INGRESS` → `TURN_2_CLAIM_EXTRACTION` → `TURN_3_EVIDENCE_RETRIEVAL` → `TURN_4_NLI_VERIFICATION` → `TURN_5_EGRESS`).

---

## 🏗️ Technical Architecture
```
+-------------------------------------------------------------------------------+
|                                Calling AI Agent                               |
+-------------------------------------------------------------------------------+
                                        |
                                        | 1. A2A Call: POST /audit (5 Credits)
                                        v
+-------------------------------------------------------------------------------+
|                      SharedNet Node Gateway Router                            |
|             (Endpoint: agentscout.sharedos.net | Port: 8000)                  |
+-------------------------------------------------------------------------------+
                                        |
                                        | 2. SharedOS Sandboxed Execution
                                        v
+-------------------------------------------------------------------------------+
|                           AgentScout Core Runtime                             |
|  - Purpose String: "Independent multi-source factual verification"            |
|  - Grants: network:http_client, tools:web_search, tools:content_extract       |
+-------------------------------------------------------------------------------+
         |                                                 ^
         | 3. Deconstruct Claims                           | 7. Return Autopsy
         v                                                 |
+----------------------+                                   |
|   Claim Extractor    |                                   |
+----------------------+                                   |
         |                                                 |
         | 4. Targeted Web Queries                         |
         v                                                 |
+----------------------+                                   |
| Multi-Source Scraper |                                   |
|  (Tier 1/2/3 Weight) |                                   |
+----------------------+                                   |
         |                                                 |
         | 5. Scraped Evidence Snippets                    |
         v                                                 |
+----------------------+                                   |
|     NLI Verifier     |                                   |
|  (Entailment Logic)  |                                   |
+----------------------+                                   |
         |                                                 |
         +------------------- 6. Score & Compile ----------+
```

---

## 🔬 Benchmark & Performance
- **Live Latency Median:** `294.0 ms`
- **P95 Latency:** `1173.0 ms`
- **Success Rate:** `100% (20/20 live diverse queries)`
- **SharedNet Timeout Compliance:** 100% under 5-minute requirement.

---

## 🏷️ Required Hackathon Fields
- **SharedOS Purpose String:** `"Independent multi-source factual verification and hallucination auditing for AI agent responses."`
- **Service Name:** `audit` (Alias: *"Challenge an Answer"*)
- **Price:** `5 Arena Credits`
- **SharedNet Node ID:** `agentscout.sharedos.net`
- **Permissions/Grants:** `network:http_client`, `storage:ephemeral_audit`, `agent:message_receive`, `agent:message_send`, `tools:web_search`, `tools:content_extract`
