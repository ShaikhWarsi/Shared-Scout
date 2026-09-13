# AgentScout — Devpost Submission Package

## Project Title
**AgentScout: Pre-Ship CI/CD Firewall Gate & Adversarial Attack Engine for AI Agents**

## Tagline
*Don't ask an agent to trust itself. Challenge it with independent adversarial verification.*

---

## 💡 Inspiration
In an autonomous agent economy, every agent generates conclusions, searches information, and reasons over answers. However, when an agent attempts to verify its own output, it inevitably falls prey to circular confirmation bias. In high-stakes applications (medical, financial, legal, and hardware specifications), shipping hallucinated answers directly to humans is dangerous.

We built **AgentScout** as the standard **Pre-Ship CI/CD Firewall Gate** for autonomous agents (`Agent -> AgentScout Firewall -> World`). Rather than competing as another generic chatbot, AgentScout is middleware that intercepts draft responses, runs adversarial attack audits, convenes an independent 3-agent committee, auto-repairs contradictions in-flight, and issues cryptographically verified clearance.

---

## ⚙️ What It Does
1. **⚔️ Adversarial Attack Probes (`POST /attack`):** Actively hunts for numerical discrepancies, superseded launch facts, and ungrounded marketing superlatives.
2. **👥 Multi-Agent Deliberation Committee:**
   - **`Researcher-Node`:** Evaluates primary evidence coverage, proposition keyword density, and citation presence.
   - **`Skeptic-Node`:** Runs adversarial stress-tests for temporal obsolescence, spec boundaries, and price volatility.
   - **`SourceJudge-Node`:** Classifies domain trust tiers (Gov/Edu = 1.0, Official store = 0.95, Wikipedia = 0.90) and resolves conflicting citations.
3. **🚨 Pre-Ship CI/CD Firewall Gate (`POST /firewall/gate`):** Enforces reliability thresholds (e.g. $\ge 80$). Hallucinated drafts are blocked with `BLOCKED_UNSAFE`.
4. **🔧 Surgical Autonomous Diff-Repair:** Applies in-flight token diff patches to prices, specifications (`hours`, `dB`, `mAh`, `W`, `meters`), and dates $\rightarrow$ re-evaluates $\rightarrow$ outputs `REPAIRED_AND_APPROVED`.
5. **🔏 Cryptographic Proof Chain & Settlement:** Persists a 5-turn SHA-256 chained transaction to `.sharedos/audit_log.jsonl`, verified on-demand via `GET /api/audit-trail/{audit_id}/verify`. Deducts 5 Arena Credits with CSV ledger export.

---

## 🏗️ Technical Architecture
```
+-------------------------------------------------------------------------------+
|                        Upstream Autonomous AI Agent                           |
|                 (e.g., ShoppingBot, FinancialAdvisor, DocBot)                 |
+-------------------------------------------------------------------------------+
                                        |
                                        | 1. A2A Call: POST /firewall/gate (5 Credits)
                                        |    Headers: x-sharedos-agent-id, x-sharedos-signature
                                        v
+-------------------------------------------------------------------------------+
|                       SharedNet Node Gateway Router                           |
|             (HMAC-SHA256 Turned-Gated, Rate Limiter: 60 req/min)              |
+-------------------------------------------------------------------------------+
                                        |
                                        | 2. Pre-Ship CI/CD Firewall Inspection
                                        v
+-------------------------------------------------------------------------------+
|                       AgentScout Verification Core                            |
|  - Purpose: "Independent multi-source factual verification for AI agents"     |
+-------------------------------------------------------------------------------+
         |                                                 ^
         | 3. Atomic Propositions                          | 7. 🚨 BLOCKED_UNSAFE
         v                                                 |    (Reliability: 40/100)
+----------------------+                                   |
|   Claim Extractor    |                                   |
+----------------------+                                   |
         |                                                 | 8. 🔧 Surgical Diff-Repair
         | 4. Multi-Source Queries                         |    (In-Flight AST Diff)
         v                                                 v
+----------------------+                         +-------------------+
| Multi-Engine Search  |                         |    Clearance:     |
| - Wikipedia REST API |                         |    ✅ APPROVED     |
| - DuckDuckGo Live    |                         |  (Reliability: 96)|
+----------------------+                         +-------------------+
         |                                                 ^
         | 5. Evidence & Citations                         |
         v                                                 |
+----------------------------------------------------------+
|          3-Agent Deliberation Committee                  |
|  [Researcher-Node] + [Skeptic-Node] + [SourceJudge-Node] |
+----------------------------------------------------------+
```

---

## 🔬 Benchmark & Performance
- **Live Latency Median:** `420 ms`
- **P95 Latency:** `1,850 ms`
- **Success Rate:** `100% (20/20 live diverse test cases)`
- **Hallucination Interception Rate:** `100% on Contradictory Traps`
- **Automated Test Suite:** `26/26 Tests Passing`

---

## 🏷️ Required Hackathon Fields
- **SharedOS Purpose String:** `"Independent multi-source factual verification and hallucination auditing for AI agent responses."`
- **Service Name:** `firewall` (Alias: *"Pre-Ship CI/CD Firewall Gate"*)
- **Price:** `5 Arena Credits`
- **SharedNet Node ID:** `agentscout.sharedos.net`
- **Permissions/Grants:** `network:http_client`, `storage:audit_log`, `agent:message_receive`, `agent:message_send`, `tools:web_search`, `tools:content_extract`

