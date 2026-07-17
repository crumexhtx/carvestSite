import json
import sys
from pathlib import Path

import env_setup  # noqa: F401
# Import the live government recall tool you created in fetch_recalls.py
from fetch_recalls import get_live_recalls, recalls_available
from fetch_marketcheck import MarketCheckError, get_market_snapshot
from openai_client import create_openai_client

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Initialize OpenAI client (Make sure your OPENAI_API_KEY environment variable is set)
client = create_openai_client()

_VEHICLES_DB: dict | None = None
_VEHICLES_DB_PATH = str(Path(__file__).resolve().parent / "vehicles.json")


def _load_vehicles_db(json_file: str | None = None) -> dict | None:
    global _VEHICLES_DB
    path = str(Path(json_file or _VEHICLES_DB_PATH).resolve())
    if _VEHICLES_DB is not None and path == str(Path(_VEHICLES_DB_PATH).resolve()):
        return _VEHICLES_DB
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return None
    if path == str(Path(_VEHICLES_DB_PATH).resolve()):
        _VEHICLES_DB = data
    return data


def _match_key(candidate: str, options) -> str | None:
    needle = str(candidate or "").strip().lower()
    if not needle:
        return None
    for option in options:
        if str(option).strip().lower() == needle:
            return str(option)
    return None


def verify_vehicle_exists(make, year, model, json_file=None):
    """
    Checks your local database to ensure the requested vehicle is real.
    Prevents the AI from processing fake or hallucinated vehicle data.

    Returns:
        (is_valid, message, canonical_make, canonical_model)
    """
    vehicles_db = _load_vehicles_db(json_file)
    if vehicles_db is None:
        db_name = json_file or "vehicles.json"
        return (
            False,
            f"Error: '{db_name}' database file not found. Run core_makes_models.py first.",
            None,
            None,
        )

    canonical_make = _match_key(make, vehicles_db)
    if canonical_make is None:
        return False, f"Brand '{make}' is not in our database.", None, None

    year_key = str(year).strip()
    if year_key not in vehicles_db[canonical_make]:
        return False, f"No data found for a {year} {canonical_make}.", None, None

    models = vehicles_db[canonical_make][year_key]
    canonical_model = _match_key(model, models)
    if canonical_model is None:
        return (
            False,
            f"Model '{model}' was not found for a {year} {canonical_make}.",
            None,
            None,
        )

    return True, "Vehicle successfully verified.", canonical_make, canonical_model


