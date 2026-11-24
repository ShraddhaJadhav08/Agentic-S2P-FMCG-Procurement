"""
main.py — FastAPI Enterprise S2P Backend
Features: Stage 4 Agentic S2P, True Separation of Duties (AGENT_SYSTEM_AUTO), and Zero-DB What-If Sandbox.
"""
import os
import io
import re
import time
import json
import uuid
import threading
import contextlib
from typing import Dict, Any, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="GoldenCrunch Enterprise S2P Command Center",
    description="Unified backend with True Separation of Duties & Autonomous Self-Healing.",
    version="5.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME", "fmcg_procurement"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", "1234"),
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432")
}

VENDOR_CATALOG = {
    "Bulk Wheat Flour": {"base_price": 35000.00, "floor_price": 31500.00, "lead_time_days": 7, "daily_burn_tons": 5.0, "corridor": "Indore → Mumbai", "distance_km": 585},
    "Refined Sugar": {"base_price": 42000.00, "floor_price": 38000.00, "lead_time_days": 10, "daily_burn_tons": 3.0, "corridor": "Baramati → Mumbai", "distance_km": 245},
    "Palm Oil": {"base_price": 75000.00, "floor_price": 68000.00, "lead_time_days": 5, "daily_burn_tons": 3.0, "corridor": "Kandla Port → Mumbai", "distance_km": 610},
    "Cocoa Beans": {"base_price": 260000.00, "floor_price": 240000.00, "lead_time_days": 14, "daily_burn_tons": 1.5, "corridor": "Kochi → Mumbai", "distance_km": 1150},
    "Bulk Corn (Maize)": {"base_price": 16000.00, "floor_price": 14500.00, "lead_time_days": 7, "daily_burn_tons": 2.0, "corridor": "Nagpur → Mumbai", "distance_km": 790},
    "Corrugated Cartons": {"base_price": 9000.00, "floor_price": 8200.00, "lead_time_days": 4, "daily_burn_tons": 2.0, "corridor": "Vapi → Mumbai", "distance_km": 170}
}

ENTERPRISE_SUPPLIER_POOL: Dict[str, List[Dict[str, Any]]] = {
    "Bulk Wheat Flour": [
        {"vendor_id": "Shakti Agro Mills Ltd.", "price_inr": 35000.0, "lead_time": 6, "reliability": 90.0},
        {"vendor_id": "Deccan Roller Flour Mills", "price_inr": 33000.0, "lead_time": 7, "reliability": 84.0},
        {"vendor_id": "Narmada Grain & Agritech", "price_inr": 38000.0, "lead_time": 5, "reliability": 96.0}
    ],
    "Refined Sugar": [
        {"vendor_id": "Konkan Sugars Ltd.", "price_inr": 41000.0, "lead_time": 8, "reliability": 91.0},
        {"vendor_id": "Baramati Cane Refineries", "price_inr": 39500.0, "lead_time": 9, "reliability": 85.0},
        {"vendor_id": "Godavari Sugar Corp.", "price_inr": 43500.0, "lead_time": 6, "reliability": 96.0}
    ],
    "Palm Oil": [
        {"vendor_id": "Sahyadri Oils Ltd.", "price_inr": 74000.0, "lead_time": 4, "reliability": 90.0},
        {"vendor_id": "Adani Wilmar Industrial", "price_inr": 71500.0, "lead_time": 5, "reliability": 86.0},
        {"vendor_id": "Godrej Agrovet Palm Div.", "price_inr": 78000.0, "lead_time": 3, "reliability": 97.0}
    ],
    "Cocoa Beans": [
        {"vendor_id": "Malabar Cocoa Estates", "price_inr": 255000.0, "lead_time": 11, "reliability": 90.0},
        {"vendor_id": "Nilgiri Craft Cocoa Ltd.", "price_inr": 246000.0, "lead_time": 13, "reliability": 85.0},
        {"vendor_id": "Olam Food Ingredients", "price_inr": 272000.0, "lead_time": 8, "reliability": 97.0}
    ],
    "Bulk Corn (Maize)": [
        {"vendor_id": "Kaveri Maize & Starch Co.", "price_inr": 15800.0, "lead_time": 6, "reliability": 91.0},
        {"vendor_id": "Vidarbha Agro Corp.", "price_inr": 14900.0, "lead_time": 7, "reliability": 85.0},
        {"vendor_id": "Indus Grain Logistics", "price_inr": 16900.0, "lead_time": 4, "reliability": 96.0}
    ],
    "Corrugated Cartons": [
        {"vendor_id": "Horizon Packtech Ltd.", "price_inr": 8900.0, "lead_time": 3, "reliability": 92.0},
        {"vendor_id": "Western India Corrugators", "price_inr": 8400.0, "lead_time": 4, "reliability": 86.0},
        {"vendor_id": "Apex Kraft Packaging", "price_inr": 9500.0, "lead_time": 2, "reliability": 97.0}
    ]
}

negotiation_sessions: Dict[str, int] = {}
latest_sandbox_analysis: Optional[Dict[str, Any]] = None

# ============================================================================
# 8-CONTROL AUTONOMOUS SELF-HEALING GUARDRAIL STATE
# ============================================================================
AUTO_HEAL_LOCK = threading.Lock()
AUTO_HEAL_STATE: Dict[str, Any] = {
    "enabled": False,                        
    "trigger_on_reorder": True,              
    "circuit_breaker_tripped": False,        
    "circuit_breaker_reason": "",
    "consecutive_failures": 0,
    "max_consecutive_failures": 2,
    "auto_orders_executed": 0,
    "max_auto_orders_per_window": 6,
    "per_order_auto_cap_inr": 2500000.0,     
    "cumulative_auto_spend_inr": 0.0,
    "max_cumulative_auto_spend_inr": 6000000.0,  
    "cooldown_seconds": 30,                  
    "last_order_timestamp_by_material": {},  
    "in_flight_materials": set(),            
    "pending_human_approvals": [],           
    "audit_trail": []                        
}

