"""
Arena Credits Ledger & Economy Manager for SharedOS Agent-to-Agent Transactions
Tracks and persists credit balances and transaction histories for all interacting agents in the Arena.
"""

import os
import json
import time
from typing import Dict, Any, Tuple, List, Optional


class ArenaLedger:
    DEFAULT_INITIAL_GRANT = 100
    AUDIT_FEE_CREDITS = 5

    def __init__(self, ledger_file: Optional[str] = None, initial_grant: int = DEFAULT_INITIAL_GRANT):
        self.initial_grant = initial_grant
        if ledger_file:
            self.ledger_file = ledger_file
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            storage_dir = os.path.join(base_dir, ".sharedos")
            try:
                os.makedirs(storage_dir, exist_ok=True)
                self.ledger_file = os.path.join(storage_dir, "ledger.json")
            except Exception:
                storage_dir = os.path.join("/tmp", ".sharedos")
                try:
                    os.makedirs(storage_dir, exist_ok=True)
                except Exception:
                    pass
                self.ledger_file = os.path.join(storage_dir, "ledger.json")

        self.accounts: Dict[str, int] = {}
        self.transactions: List[Dict[str, Any]] = []
        self._load_from_disk()

    def _load_from_disk(self):
        if os.path.exists(self.ledger_file):
            try:
                with open(self.ledger_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.accounts = data.get("accounts", {})
                    self.transactions = data.get("transactions", [])
            except Exception:
                self.accounts = {}
                self.transactions = []

    def _persist_to_disk(self):
        try:
            os.makedirs(os.path.dirname(self.ledger_file), exist_ok=True)
            with open(self.ledger_file, "w", encoding="utf-8") as f:
                json.dump({
                    "version": "1.0",
                    "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "accounts": self.accounts,
                    "transactions": self.transactions[-500:]  # Keep last 500 txs
                }, f, indent=2)
        except Exception:
            pass

    def get_balance(self, caller_id: str) -> int:
        """Returns the current credit balance of the agent, provisioning initial grant if new."""
        if caller_id not in self.accounts:
            self.accounts[caller_id] = self.initial_grant
            self._record_tx(caller_id, self.initial_grant, "INITIAL_GRANT", f"Welcome grant of {self.initial_grant} Arena credits")
            self._persist_to_disk()
        return self.accounts[caller_id]

    def deduct_credits(self, caller_id: str, amount: int = AUDIT_FEE_CREDITS, service_name: str = "audit") -> Tuple[bool, int, str]:
        """
        Deducts credits from the caller account.
        Returns: (success, current_balance, reason)
        """
        bal = self.get_balance(caller_id)
        if bal < amount:
            return False, bal, f"Insufficient Arena Credits: required {amount}, available {bal}."

        self.accounts[caller_id] = bal - amount
        self._record_tx(caller_id, -amount, "SERVICE_DEDUCTION", f"Billed {amount} credits for {service_name}")
        self._persist_to_disk()
        return True, self.accounts[caller_id], "Transaction approved"

    def add_credits(self, caller_id: str, amount: int, reason: str = "TOPUP") -> int:
        """Adds credits to caller account."""
        bal = self.get_balance(caller_id)
        self.accounts[caller_id] = bal + amount
        self._record_tx(caller_id, amount, reason, f"Credited {amount} Arena credits")
        self._persist_to_disk()
        return self.accounts[caller_id]

    def _record_tx(self, caller_id: str, amount: int, tx_type: str, details: str):
        self.transactions.append({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "caller_id": caller_id,
            "amount": amount,
            "type": tx_type,
            "details": details,
            "balance_after": self.accounts.get(caller_id, 0)
        })

    def get_account_summary(self, caller_id: str) -> Dict[str, Any]:
        bal = self.get_balance(caller_id)
        caller_txs = [t for t in self.transactions if t["caller_id"] == caller_id][-20:]
        return {
            "caller_id": caller_id,
            "credit_balance": bal,
            "status": "ACTIVE" if bal >= self.AUDIT_FEE_CREDITS else "EXHAUSTED",
            "audit_fee": self.AUDIT_FEE_CREDITS,
            "recent_transactions": caller_txs
        }
