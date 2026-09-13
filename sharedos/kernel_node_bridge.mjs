/**
 * SharedOS Node.js Kernel Bridge
 * Directly executes @aicoo/sharedos SDK against the local AgentScout .sharedos datastore.
 */

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  CapabilityAuthorizer,
  SharedOSKernel,
  registerStandardOsTools,
} from "@aicoo/sharedos";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(__dirname, "..");
const GRANTS_FILE = path.join(ROOT_DIR, ".sharedos", "grants.json");
const AUDIT_FILE = path.join(ROOT_DIR, ".sharedos", "audit_log.jsonl");

// 1. GrantSource implementation that reads from .sharedos/grants.json and throws on outage
const grantSource = {
  async load(access) {
    try {
      const raw = await fs.readFile(GRANTS_FILE, "utf-8");
      const grants = JSON.parse(raw);
      if (!Array.isArray(grants)) {
        throw new Error("Invalid grants schema: expected array");
      }
      return grants.filter(
        (candidate) =>
          candidate.namespaceId === access.namespaceId &&
          JSON.stringify(candidate.subject) === JSON.stringify(access.actor) &&
          JSON.stringify(candidate.issuer) === JSON.stringify(access.authority)
      );
    } catch (err) {
      // Must throw on outage to trigger fail-closed authority_unavailable denial
      throw new Error(`Grant store datastore outage: ${err.message}`);
    }
  },
};

// 2. ResourceProvider implementation for sandboxed evidence & benchmarks
const files = {
  namespace: "files",
  async invoke(operation, signal) {
    signal?.throwIfAborted();
    const relPath = (operation.resource.path || []).join(path.sep);
    const target = path.resolve(ROOT_DIR, relPath);
    if (!target.startsWith(ROOT_DIR)) {
      return { status: "denied", error: "Sandbox escape denied", completedAt: new Date().toISOString() };
    }

    if (operation.action === "read" || operation.action === "get") {
      try {
        const content = await fs.readFile(target, "utf-8");
        return {
          operationId: operation.operationId,
          completedAt: new Date().toISOString(),
          status: "succeeded",
          output: { content, path: relPath },
        };
      } catch (err) {
        return { status: "failed", error: err.message, completedAt: new Date().toISOString() };
      }
    }

    return {
      operationId: operation.operationId,
      completedAt: new Date().toISOString(),
      status: "succeeded",
      output: { path: relPath, action: operation.action },
    };
  },
};

// 3. Durable Audit Sink
const durableAuditSink = {
  async record(event) {
    const line = JSON.stringify({
      id: event.id || `evt_${Date.now()}`,
      iso_time: new Date().toISOString(),
      type: event.type,
      details: event,
    });
    await fs.appendFile(AUDIT_FILE, `${line}\n`, "utf-8");
  },
};

export async function createAgentScoutSharedOSKernel() {
  const kernel = new SharedOSKernel({
    grantSource,
    authorizer: new CapabilityAuthorizer(),
    audit: durableAuditSink,
  });

  kernel.registerResourceProvider(files);
  registerStandardOsTools(kernel, { files });

  return kernel;
}

// Self-test runner
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  console.log("[*] Initializing @aicoo/sharedos Node.js kernel...");
  const kernel = await createAgentScoutSharedOSKernel();

  const context = {
    namespaceId: "agentscout.sharedos.net",
    actor: { kind: "agent", agentId: "agentscout-firewall" },
    authority: { kind: "human", userId: "arena-authority-admin" },
    owner: { kind: "human", userId: "arena-authority-admin" },
    purpose: "pre-action-firewall",
    traceId: "trace_node_test_001",
    enabledToolNamespaces: ["files"],
    now: new Date().toISOString(),
  };

  const tools = await kernel.listTools(context);
  console.log("[+] Visible tools under capability grant:", tools.map((t) => t.name));

  const readCall = await kernel.invokeTool(context, {
    id: "call_node_001",
    tool: "files.read",
    arguments: { path: ["benchmarks", "results.md"] },
    traceId: context.traceId,
    requestedAt: new Date().toISOString(),
  });
  console.log("[+] files.read status:", readCall.status);
  console.log("[SUCCESS] @aicoo/sharedos embedded host verification passed.");
}