def generate_ai_vehicle_report(make, year, model, zip_code=None, vehicle_profile=None):
    """
    Verifies a car, fetches real-time federal data, and passes it to OpenAI.
    """
    # 1. First, check our local guardrail database to prevent AI hallucinations
    is_valid, message, canonical_make, canonical_model = verify_vehicle_exists(
        make, year, model
    )
    if not is_valid:
        return f"Error: {message}"

    print(
        "🤖 AI Core: Gathering live metrics for verified vehicle: "
        f"{year} {canonical_make} {canonical_model}..."
    )

    # 2. Call your fetch_recalls script to get actual, real-time government entries
    live_structural_data = get_live_recalls(canonical_make, year, canonical_model)
    if not recalls_available(live_structural_data):
        live_structural_data = {
            **live_structural_data,
            "note": (
                "NHTSA recall lookup failed or timed out. Do not claim there are zero "
                "recalls. State that recall data is temporarily unavailable."
            ),
        }

    market_data = None
    market_note = "MarketCheck listing data not requested."
    if zip_code:
        try:
            market_data = get_market_snapshot(
                make=canonical_make,
                model=canonical_model,
                year=year,
                zip_code=zip_code,
                max_listings=8,
            )
            market_note = f"MarketCheck listings loaded for ZIP {zip_code}."
        except MarketCheckError as exc:
            market_note = f"MarketCheck unavailable: {exc}"

    # 3. Structure your prompt to tightly instruct the AI
    system_instruction = (
        "You are an expert automotive analyst and senior data analyst. "
        "Understand the safety, value, and reliability of a specific vehicle. Use only the provided "
        "structural data to make your assessment. Be concise, direct, and highlight major risks. "
        "One of your tasks is to transform raw government and market data into a premium, data-driven "
        "risk assessment for a car buyer. Balance deep industry knowledge with ruthless "
        "statistical precision. Avoid generic advice; keep your tone objective, blunt, "
        "and highly analytical."
    )
    
    profile_block = json.dumps(vehicle_profile, indent=2) if vehicle_profile else "None"

    user_prompt = f"""
    Please analyze and perform a complete safety and purchasing risk analysis for the following automotive profile data:
    
    Vehicle: {year} {canonical_make} {canonical_model}
    Buyer Vehicle Profile: {profile_block}
    Market Data Status: {market_note}
    Raw Sourced Recalls Data: {json.dumps(live_structural_data, indent=2)}
    Raw Market Listings Data: {json.dumps(market_data, indent=2) if market_data else "None"}

    Format your response EXACTLY like this layout using Markdown. Do not add intro or outro text:

    ### 📊 VEHICLE RISK PROFILE
    * **Risk Classification:** [Classify as LOW RISK, MEDIUM RISK, or HIGH RISK based on the severity/volume of defects]
    * **Total Active Recalls:** [Insert total count, or 'Unavailable' if recall lookup failed]

    ### ⚠️ CRITICAL DEFECT BREAKDOWN
    [Provide a short, punchy bulleted list summarizing the most dangerous mechanical failures found in the data. Bold the affected component name. If zero recalls exist, state: 'No active safety recalls recorded for this model year.' If recall data is unavailable, state that clearly and do not invent a zero-recall result.]

    ### 🛒 CURRENT MARKET SNAPSHOT
    [If market data exists, summarize how many listings were found, typical price/mileage range, and call out 2-3 specific listings with price vs predicted fair value when available. If no market data, state that clearly.]

    ### 📉 SHOWROOM NEGOTIATION POINTS
    * **Leverage Point 1:** [Give a hyper-specific script line using a real defect or pricing delta from the data.]
    * **Leverage Point 2:** [Provide a second data-backed negotiation tactic based on recalls, pricing, or mileage.]

    """

    # 4. Call the AI model
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Fast, highly accurate, and cost-effective
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3 # Low temperature keeps the AI factual and prevents creative guessing
        )
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Failed to connect to AI Engine: {str(e)}"

# Interactive user interface loop
if __name__ == "__main__":
    print("\n=============================================")
    print("🚘 WELCOME TO CARVEST 🚘")
    print("=============================================")
    print("Type 'exit' at any prompt to quit the application.\n")
    
    while True:
        # 1. Capture User Input strings
        input_make = input("Enter Car Brand (e.g., Honda, Toyota, Ford): ").strip()
        if input_make.lower() == 'exit':
            break
            
        input_year = input("Enter Model Year (1995-2026): ").strip()
        if input_year.lower() == 'exit':
            break
            
        input_model = input("Enter Car Model (e.g., Civic, Camry, Explorer): ").strip()
        if input_model.lower() == 'exit':
            break

        input_zip = input("Enter ZIP code for local listings (optional, press Enter to skip): ").strip()
        if input_zip.lower() == 'exit':
            break
            
        print("\n---------------------------------------------")
        
        is_valid, validation_message, canonical_make, canonical_model = verify_vehicle_exists(
            input_make, input_year, input_model
        )
        
        if not is_valid:
            print(f"❌ Validation Error: {validation_message}")
            print("Please check your spelling or verify the model year and try again.\n")
            continue
            
        # 3. If passed, execute the live API query and the AI compilation
        try:
            report = generate_ai_vehicle_report(
                make=canonical_make,
                year=int(input_year),
                model=canonical_model,
                zip_code=input_zip or None,
            )
            
            print("\n=== LIVE AI GENERATED BUYER REPORT ===")
            print(report)
            print("=============================================\n")
            
        except ValueError:
            print("❌ Error: Year must be a valid number. Please try again.\n")
        except Exception as e:
            print(f"❌ An unexpected error occurred: {str(e)}\n")

    print("\nThank you for using Carvest. Goodbye!")
