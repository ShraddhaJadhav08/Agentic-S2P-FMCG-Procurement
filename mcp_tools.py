"""
mcp_tools.py — Windows-Hardened FastMCP Server for Claude Desktop
Includes live What-If Sandbox Simulation tool synced with the Web Dashboard.
"""
import os
try:
    from dotenv import load_dotenv
    load_dotenv()          # reads DB_PASSWORD etc. from your local .env file
except ImportError:
    pass
import sys
import io
import json
import uuid
import contextlib
from typing import Dict, Any

os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("AgentResourceRegistry")

DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME", "fmcg_procurement"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432")
}


@mcp.tool()
def policy_tool(query: str) -> str:
    """Search the vector database for purchasing policy rules."""
    with contextlib.redirect_stdout(io.StringIO()):
        from policy_search import search_purchasing_policy
        return search_purchasing_policy(query)


@mcp.tool()
def weather_tool(location: str = "Mumbai") -> dict:
    """Get localized weather risks and delay projections."""
    from market_telemetry import MarketTelemetry
    return MarketTelemetry.fetch_weather(location)


@mcp.tool()
def freight_tool() -> dict:
    """Get deterministic ton-km freight rates in INR."""
    from market_telemetry import MarketTelemetry
    return MarketTelemetry.fetch_freight_rates()


@mcp.tool()
def commodity_tool(ticker: str) -> dict:
    """Get localized index spot prices and trend metrics (INR per ton). Tickers: WHT, SGR, PLM, COA, CORN, CRT."""
    from market_telemetry import MarketTelemetry
    return MarketTelemetry.fetch_commodity_price(ticker)


@mcp.tool()
def fuel_tool() -> dict:
    """Get localized fuel benchmarks (INR) and freight cost multipliers."""
    from market_telemetry import MarketTelemetry
    return MarketTelemetry.fetch_fuel_index()


@mcp.tool()
def get_live_supply_chain_snapshot(location: str = "Mumbai") -> dict:
    """Pulls a complete live ecosystem snapshot for proactive AI cross-analysis."""
    from proactive_copilot import ProactiveCopilotEngine
    return ProactiveCopilotEngine.get_live_supply_chain_snapshot(location)


@mcp.tool()
def publish_copilot_insights_to_dashboard(insights_json_string: str, location: str = "Mumbai") -> dict:
    """Publishes Claude Desktop's AI-generated supply chain optimization insights into PostgreSQL."""
    from proactive_copilot import ProactiveCopilotEngine
    try:
        insights = json.loads(insights_json_string)
        return ProactiveCopilotEngine.save_insights_to_db(insights, location=location, ai_source="CLAUDE_DESKTOP_MCP")
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}


@mcp.tool()
def simulate_what_if_scenario(
    material_name: str = "Bulk Wheat Flour",
    required_tonnage: float = 25.0,
    delay_restock_days: int = 0,
    price_shock_pct: float = 0.0,
    weather_scenario: str = "CLEAR",
    carrier_mode: str = "ROAD",
    custom_budget_cap: float = 4000000.0
) -> Dict[str, Any]:
    """
    Runs a non-destructive What-If comparison (Order Day 0 vs Delayed/Shocked Order)
    using live PostgreSQL inventory & MCDM vendor ranking without modifying the database.
    """
    from main import WhatIfSandboxRequest, run_what_if_sandbox
    req = WhatIfSandboxRequest(
        material_name=material_name,
        required_tonnage=required_tonnage,
        delay_restock_days=delay_restock_days,
        price_shock_pct=price_shock_pct,
        weather_scenario=weather_scenario,
        carrier_mode=carrier_mode,
        custom_budget_cap=custom_budget_cap
    )
    return run_what_if_sandbox(req)


@mcp.tool()
def check_database_inventory(material_name: str = None) -> Dict[str, Any]:
    """Query PostgreSQL inventory stock levels and registered active suppliers."""
    import psycopg2
    from psycopg2.extras import RealDictCursor
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if material_name:
                    cur.execute("SELECT * FROM inventory WHERE material_name = %s;", (material_name,))
                    inv = cur.fetchall()
                    cur.execute("SELECT * FROM suppliers WHERE material_supplied = %s;", (material_name,))
                    sup = cur.fetchall()
                else:
                    cur.execute("SELECT * FROM inventory ORDER BY item_id;")
                    inv = cur.fetchall()
                    cur.execute("SELECT * FROM suppliers ORDER BY vendor_id;")
                    sup = cur.fetchall()
        return {"status": "SUCCESS", "inventory": [dict(r) for r in inv], "suppliers": [dict(r) for r in sup]}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}


