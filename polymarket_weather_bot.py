# INSTALL REQUIREMENTS:
# pip install requests termcolor

import requests
import json
import time
import re
from datetime import datetime, timedelta
from termcolor import colored

# --- CONFIGURATION ---
REFRESH_INTERVAL = 30  # Minutes between full scans
# Add or update city coordinates here (Lat/Lon)
CITY_COORDS = {
    "Wellington": {"lat": -41.2865, "lon": 174.7762},
    "Shenzhen": {"lat": 22.5431, "lon": 114.0579},
    "Atlanta": {"lat": 33.7490, "lon": -84.3880},
    "Chicago": {"lat": 41.8781, "lon": -87.6298},
    "Tokyo": {"lat": 35.6895, "lon": 139.6917},
    "London": {"lat": 51.5074, "lon": -0.1278},
    "New York": {"lat": 40.7128, "lon": -74.0060}
}

def f_to_c(fahrenheit):
    """Helper to convert F to C if the market is in Fahrenheit"""
    return (fahrenheit - 32) * 5.0/9.0

def get_tomorrow_date():
    """Returns tomorrow's date string for API filtering"""
    return (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

def fetch_ensemble_forecast(lat, lon):
    """
    Fetches the 51-model ensemble mean max temp from Open-Meteo.
    This is the 'Alpha' source mentioned in the video.
    """
    url = "https://ensemble-api.open-meteo.com/v1/ensemble"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max",
        "timezone": "auto",
        "models": "ensemble"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        # Index [1] is 'tomorrow' in the daily array
        return data['daily']['temperature_2m_max'][1]
    except Exception as e:
        print(colored(f"Error fetching weather: {e}", "red"))
        return None

def fetch_polymarket_weather():
    """Fetches active weather markets from the Polymarket Gamma API"""
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "active": "true",
        "closed": "false",
        "tag": "Weather",
        "limit": 100
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.json()
    except Exception as e:
        print(colored(f"Error fetching Polymarket: {e}", "red"))
        return []

def extract_temp_from_question(question):
    """
    Attempts to pull the temperature threshold from the market question.
    Example: 'Will Atlanta's high be 75.5°F or higher?' -> 75.5
    """
    # Look for numbers next to degree symbols
    match = re.search(r'(\d+\.?\d*)°', question)
    if match:
        temp = float(match.group(1))
        # If 'F' is in the question, convert to Celsius for comparison
        if "°F" in question:
            return f_to_c(temp), "F"
        return temp, "C"
    return None, None

def run_scanner():
    print(colored("="*50, "cyan"))
    print(colored("  MOON DEV WEATHER SCANNER STARTING...", "cyan", attrs=['bold']))
    print(colored("="*50, "cyan"))
    
    tomorrow = get_tomorrow_date()
    
    while True:
        markets = fetch_polymarket_weather()
        if not markets:
            print(colored("No active weather markets found. Retrying in 60s...", "yellow"))
            time.sleep(60)
            continue

        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Scanning {len(markets)} markets...")
        
        for city, coords in CITY_COORDS.items():
            # 1. Get Ensemble Forecast (The "Truth")
            forecast_c = fetch_ensemble_forecast(coords['lat'], coords['lon'])
            
            # 2. Find matching markets for this city
            city_markets = [m for m in markets if city.lower() in m['question'].lower()]
            
            if not city_markets or forecast_c is None:
                continue

            # 3. Analyze the most liquid/relevant market for the city
            # We look for the market with the highest volume or closest outcome
            for market in city_markets:
                q = market['question']
                market_temp_c, unit = extract_temp_from_question(q)
                
                if market_temp_c is None:
                    continue

                # 4. Calculate Difference (Edge)
                diff = forecast_c - market_temp_c
                
                # Logic: If forecast is 25C and market is '20C or higher', the 'Yes' is undervalued
                edge_detected = abs(diff) > 1.5  # 1.5 degree Celsius threshold for "Edge"
                
                # Formatting
                status_color = "green" if edge_detected else "white"
                forecast_display = f"{forecast_c:.1f}°C"
                market_display = f"{market_temp_c:.1f}°C (orig {unit})"
                
                print(f"[{city}] ".ljust(15) + 
                      f"Forecast: {forecast_display} | " +
                      f"Market: {market_display} | " + 
                      colored(f"Diff: {diff:+.2f}°C", status_color))

        print(colored(f"\nCycle complete. Waiting {REFRESH_INTERVAL} minutes...", "blue"))
        time.sleep(REFRESH_INTERVAL * 60)

if __name__ == "__main__":
    try:
        run_scanner()
    except KeyboardInterrupt:
        print(colored("\nScanner stopped by user.", "yellow"))
