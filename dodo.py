import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

from skyfield.api import load, Star, Topos

# -----------------------------
# Load Skyfield Data
# -----------------------------
planets = load('de422.bsp')  # works with de421 or de422
earth = planets[399]  # Earth

ts = load.timescale()

# Load Hipparcos star catalog
from skyfield.data import hipparcos
with load.open(hipparcos.URL) as f:
    stars = hipparcos.load_dataframe(f)

# -----------------------------
# Planet IDs mapping
# -----------------------------
planet_ids = {
    "Mercury": 199,
    "Venus": 299,
    "Mars": 499,
    "Moon": 301,
    "Sun": 10,
}

# Build bodies dict for easy access
bodies = {name: planets[naif_id] for name, naif_id in planet_ids.items()}

# -----------------------------
# Helper Functions
# -----------------------------
def to_altaz(obj, location, t):
    astrometric = location.at(t).observe(obj)
    alt, az, _ = astrometric.apparent().altaz()
    return alt.degrees, az.degrees

def make_sky_map(lat, lon, year, month, day, hour):
    """Generate Plotly sky map"""
    location = earth + Topos(latitude_degrees=lat, longitude_degrees=lon)
    t = ts.utc(year, month, day, hour, 0)

    # Collect planets (only visible ones above horizon)
    selected_planets = ["Mercury", "Venus", "Mars", "Moon", "Sun"]
    planet_data = []
    for name in selected_planets:
        alt, az = to_altaz(bodies[name], location, t)
        if alt > 0:
            planet_data.append((name, alt, az))

    # Collect bright stars
    bright_stars = stars[stars['magnitude'] < 6]
    star_data = []
    for hip, row in bright_stars.iterrows():
        star = Star.from_dataframe(row)
        alt, az = to_altaz(star, location, t)
        if alt > 0:
            star_data.append((row['magnitude'], alt, az, hip))

    # -----------------------------
    # Plotly chart
    # -----------------------------
    fig = go.Figure()

    # Stars
    for mag, alt, az, hip in star_data:
        size = max(0.5, 12 * np.exp(-0.4 * (mag - 1.0)))
        fig.add_trace(go.Scatterpolar(
            r=[90 - alt],
            theta=[az],
            mode="markers",
            marker=dict(size=size, color="white", opacity=0.8),
            hovertext=f"HIP {hip} (mag {mag:.2f})",
            hoverinfo="text"
        ))

    # Planets
    planet_colors = {
        "Mercury": "lightgray",
        "Venus": "lightgray",
        "Mars": "lightgray",
        "Jupiter": "lightgray",
        "Saturn": "lightgray",
    }
    for name, alt, az in planet_data:
        fig.add_trace(go.Scatterpolar(
            r=[90 - alt],
            theta=[az],
            mode="markers+text",
            marker=dict(size=15, color=planet_colors.get(name, "lightgray"),
                        line=dict(color="black", width=1))
        ))

    # Layout
    fig.update_layout(
        polar=dict(
            bgcolor="black",
            radialaxis=dict(visible=False, range=[0, 90], showgrid=False),
            angularaxis=dict(direction="clockwise", rotation=180,
                             showline=False, showticklabels=False, showgrid=False),
        ),
        showlegend=False,
        paper_bgcolor="black",
        plot_bgcolor="black",
    )

    return fig

# -----------------------------
# Dash App
# -----------------------------
app = dash.Dash(__name__)

locations = {
    # North America
    "San Francisco": (37.7749, -122.4194),
    "New York": (40.7128, -74.0060),
    "Toronto": (43.651070, -79.347015),
    "Mexico City": (19.4326, -99.1332),

    # South America
    "Buenos Aires": (-34.6037, -58.3816),
    "Rio de Janeiro": (-22.9068, -43.1729),
    "Santiago": (-33.4489, -70.6693),

    # Europe
    "London": (51.5074, -0.1278),
    "Paris": (48.8566, 2.3522),
    "Berlin": (52.5200, 13.4050),
    "Rome": (41.9028, 12.4964),
    "Moscow": (55.7558, 37.6173),

    # Africa
    "Cairo": (30.0444, 31.2357),
    "Cape Town": (-33.9249, 18.4241),
    "Nairobi": (-1.2921, 36.8219),
    "Lagos": (6.5244, 3.3792),

    # Middle East
    "Istanbul": (41.0082, 28.9784),
    "Dubai": (25.276987, 55.296249),
    "Jerusalem": (31.7683, 35.2137),

    # Asia
    "Tokyo": (35.6762, 139.6503),
    "Beijing": (39.9042, 116.4074),
    "New Delhi": (28.6139, 77.2090),
    "Bangkok": (13.7563, 100.5018),
    "Singapore": (1.3521, 103.8198),

    # Oceania
    "Sydney": (-33.8688, 151.2093),
    "Auckland": (-36.8485, 174.7633),

    # Extra
    "Honolulu": (21.3069, -157.8583),
    "Reykjavik": (64.1355, -21.8954),
    "Anchorage": (61.2181, -149.9003),
}


app.layout = html.Div(style={"backgroundColor": "black", "color": "white", "padding": "20px"}, children=[
    html.H1("🌌 Interactive Sky Map", style={"textAlign": "center"}),

    html.Label("Choose a location:"),
    dcc.Dropdown(
        id="city",
        options=[{"label": city, "value": city} for city in locations.keys()],
        value="San Francisco",
        style={"width": "300px", "color": "black"}
    ),

    html.Br(),
    html.Label("Choose date and hour (UTC):"),

    html.Div(style={"display": "flex", "gap": "20px", "alignItems": "center"}, children=[
        dcc.DatePickerSingle(
            id="date",
            date=datetime.utcnow().date(),
            display_format="YYYY-MM-DD"
        ),
        dcc.Dropdown(
            id="hour",
            options=[{"label": f"{h:02d}:00", "value": h} for h in range(24)],
            value=22,
            style={"width": "120px", "color": "black"}
        )
    ]),

    html.Br(),
    dcc.Graph(id="sky-map", style={"height": "90vh"})
])

# -----------------------------
# Callbacks
# -----------------------------
@app.callback(
    Output("sky-map", "figure"),
    [Input("city", "value"), Input("date", "date"), Input("hour", "value")]
)
def update_map(city, date, hour):
    lat, lon = locations[city]
    dt = datetime.fromisoformat(date)
    fig = make_sky_map(lat, lon, dt.year, dt.month, dt.day, hour)
    return fig

# -----------------------------
# Run Server
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