class CounterOfferRequest(BaseModel):
    session_id: str
    material_name: str
    proposed_unit_price: float = Field(..., gt=0)
    proposed_lead_time_days: int = Field(..., gt=0)
    tonnage: float = Field(..., gt=0)
    round_number: int = Field(..., ge=1, le=3)

class PipelineTriggerRequest(BaseModel):
    material_name: str = "Bulk Wheat Flour"
    required_tonnage: float = 25.0
    inventory_urgency_days: int = 4
    transport_distance_km: float = 100.0
    budget_cap: float = 4000000.0
    simulated_environment: str = "Mumbai"
    agent_id: str = "AGENT_FINANCE_01"
    auth_token: str = "secret_fin_token_123"

class StockConsumeRequest(BaseModel):
    mode: str = "SINGLE"
    material_name: str = "Bulk Wheat Flour"
    tons_used: float = 5.0
    shifts: float = 1.0
    reason: str = "Biscuit Line Production"

class AutoHealToggleRequest(BaseModel):
    enabled: bool
    reset_circuit_breaker: bool = False

class WhatIfSandboxRequest(BaseModel):
    prompt: Optional[str] = None
    material_name: str = "Bulk Wheat Flour"
    required_tonnage: float = 25.0
    delay_restock_days: int = 0
    custom_budget_cap: float = 4000000.0
    price_shock_pct: float = 0.0
    weather_scenario: str = "CLEAR"
    carrier_mode: str = "ROAD"
    transport_distance_km: float = 100.0
    agent_id: str = "AGENT_FINANCE_01"

class PolicyQueryRequest(BaseModel):
    query: str

def calculate_slab_discount(tonnage: float) -> float:
    if tonnage <= 20.0: return 0.00
    elif tonnage <= 50.0: return 0.02
    elif tonnage <= 100.0: return 0.05
    else: return 0.08

