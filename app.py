import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import folium_static
from folium.features import DivIcon
import random

# Set page configuration
st.set_page_config(
    page_title="MobiSync Route Optimization",
    page_icon="🚦",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
.title {
    font-size: 2rem;
    font-weight: bold;
    color: #1E88E5;
    text-align: center;
}
.route-card {
    padding: 1rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<p class="title">🚦 MobiSync Route Optimization</p>', unsafe_allow_html=True)

# Function to generate route coordinates between two points with some randomness
def generate_route_coords(start_coords, end_coords, variation=0.01):
    """Generate a list of coordinates forming a route between start and end"""
    # Calculate how many points to generate based on distance
    dist_lat = end_coords[0] - start_coords[0]
    dist_lng = end_coords[1] - start_coords[1]
    dist = np.sqrt(dist_lat**2 + dist_lng**2)
    num_points = max(5, int(dist * 100))
    
    # Generate route with some randomness
    route = []
    for i in range(num_points + 1):
        t = i / num_points
        # Direct path with noise
        lat = start_coords[0] + t * dist_lat + random.uniform(-variation, variation)
        lng = start_coords[1] + t * dist_lng + random.uniform(-variation, variation)
        route.append([lat, lng])
    
    # Make sure the route starts and ends at the exact coordinates
    route[0] = start_coords
    route[-1] = end_coords
    
    return route

# Function to create a map with routes
def create_route_map(start_loc, end_loc, routes):
    """Create a map with multiple route options"""
    # For this demo, we'll use fixed coordinates based on location names
    # In a real app, you'd use geocoding API to convert addresses to coordinates
    
    # Sample coordinates (lat, lng)
    locations = {
        "City Center": [40.712, -74.006],
        "Airport": [40.640, -73.779],
        "Downtown": [40.702, -74.015],
        "Midtown": [40.754, -73.984],
        "Brooklyn": [40.678, -73.944],
        "Queens": [40.728, -73.794],
        "Bronx": [40.837, -73.846],
        "Central Park": [40.785, -73.968],
        "Times Square": [40.758, -73.985],
        "Financial District": [40.707, -74.011]
    }
    
    # Use provided locations or defaults
    start_coords = locations.get(start_loc, locations["City Center"])
    end_coords = locations.get(end_loc, locations["Airport"])
    
    # Create the base map centered between start and end points
    center_lat = (start_coords[0] + end_coords[0]) / 2
    center_lng = (start_coords[1] + end_coords[1]) / 2
    route_map = folium.Map(location=[center_lat, center_lng], zoom_start=12, tiles="CartoDB positron")
    
    # Add markers for start and end points
    folium.Marker(
        location=start_coords,
        popup=start_loc,
        icon=folium.Icon(color="green", icon="play", prefix="fa"),
        tooltip=f"Start: {start_loc}"
    ).add_to(route_map)
    
    folium.Marker(
        location=end_coords,
        popup=end_loc,
        icon=folium.Icon(color="red", icon="stop", prefix="fa"),
        tooltip=f"End: {end_loc}"
    ).add_to(route_map)
    
    # Add each route with different colors and patterns
    colors = ["blue", "purple", "orange"]
    dash_patterns = ["solid", "dashed", "dotted"]
    
    for i, route in enumerate(routes):
        # Generate route coordinates
        variation = 0.005 * (i + 1)  # Different variation for each route
        route_coords = generate_route_coords(start_coords, end_coords, variation)
        
        # Traffic incidents (random points along the route)
        if random.random() < 0.7:  # 70% chance of having an incident
            incident_idx = random.randint(1, len(route_coords) - 2)
            incident_loc = route_coords[incident_idx]
            
            folium.CircleMarker(
                location=incident_loc,
                radius=5,
                color="red",
                fill=True,
                fill_opacity=0.7,
                popup="Traffic incident: Delay of 5-10 minutes"
            ).add_to(route_map)
        
        # Add the route line
        folium.PolyLine(
            route_coords,
            color=colors[i % len(colors)],
            weight=4,
            opacity=0.8,
            dash_array=["5" if dash_patterns[i % len(dash_patterns)] == "dashed" else 
                        "3, 3" if dash_patterns[i % len(dash_patterns)] == "dotted" else None],
            tooltip=f"{route['name']} - {route['time_min']:.1f} min"
        ).add_to(route_map)
        
        # Add route label in the middle of the route
        mid_point = route_coords[len(route_coords) // 2]
        folium.map.Marker(
            mid_point,
            icon=DivIcon(
                icon_size=(150, 36),
                icon_anchor=(75, 18),
                html=f'<div style="font-size: 12pt; color: {colors[i % len(colors)]}; font-weight: bold;">{route["name"]}</div>'
            )
        ).add_to(route_map)
        
        # Add traffic density indicators at intervals
        for j in range(1, len(route_coords) - 1, len(route_coords) // 5):
            if j >= len(route_coords):
                continue
                
            # Traffic density based on route congestion
            congestion = route["congestion"]
            color = "green" if congestion < 0.7 else "orange" if congestion < 0.9 else "red"
            
            folium.CircleMarker(
                location=route_coords[j],
                radius=3,
                color=color,
                fill=True,
                fill_opacity=0.7,
                tooltip=f"Traffic density: {int(congestion * 100)}%"
            ).add_to(route_map)
    
    return route_map

# Function to generate more realistic route options
def generate_routes(start, end, preferences):
    """Generate sample route options based on preferences"""
    # Adjust base values based on preferences
    avoid_tolls = preferences.get("avoid_tolls", False)
    avoid_highways = preferences.get("avoid_highways", False)
    
    # Add some variability for different routes
    base_distance = 15 + random.uniform(-3, 3)
    base_time = 25 + random.uniform(-5, 5)
    
    routes = [
        {
            'name': 'Fastest Route',
            'distance_km': base_distance + random.uniform(0, 2),
            'time_min': base_time * (1.2 if avoid_highways else 1.0),
            'congestion': random.uniform(0.6, 0.8),
            'tolls': not avoid_tolls,
            'highways': not avoid_highways
        },
        {
            'name': 'Shortest Route',
            'distance_km': base_distance * 0.85,
            'time_min': base_time * 1.2,
            'congestion': random.uniform(0.7, 0.9),
            'tolls': False,
            'highways': False
        },
        {
            'name': 'Eco-Friendly Route',
            'distance_km': base_distance * 1.1,
            'time_min': base_time * 1.1,
            'congestion': random.uniform(0.5, 0.7),
            'tolls': random.choice([True, False]),
            'highways': random.choice([True, False])
        }
    ]
    
    return routes

# -----------------------------
# Main App
# -----------------------------

st.header("Smart Route Optimization")

# Route planner section
st.subheader("Route Planner")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Starting Point**")
    start_location = st.selectbox(
        "Select start location", 
        ["City Center", "Downtown", "Midtown", "Brooklyn", "Queens", "Central Park"],
        index=0
    )

with col2:
    st.markdown("**Destination**")
    end_location = st.selectbox(
        "Select destination", 
        ["Airport", "Financial District", "Times Square", "Bronx", "Brooklyn", "Queens"],
        index=0
    )

# Route preferences
st.subheader("Route Preferences")
col1, col2 = st.columns(2)
with col1:
    avoid_tolls = st.checkbox("Avoid toll roads", False)
    avoid_highways = st.checkbox("Avoid highways", False)

with col2:
    optimize_for = st.radio(
        "Optimize for:",
        ["Time", "Distance", "Eco-Friendly"],
        index=0
    )
    
    departure_time = st.selectbox(
        "Departure time:",
        ["Now", "In 30 minutes", "In 1 hour", "In 2 hours"],
        index=0
    )

# Generate routes on button click
if st.button("Find Routes", type="primary"):
    # Generate sample routes
    routes = generate_routes(
        start_location, 
        end_location, 
        {"avoid_tolls": avoid_tolls, "avoid_highways": avoid_highways}
    )
    
    # Create two columns for routes and map
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Route Options")
        
        # Display each route with more details
        for i, route in enumerate(routes):
            if i == 0:  # Highlight recommended route
                card_color = "#e6f7ff"  # Light blue for recommended
                recommended_text = "✅ RECOMMENDED"
            else:
                card_color = "#f9f9f9"
                recommended_text = ""
                
            # Route card
            st.markdown(f"""
            <div class="route-card" style="background-color: {card_color};">
                <h4>{route['name']} {recommended_text}</h4>
                <p>
                <strong>Distance:</strong> {route['distance_km']:.1f} km<br>
                <strong>Est. Time:</strong> {route['time_min']:.1f} minutes<br>
                <strong>Congestion:</strong> {int(route['congestion']*100)}%<br>
                <strong>Features:</strong> {"Uses toll roads" if route['tolls'] else "No tolls"}, 
                {"Uses highways" if route['highways'] else "Avoids highways"}
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.subheader("Route Map")
        # Create and display the map
        route_map = create_route_map(start_location, end_location, routes)
        folium_static(route_map, width=700, height=500)
    
    # Traffic conditions along the route
    st.subheader("Current Traffic Conditions")
    
    # Generate sample traffic incidents
    incidents = []
    if random.random() < 0.7:
        incidents.append({
            "type": "Accident",
            "location": f"Near {random.choice(['Broadway', 'Main St', '5th Avenue'])}",
            "delay": f"{random.randint(5, 20)} minutes",
            "severity": "Moderate"
        })
    
    if random.random() < 0.5:
        incidents.append({
            "type": "Construction",
            "location": f"On {random.choice(['Highway 101', 'Bridge St', 'Downtown'])}",
            "delay": f"{random.randint(3, 15)} minutes",
            "severity": "Minor"
        })
    
    # Display incidents
    if incidents:
        st.warning("⚠️ Traffic incidents detected on your route")
        for incident in incidents:
            st.markdown(f"**{incident['type']}** at {incident['location']} - Expected delay: {incident['delay']} ({incident['severity']} severity)")
    else:
        st.success("✅ No major incidents reported on your route")
    
    # Additional information
    st.subheader("Additional Information")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Traffic Forecast**")
        st.markdown("🔹 Traffic expected to improve in the next hour")
        st.markdown("🔹 Rush hour congestion from 4:30 PM - 6:00 PM")
    
    with col2:
        st.markdown("**Travel Tips**")
        st.markdown("🔹 Consider departing after 6:30 PM to avoid traffic")
        st.markdown("🔹 Check for updates before departure")
        
    # Future improvement notes
    st.info("In a production app, this would use real-time traffic data and integrate with actual mapping APIs.")
else:
    # Show placeholder image when no routes are selected
    st.image("https://via.placeholder.com/800x400.png?text=Route+Map+(Enter+locations+and+click+Find+Routes)", use_column_width=True)
