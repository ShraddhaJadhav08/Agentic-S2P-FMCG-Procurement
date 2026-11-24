"""
mcdm_engine.py — Academic-Grade Two-Phase Multi-Criteria Decision Making (MCDM) Engine
Phase 1: Hard Constraint Filter with Feasibility-Aware Dynamic SLA Bounding.
Phase 2: Hybrid Relational + Min-Max Normalized Scoring so distinct supplier archetypes
         (Cost Leader, Speed Leader, Reliability Leader) win dynamically.
"""
from typing import List, Dict, Any, Optional


def get_slab_discount(tons: float) -> float:
    """Calculates discount percentage based on wholesale volume brackets (Policy v4)."""
    if tons > 100.0:
        return 0.08
    if tons >= 50.0:
        return 0.05
    if tons >= 20.0:
        return 0.02
    return 0.0


def optimize_engine(
    candidates: List[Dict[str, Any]],
    tons: float,
    material_name: str,
    distance_km: float = 100.0,
    freight_rate_per_ton_km: float = 4.50,
    freight_multiplier: float = 1.12,
    context: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Two-Phase Deterministic MCDM Optimization Engine.
    """
    # =========================================================================
    # 1. DYNAMIC WEIGHT VECTOR CALIBRATION
    # =========================================================================
    w_cost, w_lead, w_rel = 0.50, 0.30, 0.20
    urgency_days = 10
    commodity_trend = "STABLE"
    weather_condition = "CLEAR"

    if context:
        urgency_days = int(context.get("inventory_urgency_days", 10))
        commodity_trend = str(context.get("commodity_trend", "STABLE")).upper()
        weather_condition = str(context.get("weather_condition", "CLEAR")).upper()

        # Scenario A: Inventory Shortage (Days Remaining < 3) -> Prioritize Speed
        if urgency_days < 3:
            w_lead, w_cost, w_rel = 0.50, 0.30, 0.20

        # Scenario B: Severe Weather Warning -> Prioritize Delivery Reliability
        elif "STORM" in weather_condition or "MONSOON" in weather_condition or "RAIN" in weather_condition:
            w_rel, w_cost, w_lead = 0.40, 0.30, 0.30

        # Scenario C: Rising Commodity Trends -> Prioritize Cost-Containment
        elif commodity_trend == "UP":
            w_cost, w_lead, w_rel = 0.60, 0.20, 0.20

    # =========================================================================
    # 2. PHASE 1: FEASIBILITY-AWARE SLA BOUNDING & HARD CONSTRAINT FILTER
    # =========================================================================
    MAX_TRANSACTION_BUDGET_INR = float(
        (context or {}).get("custom_budget_cap", 4000000.00)
    )

    MATERIAL_SLAS = {
        "Bulk Wheat Flour": 7,
        "Refined Sugar": 10,
        "Palm Oil": 5,
        "Cocoa Beans": 14,
        "Bulk Corn (Maize)": 7,
        "Corrugated Cartons": 4
    }
    base_sla = MATERIAL_SLAS.get(material_name, 7)

    # Find the fastest physically achievable lead time in the candidate pool
    fastest_available_lead = min(
        (max(1, int(c.get("lead_time", 99))) for c in candidates),
        default=base_sla
    )

    # Tighten SLA to urgency_days if at least one supplier can physically meet it;
    # otherwise bound to base_sla and flag the unavoidable lead-time gap.
    if context and "inventory_urgency_days" in context:
        if urgency_days >= fastest_available_lead:
            max_allowed_lead_time = min(base_sla, urgency_days)
        else:
            max_allowed_lead_time = base_sla
    else:
        max_allowed_lead_time = base_sla

    discount = get_slab_discount(tons)
    survivors: List[Dict[str, Any]] = []

    for c in candidates:
        price_raw = max(1.0, float(c.get("price_inr", 0.0)))
        lead_time = max(1, int(c.get("lead_time", 1)))

        discounted_price = price_raw * (1.0 - discount)
        material_cost = discounted_price * tons

        freight_cost = c.get("freight_cost", None)
        if freight_cost is None:
            freight_cost = tons * distance_km * freight_rate_per_ton_km * freight_multiplier

        total_landed_cost = material_cost + freight_cost

        # Strict Phase-1 boundary gates
        if total_landed_cost > MAX_TRANSACTION_BUDGET_INR:
            continue
        if lead_time > max_allowed_lead_time:
            continue

        c_copy = dict(c)
        c_copy["discounted_price"] = round(discounted_price, 2)
        c_copy["material_cost"] = round(material_cost, 2)
        c_copy["freight_cost"] = round(freight_cost, 2)
        c_copy["total_landed_cost"] = round(total_landed_cost, 2)
        c_copy["lead_time"] = lead_time

        lead_gap_days = max(0, lead_time - urgency_days)
        c_copy["lead_gap_days"] = lead_gap_days
        c_copy["delivery_feasibility"] = (
            "MEETS_URGENCY_WINDOW" if lead_gap_days == 0
            else f"EXPEDITE_REQUIRED (+{lead_gap_days}d gap)"
        )

        raw_rel = float(c.get("reliability", 85.0))
        c_copy["reliability"] = raw_rel / 100.0 if raw_rel > 1.0 else raw_rel
        survivors.append(c_copy)

    if not survivors:
        return []

    # =========================================================================
    # 3. PHASE 2: HYBRID RELATIONAL + MIN-MAX CONTRAST NORMALIZATION
    # =========================================================================
    min_cost = min(s["total_landed_cost"] for s in survivors)
    max_cost = max(s["total_landed_cost"] for s in survivors)
    cost_span = max(1.0, max_cost - min_cost)

    min_lead = min(s["lead_time"] for s in survivors)
    max_lead = max(s["lead_time"] for s in survivors)
    lead_span = max(1.0, float(max_lead - min_lead))

    min_rel = min(s["reliability"] for s in survivors)
    max_rel = max(s["reliability"] for s in survivors)
    rel_span = max(0.01, max_rel - min_rel)

    for s in survivors:
        rel_cost_ratio = min_cost / s["total_landed_cost"]
        minmax_cost = (max_cost - s["total_landed_cost"]) / cost_span if max_cost > min_cost else 1.0
        n_cost = (0.50 * rel_cost_ratio) + (0.50 * minmax_cost)

        rel_lead_ratio = min_lead / s["lead_time"]
        minmax_lead = (max_lead - s["lead_time"]) / lead_span if max_lead > min_lead else 1.0
        n_lead = (0.50 * rel_lead_ratio) + (0.50 * minmax_lead)

        minmax_rel = (s["reliability"] - min_rel) / rel_span if max_rel > min_rel else s["reliability"]
        n_rel = (0.50 * s["reliability"]) + (0.50 * minmax_rel)

        score = (w_cost * n_cost) + (w_lead * n_lead) + (w_rel * n_rel)
        s["mcdm_score"] = round(score, 4)
        s["weights_applied"] = {
            "cost": w_cost,
            "lead_time": w_lead,
            "reliability": w_rel
        }

    return sorted(survivors, key=lambda x: x["mcdm_score"], reverse=True)