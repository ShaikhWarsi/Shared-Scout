# AgentScout 90-Second Demo Walkthrough Video Script

## [0:00 - 0:20] THE HOOK & THE PROBLEM
- **Visual:** Split screen showing a shopping agent answering a query: *"Find the best noise-canceling headphones under ₹3,000 in India."*
- **Voiceover:** *"Every AI agent in this hackathon can generate an answer. But when accuracy matters, you cannot ask an agent to verify itself without risking circular hallucinations. Welcome to AgentScout: the independent verification layer on SharedOS."*

## [0:20 - 0:45] THE SHAREDNET A2A TRANSACTION
- **Visual:** Terminal / UI showing the calling agent sending `POST /audit` with 5 Arena Credits. The SharedOS cloud status flushes green.
- **Voiceover:** *"For just 5 Arena credits, the shopping agent calls AgentScout to challenge its answer before showing it to the customer. AgentScout decomposes the response into atomic propositions and immediately conducts multi-source web extraction."*

## [0:45 - 1:15] THE AI ANSWER AUTOPSY
- **Visual:** The UI transitions to the Autopsy Report. Reliability Score drops to **50%**.
- **Visual Highlights:**
  - `Claim 1 (boAt Rockerz 450 @ ₹1,499)`: Green badge `✓ SUPPORTED`.
  - `Claim 2 (Realme Buds Air 5 Pro @ ₹2,499)`: Red badge `✕ CONTRADICTED`.
  - Exploded evidence card showing the manufacturer catalog proving the actual price is **₹4,999**.
- **Voiceover:** *"Within 500 milliseconds, AgentScout catches a critical hallucination: the Realme Buds Air 5 Pro retails at ₹4,999, not ₹2,499. If OPENAI_API_KEY is set, AgentScout delegates semantic reasoning to GPT-4o-mini; otherwise it uses deterministic regex."*

## [1:15 - 1:30] CLOSING & SHAREDOS AUDIT LOG
- **Visual:** The SharedOS Cryptographic Audit Trail drawer opens, showing the 5 verified turns with SHA-256 event hashes.
- **Voiceover:** *"The shopping agent updates its response, saves its credibility, and logs the verified audit trail to SharedOS. Don't ask an agent to trust itself. Ask another agent. Vote AgentScout."*
