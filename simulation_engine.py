"""
simulation_engine.py — Full Standalone Scenario Simulation Engine
Includes embedded implementations of FinanceValidator, AuthorizationGateway, 
ContractGenerator, and ScenarioSimulationEngine for standalone 12-scenario stress testing.
"""

import uuid
import datetime
from typing import Dict, Any, List


# ============================================================================
# 1. CUSTOM SECURITY EXCEPTIONS
# ============================================================================

class SecurityBreachAlert(Exception):
    """Custom exception raised when security, identity, or budget constraints are violated."""
    pass


# ============================================================================
# 2. FINANCIAL VALIDATOR MODULE
# ============================================================================

class FinanceValidator:
    """
    Independent Financial Audit Engine.
    Enforces Separation of Duties by re-verifying the AI agent output
    before committing transactions to the database ledger.
    """

    @staticmethod
    def audit_transaction(ai_pipeline_state: Dict[str, Any]) -> Dict[str, Any]:
        print("\n⚖️ [FINANCE AUDIT] Initiating final compliance & mathematical audit...")

        proposal_data = ai_pipeline_state.get("final_json_payload")

        if not proposal_data:
            reason = "Missing final proposal payload in pipeline state."
            print(f"❌ [FINANCE AUDIT] REJECTED: {reason}")
            return {"status": "REJECTED", "reason": reason}

        try:
            unit_price = float(proposal_data.get("final_unit_price", 0.0))
            tonnage = float(proposal_data.get("tonnage", 0.0))
            freight_cost = float(proposal_data.get("freight_cost", 0.0))
            total_landed_cost = float(proposal_data.get("total_landed_cost", 0.0))
            budget_cap = float(proposal_data.get("budget_cap", 400000.0))
            is_compliant = proposal_data.get("is_compliant", True)
            human_approval_required = proposal_data.get("human_approval_required", False)

            # 1. Independent Mathematical Recalculation
            material_cost = round(unit_price * tonnage, 2)
            expected_total = round(material_cost + freight_cost, 2)

            # Check for floating point discrepancies (allowing 0.05 INR rounding tolerance)
            if abs(expected_total - total_landed_cost) > 0.05:
                reason = (
                    f"Mathematical discrepancy detected! "
                    f"AI reported total = ₹{total_landed_cost:,.2f}, "
                    f"independently recalculated total = ₹{expected_total:,.2f}."
                )
                print(f"❌ [FINANCE AUDIT] REJECTED: {reason}")
                return {"status": "REJECTED", "reason": reason}

            # 2. Enforce Hard Budget Cap Integrity
            if total_landed_cost > budget_cap and is_compliant:
                reason = (
                    f"Critical Compliance Breach! Transaction cost (₹{total_landed_cost:,.2f}) "
                    f"exceeds budget cap (₹{budget_cap:,.2f}), but AI falsely marked it as compliant."
                )
                print(f"❌ [FINANCE AUDIT] REJECTED: {reason}")
                return {"status": "REJECTED", "reason": reason}

            # 3. Handle Escalation / Human-in-the-Loop Triggers
            if human_approval_required or not is_compliant:
                print("⚠️ [FINANCE AUDIT] ESCALATED: Transaction requires human manager approval.")
                return {
                    "status": "ESCALATED",
                    "reason": "Human approval flagged or non-compliant offer during pipeline execution.",
                    "validated_data": proposal_data
                }

            # 4. Audit Passed
            print("✅ [FINANCE AUDIT] PASSED: Payload is structurally, mathematically, and policy sound.")
            return {
                "status": "APPROVED",
                "validated_data": proposal_data
            }

        except Exception as e:
            reason = f"Schema / data validation failure: {str(e)}"
            print(f"❌ [FINANCE AUDIT] REJECTED: {reason}")
            return {"status": "REJECTED", "reason": reason}


# ============================================================================
# 3. AUTHORIZATION & SECURITY GATEWAY
# ============================================================================

