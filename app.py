import streamlit as st
import requests
import folium
import pandas as pd
import numpy as np
import polyline
import json
import time
import datetime
import base64
import hashlib
import hmac
import os
from streamlit_folium import folium_static
from folium.plugins import HeatMap
import plotly.express as px
import plotly.graph_objects as go

# Set page configuration
st.set_page_config(
    page_title="MobiSync Platform",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .subtitle {
        font-size: 1.5rem;
        font-weight: 500;
        color: #424242;
        margin-bottom: 1rem;
    }
    .card {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .metric-container {
        display: flex;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: white;
        border-radius: 0.5rem;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        text-align: center;
        flex: 1;
        min-width: 150px;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    .metric-label {
        color: #666;
        font-size: 0.9rem;
    }
    .btn-primary {
        background-color: #1E88E5;
        color: white;
        border: none;
        border-radius: 0.25rem;
        padding: 0.5rem 1rem;
        font-size: 1rem;
        cursor: pointer;
    }
    .btn-secondary {
        background-color: #78909C;
        color: white;
        border: none;
        border-radius: 0.25rem;
        padding: 0.5rem 1rem;
        font-size: 1rem;
        cursor: pointer;
    }
    .footer {
        text-align: center;
        color: #666;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #eee;
    }
    .success-alert {
        padding: 1rem;
        background-color: #d4edda;
        color: #155724;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
    }
    .warning-alert {
        padding: 1rem;
        background-color: #fff3cd;
        color: #856404;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
    }
    .error-alert {
        padding: 1rem;
        background-color: #f8d7da;
        color: #721c24;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Constants
GOOGLE_MAPS_API_KEY = "YOUR_GOOGLE_MAPS_API_KEY_HERE"
OPENROUTE_API_KEY = "YOUR_OPENROUTE_API_KEY_HERE"
SECRET_KEY = "MobiSync_Secret_Key_Change_This_In_Production"  # For session management

# In-memory user database (replace with a real database in production)
USERS = {
    "demo@mobisync.com": {
        "password_hash": hashlib.sha256("demo123".encode()).hexdigest(),
        "name": "Demo User"
    },
    "admin@mobisync.com": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "name": "Admin User"
    }
}

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'route_data' not in st.session_state:
    st.session_state.route_data = None
if 'last_search' not in st.session_state:
    st.session_state.last_search = None

# Authentication functions
def verify_password(username, password):
    if username in USERS:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == USERS[username]["password_hash"]
    return False

def login_user(username, password):
    if verify_password(username, password):
        st.session_state.logged_in = True
        st.session_state.username = username
        return True
    return False

def logout_user():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.route_data = None
    st.session_state.last_search = None

# Geocoding function (converts address to coordinates)
def geocode_address(address, api_key=GOOGLE_MAPS_API_KEY):
    try:
        # Using Google Maps Geocoding API
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}"
        response = requests.get(url)
        data = response.json()
        
        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            return location['lat'], location['lng']
        else:
            st.error(f"Geocoding error: {data['status']}")
            return None
    except Exception as e:
        st.error(f"Geocoding error: {str(e)}")
        return None

# Route optimization function
def get_optimized_route(origin_coords, destination_coords, api="google"):
    try:
        if api == "google":
            # Using Google Maps Directions API
            origin = f"{origin_coords[0]},{origin_coords[1]}"
            destination = f"{destination_coords[0]},{destination_coords[1]}"
            url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&alternatives=true&key={GOOGLE_MAPS_API_KEY}"
            
            response = requests.get(url)
            data = response.json()
            
            if data['status'] == 'OK':
                routes = []
                for route in data['routes']:
                    route_info = {
                        'summary': route['summary'],
                        'distance': sum(leg['distance']['value'] for leg in route['legs']) / 1000,  # km
                        'duration': sum(leg['duration']['value'] for leg in route['legs']) / 60,  # minutes
                        'polyline': route['overview_polyline']['points'],
                        'steps': []
                    }
                    
                    # Extract step-by-step directions
                    for leg in route['legs']:
                        for step in leg['steps']:
                            route_info['steps'].append({
                                'instruction': step['html_instructions'],
                                'distance': step['distance']['text'],
                                'duration': step['duration']['text']
                            })
                    
                    routes.append(route_info)
                return routes
            else:
                st.error(f"Route optimization error: {data['status']}")
                return None
                
        elif api == "openroute":
            # Using OpenRouteService API
            headers = {
                'Authorization': OPENROUTE_API_KEY,
                'Content-Type': 'application/json'
            }
            
            body = {
                "coordinates": [
                    [origin_coords[1], origin_coords[0]],  # Note: OpenRouteService uses [lon, lat]
                    [destination_coords[1], destination_coords[0]]
                ],
                "instructions": True,
                "preference": "recommended",
                "units": "km",
                "language": "en",
                "geometry": True,
                "alternative_routes": {
                    "target_count": 3,
                    "weight_factor": 1.5
                }
            }
            
            url = "https://api.openrouteservice.org/v2/directions/driving-car"
            response = requests.post(url, json=body, headers=headers)
            data = response.json()
            
            if 'routes' in data:
                routes = []
                for route in data['routes']:
                    steps = []
                    for segment in route['segments']:
                        for step in segment['steps']:
                            steps.append({
                                'instruction': step['instruction'],
                                'distance': f"{step['distance']} km",
                                'duration': f"{int(step['duration'] / 60)} mins"
                            })
                    
                    route_info = {
                        'summary': route['summary']['text'] if 'text' in route['summary'] else "Optimized Route",
                        'distance': route['summary']['distance'],  # km
                        'duration': route['summary']['duration'] / 60,  # minutes
                        'polyline': route['geometry'],  # GeoJSON format
                        'steps': steps
                    }
                    routes.append(route_info)
                return routes
            else:
                st.error(f"Route optimization error: {data.get('error', 'Unknown error')}")
                return None
    except Exception as e:
        st.error(f"Route optimization error: {str(e)}")
        return None

# Generate simulated traffic data for visualization
def generate_traffic_data(center_lat, center_lng, radius=0.05, n_points=200):
    np.random.seed(int(time.time()))
    
    # Generate random points around the center
    lats = np.random.normal(center_lat, radius, n_points)
    lngs = np.random.normal(center_lng, radius, n_points)
    
    # Generate congestion values (1-10 scale)
    # Simulate higher congestion near the center and major roads
    congestion = []
    for i in range(n_points):
        # Distance from center (normalized)
        dist = np.sqrt((lats[i] - center_lat)**2 + (lngs[i] - center_lng)**2) / radius
        
        # Base congestion (higher near center)
        base = max(1, min(10, 10 * (1 - dist * 0.7)))
        
        # Add some randomness
        noise = np.random.normal(0, 1)
        final_congestion = max(1, min(10, base + noise))
        congestion.append(final_congestion)
    
    # Create DataFrame
    df = pd.DataFrame({
        'lat': lats,
        'lng': lngs,
        'congestion': congestion
    })
    
    return df

# Create traffic map with congestion visualization
def create_traffic_map(route_data, traffic_data=None):
    # Extract coordinates from the first route
    if not route_data:
        return None
        
    first_route = route_data[0]
    if 'polyline' in first_route:
        # Handle Google Maps polyline format
        if isinstance(first_route['polyline'], str):
            route_coords = polyline.decode(first_route['polyline'])
        else:
            # Handle GeoJSON format from OpenRouteService
            route_coords = []
            for coord in first_route['polyline']['coordinates']:
                route_coords.append([coord[1], coord[0]])  # Convert [lng, lat] to [lat, lng]
    else:
        return None
    
    # Create map centered on the route
    center_lat = route_coords[len(route_coords)//2][0]
    center_lng = route_coords[len(route_coords)//2][1]
    
    m = folium.Map(location=[center_lat, center_lng], zoom_start=12, tiles="CartoDB positron")
    
    # Draw route polyline
    folium.PolyLine(
        route_coords,
        color='blue',
        weight=5,
        opacity=0.7
    ).add_to(m)
    
    # Add markers for start and end points
    folium.Marker(
        route_coords[0],
        popup="Start",
        icon=folium.Icon(color='green', icon='play')
    ).add_to(m)
    
    folium.Marker(
        route_coords[-1],
        popup="Destination",
        icon=folium.Icon(color='red', icon='stop')
    ).add_to(m)
    
    # If no traffic data is provided, generate some
    if traffic_data is None:
        traffic_data = generate_traffic_data(center_lat, center_lng)
    
    # Add traffic congestion visualization
    heat_data = []
    for _, row in traffic_data.iterrows():
        # Weight by congestion level (1-10)
        weight = row['congestion'] / 2  # Scale down for better visualization
        heat_data.append([row['lat'], row['lng'], weight])
    
    # Add heat map layer
    HeatMap(
        heat_data,
        radius=15,
        gradient={
            0.2: 'green',
            0.5: 'yellow',
            0.8: 'orange',
            1.0: 'red'
        }
    ).add_to(m)
    
    return m

# Function to display route details
def display_route_details(route_data):
    if not route_data:
        return
    
    # Display tabs for different routes
    route_tabs = st.tabs([f"Route {i+1}: {route['summary']}" for i, route in enumerate(route_data)])
    
    for i, tab in enumerate(route_tabs):
        route = route_data[i]
        with tab:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Distance", f"{route['distance']:.1f} km")
            with col2:
                st.metric("Duration", f"{route['duration']:.1f} mins")
            with col3:
                # Calculate estimated arrival
                now = datetime.datetime.now()
                arrival = now + datetime.timedelta(minutes=route['duration'])
                st.metric("Est. Arrival", arrival.strftime("%H:%M"))
            
            st.subheader("Directions")
            for j, step in enumerate(route['steps']):
                st.markdown(f"**{j+1}.** {step['instruction'].replace('<b>', '**').replace('</b>', '**')} ({step['distance']})")

# Search history function
def add_to_search_history(origin, destination, route_data):
    if 'search_history' not in st.session_state:
        st.session_state.search_history = []
    
    # Add to history
    st.session_state.search_history.append({
        'timestamp': datetime.datetime.now(),
        'origin': origin,
        'destination': destination,
        'route_summary': route_data[0]['summary'] if route_data else "Unknown",
        'distance': route_data[0]['distance'] if route_data else 0,
        'duration': route_data[0]['duration'] if route_data else 0
    })
    
    # Keep only the last 10 entries
    if len(st.session_state.search_history) > 10:
        st.session_state.search_history = st.session_state.search_history[-10:]

# Function to display metrics
def display_metrics(route_data, traffic_data):
    st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
    
    # Average congestion (1-10 scale)
    avg_congestion = traffic_data['congestion'].mean()
    col_class = "success" if avg_congestion < 4 else "warning" if avg_congestion < 7 else "error"
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Avg. Congestion</div>
        <div class='metric-value' style='color: {"green" if avg_congestion < 4 else "orange" if avg_congestion < 7 else "red"}'>{avg_congestion:.1f}/10</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Best route details
    if route_data:
        best_route = min(route_data, key=lambda x: x['duration'])
        
        # Distance
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Best Route Distance</div>
            <div class='metric-value'>{best_route['distance']:.1f} km</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Duration
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Best Route Time</div>
            <div class='metric-value'>{best_route['duration']:.1f} min</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Calculate time savings compared to longest route
        longest_route = max(route_data, key=lambda x: x['duration'])
        time_saved = longest_route['duration'] - best_route['duration']
        
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Time Saved</div>
            <div class='metric-value' style='color: green'>{time_saved:.1f} min</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# Main App Logic
def main():
    st.markdown('<p class="title">🚦 MobiSync Platform</p>', unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        st.image("https://via.placeholder.com/200x80?text=MobiSync+Logo", use_column_width=True)
        
        if st.session_state.logged_in:
            st.markdown(f"**Welcome, {USERS[st.session_state.username]['name']}!**")
            
            nav_options = ["Route Planner", "Traffic Visualization", "Search History", "Settings"]
            page = st.radio("Navigation", nav_options)
            
            if st.button("Logout"):
                logout_user()
                st.experimental_rerun()
        else:
            page = "Login"
    
    # Login page
    if page == "Login":
        st.markdown('<p class="subtitle">Login to MobiSync</p>', unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            
            email = st.text_input("Email Address", placeholder="Enter your email")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Login", use_container_width=True):
                    if login_user(email, password):
                        st.success("Login successful! Redirecting...")
                        time.sleep(1)
                        st.experimental_rerun()
                    else:
                        st.error("Invalid email or password.")
            
            with col2:
                if st.button("Demo Login", use_container_width=True):
                    if login_user("demo@mobisync.com", "demo123"):
                        st.success("Demo login successful! Redirecting...")
                        time.sleep(1)
                        st.experimental_rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("""
            <div style="text-align: center; margin-top: 1rem;">
                <p>Demo Credentials:</p>
                <p><strong>Email:</strong> demo@mobisync.com | <strong>Password:</strong> demo123</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Route Planner page
    elif page == "Route Planner":
        st.markdown('<p class="subtitle">Smart Route Planner</p>', unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                origin = st.text_input("Starting Point", 
                                      value=st.session_state.get('last_origin', ''),
                                      placeholder="Enter starting location")
            
            with col2:
                destination = st.text_input("Destination", 
                                           value=st.session_state.get('last_destination', ''),
                                           placeholder="Enter destination")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                avoid_tolls = st.checkbox("Avoid Tolls")
            
            with col2:
                avoid_highways = st.checkbox("Avoid Highways")
            
            with col3:
                api_choice = st.radio("API Provider", ["Google Maps", "OpenRouteService"], horizontal=True)
            
            if st.button("Find Route", use_container_width=True):
                with st.spinner("Finding optimal route..."):
                    # Save search info
                    st.session_state.last_origin = origin
                    st.session_state.last_destination = destination
                    
                    # Geocode addresses
                    origin_coords = geocode_address(origin)
                    destination_coords = geocode_address(destination)
                    
                    if origin_coords and destination_coords:
                        # Get route data
                        api = "google" if api_choice == "Google Maps" else "openroute"
                        route_data = get_optimized_route(origin_coords, destination_coords, api)
                        
                        if route_data:
                            st.session_state.route_data = route_data
                            st.session_state.last_search = {
                                'origin': origin,
                                'destination': destination
                            }
                            
                            # Add to search history
                            add_to_search_history(origin, destination, route_data)
                            
                            # Success message
                            st.success("Route found successfully!")
                        else:
                            st.error("Could not find a route between these locations.")
                    else:
                        st.error("Could not find one or both locations. Please check the addresses.")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Display route results if available
        if st.session_state.route_data:
            route_data = st.session_state.route_data
            
            # Generate traffic data around the route
            first_route = route_data[0]
            if 'polyline' in first_route:
                if isinstance(first_route['polyline'], str):
                    route_coords = polyline.decode(first_route['polyline'])
                else:
                    # Handle GeoJSON format
                    route_coords = [[coord[1], coord[0]] for coord in first_route['polyline']['coordinates']]
                
                center_lat = route_coords[len(route_coords)//2][0]
                center_lng = route_coords[len(route_coords)//2][1]
                traffic_data = generate_traffic_data(center_lat, center_lng)
                
                # Display metrics
                display_metrics(route_data, traffic_data)
                
                # Create and display map
                st.subheader("Route Map with Traffic")
                map_obj = create_traffic_map(route_data, traffic_data)
                if map_obj:
                    folium_static(map_obj, width=1000, height=500)
                
                # Display directions
                st.subheader("Route Details")
                display_route_details(route_data)
                
                # Congestion analysis
                st.subheader("Traffic Congestion Analysis")
                
                # Create a chart showing congestion levels along the route
                distance_points = np.linspace(0, first_route['distance'], 20)
                congestion_points = []
                
                for i, dist in enumerate(distance_points):
                    # Simulate congestion at different points of the route
                    # Higher at the beginning and end (urban areas)
                    if i < len(distance_points) * 0.2 or i > len(distance_points) * 0.8:
                        base_congestion = np.random.uniform(6, 9)
                    else:
                        base_congestion = np.random.uniform(2, 5)
                    
                    congestion_points.append(base_congestion)
                
                # Create congestion chart
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=distance_points,
                    y=congestion_points,
                    mode='lines+markers',
                    name='Congestion Level',
                    line=dict(color='red', width=2),
                    marker=dict(size=8)
                ))
                
                fig.update_layout(
                    title="Congestion Level Along Route",
                    xaxis_title="Distance (km)",
                    yaxis_title="Congestion Level (1-10)",
                    yaxis=dict(range=[0, 10]),
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Traffic analysis explanation
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown("""
                    ### Traffic Analysis
                    
                    The traffic analysis above shows congestion levels along your route. Key observations:
                    
                    - **Beginning and end of route**: Higher congestion levels (typical for urban areas)
                    - **Middle sections**: Lower congestion levels (typically highway or less congested areas)
                    - **Overall traffic conditions**: The route has an average congestion level of 
                      """+f"**{traffic_data['congestion'].mean():.1f}**"+""" out of 10.
                    
                    MobiSync analyzes real-time and historical traffic data to provide you with the most efficient route.
                    """)
                
                with col2:
                    # Traffic rating
                    avg_congestion = traffic_data['congestion'].mean()
                    rating_color = "green" if avg_congestion < 4 else "orange" if avg_congestion < 7 else "red"
                    rating_text = "Good" if avg_congestion < 4 else "Moderate" if avg_congestion < 7 else "Heavy"
                    
                    st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 1rem; border-radius: 0.5rem; text-align: center;">
                        <h4>Traffic Rating</h4>
                        <div style="font-size: 2.5rem; font-weight: bold; color: {rating_color};">
                            {rating_text}
                        </div>
                        <div style="font-size: 1.5rem; color: {rating_color};">
                            {avg_congestion:.1f}/10
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
    
    # Traffic Visualization page
    elif page == "Traffic Visualization":
        st.markdown('<p class="subtitle">Traffic Visualization</p>', unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            
            visualization_type = st.radio(
                "Select Visualization Type",
                ["Live Traffic Map", "Congestion Heatmap", "Traffic Patterns"],
                horizontal=True
            )
            
            if st.session_state.route_data:
                # Use the last route for visualization
                route_data = st.session_state.route_data
                first_route = route_data[0]
                
                if 'polyline' in first_route:
                    if isinstance(first_route['polyline'], str):
                        route_coords = polyline.decode(first_route['polyline'])
                    else:
                        # Handle GeoJSON format
                        route_coords = [[coord[1], coord[0]] for coord in first_route['polyline']['coordinates']]
                    
                    center_lat = route_coords[len(route_coords)//2][0]
                    center_lng = route_coords[len(route_coords)//2][1]
                else:
                    # Fallback to default coordinates
                    center_lat, center_lng = 40.7128, -74.0060  # NYC
            else:
                # Default to NYC if no route data
                center_lat, center_lng = 40.7128, -74.0060
                route_data = None
            
            # Generate traffic data
            traffic_data = generate_traffic_data(center_lat, center_lng, radius=0.05, n_points=300)
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        if visualization_type == "Live Traffic Map":
            st.subheader("Live Traffic Map")
            
            # Create map
            if route_data:
                map_obj = create_traffic_map(route_data, traffic_data)
            else:
                # Create a map centered on the default location without a route
                m = folium.Map(location=[center_lat, center_lng], zoom_start=12, tiles="CartoDB positron")
                
                # Add heat map layer
                heat_data = []
                for _, row in traffic_data.iterrows():
                    heat_data.append([row['lat'], row['lng'], row['congestion'] / 2])
                
                HeatMap(
                    heat_data,
                    radius=15,
                    gradient={
                        0.2: 'green',
                        0.5: 'yellow',
                        0.8: 'orange',
                        1.0: 'red'
                    }
                ).add_to(m)
                
                map_obj = m
            
            folium_static(map_obj, width=1000, height=600)
            
            # Legend
            st.markdown("""
            <div style="display: flex; justify-content: center; gap: 2rem; margin-top: 1rem;">
                <div><span style="background-color: green; width: 15px; height: 15px; display: inline-block; border-radius: 50%;"></span> Low Congestion</div>
                <div><span style="background-color: yellow; width
