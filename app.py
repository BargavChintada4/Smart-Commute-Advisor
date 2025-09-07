import streamlit as st
import requests
import pandas as pd
from streamlit_geolocation import streamlit_geolocation
from streamlit_folium import st_folium
import folium
from datetime import datetime
import os

# --- API Configuration ---
# Load API keys from environment variables (for cloud) or Streamlit's secrets (for local)
# This makes the app deployable without code changes.
WAQI_API_TOKEN = os.environ.get("WAQI_API_TOKEN") or st.secrets.get("WAQI_API_TOKEN")
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY") or st.secrets.get("GOOGLE_MAPS_API_KEY")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY") or st.secrets.get("OPENWEATHER_API_KEY")

# Stop the app if any API key is missing
if not all([WAQI_API_TOKEN, GOOGLE_MAPS_API_KEY, OPENWEATHER_API_KEY]):
    st.error("One or more API keys are missing. Please check your configuration.")
    st.stop()

# --- Data Fetching Functions ---

def get_aqi_data(location_query):
    """Fetches Air Quality Index data from WAQI, supporting both city name and lat/lon."""
    # Use the appropriate API endpoint based on whether the input is coordinates or a city name
    if ',' in location_query:
        lat, lon = location_query.split(',')
        url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={WAQI_API_TOKEN}"
    else:
        url = f"https://api.waqi.info/feed/{location_query}/?token={WAQI_API_TOKEN}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "ok":
            aqi_value = int(data["data"]["aqi"]) if str(data["data"]["aqi"]).isdigit() else None
            dominant_pollutant = data["data"].get("dominentpol")
            return {"aqi": aqi_value, "pollutant": dominant_pollutant}
    except requests.exceptions.RequestException:
        # Fail silently on error to ensure a clean user experience
        pass
    return None

def get_commute_info(origin, destination, mode):
    """Fetches commute time from Google Maps and calculates traffic delay for driving."""
    params = {"origin": origin, "destination": destination, "mode": mode, "key": GOOGLE_MAPS_API_KEY}
    if mode == "driving":
        params["departure_time"] = "now"  # Required for traffic prediction

    url = "https://maps.googleapis.com/maps/api/directions/json"
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "OK":
            leg = data["routes"][0]["legs"][0]
            travel_time = leg.get('duration_in_traffic', leg.get('duration'))['value']
            
            traffic_delay = 0
            if mode == "driving":
                # Calculate the delay by comparing duration in traffic to normal duration
                base_duration = leg.get('duration')['value']
                traffic_delay = travel_time - base_duration
            
            return {"time": round(travel_time / 60), "delay": round(traffic_delay / 60)}
    except (requests.exceptions.RequestException, IndexError):
        pass
    return None

