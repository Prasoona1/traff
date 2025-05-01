import streamlit as st
import requests
import folium
import polyline
from streamlit_folium import folium_static
import json
import pandas as pd
from datetime import datetime
import random
import time

# Set page configuration
st.set_page_config(
    page_title="MobiSync Platform",
    page_icon="🚗",
    layout="wide"
)

# Mock user database (in a real app, you'd use a proper database)
USERS = {
    "demo": "password",
    "user": "pass123"
}

# App state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'route_calculated' not in st.session_state:
    st.session_state.route_calculated = False
if 'last_search' not in st.session_state:
    st.session_state.last_search = {}

# OpenRouteService API key placeholder
ORS_API_KEY = "YOUR_OPENROUTESERVICE_API_KEY"  # Replace with your actual API key

# Function to handle login
def login(username, password):
    if username in USERS and USERS[username] == password:
        st.session_state.logged_in = True
        st.session_state.username = username
        return True
    return False

# Function to handle logout
def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.route_calculated = False

# Function to geocode an address using OpenRouteService
def geocode_address(address):
    url = f"https://api.openrouteservice.org/geocode/search"
    params = {
        "api_key": ORS_API_KEY,
        "text": address,
        "size": 1
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data["features"]:
                coords = data["features"][0]["geometry"]["coordinates"]
                return coords  # [lon, lat]
            else:
                return None
        else:
            st.error(f"Error in geocoding: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error in geocoding: {str(e)}")
        return None

# Function to get route using OpenRouteService
def get_route(start_coords, end_coords):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {
        'Authorization': ORS_API_KEY,
        'Content-Type': 'application/json'
    }
    data = {
        "coordinates": [start_coords, end_coords],
        "instructions": True,
        "format": "geojson"
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error in routing: {response.status_code}")
            # For demo, return mock data if API call fails
            return generate_mock_route_data(start_coords, end_coords)
    except Exception as e:
        st.error(f"Error in routing: {str(e)}")
        # For demo, return mock data if API call fails
        return generate_mock_route_data(start_coords, end_coords)

# Function to generate mock route data for demo purposes
def generate_mock_route_data(start_coords, end_coords):
    # Create a simple straight line between start and end points
    num_points = 10
    route_points = []
    
    for i in range(num_points):
        factor = i / (num_points - 1)
        lon = start_coords[0] + (end_coords[0] - start_coords[0]) * factor
        lat = start_coords[1] + (end_coords[1] - start_coords[1]) * factor
        route_points.append([lon, lat])
    
    # Create mock traffic congestion data
    mock_traffic = []
    for i in range(num_points - 1):
        congestion = random.choice(["low", "medium", "high"])
        mock_traffic.append({
            "segment": [route_points[i], route_points[i+1]],
            "congestion": congestion
        })
    
    # Mock route data structure
    mock_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "segments": [
                        {
                            "distance": random.uniform(5000, 15000),
                            "duration": random.uniform(300, 900),
                            "steps": [
                                {
                                    "distance": random.uniform(500, 2000),
                                    "duration": random.uniform(60, 180),
                                    "instruction": f"Mock instruction {i+1}",
                                    "name": f"Street {i+1}"
                                } for i in range(5)
                            ]
                        }
                    ],
                    "summary": {
                        "distance": random.uniform(5000, 15000),
                        "duration": random.uniform(300, 900)
                    },
                    "traffic": mock_traffic
                },
                "geometry": {
                    "coordinates": route_points,
                    "type": "LineString"
                }
            }
        ]
    }
    return mock_data

# Function to get mock traffic data (in a real app, you'd integrate with a traffic API)
def get_traffic_data(route_data):
    # In a real app, you'd call an actual traffic API here
    # For this demo, we'll generate random traffic data along the route
    
    coordinates = route_data["features"][0]["geometry"]["coordinates"]
    traffic_data = []
    
    # Generate traffic congestion levels for segments of the route
    for i in range(len(coordinates) - 1):
        # Random congestion level: low, medium, high
        congestion = random.choice(["low", "medium", "high"])
        segment = [coordinates[i], coordinates[i+1]]
        traffic_data.append({
            "segment": segment,
            "congestion": congestion
        })
    
    return traffic_data

