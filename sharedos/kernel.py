"""
SharedOS Capability Kernel & Authorizer
Provides fail-closed capability verification, resource provider dispatching,
and durable audit logging for every agent tool call and file operation.
"""

import os
import sys
import time
import uuid
from typing import Dict, Any, List, Optional, Callable

from sharedos.grant_store import CapabilityGrantStore, GrantStoreOutageError
from sharedos.cloud_audit_sink import DurableSharedOSAuditSink


class FilesResourceProvider:
    """
    Standard SharedOS 'files' resource plane provider.
    Provides sandboxed read, search, list, and stat operations for agent evidence & fixtures.
    """

    def __init__(self, root_dir: Optional[str] = None):
        self.root_dir = os.path.abspath(root_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.namespace = "files"

    def invoke(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        action = operation.get("action", "read")
        resource = operation.get("resource", {})
        path_segments = resource.get("path", [])
        rel_path = os.path.join(*path_segments) if path_segments else ""
        target_path = os.path.abspath(os.path.join(self.root_dir, rel_path))

        # Enforce sandbox containment (no directory traversal escapes)
        if not target_path.startswith(self.root_dir):
            return {
                "status": "denied",
                "error": "Path traversal escape denied",
                "reasonCode": "sandbox_violation"
            }

        if action in ("read", "get"):
            if not os.path.exists(target_path) or os.path.isdir(target_path):
                return {"status": "failed", "error": f"File not found: {rel_path}", "reasonCode": "not_found"}
            try:
                with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(100000)  # bounded read
                return {"status": "succeeded", "output": {"content": content, "path": rel_path}}
            except Exception as e:
                return {"status": "failed", "error": str(e), "reasonCode": "io_error"}

        elif action in ("list", "readdir"):
            if not os.path.exists(target_path):
                return {"status": "failed", "error": "Directory not found", "reasonCode": "not_found"}
            try:
                entries = [
                    {"name": name, "is_dir": os.path.isdir(os.path.join(target_path, name))}
                    for name in os.listdir(target_path)[:100]
                ]
                return {"status": "succeeded", "output": {"entries": entries}}
            except Exception as e:
                return {"status": "failed", "error": str(e), "reasonCode": "io_error"}

        elif action in ("search", "grep"):
            query = operation.get("input", {}).get("query", "").lower()
            hits = []
            if os.path.exists(target_path):
                for root, _, files in os.walk(target_path):
                    for file in files:
                        if file.endswith((".py", ".json", ".md", ".txt", ".jsonl")):
                            fp = os.path.join(root, file)
                            try:
                                with open(fp, "r", encoding="utf-8", errors="replace") as f:
                                    text = f.read()
                                    if query in text.lower():
                                        hits.append({"file": os.path.relpath(fp, self.root_dir), "match": True})
                                        if len(hits) >= 20:
                                            break
                            except Exception:
                                pass
            return {"status": "succeeded", "output": {"hits": hits, "query": query}}

        elif action in ("stat",):
            if not os.path.exists(target_path):
                return {"status": "failed", "error": "File not found", "reasonCode": "not_found"}
            st = os.stat(target_path)
            return {
                "status": "succeeded",
                "output": {
                    "size": st.st_size,
                    "mtime": st.st_mtime,
                    "is_dir": os.path.isdir(target_path)
                }
            }

        return {"status": "failed", "error": f"Unsupported action: {action}", "reasonCode": "unsupported_action"}


class CapabilityAuthorizer:
    """
    Evaluates requested tool invocations against active capability grants loaded from GrantStore.
    """

    def __init__(self, grant_store: CapabilityGrantStore):
        self.grant_store = grant_store

    def authorize(
        self,
        context: Dict[str, Any],
        resource_namespace: str,
        resource_path: List[str],
        action: str
    ) -> Dict[str, Any]:
        try:
            grants = self.grant_store.load_active_grants_for(context)
        except GrantStoreOutageError as e:
            return {
                "allowed": False,
                "reasonCode": "authority_unavailable",
                "message": f"Grant store outage: {e}",
                "failClosed": True
            }

        context_purpose = context.get("purpose", "")
        now_iso = context.get("now", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

        for grant in grants:
            constraints = grant.get("constraints", {})
            
            # 1. Purpose check
            allowed_purposes = constraints.get("purposes")
            if allowed_purposes and context_purpose and context_purpose not in allowed_purposes:
                continue

            # 2. Expiry check
            expires_at = constraints.get("expiresAt")
            if expires_at and expires_at < now_iso:
                continue

            # 3. Max uses check
            max_uses = constraints.get("maxUses")
            if max_uses is not None and max_uses <= 0:
                continue

            # 4. Capability capabilities match
            for cap in grant.get("capabilities", []):
                res = cap.get("resource", {})
                if res.get("namespace") != resource_namespace and res.get("namespace") != "*":
                    continue

                # Action match
                allowed_actions = cap.get("actions", [])
                if action not in allowed_actions and "*" not in allowed_actions:
                    continue

                # Path match & scope
                cap_path = res.get("path", [])
                scope = cap.get("scope", "descendants")

                if scope == "all" or cap_path == ["*"]:
                    path_matched = True
                elif scope == "exact":
                    path_matched = (cap_path == resource_path)
                elif scope == "descendants":
                    path_matched = (
                        len(resource_path) >= len(cap_path) and
                        resource_path[:len(cap_path)] == cap_path
                    ) or not cap_path
                elif scope == "ancestors":
                    path_matched = (
                        len(resource_path) <= len(cap_path) and
                        cap_path[:len(resource_path)] == resource_path
                    )
                else:
                    path_matched = (cap_path == resource_path)

                if path_matched:
                    # Bounded grant consumption
                    if max_uses is not None:
                        self.grant_store.try_consume_use(grant["id"])
                    
                    return {
                        "allowed": True,
                        "grantId": grant["id"],
                        "reasonCode": "authorized"
                    }

        return {
            "allowed": False,
            "reasonCode": "no_matching_grant",
            "message": f"No active capability grant authorized {resource_namespace}:{'/'.join(resource_path)} ({action})"
        }


class SharedOSKernel:
    """
    Production-grade SharedOS Kernel for AgentScout.
    Enforces deny-by-default capability authorization, tool registration, and audit syncing.
    """

    def __init__(
        self,
        grant_store: Optional[CapabilityGrantStore] = None,
        audit_sink: Optional[DurableSharedOSAuditSink] = None,
        node_id: str = "agentscout.sharedos.net"
    ):
        self.node_id = node_id
        self.grant_store = grant_store or CapabilityGrantStore()
        self.authorizer = CapabilityAuthorizer(self.grant_store)
        self.audit_sink = audit_sink or DurableSharedOSAuditSink()
        self.resource_providers: Dict[str, Any] = {}
        self.tools: Dict[str, Dict[str, Any]] = {}
        
        # Register standard files resource provider
        self.register_resource_provider(FilesResourceProvider())
        self._register_standard_tools()

    def register_resource_provider(self, provider: Any):
        self.resource_providers[provider.namespace] = provider

    def register_tool(
        self,
        name: str,
        namespace: str,
        handler: Callable[[Dict[str, Any]], Dict[str, Any]],
        description: str = "",
        resource_mapping: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    ):
        self.tools[name] = {
            "name": name,
            "namespace": namespace,
            "handler": handler,
            "description": description,
            "resource_mapping": resource_mapping or (lambda args: {"namespace": namespace, "path": [name], "action": "invoke"})
        }

    def _register_standard_tools(self):
        """Registers standard OS file tools."""
        files_provider = self.resource_providers.get("files")
        if files_provider:
            self.register_tool(
                name="files.read",
                namespace="files",
                description="Reads content from a sandboxed evidence file",
                handler=lambda args: files_provider.invoke({
                    "action": "read",
                    "resource": {"namespace": "files", "path": args.get("path", [])}
                }),
                resource_mapping=lambda args: {
                    "namespace": "files",
                    "path": args.get("path", []),
                    "action": "read"
                }
            )
            self.register_tool(
                name="files.search",
                namespace="files",
                description="Performs semantic/text search across sandboxed files",
                handler=lambda args: files_provider.invoke({
                    "action": "search",
                    "resource": {"namespace": "files", "path": args.get("path", [])},
                    "input": {"query": args.get("query", "")}
                }),
                resource_mapping=lambda args: {
                    "namespace": "files",
                    "path": args.get("path", []),
                    "action": "search"
                }
            )
            self.register_tool(
                name="files.list",
                namespace="files",
                description="Lists directory entries in the evidence folder",
                handler=lambda args: files_provider.invoke({
                    "action": "list",
                    "resource": {"namespace": "files", "path": args.get("path", [])}
                }),
                resource_mapping=lambda args: {
                    "namespace": "files",
                    "path": args.get("path", []),
                    "action": "list"
                }
            )

    def list_tools(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Lists tools available and visible to the given access context."""
        enabled_namespaces = set(context.get("enabledToolNamespaces", ["agentscout", "files", "sharedos"]))
        visible = []
        for name, tool in self.tools.items():
            if tool["namespace"] in enabled_namespaces:
                visible.append({
                    "name": tool["name"],
                    "namespace": tool["namespace"],
                    "description": tool["description"]
                })
        return visible

    def invoke_tool(self, context: Dict[str, Any], call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Authorizes and executes exactly one bounded tool call.
        Enforces 3-tier gate: Registered -> Namespace Enabled -> Capability Allowed.
        Records every decision to the DurableAuditSink.
        """
        tool_name = call.get("tool") or call.get("name", "")
        tool_args = call.get("arguments") or call.get("input", {})
        call_id = call.get("id") or f"call_{uuid.uuid4().hex[:12]}"
        
        tool = self.tools.get(tool_name)
        if not tool:
            decision = {"allowed": False, "reasonCode": "tool_not_found", "message": f"Tool '{tool_name}' not registered"}
            self.audit_sink.record_decision("tool.invoked", context, decision, call, event_id=call_id)
            return {"status": "denied", "callId": call_id, **decision}

        # Gate 2: Namespace enablement
        enabled_namespaces = set(context.get("enabledToolNamespaces", ["agentscout", "files", "sharedos"]))
        if tool["namespace"] not in enabled_namespaces:
            decision = {
                "allowed": False,
                "reasonCode": "namespace_disabled",
                "message": f"Tool namespace '{tool['namespace']}' is disabled for this context"
            }
            self.audit_sink.record_decision("tool.invoked", context, decision, call, event_id=call_id)
            return {"status": "denied", "callId": call_id, **decision}

        # Gate 3: Capability authorization
        req = tool["resource_mapping"](tool_args)
        auth_decision = self.authorizer.authorize(
            context=context,
            resource_namespace=req.get("namespace", tool["namespace"]),
            resource_path=req.get("path", [tool_name]),
            action=req.get("action", "invoke")
        )

        if not auth_decision.get("allowed"):
            self.audit_sink.record_decision("tool.invoked", context, auth_decision, call, event_id=call_id)
            return {"status": "denied", "callId": call_id, **auth_decision}

        # Execute registered handler
        try:
            handler_result = tool["handler"](tool_args)
            record_decision = {
                "allowed": True,
                "reasonCode": "authorized",
                "grantId": auth_decision.get("grantId"),
                "status": "succeeded"
            }
            self.audit_sink.record_decision("tool.invoked", context, record_decision, call, event_id=call_id)
            return {
                "status": "succeeded",
                "callId": call_id,
                "grantId": auth_decision.get("grantId"),
                "output": handler_result
            }
        except Exception as e:
            err_decision = {
                "allowed": True,
                "reasonCode": "execution_error",
                "error": str(e),
                "status": "failed"
            }
            self.audit_sink.record_decision("tool.invoked", context, err_decision, call, event_id=call_id)
            return {"status": "failed", "callId": call_id, "error": str(e)}