def get_lat_lon(city):
    """Converts a city name to latitude and longitude using OpenWeather's Geocoding API."""
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={OPENWEATHER_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data:
            return data[0]["lat"], data[0]["lon"]
    except requests.exceptions.RequestException:
        pass
    return None, None

def get_weather_data(lat, lon):
    """Fetches rich weather data from the OpenWeatherMap One Call API 3.0."""
    if lat is None or lon is None: return None
    url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=minutely&units=metric&appid={OPENWEATHER_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Extract and return the most useful fields from the rich API response
        return {
            "current_temp": data["current"]["temp"],
            "main_condition": data["current"]["weather"][0]["main"],
            "summary": data.get("daily", [{}])[0].get("summary", "No summary available."),
            "alerts": data.get("alerts", []),
            "hourly_forecast": data.get("hourly", [])
        }
    except requests.exceptions.RequestException:
        pass
    return None

# --- Core Recommendation Logic ---

def get_recommendation(aqi, driving_data, transit_time, weather_main):
    """Generates a commute recommendation based on a prioritized set of rules."""
    driving_time = driving_data.get("time") if driving_data else None
    traffic_delay = driving_data.get("delay", 0) if driving_data else 0

    # Priority 1: Adverse weather overrides all other factors
    if weather_main in ["Rain", "Thunderstorm", "Drizzle", "Snow", "Mist", "Fog"]:
        return f"**Driving is strongly advised due to '{weather_main}'.** Expect a travel time of ~{driving_time} minutes. Stay safe!"

    # Priority 2: If weather is fine, compare commute times and traffic
    if driving_time is not None and transit_time is not None:
        if traffic_delay > 20:
            return f"**Take Public Transit.** Traffic is heavy, with a delay of ~{traffic_delay} minutes. It will be much faster."
        time_difference = driving_time - transit_time
        if time_difference > 20:
            return f"**Take Public Transit.** It's about {time_difference} minutes faster."
        if aqi is not None and aqi > 150:
            return f"**Driving is recommended due to high AQI ({aqi}).** Commute times are comparable, but a car offers better protection."
        return f"**Commute times are comparable.** Choose based on your preference! Traffic is moderate with a delay of ~{traffic_delay} minutes."
    
    # Fallback recommendations if only one mode of transport data is available
    elif driving_time is not None:
        return f"**Driving is the recommended option.** Estimated time is ~{driving_time} minutes with a traffic delay of ~{traffic_delay} minutes."
    elif transit_time is not None:
         return f"**Public Transit is the recommended option.** Estimated time is ~{transit_time} minutes."
    
    # Final fallback if no commute data is available
    else:
        return "⚠️ **No commute data available.** Cannot provide a time-based recommendation."

# --- Streamlit User Interface ---

st.set_page_config(page_title="Smart Commute Advisor", page_icon="🚗", layout="centered")
st.title("Smart Commute Advisor")
st.markdown("Your daily guide to choosing the best commute mode!")

# Define the default map center for a better user experience
DEFAULT_MAP_CENTER = [22.3158, 87.3100]

# --- Origin Input Section with Multiple Methods ---
st.write("### 📍 Origin")
origin_method = st.radio("How to set your origin?", ["Use My Current GPS", "Select on Map", "Enter Manually"], horizontal=True, label_visibility="collapsed")

origin = None
if origin_method == "Use My Current GPS":
    with st.spinner("Activating GPS..."):
        location_data = streamlit_geolocation()
    if location_data and location_data.get('latitude'):
        origin = f"{location_data['latitude']},{location_data['longitude']}"
        st.success(f"GPS Location captured: {origin}")
    else:
        st.info("Could not retrieve GPS location. Grant permission or try another method.")
elif origin_method == "Select on Map":
    st.write("Click on the map to select your starting point.")
    m_origin = folium.Map(location=DEFAULT_MAP_CENTER, zoom_start=14)
    map_data_origin = st_folium(m_origin, key="origin_map", width=700, height=400)
    if map_data_origin and map_data_origin.get("last_clicked"):
        lat, lon = map_data_origin["last_clicked"]["lat"], map_data_origin["last_clicked"]["lng"]
        origin = f"{lat},{lon}"
        st.success(f"Origin Map Location selected: {origin}")
else: # Manual Entry
    origin = st.text_input("Enter your Home Location or City", "IIT Kharagpur")

# --- Destination Input Section with Multiple Methods ---
st.write("### 🏁 Destination")
destination_method = st.radio("How to set your destination?",["Select on Map", "Enter Manually"], horizontal=True, label_visibility="collapsed")

destination = None
if destination_method == "Select on Map":
    st.write("Click on the map to select your destination.")
    m_dest = folium.Map(location=DEFAULT_MAP_CENTER, zoom_start=14)
    map_data_dest = st_folium(m_dest, key="dest_map", width=700, height=400)
    if map_data_dest and map_data_dest.get("last_clicked"):
        lat, lon = map_data_dest["last_clicked"]["lat"], map_data_dest["last_clicked"]["lng"]
        destination = f"{lat},{lon}"
        st.success(f"Destination Map Location selected: {destination}")
else: # Manual Entry
    destination = st.text_input("Enter your Work Location", "Howrah Railway Station")


# --- Main Application Logic on Button Click ---
if st.button("Get My Commute Advice", type="primary"):
    # Validate that all necessary inputs have been provided
    if not origin or not destination or len(origin) < 3 or len(destination) < 3:
        st.warning("Please provide a valid origin and destination.")
    else:
        with st.spinner("Analyzing your personalized commute..."):
            # Determine the latitude and longitude for environmental data based on the origin
            lat, lon = None, None
            if isinstance(origin, str) and ',' in origin:
                lat, lon = map(float, origin.split(','))
            else:
                lat, lon = get_lat_lon(origin)
            
            # Fetch all data from the APIs concurrently
            aqi_data = get_aqi_data(origin)
            weather_data = get_weather_data(lat, lon)
            driving_data = get_commute_info(origin, destination, "driving")
            transit_data = get_commute_info(origin, destination, "transit")

            # Extract final values for display, handling potential None results
            aqi_value = aqi_data["aqi"] if aqi_data else None
            driving_minutes = driving_data["time"] if driving_data else None
            transit_minutes = transit_data["time"] if transit_data else None
            weather_main = weather_data["main_condition"] if weather_data else None

            # --- Display Commute Report ---
            st.subheader("Your Commute Report")
            
            # Conditionally render each metric only if data was successfully fetched
            if driving_data:
                col1, col2 = st.columns(2)
                col1.metric("🚗 Driving Time", f"{driving_minutes} min")
                traffic_delay = driving_data.get("delay", 0)
                traffic_condition = "Heavy" if traffic_delay > 20 else "Moderate" if traffic_delay > 10 else "Light"
                traffic_value = f"{traffic_condition} (~{traffic_delay} min)" if traffic_delay > 0 else traffic_condition
                col2.metric("🚦 Traffic Condition", value=traffic_value)

            col1, col2, col3 = st.columns(3)
            if transit_data:
                col1.metric("🚇 Public Transit", f"{transit_minutes} min")
            if weather_data:
                col2.metric("🌦️ Weather", weather_main)
                col3.metric("🌡️ Temperature", f"{weather_data['current_temp']:.1f} °C")
            
            if aqi_data and aqi_value is not None:
                st.metric("💨 Air Quality (AQI)", f"{aqi_value}", help=f"Dominant Pollutant: {aqi_data['pollutant'].upper()}" if aqi_data.get('pollutant') else "Main pollutant.")

            # --- Display Recommendation and Forecasts ---
            st.subheader("💡 Today's Recommendation")
            final_recommendation = get_recommendation(aqi_value, driving_data, transit_minutes, weather_main)
            st.info(final_recommendation)

            if weather_data and weather_data["hourly_forecast"]:
                st.subheader("🕒 Hourly Forecast (Next 12 Hours)")
                hourly_data = weather_data["hourly_forecast"][:12]
                chart_data = {"Time": [datetime.fromtimestamp(h['dt']).strftime('%H:%M') for h in hourly_data], "Temperature (°C)": [h['temp'] for h in hourly_data], "Rain Chance (%)": [h.get('pop', 0) * 100 for h in hourly_data]}
                df_chart = pd.DataFrame(chart_data).set_index("Time")
                st.line_chart(df_chart)