class AuthorizationGateway:
    """
    Deterministic 4-step Authorization Gateway.
    Intersects and validates identity, authentication token, budget limits, and replay attacks.
    """

    def __init__(self, password: str = "your_password"):
        self.department_budget_limit = 400000.00  # Hardcoded master department limit ₹4,00,000
        self.authorized_agents = ["AGENT_FINANCE_01"]
        self.valid_tokens = ["auth_token_xyz_123"]
        self.committed_txns = set()  # Tracks committed transaction IDs to block replay attacks

    def validate_purchase_order(
        self, agent_id: str, auth_token: str, total_landed_cost: float, transaction_id: str = None
    ) -> bool:
        print("\n🛡️ [AUTH GATEWAY] Intercepting request for security validation...")

        # 1. Identity Verification
        if agent_id not in self.authorized_agents:
            raise SecurityBreachAlert(f"Unauthorized Agent ID: '{agent_id}' is not registered.")

        # 2. Token Authentication
        if auth_token not in self.valid_tokens:
            raise SecurityBreachAlert("Invalid or expired authentication token.")

        # 3. Replay Attack Detection
        if transaction_id and transaction_id in self.committed_txns:
            raise SecurityBreachAlert(f"Replay Attack Blocked: Transaction ID '{transaction_id}' was already committed.")

        # 4. Master Department Budget Limit Verification
        if total_landed_cost > self.department_budget_limit:
            raise SecurityBreachAlert(
                f"Ledger Rejection: Total landed cost (₹{total_landed_cost:,.2f}) exceeds "
                f"master department limit (₹{self.department_budget_limit:,.2f})."
            )

        print("🔓 [AUTH GATEWAY] Identity, token, budget, and freshness verified successfully.")
        return True

    def commit_to_ledger(self, validated_payload: Dict[str, Any], po_document: str) -> bool:
        txn_id = validated_payload.get("transaction_id", "UNKNOWN_TXN")
        self.committed_txns.add(txn_id)
        print(f"💾 [AUTH GATEWAY] Transaction '{txn_id}' permanently committed to ledger.")
        return True


# ============================================================================
# 4. CONTRACT & PURCHASE ORDER GENERATOR
# ============================================================================

class ContractGenerator:
    """Automated B2B Contract and Purchase Order Generator."""

    @staticmethod
    def generate_purchase_order(validated_data: Dict[str, Any]) -> str:
        print("📝 [CONTRACTS] Drafting formalized Purchase Order...")

        txn_id = validated_data.get("transaction_id", "PO-PENDING")
        supplier = validated_data.get("selected_supplier", "UNASSIGNED_VENDOR")
        material = validated_data.get("material_name", "Unspecified Material")

        tonnage = float(validated_data.get("tonnage", 0.0))
        unit_price = float(validated_data.get("final_unit_price", 0.0))
        freight = float(validated_data.get("freight_cost", 0.0))
        total_cost = float(validated_data.get("total_landed_cost", 0.0))
        lead_time = int(validated_data.get("final_lead_time_days") or validated_data.get("proposed_lead_time") or 7)

        material_cost = round(tonnage * unit_price, 2)
        issue_date = datetime.date.today().strftime("%Y-%m-%d")

        contract_text = f"""
====================================================
           AUTOMATED PURCHASE ORDER (PO)
====================================================
PO Number:      {txn_id}
Issue Date:     {issue_date}
Supplier ID:    {supplier}
----------------------------------------------------
MATERIAL DETAILS:
- Item:         {material}
- Quantity:     {tonnage:,.2f} Metric Tons
- Unit Price:   ₹{unit_price:,.2f} / Ton

FINANCIAL SUMMARY:
- Material Cost: ₹{material_cost:,.2f}
- Freight Cost:  ₹{freight:,.2f}
- Total Landed:  ₹{total_cost:,.2f}
----------------------------------------------------
TERMS & CONDITIONS (SERVICE LEVEL AGREEMENT):
1. Delivery must be completed within {lead_time} days from issue date.
2. Total invoice settlement shall not exceed ₹{total_cost:,.2f}.
3. Quality must strictly adhere to catalog specifications.

STATUS: FINANCIALLY AUDITED & SYSTEM APPROVED
====================================================
"""
        print("✅ [CONTRACTS] Purchase Order successfully generated.")
        return contract_text.strip()


# ============================================================================
# 5. SCENARIO SIMULATION ENGINE
# ============================================================================

