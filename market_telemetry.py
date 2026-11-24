"""
market_telemetry.py — Real-Time Environmental and Market Intelligence Telemetry
Fetches live weather (Open-Meteo) and live commodity/fuel feeds (Yahoo Finance)
with automatic fallback to Policy v4 benchmarks if offline.
"""
import requests

# Standard browser header for live market API requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

class MarketTelemetry:

    @staticmethod
    def fetch_weather(location: str = "Mumbai") -> dict:
        """
        Fetches real-time regional weather and delivery risk metrics via Open-Meteo API.
        Still supports passing 'STORM' in location to simulate Severe Monsoon on demand.
        """
        # 1. Manual simulation override for stress testing
        if "STORM" in location.upper():
            return {
                "location": location,
                "source": "SIMULATION_OVERRIDE",
                "condition": "Severe Monsoon",
                "delivery_risk_score": 0.95,
                "delay_days": 4
            }

        # 2. Live API Lookup via Open-Meteo (No API Key Required)
        try:
            clean_city = location.split("_")[0].strip() or "Mumbai"
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={clean_city}&count=1&language=en&format=json"
            geo_res = requests.get(geo_url, timeout=4).json()

            if geo_res.get("results"):
                lat = geo_res["results"][0]["latitude"]
                lon = geo_res["results"][0]["longitude"]
                resolved_name = geo_res["results"][0]["name"]
            else:
                # Default to Mumbai coordinates
                lat, lon, resolved_name = 19.0760, 72.8777, "Mumbai"

            weather_url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}&current=temperature_2m,precipitation,weather_code,wind_speed_10m"
            )
            w_data = requests.get(weather_url, timeout=4).json().get("current", {})

            precip = float(w_data.get("precipitation", 0.0))
            w_code = int(w_data.get("weather_code", 0))
            temp_c = w_data.get("temperature_2m", 30.0)
            wind_kmh = w_data.get("wind_speed_10m", 10.0)

            # Map WMO weather codes & precipitation to MCDM risk levels
            if w_code in (65, 67, 82, 95, 96, 99) or precip > 10.0 or wind_kmh > 50.0:
                condition = "Severe Monsoon / Storm"
                risk_score = 0.90
                delay_days = 4
            elif w_code in (51, 53, 55, 61, 63, 80, 81) or precip > 1.0:
                condition = "Rain / Moderate Risk"
                risk_score = 0.45
                delay_days = 1
            else:
                condition = "Clear"
                risk_score = 0.10
                delay_days = 0

            return {
                "location": resolved_name,
                "source": "LIVE_OPEN_METEO_API",
                "condition": condition,
                "temperature_c": temp_c,
                "precipitation_mm": precip,
                "wind_speed_kmh": wind_kmh,
                "delivery_risk_score": risk_score,
                "delay_days": delay_days
            }

        except Exception as e:
            # Safe fallback if offline
            return {
                "location": location,
                "source": f"FALLBACK_BASELINE ({str(e)})",
                "condition": "Clear",
                "delivery_risk_score": 0.10,
                "delay_days": 0
            }

    @staticmethod
    def fetch_freight_rates() -> dict:
        """
        Returns contractual base ton-km rates in INR (per Policy v4 Section 5),
        dynamically paired with live fuel multipliers during logistics calculation.
        """
        return {
            "FastFreight Logistics": 4.50,      # Road (INR/ton-km)
            "National Rail Cargo": 2.00,        # Rail (INR/ton-km)
            "Express Transit Freight": 5.20     # Road Express (INR/ton-km)
        }

    @staticmethod
    def fetch_commodity_price(ticker: str) -> dict:
        """
        Fetches real-time global commodity market movements from Yahoo Finance
        and calibrates localized INR spot prices and trends (UP, DOWN, STABLE).
        """
        baseline_catalog = {
            "WHT":  {"name": "Bulk Wheat Flour",   "base_inr": 35000.00,  "yf_symbol": "ZW=F", "fallback_trend": "UP",     "fallback_pct": 1.8},
            "SGR":  {"name": "Refined Sugar",      "base_inr": 42000.00,  "yf_symbol": "SB=F", "fallback_trend": "STABLE", "fallback_pct": 0.2},
            "PLM":  {"name": "Palm Oil",           "base_inr": 75000.00,  "yf_symbol": "ZL=F", "fallback_trend": "DOWN",   "fallback_pct": -2.4},
            "COA":  {"name": "Cocoa Beans",        "base_inr": 260000.00, "yf_symbol": "CC=F", "fallback_trend": "UP",     "fallback_pct": 5.1},
            "CORN": {"name": "Bulk Corn (Maize)",  "base_inr": 16000.00,  "yf_symbol": "ZC=F", "fallback_trend": "STABLE", "fallback_pct": -0.5},
            "CRT":  {"name": "Corrugated Cartons", "base_inr": 9000.00,   "yf_symbol": "PKG",  "fallback_trend": "STABLE", "fallback_pct": 0.0}
        }

        key = ticker.upper().strip()
        if key not in baseline_catalog:
            return {"spot_price_inr": 0.0, "trend": "UNKNOWN", "change_30d_pct": 0.0, "source": "INVALID_TICKER"}

        item = baseline_catalog[key]
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{item['yf_symbol']}?range=1mo&interval=1d"
            res = requests.get(url, headers=HEADERS, timeout=4).json()
            meta = res["chart"]["result"][0]["meta"]
            closes = [c for c in res["chart"]["result"][0]["indicators"]["quote"][0]["close"] if c is not None]

            current_price = float(meta.get("regularMarketPrice") or closes[-1])
            month_open = float(closes[0]) if closes else current_price

            change_pct = round(((current_price - month_open) / month_open) * 100.0, 2) if month_open else 0.0

            if change_pct > 1.0:
                trend = "UP"
            elif change_pct < -1.0:
                trend = "DOWN"
            else:
                trend = "STABLE"

            # Scale localized INR spot price within safe +/- 5% market band
            bounded_pct = max(-5.0, min(5.0, change_pct))
            live_spot_inr = round(item["base_inr"] * (1.0 + (bounded_pct / 100.0)), 2)

            return {
                "ticker": key,
                "material_name": item["name"],
                "source": f"LIVE_MARKET_FEED ({item['yf_symbol']})",
                "global_futures_price": round(current_price, 2),
                "spot_price_inr": live_spot_inr,
                "trend": trend,
                "change_30d_pct": change_pct
            }
        except Exception as e:
            return {
                "ticker": key,
                "material_name": item["name"],
                "source": f"FALLBACK_BASELINE ({str(e)})",
                "spot_price_inr": item["base_inr"],
                "trend": item["fallback_trend"],
                "change_30d_pct": item["fallback_pct"]
            }

    @staticmethod
    def fetch_fuel_index() -> dict:
        """
        Fetches live Brent Crude Oil futures (BZ=F) to dynamically compute
        localized diesel benchmarks and the freight cost multiplier.
        """
        base_diesel_inr = 94.50
        base_brent_usd = 75.00

        try:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/BZ=F?range=5d&interval=1d"
            res = requests.get(url, headers=HEADERS, timeout=4).json()
            meta = res["chart"]["result"][0]["meta"]
            live_brent = float(meta.get("regularMarketPrice", base_brent_usd))

            # Adjust diesel benchmark & freight multiplier proportionally to live Brent crude
            ratio = live_brent / base_brent_usd
            live_diesel_inr = round(base_diesel_inr * (0.7 + 0.3 * ratio), 2)
            live_multiplier = round(max(1.00, min(1.35, 1.0 + (0.12 * ratio))), 2)
            status = "HIGH" if live_multiplier >= 1.10 else ("MODERATE" if live_multiplier >= 1.05 else "LOW")

            return {
                "source": "LIVE_BRENT_CRUDE_FEED (BZ=F)",
                "brent_crude_usd_barrel": round(live_brent, 2),
                "fuel_price_per_liter_inr": live_diesel_inr,
                "freight_cost_multiplier": live_multiplier,
                "index_status": status
            }
        except Exception as e:
            return {
                "source": f"FALLBACK_BASELINE ({str(e)})",
                "fuel_price_per_liter_inr": 94.50,
                "freight_cost_multiplier": 1.12,
                "index_status": "HIGH"
            }