"""
agent_states.py — Defines the shared memory state and the strict JSON output schema.

UPDATES:
1. Tokenless Migration: Removed 'token_hash' from FinalProposalSchema. Added 'session_id'
   to represent the active operational session validated by the Authorization Gateway.
2. Localized Currencies: Added field-level documentation indicating that prices and
   limits are strictly denominated in Indian Rupees (INR).
3. Reducer Validation: Preserved LangGraph's 'operator.add' channel for state tracing.
"""

import operator
from typing import Annotated, Any, Dict, List, Optional, TypedDict
from pydantic import BaseModel, Field

# ============================================================================
# 1. TRANSACTION HANDOFF SCHEMA (For Members 2 & 3)
# ============================================================================
class FinalProposalSchema(BaseModel):
    """
    Strict, Pydantic-validated schema representing an unverified purchasing proposal.
    Intercepted deterministically by the Authorization Gateway before database commit.
    """
    transaction_id: str = Field(..., description="Unique UUID generated for this transaction")
    session_id: str = Field(..., description="Active session ID associated with this purchase cycle")
    agent_id: str = Field(..., description="The registered ID of the submitting agent (e.g. AGENT_FINANCE_01)")
    selected_supplier: str = Field(..., description="Name of the vendor shortlisted by the MCDM Engine")
    material_name: str = Field(..., description="The approved commodity being purchased")
    tonnage: float = Field(..., gt=0.0, description="Volume of material requested in tons")
    final_unit_price: float = Field(..., gt=0.0, description="Negotiated price in Indian Rupees (INR) per ton")
    freight_cost: float = Field(..., ge=0.0, description="Logistics overhead estimated by the Logistics Agent in INR")
    total_landed_cost: float = Field(..., gt=0.0, description="True Landed Cost (Material Cost + Freight) in INR")
    budget_cap: float = Field(..., description="Assign transaction budget cap in INR (Max INR 40 Lakhs)")
    is_compliant: bool = Field(..., description="Flag indicating if the proposal meets all baseline policies")
    human_approval_required: bool = Field(..., description="Triggers a human-in-the-loop gate if safety boundaries are violated")


# ============================================================================
# 2. SHARED WORKFLOW STATE (For LangGraph Agents)
# ============================================================================
class SharedPurchaseOrderState(TypedDict):
    """
    The shared memory state passed between cognitive agents in the LangGraph workflow.
    """
    session_id: str                         # The active execution session ID
    material_name: str                      # Commodity requested (from config.APPROVED_CATALOG)
    required_tonnage: float                 # Requested purchase volume
    transport_distance_km: float            # Distance estimate from factory to supplier
    budget_cap: float                       # Maximum allowed budget for this order (INR)
    simulated_environment: str              # Holds 'NORMAL' or 'SIMULATION' mode flag
    candidate_suppliers: List[Dict[str, Any]] # Surviving suppliers loaded from database
    negotiation_rounds: int                 # Count of current B2B negotiation rounds (Max 3)
    proposed_price: float                   # Active unit price counter during B2B exchanges
    proposed_lead_time: int                 # Active lead time counter during B2B exchanges
    winning_offer: Optional[Dict[str, Any]] # Selected offer after MCDM optimization ranking
    human_approval_required: bool           # True if margins breached or negotiation fails after round 3
    final_json_payload: Dict[str, Any]      # Final dictionary matching FinalProposalSchema

    # Reducer channel: appends agent decisions sequentially to construct the UI trace
    explainability_trace: Annotated[List[Dict[str, Any]], operator.add]