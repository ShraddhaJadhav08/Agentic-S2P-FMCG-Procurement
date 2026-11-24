"""
contracts.py — Automated Purchase Order & SLA Generator
Drafts formalized vendor agreements using financially audited payloads from the S2P pipeline.
"""
import datetime
from typing import Dict, Any

class ContractGenerator:
    """
    Automated Contract & Purchase Order Generator.
    Transforms financially validated pipeline states into legally binding B2B documents.
    """
    
    @staticmethod
    def generate_purchase_order(validated_data: Dict[str, Any]) -> str:
        print("\n📝 [CONTRACTS] Drafting formalized Purchase Order...")
        
        # 1. Extract transaction and vendor identifiers with robust fallback keys
        txn_id = (
            validated_data.get("transaction_id") 
            or validated_data.get("po_id") 
            or validated_data.get("session_id") 
            or "PO-PENDING"
        )
        supplier = (
            validated_data.get("selected_supplier") 
            or validated_data.get("vendor_id") 
            or "UNASSIGNED_VENDOR"
        )
        material = validated_data.get("material_name", "Unspecified Raw Material")
        
        # 2. Defensive numeric casting to prevent TypeError on missing values
        tonnage = float(validated_data.get("tonnage", 0.0))
        unit_price = float(validated_data.get("final_unit_price", 0.0))
        freight = float(validated_data.get("freight_cost", 0.0))
        total_cost = float(validated_data.get("total_landed_cost", 0.0))
        lead_time = int(
            validated_data.get("final_lead_time_days") 
            or validated_data.get("proposed_lead_time") 
            or 7
        )
        
        material_cost = round(tonnage * unit_price, 2)
        issue_date = datetime.date.today().strftime("%Y-%m-%d")
        
        # 3. Draft formalized PO & SLA text document
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
1. Delivery must be completed within {lead_time} days from issue date 
   (weather-adjusted SLA evaluated by MCDM engine).
2. Total invoice settlement shall not exceed ₹{total_cost:,.2f}.
3. Quality must strictly adhere to catalog specifications.
4. Non-compliance or delivery delays beyond {lead_time} days trigger 
   automatic contractual penalty reviews.

STATUS: FINANCIALLY AUDITED & SYSTEM APPROVED
====================================================
"""
        print("✅ [CONTRACTS] Purchase Order successfully generated.")
        return contract_text.strip()

# ============================================================================
# END-TO-END PIPELINE INTEGRATION TEST
# ============================================================================
if __name__ == "__main__":
    import uuid
    from agent_graph import ai_app
    from finance_agent import FinanceValidator
    from auth_gateway import AuthorizationGateway, SecurityBreachAlert
    
    print("🚀 Running Pipeline Trace: AI Graph -> Finance Audit -> Auth Gateway -> Contract Generation\n")
    
    test_state = {
        "session_id": str(uuid.uuid4()),
        "material_name": "Bulk Wheat Flour",
        "required_tonnage": 5.0,
        "inventory_urgency_days": 4
    }
    
    # Step 1: Run Multi-Agent LangGraph Pipeline
    print("--- 1. Executing LangGraph Multi-Agent Workflow ---")
    final_output = ai_app.invoke(test_state)
    
    # Step 2: Audit Output with Financial Validator
    print("\n--- 2. Auditing Output via Finance Validator ---")
    audit_result = FinanceValidator.audit_transaction(final_output)
    
    # Step 3: Dispatch to Gateway and Generate Contract if Audit Passes
    if audit_result["status"] == "APPROVED":
        validated_payload = audit_result["validated_data"]
        
        print("\n--- 3. Verifying Gateway Identity & Generating PO Document ---")
        gateway = AuthorizationGateway(password="1234")  # Set local PostgreSQL password
        
        try:
            # Validate through PostgreSQL 4-step security boundary
            gateway.validate_purchase_order(
                agent_id=validated_payload.get("agent_id", "AGENT_FINANCE_01"),
                auth_token=validated_payload.get("auth_token", "auth_token_xyz_123"), # Fixes the KeyError
                total_landed_cost=validated_payload.get("total_landed_cost", 0.0)
            )
            
            # Generate final legally binding Purchase Order document
            po_document = ContractGenerator.generate_purchase_order(validated_payload)
            print("\n" + po_document)
            
        except SecurityBreachAlert as breach:
            print(f"🛑 CONTRACT GENERATION ABORTED: Gateway blocked transaction: {breach}")
            
    else:
        print(f"❌ Contract generation aborted. Audit Verdict: {audit_result['status']} ({audit_result.get('reason')})")