# Function to create a map with route and traffic
def create_map(route_data, traffic_data):
    # Extract coordinates from the route
    coordinates = route_data["features"][0]["geometry"]["coordinates"]
    
    # Find the center of the route for the map
    center_lat = sum(coord[1] for coord in coordinates) / len(coordinates)
    center_lon = sum(coord[0] for coord in coordinates) / len(coordinates)
    
    # Create a map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10)
    
    # Add start and end markers
    folium.Marker(
        [coordinates[0][1], coordinates[0][0]],
        popup="Start",
        icon=folium.Icon(color="green", icon="play")
    ).add_to(m)
    
    folium.Marker(
        [coordinates[-1][1], coordinates[-1][0]],
        popup="End",
        icon=folium.Icon(color="red", icon="stop")
    ).add_to(m)
    
    # Add traffic congestion visualization
    for segment in traffic_data:
        coords = segment["segment"]
        congestion = segment["congestion"]
        
        # Set color based on congestion level
        if congestion == "low":
            color = "green"
        elif congestion == "medium":
            color = "orange"
        else:  # high
            color = "red"
        
        # Add line segment with appropriate color
        folium.PolyLine(
            [[coords[0][1], coords[0][0]], [coords[1][1], coords[1][0]]],
            color=color,
            weight=5,
            opacity=0.8,
            tooltip=f"Traffic: {congestion.capitalize()}"
        ).add_to(m)
    
    return m

# Function to parse directions from route data
def get_directions(route_data):
    try:
        segments = route_data["features"][0]["properties"]["segments"]
        directions = []
        
        for segment in segments:
            for step in segment["steps"]:
                directions.append({
                    "instruction": step["instruction"],
                    "distance": f"{step['distance']/1000:.2f} km",
                    "duration": f"{step['duration']/60:.1f} min"
                })
        
        return directions
    except Exception as e:
        # For demo purposes, return mock directions if parsing fails
        return [
            {"instruction": "Continue straight", "distance": "1.50 km", "duration": "5.0 min"},
            {"instruction": "Turn right onto Main Street", "distance": "0.80 km", "duration": "3.5 min"},
            {"instruction": "Turn left at the roundabout", "distance": "2.30 km", "duration": "7.2 min"},
            {"instruction": "Merge onto Highway", "distance": "5.40 km", "duration": "12.8 min"},
            {"instruction": "Take exit 42", "distance": "0.60 km", "duration": "1.5 min"},
            {"instruction": "Arrive at destination", "distance": "0.10 km", "duration": "0.5 min"}
        ]

# Function to get route summary
def get_route_summary(route_data):
    try:
        summary = route_data["features"][0]["properties"]["summary"]
        return {
            "distance": f"{summary['distance']/1000:.2f} km",
            "duration": f"{summary['duration']/60:.1f} min"
        }
    except Exception as e:
        # For demo purposes, return mock summary if parsing fails
        return {
            "distance": "10.70 km",
            "duration": "30.5 min"
        }