@mcp.tool()
def check_procurement_ledger(limit: int = 10) -> Dict[str, Any]:
    """Fetch committed Purchase Orders and blocked security events from PostgreSQL."""
    import psycopg2
    from psycopg2.extras import RealDictCursor
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM purchase_orders ORDER BY po_id DESC LIMIT %s;", (limit,))
                orders = cur.fetchall()
                cur.execute("SELECT * FROM audit_log ORDER BY event_id DESC LIMIT %s;", (limit,))
                audits = cur.fetchall()
        return {
            "status": "SUCCESS",
            "purchase_orders": [dict(r) for r in orders],
            "security_audit_log": [dict(r) for r in audits]
        }
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}


@mcp.tool()
def run_s2p_procurement_pipeline(
    material_name: str,
    required_tonnage: float,
    inventory_urgency_days: int = 4,
    transport_distance_km: float = 100.0,
    budget_cap: float = 4000000.0,
    agent_id: str = "AGENT_FINANCE_01",
    auth_token: str = "secret_fin_token_123"
) -> Dict[str, Any]:
    """Runs the full 4-Agent LangGraph workflow, Finance Validator, Authorization Gateway, and Contract Generator."""
    log_capture = io.StringIO()
    with contextlib.redirect_stdout(log_capture):
        from agent_graph import ai_app
        from finance_agent import FinanceValidator
        from auth_gateway import AuthorizationGateway, SecurityBreachAlert
        from contracts import ContractGenerator

        state_input = {
            "session_id": str(uuid.uuid4()),
            "material_name": material_name,
            "required_tonnage": float(required_tonnage),
            "inventory_urgency_days": int(inventory_urgency_days),
            "transport_distance_km": float(transport_distance_km),
            "budget_cap": float(budget_cap)
        }
        final_state = ai_app.invoke(state_input)
        audit = FinanceValidator.audit_transaction(final_state)

        result = {
            "session_id": state_input["session_id"],
            "explainability_trace": final_state.get("explainability_trace", []),
            "winning_offer": final_state.get("winning_offer"),
            "finance_audit_verdict": audit["status"],
            "finance_audit_reason": audit.get("reason", "Passed all checks."),
            "gateway_verdict": "SKIPPED",
            "purchase_order_document": None
        }

        if audit["status"] == "APPROVED":
            val_data = audit["validated_data"]
            val_data["agent_id"] = agent_id
            val_data["material_name"] = material_name
            winner = final_state.get("winning_offer") or {}
            if "vendor_name" not in val_data:
                val_data["vendor_name"] = winner.get("vendor_name") or winner.get("vendor_id", "Approved Vendor")
            if "total_tonnage" not in val_data:
                val_data["total_tonnage"] = required_tonnage
            if "negotiated_unit_price" not in val_data:
                val_data["negotiated_unit_price"] = winner.get("negotiated_unit_price") or winner.get("discounted_price") or winner.get("price_inr") or 1.0

            gateway = AuthorizationGateway(password=DB_CONFIG["password"])
            try:
                gateway.validate_purchase_order(
                    agent_id=agent_id,
                    auth_token=auth_token,
                    total_landed_cost=val_data["total_landed_cost"]
                )
                po_doc = ContractGenerator.generate_purchase_order(val_data)
                gateway.commit_to_ledger(val_data, po_doc)
                result["gateway_verdict"] = "AUTHORIZED_AND_COMMITTED"
                result["purchase_order_document"] = po_doc
            except SecurityBreachAlert as breach:
                result["gateway_verdict"] = f"BLOCKED BY GATEWAY: {str(breach)}"

    result["console_trace"] = log_capture.getvalue()
    return result


@mcp.tool()
def run_12_scenario_simulation() -> Dict[str, Any]:
    """Runs the 12 adversarial stress-testing scenarios and returns the summary matrix."""
    log_capture = io.StringIO()
    with contextlib.redirect_stdout(log_capture):
        from simulation_engine import ScenarioSimulationEngine
        sim = ScenarioSimulationEngine(db_password=DB_CONFIG["password"])
        sim.run_all_scenarios()

    passed = sum(1 for r in sim.audit_results if r["passed"])
    total = len(sim.audit_results)
    return {
        "final_score": f"{passed}/{total} Scenarios Passed ({(passed/total)*100:.1f}%)",
        "matrix": sim.audit_results,
        "console_trace": log_capture.getvalue()
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")