# ============================================================================
# AUTONOMOUS SELF-HEALING ORCHESTRATOR (SEPARATION OF DUTIES FIX)
# ============================================================================
def execute_autonomous_self_healing(breached_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Evaluates breached inventory items. Uses the AGENT_SYSTEM_AUTO credentials
    to commit routine orders < ₹25L. Escalates higher values to the Human Manager Queue.
    """
    from agent_graph import ai_app
    from finance_agent import FinanceValidator
    from auth_gateway import AuthorizationGateway, SecurityBreachAlert
    from contracts import ContractGenerator

    gw = AuthorizationGateway(password=DB_CONFIG["password"])
    actions_taken: List[Dict[str, Any]] = []

    if not AUTO_HEAL_STATE["enabled"]:
        return actions_taken

    for item in breached_items:
        mat = item["material_name"]
        cur_stock = float(item["current_stock_tons"])
        safety = float(item["safety_stock_tons"])
        reorder = float(item["reorder_point_tons"])
        now_ts = time.time()

        with AUTO_HEAL_LOCK:
            if AUTO_HEAL_STATE["circuit_breaker_tripped"]:
                actions_taken.append({"material": mat, "outcome": "BLOCKED_CIRCUIT_BREAKER", "detail": "Circuit breaker is TRIPPED."})
                continue

            if AUTO_HEAL_STATE["auto_orders_executed"] >= AUTO_HEAL_STATE["max_auto_orders_per_window"]:
                AUTO_HEAL_STATE["circuit_breaker_tripped"] = True
                AUTO_HEAL_STATE["enabled"] = False
                AUTO_HEAL_STATE["circuit_breaker_reason"] = "Max autonomous order frequency exceeded."
                gw.create_notification("SECURITY", "⚡ Circuit Breaker Tripped", AUTO_HEAL_STATE["circuit_breaker_reason"], mat)
                continue

            last_ts = AUTO_HEAL_STATE["last_order_timestamp_by_material"].get(mat, 0)
            if (now_ts - last_ts) < AUTO_HEAL_STATE["cooldown_seconds"]:
                actions_taken.append({"material": mat, "outcome": "SKIPPED_IDEMPOTENCY_COOLDOWN", "detail": "Idempotency lock active."})
                continue

            if mat in AUTO_HEAL_STATE["in_flight_materials"] or any(p["material_name"] == mat for p in AUTO_HEAL_STATE["pending_human_approvals"]):
                actions_taken.append({"material": mat, "outcome": "SKIPPED_ALREADY_RESERVED", "detail": "Inbound reservation exists."})
                continue

            AUTO_HEAL_STATE["in_flight_materials"].add(mat)

        try:
            target_stock = round(reorder * 1.25, 0)
            raw_needed = max(21.0, round(target_stock - cur_stock, 0))
            if mat == "Cocoa Beans": raw_needed = min(raw_needed, 12.0)

            urgency_days = 2 if cur_stock <= safety else 4
            corridor_dist = float(VENDOR_CATALOG.get(mat, {}).get("distance_km", 100.0))
            idempotency_key = f"AUTO_{mat[:3].upper()}_{int(now_ts)}"

            state_input = {
                "session_id": idempotency_key,
                "material_name": mat,
                "required_tonnage": float(raw_needed),
                "inventory_urgency_days": urgency_days,
                "transport_distance_km": corridor_dist,
                "budget_cap": 4000000.0,
                "simulated_environment": "Mumbai"
            }

            with contextlib.redirect_stdout(io.StringIO()):
                final_state = ai_app.invoke(state_input)
                audit = FinanceValidator.audit_transaction(final_state)

            if audit["status"] != "APPROVED":
                with AUTO_HEAL_LOCK:
                    AUTO_HEAL_STATE["consecutive_failures"] += 1
                    if AUTO_HEAL_STATE["consecutive_failures"] >= AUTO_HEAL_STATE["max_consecutive_failures"]:
                        AUTO_HEAL_STATE["circuit_breaker_tripped"] = True
                        AUTO_HEAL_STATE["enabled"] = False
                actions_taken.append({"material": mat, "outcome": "REJECTED_BY_FINANCE_AUDIT", "detail": audit.get("reason", "Failed audit")})
                continue

            val_data = audit["validated_data"]
            
            # --- SEPARATION OF DUTIES FIX: AI USES ITS OWN IDENTITY ---
            val_data["agent_id"] = "AGENT_SYSTEM_AUTO"  
            val_data["material_name"] = mat
            winner = final_state.get("winning_offer") or {}
            val_data["vendor_name"] = val_data.get("vendor_name") or winner.get("vendor_id", "Approved Vendor")
            val_data["total_tonnage"] = float(raw_needed)
            val_data["negotiated_unit_price"] = float(val_data.get("negotiated_unit_price") or winner.get("discounted_price") or winner.get("price_inr") or 1.0)
            landed_cost = float(val_data["total_landed_cost"])

            exceeds_per_order_cap = landed_cost > AUTO_HEAL_STATE["per_order_auto_cap_inr"]
            exceeds_cumulative_cap = (AUTO_HEAL_STATE["cumulative_auto_spend_inr"] + landed_cost) > AUTO_HEAL_STATE["max_cumulative_auto_spend_inr"]

            # IF > ₹25L: ESCALATE TO HUMAN QUEUE
            if exceeds_per_order_cap or exceeds_cumulative_cap:
                esc_reason = f"Order cost ₹{landed_cost:,.0f} exceeds autonomous limit" if exceeds_per_order_cap else "Rolling spend cap breached"
                pending_obj = {
                    "approval_id": idempotency_key,
                    "material_name": mat,
                    "tonnage": raw_needed,
                    "vendor_name": val_data["vendor_name"],
                    "total_landed_cost": landed_cost,
                    "carrier": val_data.get("selected_carrier", "Road"),
                    "reason": esc_reason,
                    "validated_data": val_data,
                    "created_at": time.strftime("%H:%M:%S")
                }
                with AUTO_HEAL_LOCK:
                    AUTO_HEAL_STATE["pending_human_approvals"].append(pending_obj)
                    AUTO_HEAL_STATE["audit_trail"].insert(0, {
                        "idempotency_key": idempotency_key,
                        "material": mat, "tons": raw_needed, "vendor": val_data["vendor_name"],
                        "landed_cost": landed_cost, "status": "ESCALATED_HUMAN_APPROVAL",
                        "reason": esc_reason, "timestamp": time.strftime("%H:%M:%S")
                    })
                gw.create_notification("WARNING", f"⏸️ Human Approval Required: {raw_needed:g}T {mat}", f"{esc_reason}. Queued for manager sign-off.", mat)
                actions_taken.append({"material": mat, "outcome": "ESCALATED_TO_HUMAN", "detail": esc_reason, "pending": pending_obj})
                continue

            # IF < ₹25L: AUTO-COMMIT AS AGENT_SYSTEM_AUTO
            gw.validate_purchase_order("AGENT_SYSTEM_AUTO", "auto_sys_token_999", landed_cost)
            po_doc = ContractGenerator.generate_purchase_order(val_data)
            po_id = gw.commit_to_ledger(val_data, po_doc)

            with AUTO_HEAL_LOCK:
                AUTO_HEAL_STATE["consecutive_failures"] = 0
                AUTO_HEAL_STATE["auto_orders_executed"] += 1
                AUTO_HEAL_STATE["cumulative_auto_spend_inr"] = round(AUTO_HEAL_STATE["cumulative_auto_spend_inr"] + landed_cost, 2)
                AUTO_HEAL_STATE["last_order_timestamp_by_material"][mat] = now_ts
                AUTO_HEAL_STATE["audit_trail"].insert(0, {
                    "idempotency_key": idempotency_key, "po_id": po_id,
                    "material": mat, "tons": raw_needed, "vendor": val_data["vendor_name"],
                    "carrier": val_data.get("selected_carrier", "Road"), "landed_cost": landed_cost,
                    "status": "AUTO_COMMITTED", "reason": f"Restored +{raw_needed:g}T.", "timestamp": time.strftime("%H:%M:%S")
                })

            gw.create_notification("PO_COMMITTED", f"⚡ Auto-Healed PO #{po_id}: +{raw_needed:g}T {mat}", f"System autonomously replenished {raw_needed:g}T.", mat)
            actions_taken.append({"material": mat, "outcome": "AUTO_REPLENISHED", "po_id": po_id, "tons_ordered": raw_needed, "vendor": val_data["vendor_name"], "landed_cost": landed_cost})

        except SecurityBreachAlert as breach:
            with AUTO_HEAL_LOCK:
                AUTO_HEAL_STATE["consecutive_failures"] += 1
                if AUTO_HEAL_STATE["consecutive_failures"] >= AUTO_HEAL_STATE["max_consecutive_failures"]:
                    AUTO_HEAL_STATE["circuit_breaker_tripped"] = True
                    AUTO_HEAL_STATE["enabled"] = False
            actions_taken.append({"material": mat, "outcome": "GATEWAY_BLOCKED", "detail": str(breach)})
        finally:
            with AUTO_HEAL_LOCK:
                AUTO_HEAL_STATE["in_flight_materials"].discard(mat)

    return actions_taken

@app.get("/api/auto-heal/status")
def get_auto_heal_status() -> Dict[str, Any]:
    return {
        "enabled": AUTO_HEAL_STATE["enabled"],
        "circuit_breaker_tripped": AUTO_HEAL_STATE["circuit_breaker_tripped"],
        "circuit_breaker_reason": AUTO_HEAL_STATE["circuit_breaker_reason"],
        "consecutive_failures": AUTO_HEAL_STATE["consecutive_failures"],
        "max_consecutive_failures": AUTO_HEAL_STATE["max_consecutive_failures"],
        "auto_orders_executed": AUTO_HEAL_STATE["auto_orders_executed"],
        "max_auto_orders_per_window": AUTO_HEAL_STATE["max_auto_orders_per_window"],
        "per_order_auto_cap_inr": AUTO_HEAL_STATE["per_order_auto_cap_inr"],
        "cumulative_auto_spend_inr": AUTO_HEAL_STATE["cumulative_auto_spend_inr"],
        "max_cumulative_auto_spend_inr": AUTO_HEAL_STATE["max_cumulative_auto_spend_inr"],
        "cooldown_seconds": AUTO_HEAL_STATE["cooldown_seconds"],
        "pending_human_approvals": [
            {k: v for k, v in p.items() if k != "validated_data"}
            for p in AUTO_HEAL_STATE["pending_human_approvals"]
        ],
        "audit_trail": AUTO_HEAL_STATE["audit_trail"][:15]
    }

@app.post("/api/auto-heal/toggle")
def toggle_auto_heal(req: AutoHealToggleRequest) -> Dict[str, Any]:
    from auth_gateway import AuthorizationGateway
    gw = AuthorizationGateway(password=DB_CONFIG["password"])
    with AUTO_HEAL_LOCK:
        if req.reset_circuit_breaker:
            AUTO_HEAL_STATE["circuit_breaker_tripped"] = False
            AUTO_HEAL_STATE["circuit_breaker_reason"] = ""
            AUTO_HEAL_STATE["consecutive_failures"] = 0
            AUTO_HEAL_STATE["auto_orders_executed"] = 0
            AUTO_HEAL_STATE["cumulative_auto_spend_inr"] = 0.0
            AUTO_HEAL_STATE["last_order_timestamp_by_material"].clear()
        AUTO_HEAL_STATE["enabled"] = bool(req.enabled)

    state_str = "ARMED (8 Guardrails Active)" if AUTO_HEAL_STATE["enabled"] else "DISARMED (Kill Switch Engaged)"
    gw.create_notification("INFO", f"Autonomous Self-Healing: {state_str}", f"Manager set autonomous replenishment state to {state_str}.")
    return get_auto_heal_status()

@app.post("/api/auto-heal/approve/{approval_id}")
def approve_escalated_order(approval_id: str) -> Dict[str, Any]:
    from auth_gateway import AuthorizationGateway
    from contracts import ContractGenerator
    gw = AuthorizationGateway(password=DB_CONFIG["password"])

    target = None
    with AUTO_HEAL_LOCK:
        for p in AUTO_HEAL_STATE["pending_human_approvals"]:
            if p["approval_id"] == approval_id:
                target = p
                break
        if target:
            AUTO_HEAL_STATE["pending_human_approvals"] = [p for p in AUTO_HEAL_STATE["pending_human_approvals"] if p["approval_id"] != approval_id]

    if not target:
        raise HTTPException(status_code=404, detail="Pending approval ID not found.")

    val_data = target["validated_data"]
    # --- HUMAN TAKES OWNERSHIP FIX ---
    val_data["agent_id"] = "AGENT_FINANCE_01"  
    gw.validate_purchase_order("AGENT_FINANCE_01", "secret_fin_token_123", val_data["total_landed_cost"])
    
    po_doc = ContractGenerator.generate_purchase_order(val_data)
    po_id = gw.commit_to_ledger(val_data, po_doc)

    with AUTO_HEAL_LOCK:
        AUTO_HEAL_STATE["last_order_timestamp_by_material"][target["material_name"]] = time.time()
        AUTO_HEAL_STATE["audit_trail"].insert(0, {
            "idempotency_key": approval_id, "po_id": po_id,
            "material": target["material_name"], "tons": target["tonnage"], "vendor": target["vendor_name"],
            "landed_cost": target["total_landed_cost"], "status": "HUMAN_APPROVED_COMMITTED",
            "reason": "Manager approved escalated high-value order.", "timestamp": time.strftime("%H:%M:%S")
        })

    return {"status": "COMMITTED", "po_id": po_id, "auto_heal": get_auto_heal_status()}

@app.post("/api/auto-heal/reject/{approval_id}")
def reject_escalated_order(approval_id: str) -> Dict[str, Any]:
    with AUTO_HEAL_LOCK:
        AUTO_HEAL_STATE["pending_human_approvals"] = [p for p in AUTO_HEAL_STATE["pending_human_approvals"] if p["approval_id"] != approval_id]
        AUTO_HEAL_STATE["audit_trail"].insert(0, {
            "idempotency_key": approval_id, "material": "Escalated Requisition", "tons": 0, "vendor": "-",
            "landed_cost": 0, "status": "HUMAN_REJECTED", "reason": "Manager rejected escalated order.", "timestamp": time.strftime("%H:%M:%S")
        })
    return {"status": "REJECTED", "auto_heal": get_auto_heal_status()}


def parse_nlp_prompt_into_request(req: WhatIfSandboxRequest) -> WhatIfSandboxRequest:
    if not req.prompt: return req
    text = req.prompt.lower()
    if "palm" in text: req.material_name = "Palm Oil"
    elif "sugar" in text: req.material_name = "Refined Sugar"
    elif "cocoa" in text: req.material_name = "Cocoa Beans"
    elif "corn" in text or "maize" in text: req.material_name = "Bulk Corn (Maize)"
    elif "carton" in text or "box" in text or "packag" in text: req.material_name = "Corrugated Cartons"
    elif "wheat" in text or "flour" in text: req.material_name = "Bulk Wheat Flour"

    tons_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:tons?|t\b)", text)
    if tons_m: req.required_tonnage = float(tons_m.group(1))

    delay_m = re.search(r"(?:delay\w*|wait\w*|hold\w*|postpone\w*|for|in)\s*(\d+)\s*days?", text)
    if delay_m: req.delay_restock_days = int(delay_m.group(1))
    else:
        bare_d = re.search(r"(\d+)\s*days?", text)
        if bare_d: req.delay_restock_days = int(bare_d.group(1))

    shock_m = re.search(r"([+-]?\d+(?:\.\d+)?)\s*%", text)
    if shock_m:
        val = float(shock_m.group(1))
        if any(w in text for w in ["decrease", "drop", "down", "fall", "reduce", "lower", "cut", "discount"]): val = -abs(val)
        req.price_shock_pct = val

    lakh_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakhs?|l\b)", text)
    if lakh_m: req.custom_budget_cap = float(lakh_m.group(1)) * 100000.0

    if any(w in text for w in ["storm", "monsoon", "cyclone", "severe"]): req.weather_scenario = "MONSOON_STORM"
    elif "rain" in text: req.weather_scenario = "RAIN"

    if "rail" in text or "train" in text: req.carrier_mode = "RAIL"
    elif "express" in text or "air" in text: req.carrier_mode = "EXPRESS"
    return req


@app.post("/supplier/counteroffer")
def process_counter_offer(request: CounterOfferRequest) -> Dict[str, Any]:
    if request.material_name not in VENDOR_CATALOG: raise HTTPException(status_code=404, detail="Material not found.")
    session_key = f"{request.session_id}_{request.material_name}"
    current_round = negotiation_sessions.get(session_key, 0)
    if request.round_number <= current_round: raise HTTPException(status_code=400, detail="Invalid round order.")
    negotiation_sessions[session_key] = request.round_number
    material = VENDOR_CATALOG[request.material_name]
    base_price, floor_price, min_lead_time = material["base_price"], material["floor_price"], material["lead_time_days"]
    discount_pct = calculate_slab_discount(request.tonnage)
    discounted_base_price = base_price * (1.0 - discount_pct)

    price_accepted = request.proposed_unit_price >= floor_price
    lead_time_accepted = request.proposed_lead_time_days >= min_lead_time

    if price_accepted and lead_time_accepted:
        status, final_price, final_lead_time, msg = "COUNTER_OFFER_ACCEPTED", request.proposed_unit_price, request.proposed_lead_time_days, f"Accepted in Round {request.round_number}."
    else:
        if request.round_number < 3:
            compromise_price = max(floor_price, (discounted_base_price + request.proposed_unit_price) / 2)
            status, final_price, final_lead_time, msg = "COUNTER_PROPOSAL_OFFERED", round(compromise_price, 2), max(min_lead_time, request.proposed_lead_time_days), f"Compromises in Round {request.round_number}."
        else:
            status, final_price, final_lead_time, msg = "NEGOTIATION_FAILED", discounted_base_price, min_lead_time, "Final round reached. Fails to meet margins."

    return {
        "session_id": request.session_id, "material_name": request.material_name, "round_number": request.round_number,
        "proposed_unit_price": request.proposed_unit_price, "negotiated_unit_price": round(final_price, 2),
        "negotiated_lead_time_days": final_lead_time, "total_cost": round(final_price * request.tonnage, 2),
        "status": status, "message": msg
    }


@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    dashboard_path = os.path.join(BASE_DIR, "dashboard.html")
    if os.path.exists(dashboard_path): return FileResponse(dashboard_path)
    return HTMLResponse("<h2>dashboard.html not found.</h2>")


@app.get("/api/telemetry")
def get_live_telemetry(location: str = "Mumbai") -> Dict[str, Any]:
    from market_telemetry import MarketTelemetry
    weather = MarketTelemetry.fetch_weather(location)
    fuel = MarketTelemetry.fetch_fuel_index()
    freight = MarketTelemetry.fetch_freight_rates()
    commodities = [MarketTelemetry.fetch_commodity_price(t) for t in ["WHT", "SGR", "PLM", "COA", "CORN", "CRT"]]
    corridors = [{
        "material": mat, "corridor": info["corridor"], "distance_km": info["distance_km"],
        "road_rate_inr_t": round(info["distance_km"] * 4.50 * fuel.get("freight_cost_multiplier", 1.12), 0),
        "rail_rate_inr_t": round(info["distance_km"] * 2.00 * fuel.get("freight_cost_multiplier", 1.12), 0),
        "weather_delay_days": weather.get("delay_days", 0)
    } for mat, info in VENDOR_CATALOG.items()]

    return {"weather": weather, "fuel": fuel, "freight": freight, "commodities": commodities, "logistics_corridors": corridors}


@app.get("/api/ledger")
def get_postgres_ledger() -> Dict[str, Any]:
    try:
        from auth_gateway import AuthorizationGateway
        AuthorizationGateway(password=DB_CONFIG["password"])
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM inventory ORDER BY item_id;")
                inventory = [dict(r) for r in cur.fetchall()]
                cur.execute("SELECT * FROM purchase_orders ORDER BY po_id DESC LIMIT 20;")
                orders = [dict(r) for r in cur.fetchall()]
                cur.execute("SELECT * FROM audit_log ORDER BY event_id DESC LIMIT 20;")
                audits = [dict(r) for r in cur.fetchall()]
                cur.execute("SELECT * FROM suppliers ORDER BY vendor_id;")
                suppliers = [dict(r) for r in cur.fetchall()]
                cur.execute("SELECT * FROM manager_notifications ORDER BY notif_id DESC LIMIT 30;")
                notifs = [dict(r) for r in cur.fetchall()]
                for n in notifs:
                    if n.get("created_at"): n["created_at"] = n["created_at"].strftime("%H:%M:%S")

        return {
            "status": "CONNECTED", "inventory": inventory, "purchase_orders": orders,
            "audit_log": audits, "suppliers": suppliers, "notifications": notifs,
            "auto_heal": get_auto_heal_status()
        }
    except Exception as e:
        return {"status": "ERROR", "message": str(e), "inventory": [], "purchase_orders": [], "audit_log": [], "notifications": []}


@app.post("/api/inventory/consume")
def consume_inventory_endpoint(req: StockConsumeRequest) -> Dict[str, Any]:
    try:
        from auth_gateway import AuthorizationGateway
        gw = AuthorizationGateway(password=DB_CONFIG["password"])

        if req.mode.upper() == "PRODUCTION_SHIFT":
            shift_results = gw.run_production_shift(shifts=req.shifts)
            breaches = [r for r in shift_results if r["threshold_status"] != "HEALTHY"]
            auto_actions = execute_autonomous_self_healing(breaches) if breaches else []
            return {
                "status": "SHIFT_COMPLETED", "shifts_executed": req.shifts, "materials_updated": len(shift_results),
                "threshold_breaches": len(breaches), "details": shift_results, "auto_heal_actions": auto_actions,
                "auto_heal_status": get_auto_heal_status()
            }
        else:
            res = gw.consume_factory_stock(material_name=req.material_name, tons_used=req.tons_used, reason=req.reason)
            breaches = [res] if res["threshold_status"] != "HEALTHY" else []
            auto_actions = execute_autonomous_self_healing(breaches) if breaches else []
            return {"status": "CONSUMED", "detail": res, "auto_heal_actions": auto_actions, "auto_heal_status": get_auto_heal_status()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/notifications")
def get_manager_notifications() -> Dict[str, Any]:
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM manager_notifications ORDER BY notif_id DESC LIMIT 30;")
                rows = [dict(r) for r in cur.fetchall()]
                for r in rows:
                    if r.get("created_at"): r["created_at"] = r["created_at"].strftime("%H:%M:%S")
        return {"status": "OK", "notifications": rows}
    except Exception as e:
        return {"status": "ERROR", "notifications": [], "message": str(e)}


@app.delete("/api/notifications")
def clear_manager_notifications() -> Dict[str, Any]:
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM manager_notifications;")
                conn.commit()
        return {"status": "CLEARED"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/what-if")
def run_what_if_sandbox(req: WhatIfSandboxRequest) -> Dict[str, Any]:
    global latest_sandbox_analysis
    from mcdm_engine import optimize_engine, get_slab_discount
    from market_telemetry import MarketTelemetry

    req = parse_nlp_prompt_into_request(req)

    cur_stock, safety_stock, reorder_pt, max_sla, max_budget_ton = 15.0, 10.0, 25.0, 7, 40000.0
    db_suppliers = []
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM inventory WHERE material_name = %s;", (req.material_name,))
                inv = cur.fetchone()
                if inv:
                    cur_stock, safety_stock, reorder_pt = float(inv["current_stock_tons"]), float(inv["safety_stock_tons"]), float(inv["reorder_point_tons"])
                    max_sla, max_budget_ton = int(inv["max_lead_time_days"]), float(inv["max_budget_per_ton"])
                cur.execute("SELECT vendor_id, price_inr, lead_time_days AS lead_time, reliability FROM suppliers WHERE material_supplied = %s AND is_active = TRUE;", (req.material_name,))
                db_suppliers = [dict(r) for r in cur.fetchall()]
    except Exception:
        pass

    raw_pool = db_suppliers if db_suppliers else ENTERPRISE_SUPPLIER_POOL.get(req.material_name, [])
    daily_burn = float(VENDOR_CATALOG.get(req.material_name, {}).get("daily_burn_tons", 5.0))
    base_carrier_rate = {"ROAD": 4.50, "RAIL": 2.00, "EXPRESS": 5.20}.get(req.carrier_mode.upper(), 4.50)
    fuel_mult = float(MarketTelemetry.fetch_fuel_index().get("freight_cost_multiplier", 1.12))

    weather_delay = 0
    if "STORM" in req.weather_scenario.upper() or "MONSOON" in req.weather_scenario.upper(): weather_delay = 3 if req.carrier_mode.upper() == "ROAD" else 1
    elif "RAIN" in req.weather_scenario.upper(): weather_delay = 1 if req.carrier_mode.upper() == "ROAD" else 0

    cover_day0 = round(cur_stock / max(0.5, daily_burn), 1)
    baseline_ranked = optimize_engine(candidates=[dict(s) for s in raw_pool], tons=req.required_tonnage, material_name=req.material_name, distance_km=req.transport_distance_km, freight_rate_per_ton_km=base_carrier_rate, freight_multiplier=fuel_mult, context={"inventory_urgency_days": max(1, int(round(cover_day0))), "commodity_trend": "STABLE", "weather_condition": "CLEAR", "custom_budget_cap": req.custom_budget_cap})

    burned_during_delay = round(daily_burn * max(0, req.delay_restock_days), 2)
    projected_stock_at_order = max(0.0, round(cur_stock - burned_during_delay, 2))
    remaining_cover_days = round(projected_stock_at_order / max(0.5, daily_burn), 1)

    shock_mult = 1.0 + (float(req.price_shock_pct) / 100.0)
    sim_candidates = [{"vendor_id": s["vendor_id"], "price_inr": round(float(s["price_inr"]) * shock_mult, 2), "lead_time": int(s["lead_time"]) + weather_delay, "reliability": float(s["reliability"])} for s in raw_pool]
    trend_str = "UP" if req.price_shock_pct > 2.0 else ("DOWN" if req.price_shock_pct < -2.0 else "STABLE")
    
    ranked = optimize_engine(candidates=sim_candidates, tons=req.required_tonnage, material_name=req.material_name, distance_km=req.transport_distance_km, freight_rate_per_ton_km=base_carrier_rate, freight_multiplier=fuel_mult, context={"inventory_urgency_days": max(1, int(round(remaining_cover_days))), "commodity_trend": trend_str, "weather_condition": req.weather_scenario, "custom_budget_cap": req.custom_budget_cap})

    if not ranked:
        return {"sandbox_mode": "MEMORY_ONLY_ZERO_DB_IMPACT", "verdict": "NO_SURVIVING_SUPPLIER", "material_name": req.material_name, "required_tonnage": req.required_tonnage, "current_stock_tons": cur_stock, "projected_stock_after_delay_tons": projected_stock_at_order, "remaining_cover_days": remaining_cover_days, "stockout_days_gap": round(max(0.0, 5.0 - remaining_cover_days), 1), "headline": f"All suppliers violated the ₹{req.custom_budget_cap:,.0f} cap or SLA.", "assumptions": [], "comparison_table": [], "recommendation": "Increase budget cap.", "ranked_suppliers": []}

    winner, base_winner = ranked[0], baseline_ranked[0] if baseline_ranked else ranked[0]
    lead_base, lead_sim = int(base_winner["lead_time"]), int(winner["lead_time"])
    arrival_day_base, arrival_day_sim = lead_base, req.delay_restock_days + lead_sim

    days_without_base, days_without_sim = round(max(0.0, arrival_day_base - cover_day0), 1), round(max(0.0, arrival_day_sim - cover_day0), 1)
    extra_downtime_days = round(max(0.0, days_without_sim - days_without_base), 1)
    unmet_tons_base, unmet_tons_sim = round(days_without_base * daily_burn, 1), round(days_without_sim * daily_burn, 1)

    cost_delta_inr = round(winner["total_landed_cost"] - base_winner["total_landed_cost"], 2)
    savings_inr = round(-cost_delta_inr, 2)
    slab_pct = int(get_slab_discount(req.required_tonnage) * 100)

    if req.delay_restock_days > 0 and extra_downtime_days > 0:
        if savings_inr > 0: headline = f"Delaying doesn't pay off: saving ₹{savings_inr:,.0f} leaves factory without {req.material_name} for {days_without_sim:g} days."
        else: headline = f"Critical Stockout Warning: delaying {req.delay_restock_days} days causes {days_without_sim:g} days of lost production."
    elif savings_inr > 0: headline = f"Favorable Scenario: saves ₹{savings_inr:,.0f} on {req.required_tonnage:g}T via {winner['vendor_id']}."
    else: headline = f"Cost Impact Analysis: landed cost shifts by ₹{cost_delta_inr:+,.0f} via {winner['vendor_id']}."

    assumptions = [
        f"Live PostgreSQL stock is {cur_stock:g}T; factory burn rate stays at {daily_burn:g}T/day (Stock hits zero on Day {cover_day0:g}).",
        f"Supplier quotes shift by {req.price_shock_pct:+.1f}% with {slab_pct}% wholesale slab applied on {req.required_tonnage:g}T."
    ]

    comparison_table = [
        {"metric": "Order Placed", "baseline": "Day 0 (Immediate)", "scenario": f"Day {req.delay_restock_days}"},
        {"metric": "Stock Hits Zero", "baseline": f"Day {cover_day0:g} ({cur_stock:g}T)", "scenario": f"Day {cover_day0:g} ({cur_stock:g}T)"},
        {"metric": f"Delivery Arrival ({lead_sim}d SLA)", "baseline": f"Day {arrival_day_base}", "scenario": f"Day {arrival_day_sim}"},
        {"metric": "Days Without Material", "baseline": f"{days_without_base:g}d ({unmet_tons_base:g}T unmet)", "scenario": f"{days_without_sim:g}d ({unmet_tons_sim:g}T unmet)"},
        {"metric": "Total Landed Cost", "baseline": f"₹{base_winner['total_landed_cost']:,.0f}", "scenario": f"₹{winner['total_landed_cost']:,.0f} ({cost_delta_inr:+,.0f})"}
    ]

    recommendation = (f"Hybrid Strategy: Dispatch immediate bridge batch of {max(5.0, round(unmet_tons_base + 5.0))}T now from {base_winner['vendor_id']}." if days_without_sim > 0 else f"Optimal Execution: Proceed with {req.required_tonnage:g}T from {winner['vendor_id']} via {req.carrier_mode} (Landed ₹{winner['total_landed_cost']:,.0f}).")

    result_payload = {
        "sandbox_mode": "MEMORY_ONLY_ZERO_DB_IMPACT", "verdict": "APPROVED_IN_SANDBOX" if days_without_sim == 0 else "STOCKOUT_RISK_DETECTED",
        "headline": headline, "assumptions": assumptions, "comparison_table": comparison_table, "material_name": req.material_name, "required_tonnage": req.required_tonnage,
        "delay_restock_days": req.delay_restock_days, "price_shock_pct": req.price_shock_pct, "remaining_cover_days": remaining_cover_days,
        "winning_supplier": winner["vendor_id"], "winning_lead_time_days": lead_sim, "stockout_days_gap": days_without_sim,
        "slab_discount_pct": slab_pct, "total_landed_cost_inr": winner["total_landed_cost"], "recommendation": recommendation
    }
    latest_sandbox_analysis = result_payload
    return result_payload


@app.post("/api/run-pipeline")
def trigger_s2p_pipeline(req: PipelineTriggerRequest) -> Dict[str, Any]:
    log_capture = io.StringIO()
    with contextlib.redirect_stdout(log_capture):
        from agent_graph import ai_app
        from finance_agent import FinanceValidator
        from auth_gateway import AuthorizationGateway, SecurityBreachAlert
        from contracts import ContractGenerator

        state_input = {"session_id": str(uuid.uuid4()), "material_name": req.material_name, "required_tonnage": float(req.required_tonnage), "inventory_urgency_days": int(req.inventory_urgency_days), "transport_distance_km": float(req.transport_distance_km), "budget_cap": float(req.budget_cap), "simulated_environment": req.simulated_environment}
        final_state = ai_app.invoke(state_input)
        audit = FinanceValidator.audit_transaction(final_state)

        response = {"session_id": state_input["session_id"], "explainability_trace": final_state.get("explainability_trace", []), "winning_offer": final_state.get("winning_offer"), "finance_audit_status": audit["status"], "gateway_status": "SKIPPED", "po_document": None}

        if audit["status"] == "APPROVED":
            val_data = audit["validated_data"]
            val_data["agent_id"] = req.agent_id
            val_data["material_name"] = req.material_name
            winner = final_state.get("winning_offer") or {}
            val_data["vendor_name"] = val_data.get("vendor_name") or winner.get("vendor_id", "Approved Vendor")
            val_data["total_tonnage"] = req.required_tonnage
            val_data["negotiated_unit_price"] = winner.get("negotiated_unit_price") or winner.get("discounted_price") or winner.get("price_inr") or 1.0

            gateway = AuthorizationGateway(password=DB_CONFIG["password"])
            try:
                gateway.validate_purchase_order(agent_id=req.agent_id, auth_token=req.auth_token, total_landed_cost=val_data["total_landed_cost"])
                po_doc = ContractGenerator.generate_purchase_order(val_data)
                gateway.commit_to_ledger(val_data, po_doc)
                response["gateway_status"] = "AUTHORIZED_AND_COMMITTED"
                response["po_document"] = po_doc
            except SecurityBreachAlert as breach:
                response["gateway_status"] = f"BLOCKED: {str(breach)}"

    response["console_logs"] = log_capture.getvalue()
    return response


@app.post("/api/policy-search")
def query_policy_rag(req: PolicyQueryRequest) -> Dict[str, Any]:
    with contextlib.redirect_stdout(io.StringIO()):
        from policy_search import search_purchasing_policy
        return {"query": req.query, "result": search_purchasing_policy(req.query)}


@app.post("/api/simulate")
def execute_stress_simulation() -> Dict[str, Any]:
    log_capture = io.StringIO()
    with contextlib.redirect_stdout(log_capture):
        from simulation_engine import ScenarioSimulationEngine
        sim = ScenarioSimulationEngine(db_password=DB_CONFIG["password"])
        sim.run_all_scenarios()

    passed = sum(1 for r in sim.audit_results if r["passed"])
    total = len(sim.audit_results)
    return {"score": f"{passed}/{total} Passed", "results": sim.audit_results}


@app.get("/api/proactive-insights")
def get_proactive_insights(location: str = "Mumbai") -> Dict[str, Any]:
    try:
        from proactive_copilot import ProactiveCopilotEngine
        data = ProactiveCopilotEngine.get_dashboard_insights(location=location)

        inv_map, fastest_sup_map = {}, {}
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM inventory;")
                for r in cur.fetchall(): inv_map[r["material_name"]] = dict(r)
                cur.execute("SELECT material_supplied, vendor_id, lead_time_days FROM suppliers WHERE is_active = TRUE ORDER BY lead_time_days ASC;")
                for s in cur.fetchall():
                    if s["material_supplied"] not in fastest_sup_map: fastest_sup_map[s["material_supplied"]] = dict(s)

        for item in data.get("insights", []):
            raw_payload = item.get("action_payload") or {}
            if isinstance(raw_payload, str):
                try: raw_payload = json.loads(raw_payload)
                except Exception: raw_payload = {}
            mat = raw_payload.get("material_name")
            if not mat:
                blob = f"{item.get('title', '')} {item.get('message', '')}".lower()
                for candidate_mat in VENDOR_CATALOG.keys():
                    if any(w in blob for w in candidate_mat.lower().split()):
                        mat = candidate_mat
                        break
                mat = mat or "Bulk Wheat Flour"

            tons, urg = float(raw_payload.get("required_tonnage") or 25.0), int(raw_payload.get("inventory_urgency_days") or 3)
            live_inv, live_sup, burn = inv_map.get(mat, {}), fastest_sup_map.get(mat, {}), VENDOR_CATALOG.get(mat, {}).get("daily_burn_tons", 3.0)
            cur_stk = float(live_inv.get("current_stock_tons", 15.0))

            item["live_cover_days"] = round(cur_stk / max(0.5, burn), 1)
            item["live_fastest_sla_days"] = int(live_sup.get("lead_time_days", 5))
            item["live_vendor_name"] = live_sup.get("vendor_id", "Approved Supplier")
            item["action_payload"] = {"material_name": mat, "required_tonnage": tons, "inventory_urgency_days": urg, "transport_distance_km": float(raw_payload.get("transport_distance_km") or 100.0), "budget_cap": 4000000.0, "simulated_environment": location, "agent_id": "AGENT_FINANCE_01"}
            if not item.get("action_label"): item["action_label"] = f"Dispatch {tons:g}T {mat}"

        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Copilot DB Error: {str(e)}")