# Main application
def main():
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #34495e;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
    }
    .success-message {
        color: #28a745;
        font-weight: bold;
    }
    .traffic-legend {
        display: flex;
        justify-content: center;
        margin: 10px 0;
    }
    .traffic-legend-item {
        display: flex;
        align-items: center;
        margin: 0 10px;
    }
    .legend-color {
        width: 20px;
        height: 10px;
        margin-right: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("<h1 class='main-header'>🚗 MobiSync Platform</h1>", unsafe_allow_html=True)
    
    # Login section
    if not st.session_state.logged_in:
        st.markdown("<h2 class='sub-header'>Login</h2>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_button = st.button("Login")
            
            if login_button:
                if login(username, password):
                    st.success(f"Welcome, {username}!")
                    st.experimental_rerun()
                else:
                    st.error("Invalid username or password. Try demo/password")
        
        with col2:
            st.markdown("<div class='info-box'>", unsafe_allow_html=True)
            st.markdown("### Demo Credentials")
            st.markdown("Username: `demo`")
            st.markdown("Password: `password`")
            st.markdown("</div>", unsafe_allow_html=True)
    
    # Main app content for logged-in users
    else:
        # Sidebar with user info and logout
        with st.sidebar:
            st.markdown(f"### Logged in as: {st.session_state.username}")
            if st.button("Logout"):
                logout()
                st.experimental_rerun()
            
            st.markdown("---")
            st.markdown("### Traffic Legend")
            st.markdown("""
            <div class='traffic-legend'>
                <div class='traffic-legend-item'>
                    <div class='legend-color' style='background-color: green;'></div>
                    <span>Low</span>
                </div>
                <div class='traffic-legend-item'>
                    <div class='legend-color' style='background-color: orange;'></div>
                    <span>Medium</span>
                </div>
                <div class='traffic-legend-item'>
                    <div class='legend-color' style='background-color: red;'></div>
                    <span>High</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Main content
        st.markdown("<h2 class='sub-header'>Route Planner</h2>", unsafe_allow_html=True)
        
        # Route input form
        col1, col2 = st.columns([1, 1])
        
        with col1:
            source = st.text_input("Starting Point", "New York, NY")
        
        with col2:
            destination = st.text_input("Destination", "Boston, MA")
        
        if st.button("Calculate Route"):
            with st.spinner("Calculating optimal route..."):
                # Geocode source and destination
                source_coords = geocode_address(source)
                dest_coords = geocode_address(destination)
                
                if source_coords and dest_coords:
                    # Get route data
                    route_data = get_route(source_coords, dest_coords)
                    
                    # Get traffic data
                    traffic_data = get_traffic_data(route_data)
                    
                    # Store in session state
                    st.session_state.route_calculated = True
                    st.session_state.last_search = {
                        "source": source,
                        "destination": destination,
                        "route_data": route_data,
                        "traffic_data": traffic_data,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    st.success("Route calculated successfully!")
                    time.sleep(1)  # Small delay for better UX
                    st.experimental_rerun()
                else:
                    st.error("Could not geocode one or both addresses. Please check your input.")
        
        # Display route if calculated
        if st.session_state.route_calculated:
            st.markdown("---")
            st.markdown("<h2 class='sub-header'>Route Information</h2>", unsafe_allow_html=True)
            
            route_data = st.session_state.last_search["route_data"]
            traffic_data = st.session_state.last_search["traffic_data"]
            
            # Route summary
            summary = get_route_summary(route_data)
            
            st.markdown(f"""
            <div class='info-box'>
                <h3>Journey Details</h3>
                <p><strong>From:</strong> {st.session_state.last_search['source']}</p>
                <p><strong>To:</strong> {st.session_state.last_search['destination']}</p>
                <p><strong>Total Distance:</strong> {summary['distance']}</p>
                <p><strong>Estimated Time:</strong> {summary['duration']}</p>
                <p><strong>Last Updated:</strong> {st.session_state.last_search['timestamp']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Create and display map
            st.markdown("<h3>Route Map with Traffic Conditions</h3>", unsafe_allow_html=True)
            m = create_map(route_data, traffic_data)
            folium_static(m, width=800, height=500)
            
            # Display directions
            st.markdown("<h3>Turn-by-Turn Directions</h3>", unsafe_allow_html=True)
            directions = get_directions(route_data)
            
            directions_df = pd.DataFrame(directions)
            st.table(directions_df)
            
            # Add refresh button
            if st.button("Refresh Traffic Data"):
                with st.spinner("Updating traffic information..."):
                    # Update traffic data only
                    updated_traffic = get_traffic_data(route_data)
                    st.session_state.last_search["traffic_data"] = updated_traffic
                    st.session_state.last_search["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.success("Traffic data updated!")
                    time.sleep(1)  # Small delay for better UX
                    st.experimental_rerun()

if __name__ == "__main__":
    main()
