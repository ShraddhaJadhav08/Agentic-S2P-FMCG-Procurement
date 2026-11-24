"""
auth_gateway.py — Zero-Trust Authorization Gateway + Live Inventory Lifecycle & Manager Alerts
1. Enforces 4-step RBAC, token authentication, separation of duties, and ₹40L budget cap.
2. Automatically ADDS ordered tonnage to PostgreSQL `inventory` whenever a PO is committed.
3. Reduces stock via `consume_factory_stock()` (single item) or `run_production_shift()`
   (full biscuit recipe batch) and triggers automatic CRITICAL / REORDER manager alerts.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, List


class SecurityBreachAlert(Exception):
    """Raised when an agent violates any of the 4 Zero-Trust Authorization Gateway checks."""
    pass


class AuthorizationGateway:
    AUTHORIZED_AGENTS = {
        "AGENT_FINANCE_01": {
            "role": "FINANCE_COMMIT",
            "token": "secret_fin_token_123",
            "max_cap": 4000000.00
        },
        "AGENT_SOURCING_01": {
            "role": "SOURCING_NEGOTIATE",
            "token": "secret_src_token_456",
            "max_cap": 0.00
        },
        "AGENT_INVENTORY_01": {
            "role": "INVENTORY_READ",
            "token": "secret_inv_token_789",
            "max_cap": 0.00
        },
        "AGENT_SYSTEM_AUTO": {
            "role": "AUTONOMOUS_ORCHESTRATOR",
            "token": "auto_sys_token_999",
            "max_limit_inr": 2500000.0  # Visa Stage 3 Autonomous Limit
        }
    }

    # Standard GoldenCrunch Biscuit Shift Bill of Materials (Tons used per shift)
    BISCUIT_SHIFT_BOM = {
        "Bulk Wheat Flour": 5.0,
        "Refined Sugar": 3.0,
        "Palm Oil": 3.0,
        "Cocoa Beans": 1.5,
        "Bulk Corn (Maize)": 2.0,
        "Corrugated Cartons": 2.0
    }

    def __init__(
        self,
        password: str = "sneha123",
        dbname: str = "fmcg_procurement",
        user: str = "postgres",
        host: str = "localhost",
        port: str = "5432",
        **kwargs
    ):
        self.db_config = {
            "dbname": os.environ.get("DB_NAME", "fmcg_procurement"),
            "user": os.environ.get("DB_USER","postgres"),
            "password": os.environ.get("DB_PASSWORD", "sneha123"),
            "host": os.environ.get("DB_HOST", "localhost"),
            "port": os.environ.get("DB_PORT", "5432")
        }
        self._ensure_notifications_table()

    def _ensure_notifications_table(self):
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS manager_notifications (
                            notif_id SERIAL PRIMARY KEY,
                            notif_type VARCHAR(30) DEFAULT 'INFO',
                            title VARCHAR(160),
                            message TEXT,
                            material_name VARCHAR(100),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    conn.commit()
        except Exception:
            pass

    def create_notification(
        self,
        notif_type: str,
        title: str,
        message: str,
        material_name: str = ""
    ):
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO manager_notifications (notif_type, title, message, material_name)
                        VALUES (%s, %s, %s, %s);
                    """, (notif_type.upper(), title, message, material_name))
                    conn.commit()
        except Exception as e:
            print(f"[Notification Log Warning]: {e}")

    def _log_security_event(self, agent_id: str, step_failed: str, error_message: str):
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO audit_log (agent_id, step_failed, error_message)
                        VALUES (%s, %s, %s);
                    """, (agent_id, step_failed, error_message))
                    conn.commit()
            self.create_notification(
                notif_type="SECURITY",
                title=f"Threat Blocked: {agent_id} ({step_failed})",
                message=error_message
            )
        except Exception as e:
            print(f"[Audit Log Error]: {e}")

    def validate_purchase_order(
        self,
        agent_id: str,
        auth_token: str,
        total_landed_cost: float
    ) -> bool:
        if agent_id not in self.AUTHORIZED_AGENTS:
            msg = f"Unregistered rogue agent '{agent_id}' blocked at gateway."
            self._log_security_event(agent_id, "STEP_1_IDENTITY", msg)
            raise SecurityBreachAlert(msg)

        agent_profile = self.AUTHORIZED_AGENTS[agent_id]

        if auth_token != agent_profile["token"]:
            msg = f"Invalid authentication token presented by '{agent_id}'."
            self._log_security_event(agent_id, "STEP_2_TOKEN_AUTH", msg)
            raise SecurityBreachAlert(msg)

        if agent_profile["role"] not in ["FINANCE_COMMIT", "OVERSIGHT", "AUTONOMOUS_ORCHESTRATOR"]:
            msg = (
                f"Separation of Duties violation: '{agent_id}' has role '{agent_profile['role']}' "
                f"(zero financial commit authority)."
            )
            self._log_security_event(agent_id, "STEP_3_SEPARATION_OF_DUTIES", msg)
            raise SecurityBreachAlert(msg)

        if float(total_landed_cost) > agent_profile["max_cap"]:
            msg = (
                f"Transaction of ₹{float(total_landed_cost):,.2f} exceeds hard spending cap "
                f"of ₹{agent_profile['max_cap']:,.2f} for '{agent_id}'."
            )
            self._log_security_event(agent_id, "STEP_4_BUDGET_CAP", msg)
            raise SecurityBreachAlert(msg)

        return True

    def commit_to_ledger(self, validated_data: Dict[str, Any], po_document: str) -> int:
        """
        Commits the PO to `purchase_orders` AND automatically ADDS `total_tonnage`
        to `inventory.current_stock_tons` in PostgreSQL.
        """
        agent_id = validated_data.get("agent_id", "AGENT_FINANCE_01")
        vendor_name = validated_data.get("vendor_name") or validated_data.get("vendor_id", "Approved Vendor")
        material_name = validated_data.get("material_name", "Bulk Wheat Flour")
        tonnage = float(validated_data.get("total_tonnage", 0.0))
        unit_price = float(validated_data.get("negotiated_unit_price", 0.0))
        landed_cost = float(validated_data.get("total_landed_cost", 0.0))

        with psycopg2.connect(**self.db_config) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO purchase_orders
                    (agent_id, vendor_name, total_tonnage, negotiated_unit_price, total_landed_cost)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING po_id;
                """, (agent_id, vendor_name, tonnage, unit_price, landed_cost))
                po_row = cur.fetchone()
                po_id = po_row["po_id"] if po_row else 0

                # Automatically ADD ordered tonnage to factory inventory
                cur.execute("""
                    UPDATE inventory
                    SET current_stock_tons = current_stock_tons + %s
                    WHERE material_name = %s
                    RETURNING current_stock_tons;
                """, (tonnage, material_name))
                inv_row = cur.fetchone()
                new_stock = float(inv_row["current_stock_tons"]) if inv_row else tonnage
                conn.commit()

        self.create_notification(
            notif_type="PO_COMMITTED",
            title=f"PO #{po_id} Delivered · +{tonnage:g}T {material_name}",
            message=(
                f"Order from {vendor_name} committed (₹{landed_cost:,.0f}). "
                f"{material_name} inventory increased by +{tonnage:g}T → Now at {new_stock:g}T."
            ),
            material_name=material_name
        )
        return po_id

    def consume_factory_stock(
        self,
        material_name: str,
        tons_used: float,
        reason: str = "Biscuit Line Production"
    ) -> Dict[str, Any]:
        """
        Reduces `inventory.current_stock_tons` when raw materials are consumed by the plant
        and generates CRITICAL or REORDER alerts if thresholds are crossed.
        """
        if float(tons_used) <= 0:
            raise ValueError("Consumption tonnage must be greater than 0.")

        with psycopg2.connect(**self.db_config) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM inventory WHERE material_name = %s;", (material_name,))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Material '{material_name}' not found in inventory.")

                old_stock = float(row["current_stock_tons"])
                safety = float(row["safety_stock_tons"])
                reorder = float(row["reorder_point_tons"])
                new_stock = max(0.0, round(old_stock - float(tons_used), 2))

                cur.execute("""
                    UPDATE inventory
                    SET current_stock_tons = %s
                    WHERE material_name = %s;
                """, (new_stock, material_name))
                conn.commit()

        alert_status = "HEALTHY"
        if new_stock <= safety:
            alert_status = "CRITICAL_SAFETY_BREACH"
            self.create_notification(
                notif_type="CRITICAL",
                title=f"🚨 Critical Safety Stock Breach: {material_name} ({new_stock:g}T)",
                message=(
                    f"Consumed {tons_used:g}T ({reason}). Stock dropped from {old_stock:g}T to {new_stock:g}T "
                    f"(Safety Stock: {safety:g}T). Immediate emergency S2P order required!"
                ),
                material_name=material_name
            )
        elif new_stock <= reorder:
            alert_status = "REORDER_THRESHOLD_BREACH"
            self.create_notification(
                notif_type="WARNING",
                title=f"⚠️ Reorder Threshold Crossed: {material_name} ({new_stock:g}T)",
                message=(
                    f"Consumed {tons_used:g}T ({reason}). Stock dropped from {old_stock:g}T to {new_stock:g}T "
                    f"(Reorder Point: {reorder:g}T). Trigger S2P replenishment."
                ),
                material_name=material_name
            )
        else:
            self.create_notification(
                notif_type="USAGE",
                title=f"Factory Consumption: -{tons_used:g}T {material_name}",
                message=f"Used {tons_used:g}T for {reason}. Remaining stock: {new_stock:g}T.",
                material_name=material_name
            )

        return {
            "material_name": material_name,
            "previous_stock_tons": old_stock,
            "tons_consumed": float(tons_used),
            "current_stock_tons": new_stock,
            "safety_stock_tons": safety,
            "reorder_point_tons": reorder,
            "threshold_status": alert_status
        }

    def run_production_shift(self, shifts: float = 1.0) -> List[Dict[str, Any]]:
        """
        Simulates a full GoldenCrunch biscuit production shift across all 6 raw materials
        using the standard Bill of Materials (BOM).
        """
        results = []
        for mat, base_tons in self.BISCUIT_SHIFT_BOM.items():
            used = round(base_tons * float(shifts), 2)
            res = self.consume_factory_stock(
                material_name=mat,
                tons_used=used,
                reason=f"GoldenCrunch Production Shift (×{shifts:g})"
            )
            results.append(res)
        return results


if __name__ == "__main__":
    gw = AuthorizationGateway()
    print("✅ Step 1 Ready: AuthorizationGateway with Auto-Restock, Factory Consumption & Alerts initialized!")