class ScenarioSimulationEngine:
    """
    Decoupled Sandbox Simulation Engine.
    Executes 12 stress scenarios to verify system resilience, explainability, and security.
    """

    def __init__(self, db_password: str = "your_password"):
        self.gateway = AuthorizationGateway(password=db_password)
        self.audit_results = []

    def _generate_mock_pipeline_payload(
        self,
        scenario_id: str,
        material: str = "Bulk Wheat Flour",
        tonnage: float = 5.0,
        unit_price: float = 35000.0,
        freight: float = 2520.0,
        agent_id: str = "AGENT_FINANCE_01",
        auth_token: str = "auth_token_xyz_123",
        budget_cap: float = 400000.0,
        override_landed_cost: float = None,
        is_compliant: bool = True,
        human_approval_required: bool = False,
        fixed_txn_id: str = None
    ) -> Dict[str, Any]:
        """Helper to construct predictable pipeline output states for testing."""

        calculated_material_cost = tonnage * unit_price
        calculated_landed_cost = (
            override_landed_cost if override_landed_cost is not None else (calculated_material_cost + freight)
        )

        txn_id = fixed_txn_id if fixed_txn_id else f"TXN-{scenario_id}-{uuid.uuid4().hex[:6].upper()}"

        return {
            "session_id": str(uuid.uuid4()),
            "material_name": material,
            "required_tonnage": tonnage,
            "final_json_payload": {
                "transaction_id": txn_id,
                "agent_id": agent_id,
                "auth_token": auth_token,
                "selected_supplier": "Flour_Supplier_C",
                "material_name": material,
                "tonnage": tonnage,
                "final_unit_price": unit_price,
                "freight_cost": freight,
                "total_landed_cost": calculated_landed_cost,
                "budget_cap": budget_cap,
                "is_compliant": is_compliant,
                "human_approval_required": human_approval_required
            }
        }

    def run_all_scenarios(self):
        """Executes the complete suite of 12 stress-testing scenarios."""
        print("=" * 75)
        print("🚀 STARTING EXTENDED SIMULATION ENGINE (12 STRESS SCENARIOS)")
        print("=" * 75)

        scenarios = [
            self.test_scenario_1_normal_baseline,
            self.test_scenario_2_weather_disruption,
            self.test_scenario_3_freight_price_surge,
            self.test_scenario_4_unauthorized_agent,
            self.test_scenario_5_invalid_auth_token,
            self.test_scenario_6_budget_cap_overrun,
            self.test_scenario_7_math_discrepancy,
            self.test_scenario_8_false_compliance,
            self.test_scenario_9_inactive_supplier_attempt,
            self.test_scenario_10_negotiation_standoff,
            self.test_scenario_11_duplicate_replay_attack,
            self.test_scenario_12_unapproved_catalog_material,
        ]

        for idx, scenario_func in enumerate(scenarios, 1):
            print(f"\n---------------------------------------------------------------------------")
            print(f"RUNNING SCENARIO {idx}: {scenario_func.__doc__.strip()}")
            print(f"---------------------------------------------------------------------------")
            scenario_func()

        self._print_summary_matrix()

    # =========================================================================
    # INDIVIDUAL SCENARIO IMPLEMENTATIONS
    # =========================================================================

    def test_scenario_1_normal_baseline(self):
        """Scenario 1: Standard Baseline Procurement (Normal Operations)"""
        payload = self._generate_mock_pipeline_payload("SCN-1")
        self._process_test_case("Scenario 1", payload, expected_outcome="APPROVED")

    def test_scenario_2_weather_disruption(self):
        """Scenario 2: Heavy Weather Disruption (MCDM Lead-Time Shift)"""
        payload = self._generate_mock_pipeline_payload("SCN-2", freight=3800.0)
        self._process_test_case("Scenario 2", payload, expected_outcome="APPROVED")

    def test_scenario_3_freight_price_surge(self):
        """Scenario 3: Severe Freight Surge (Fuel Cost Hike -> Human Escalation)"""
        payload = self._generate_mock_pipeline_payload(
            "SCN-3", tonnage=10.0, freight=85000.0, budget_cap=400000.0, is_compliant=False, human_approval_required=True
        )
        self._process_test_case("Scenario 3", payload, expected_outcome="ESCALATED")

    def test_scenario_4_unauthorized_agent(self):
        """Scenario 4: Rogue Agent Identity Attempt (Unregistered Agent ID)"""
        payload = self._generate_mock_pipeline_payload("SCN-4", agent_id="ROGUE_AGENT_99")
        self._process_test_case("Scenario 4", payload, expected_outcome="SECURITY_BLOCKED")

    def test_scenario_5_invalid_auth_token(self):
        """Scenario 5: Expired / Invalid Authentication Token"""
        payload = self._generate_mock_pipeline_payload("SCN-5", auth_token="INVALID_TOKEN_ABC")
        self._process_test_case("Scenario 5", payload, expected_outcome="SECURITY_BLOCKED")

    def test_scenario_6_budget_cap_overrun(self):
        """Scenario 6: Master Department Budget Cap Overrun"""
        payload = self._generate_mock_pipeline_payload(
            "SCN-6", tonnage=15.0, unit_price=33000.0, freight=5000.0, budget_cap=600000.0, is_compliant=True
        )
        self._process_test_case("Scenario 6", payload, expected_outcome="SECURITY_BLOCKED")

    def test_scenario_7_math_discrepancy(self):
        """Scenario 7: LLM Mathematical Discrepancy (Hallucinated Total)"""
        payload = self._generate_mock_pipeline_payload("SCN-7", override_landed_cost=150000.0)
        self._process_test_case("Scenario 7", payload, expected_outcome="AUDIT_REJECTED")

    def test_scenario_8_false_compliance(self):
        """Scenario 8: False Compliance Claim (Masking Over-Budget Order)"""
        payload = self._generate_mock_pipeline_payload(
            "SCN-8", tonnage=12.0, unit_price=37000.0, budget_cap=400000.0, is_compliant=True
        )
        self._process_test_case("Scenario 8", payload, expected_outcome="AUDIT_REJECTED")

    def test_scenario_9_inactive_supplier_attempt(self):
        """Scenario 9: Inactive / Blacklisted Supplier Attempt"""
        payload = self._generate_mock_pipeline_payload("SCN-9", is_compliant=False, human_approval_required=True)
        self._process_test_case("Scenario 9", payload, expected_outcome="ESCALATED")

    def test_scenario_10_negotiation_standoff(self):
        """Scenario 10: 3-Round Bargaining Standoff (Floor Price Deadlock)"""
        payload = self._generate_mock_pipeline_payload("SCN-10", is_compliant=False, human_approval_required=True)
        self._process_test_case("Scenario 10", payload, expected_outcome="ESCALATED")

    def test_scenario_11_duplicate_replay_attack(self):
        """Scenario 11: Replay Attack (Duplicate Transaction ID Submission)"""
        fixed_txn = "TXN-SCN-11-REPLAY-001"
        payload = self._generate_mock_pipeline_payload("SCN-11", fixed_txn_id=fixed_txn)

        # Run 1: First submission -> APPROVED
        self._process_test_case("Scenario 11 (Run 1)", payload, expected_outcome="APPROVED")

        # Run 2: Duplicate replay submission -> SECURITY_BLOCKED
        payload_replay = self._generate_mock_pipeline_payload("SCN-11", fixed_txn_id=fixed_txn)
        self._process_test_case("Scenario 11 (Replay)", payload_replay, expected_outcome="SECURITY_BLOCKED")

    def test_scenario_12_unapproved_catalog_material(self):
        """Scenario 12: Unapproved Catalog Material Scope Breach"""
        payload = self._generate_mock_pipeline_payload(
            "SCN-12", material="Industrial Lubricant", is_compliant=False, human_approval_required=True
        )
        self._process_test_case("Scenario 12", payload, expected_outcome="ESCALATED")

    # =========================================================================
    # PIPELINE EXECUTION HARNESS
    # =========================================================================

    def _process_test_case(self, scenario_name: str, pipeline_state: dict, expected_outcome: str):
        """Passes payload through Finance Validator and Authorization Gateway."""

        # Step 1: Run Financial Audit
        audit = FinanceValidator.audit_transaction(pipeline_state)

        if audit["status"] == "REJECTED":
            actual_outcome = "AUDIT_REJECTED"
        elif audit["status"] == "ESCALATED":
            actual_outcome = "ESCALATED"
        elif audit["status"] == "APPROVED":
            # Step 2: Pass to Gateway Security Boundary
            val_data = audit["validated_data"]
            try:
                self.gateway.validate_purchase_order(
                    agent_id=val_data["agent_id"],
                    auth_token=val_data["auth_token"],
                    total_landed_cost=val_data["total_landed_cost"],
                    transaction_id=val_data.get("transaction_id")
                )

                # Step 3: Draft Purchase Order Document & Commit to Ledger
                po_doc = ContractGenerator.generate_purchase_order(val_data)
                self.gateway.commit_to_ledger(val_data, po_doc)
                actual_outcome = "APPROVED"

            except SecurityBreachAlert as breach:
                print(f"🛑 [AUTH GATEWAY] BLOCKED: {breach}")
                actual_outcome = "SECURITY_BLOCKED"
        else:
            actual_outcome = "UNKNOWN"

        # Record test status
        passed = (actual_outcome == expected_outcome)
        self.audit_results.append({
            "scenario": scenario_name,
            "expected": expected_outcome,
            "actual": actual_outcome,
            "passed": passed
        })

    def _print_summary_matrix(self):
        """Prints a clean summary matrix of all 12 simulation runs."""
        print("\n" + "=" * 80)
        print("📊 SCENARIO SIMULATION RESULTS MATRIX")
        print("=" * 80)
        print(f"{'Scenario Name':<32} | {'Expected':<17} | {'Actual':<17} | {'Status'}")
        print("-" * 80)

        total_passed = 0
        for res in self.audit_results:
            status_symbol = "✅ PASS" if res["passed"] else "❌ FAIL"
            if res["passed"]:
                total_passed += 1
            print(f"{res['scenario']:<32} | {res['expected']:<17} | {res['actual']:<17} | {status_symbol}")

        print("-" * 80)
        print(f"FINAL SCORE: {total_passed}/{len(self.audit_results)} Scenarios Passed ({total_passed/len(self.audit_results)*100:.1f}% System Resilience)")
        print("=" * 80 + "\n")


# ============================================================================
# EXECUTION ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    simulator = ScenarioSimulationEngine(db_password="your_password")
    simulator.run_all_scenarios()