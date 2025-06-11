import streamlit as st
import sqlite3
import pandas as pd
import pickle
import requests
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from pathlib import Path
import numpy as np
import pickle

with open('models/crop.pkl', 'rb') as file:
    crop_model = pickle.load(file)

with open('models/fertilizer.pkl', 'rb') as file:
    fertilizer_model = pickle.load(file)

# Page configuration
st.set_page_config(
    page_title="🌾 Smart Agriculture Platform",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #2E8B57;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #2E8B57, #32CD32);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .crop-card {
        border: 2px solid #e0e0e0;
        border-radius: 15px;
        padding: 1rem;
        margin: 1rem 0;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #2E8B57 0%, #228B22 100%);
    }
</style>
""", unsafe_allow_html=True)

# Database setup
DB_PATH = 'smart_agriculture.db'

def init_database():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            email TEXT,
            location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Crops table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            unit TEXT DEFAULT 'kg',
            user_id INTEGER,
            image_url TEXT,
            category TEXT,
            harvest_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crop_id INTEGER,
            buyer_id INTEGER,
            seller_id INTEGER,
            quantity INTEGER,
            total_price REAL,
            status TEXT DEFAULT 'pending',
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (crop_id) REFERENCES crops (id),
            FOREIGN KEY (buyer_id) REFERENCES users (id),
            FOREIGN KEY (seller_id) REFERENCES users (id)
        )
    ''')
    
    # Price history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crop_name TEXT NOT NULL,
            price REAL NOT NULL,
            market TEXT,
            date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_database()

def predict_crop(N, P, K, temperature, humidity, ph, rainfall):
    try:
        input_data = np.array([[N, P, K, temperature, humidity, ph, rainfall]])
        prediction = crop_model.predict(input_data)
        return prediction[0]
    except Exception as e:
        return f"Error in prediction: {str(e)}"

def predict_fertilizer(N, P, K, crop, soil_type, temperature, humidity, moisture):
    """
    Predict fertilizer using trained model.
    """
    try:
        input_data = pd.DataFrame([{
            'Temparature': temperature,      # Exact spelling from CSV
            'Humidity ': humidity,           # Note: trailing space
            'Moisture': moisture,
            'Soil Type': soil_type,
            'Crop Type': crop,
            'Nitrogen': N,
            'Potassium': K,
            'Phosphorous': P
        }])
        prediction = fertilizer_model.predict(input_data)
        return prediction[0]
    except Exception as e:
        return f"Prediction error: {str(e)}"


# Session state initialization
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = None

# Authentication functions
def login_user(phone):
    """Login user with phone number"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    user = cursor.fetchone()
    conn.close()
    return user

def register_user(name, phone, email="", location=""):
    """Register new user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (name, phone, email, location) VALUES (?, ?, ?, ?)",
                      (name, phone, email, location))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None

# Weather API function
def get_weather_data(lat, lon):
    """Get weather data from OpenWeatherMap API"""
    api_key = "7e8545f84e0a5f340abc6b9f0e78ef8a"  # Your API key
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

# Main application
def main():
    if not st.session_state.logged_in:
        show_login_page()
    else:
        show_main_app()

def show_login_page():
    """Display login/registration page"""
    st.markdown('<h1 class="main-header">🌾 Smart Agriculture Platform</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])
        
        with tab1:
            st.subheader("Login to your account")
            phone = st.text_input("📱 Phone Number", placeholder="Enter your phone number")
            
            if st.button("🚀 Login", use_container_width=True):
                if phone:
                    user = login_user(phone)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user[0]
                        st.session_state.user_name = user[1]
                        st.success(f"Welcome back, {user[1]}!")
                        st.rerun()
                    else:
                        st.error("User not found. Please register first.")
                else:
                    st.error("Please enter your phone number")
        
        with tab2:
            st.subheader("Create new account")
            name = st.text_input("👤 Full Name", placeholder="Enter your full name")
            phone = st.text_input("📱 Phone Number", placeholder="Enter your phone number", key="reg_phone")
            email = st.text_input("📧 Email (Optional)", placeholder="Enter your email")
            location = st.text_input("📍 Location (Optional)", placeholder="Enter your location")
            
            if st.button("✅ Register", use_container_width=True):
                if name and phone:
                    user_id = register_user(name, phone, email, location)
                    if user_id:
                        st.success("Registration successful! Please login.")
                    else:
                        st.error("Phone number already exists. Please login.")
                else:
                    st.error("Please fill in required fields")

def show_main_app():
    """Display main application interface"""
    # Sidebar navigation
    with st.sidebar:
        st.markdown(f"### Welcome, {st.session_state.user_name}! 👋")
        
        menu = st.selectbox(
            "🧭 Navigation",
            ["🏠 Dashboard", "🛒 Marketplace", "📊 Price Comparison", "🌤️ Weather", 
             "🌱 Crop Recommendation", "🧪 Fertilizer Recommendation", "📦 My Orders", "👤 Profile"]
        )
        
        st.markdown("---")
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.user_name = None
            st.rerun()
    
    # Main content based on selected menu
    if menu == "🏠 Dashboard":
        show_dashboard()
    elif menu == "🛒 Marketplace":
        show_marketplace()
    elif menu == "📊 Price Comparison":
        show_price_comparison()
    elif menu == "🌤️ Weather":
        show_weather()
    elif menu == "🌱 Crop Recommendation":
        show_crop_recommendation()
    elif menu == "🧪 Fertilizer Recommendation":
        show_fertilizer_recommendation()
    elif menu == "📦 My Orders":
        show_orders()
    elif menu == "👤 Profile":
        show_profile()

def show_dashboard():
    """Display dashboard with overview"""
    st.markdown('<h1 class="main-header">🏠 Dashboard</h1>', unsafe_allow_html=True)
    
    # Get statistics
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM crops")
    total_crops = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM crops WHERE user_id = ?", (st.session_state.user_id,))
    my_crops = cursor.fetchone()[0]
    
    conn.close()
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h2>🌾</h2>
            <h3>{total_crops}</h3>
            <p>Total Crops</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h2>📦</h2>
            <h3>{total_orders}</h3>
            <p>Total Orders</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h2>👥</h2>
            <h3>{total_users}</h3>
            <p>Total Users</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h2>🏪</h2>
            <h3>{my_crops}</h3>
            <p>My Listings</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.subheader("📈 Recent Market Activity")
    conn = sqlite3.connect(DB_PATH)
    recent_crops = pd.read_sql_query("""
        SELECT c.name, c.price, c.quantity, u.name as seller, c.created_at
        FROM crops c 
        JOIN users u ON c.user_id = u.id 
        ORDER BY c.created_at DESC 
        LIMIT 5
    """, conn)
    conn.close()
    
    if not recent_crops.empty:
        st.dataframe(recent_crops, use_container_width=True)
    else:
        st.info("No recent activity")

def show_marketplace():
    """Display marketplace for buying/selling crops"""
    st.markdown('<h1 class="main-header">🛒 Marketplace</h1>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🛍️ Buy Crops", "🏪 Sell Crops"])
    
    with tab1:
        st.subheader("Available Crops")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            search_term = st.text_input("🔍 Search crops", placeholder="Enter crop name...")
        with col2:
            category_filter = st.selectbox("📂 Category", ["All", "Grains", "Vegetables", "Fruits", "Pulses"])
        with col3:
            sort_by = st.selectbox("🔢 Sort by", ["Price (Low to High)", "Price (High to Low)", "Newest", "Quantity"])
        
        # Get crops from database
        conn = sqlite3.connect(DB_PATH)
        query = """
            SELECT c.*, u.name as seller_name, u.phone as seller_phone 
            FROM crops c 
            JOIN users u ON c.user_id = u.id 
            WHERE c.user_id != ?
        """
        params = [st.session_state.user_id]
        
        if search_term:
            query += " AND c.name LIKE ?"
            params.append(f"%{search_term}%")
        
        if category_filter != "All":
            query += " AND c.category = ?"
            params.append(category_filter)
        
        # Apply sorting
        if sort_by == "Price (Low to High)":
            query += " ORDER BY c.price ASC"
        elif sort_by == "Price (High to Low)":
            query += " ORDER BY c.price DESC"
        elif sort_by == "Newest":
            query += " ORDER BY c.created_at DESC"
        else:
            query += " ORDER BY c.quantity DESC"
        
        crops_df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if not crops_df.empty:
            for _, crop in crops_df.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="crop-card">
                        <h3>🌾 {crop['name']}</h3>
                        <p><strong>Price:</strong> ${crop['price']}/{crop['unit']}</p>
                        <p><strong>Quantity:</strong> {crop['quantity']} {crop['unit']}</p>
                        <p><strong>Seller:</strong> {crop['seller_name']}</p>
                        <p><strong>Description:</strong> {crop['description'] or 'No description'}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col2:
                        quantity_to_buy = st.number_input(
                            f"Quantity to buy", 
                            min_value=1, 
                            max_value=crop['quantity'], 
                            value=1, 
                            key=f"qty_{crop['id']}"
                        )
                    with col3:
                        if st.button(f"🛒 Buy", key=f"buy_{crop['id']}"):
                            # Create order
                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            total_price = quantity_to_buy * crop['price']
                            cursor.execute("""
                                INSERT INTO orders (crop_id, buyer_id, seller_id, quantity, total_price)
                                VALUES (?, ?, ?, ?, ?)
                            """, (crop['id'], st.session_state.user_id, crop['user_id'], quantity_to_buy, total_price))
                            
                            # Update crop quantity
                            new_quantity = crop['quantity'] - quantity_to_buy
                            cursor.execute("UPDATE crops SET quantity = ? WHERE id = ?", (new_quantity, crop['id']))
                            
                            conn.commit()
                            conn.close()
                            
                            st.success(f"Order placed successfully! Total: ${total_price}")
                            st.rerun()
                    
                    st.markdown("---")
        else:
            st.info("No crops available for purchase")
    
    with tab2:
        st.subheader("Add New Crop Listing")
        
        with st.form("add_crop_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                crop_name = st.text_input("🌾 Crop Name", placeholder="e.g., Wheat, Rice, Tomato")
                price = st.number_input("💰 Price per unit ($)", min_value=0.01, step=0.01)
                quantity = st.number_input("📦 Quantity", min_value=1, step=1)
                unit = st.selectbox("📏 Unit", ["kg", "quintal", "ton", "pieces", "dozen"])
            
            with col2:
                category = st.selectbox("📂 Category", ["Grains", "Vegetables", "Fruits", "Pulses", "Spices", "Other"])
                harvest_date = st.date_input("📅 Harvest Date")
                image_url = st.text_input("🖼️ Image URL (Optional)", placeholder="https://example.com/image.jpg")
                description = st.text_area("📝 Description", placeholder="Describe your crop...")
            
            submitted = st.form_submit_button("➕ Add Crop Listing")
            
            if submitted:
                if crop_name and price > 0 and quantity > 0:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO crops (name, description, price, quantity, unit, user_id, image_url, category, harvest_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (crop_name, description, price, quantity, unit, st.session_state.user_id, image_url, category, harvest_date))
                    conn.commit()
                    conn.close()
                    
                    st.success("Crop listing added successfully!")
                    st.rerun()
                else:
                    st.error("Please fill in all required fields")
        
        st.markdown("---")
        st.subheader("My Crop Listings")
        
        # Show user's crops
        conn = sqlite3.connect(DB_PATH)
        my_crops_df = pd.read_sql_query("""
            SELECT * FROM crops WHERE user_id = ? ORDER BY created_at DESC
        """, conn, params=[st.session_state.user_id])
        conn.close()
        
        if not my_crops_df.empty:
            for _, crop in my_crops_df.iterrows():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.write(f"**{crop['name']}** - ${crop['price']}/{crop['unit']} | Qty: {crop['quantity']}")
                
                with col2:
                    if st.button("✏️ Edit", key=f"edit_{crop['id']}"):
                        st.session_state[f"editing_{crop['id']}"] = True
                
                with col3:
                    if st.button("🗑️ Delete", key=f"delete_{crop['id']}"):
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM crops WHERE id = ?", (crop['id'],))
                        conn.commit()
                        conn.close()
                        st.success("Crop deleted successfully!")
                        st.rerun()
                
                # Edit form
                if st.session_state.get(f"editing_{crop['id']}", False):
                    with st.form(f"edit_crop_{crop['id']}"):
                        new_price = st.number_input("New Price", value=float(crop['price']))
                        new_quantity = st.number_input("New Quantity", value=int(crop['quantity']))
                        new_description = st.text_area("New Description", value=crop['description'] or "")
                        
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.form_submit_button("💾 Save"):
                                conn = sqlite3.connect(DB_PATH)
                                cursor = conn.cursor()
                                cursor.execute("""
                                    UPDATE crops SET price = ?, quantity = ?, description = ? WHERE id = ?
                                """, (new_price, new_quantity, new_description, crop['id']))
                                conn.commit()
                                conn.close()
                                
                                st.session_state[f"editing_{crop['id']}"] = False
                                st.success("Crop updated successfully!")
                                st.rerun()
                        
                        with col_cancel:
                            if st.form_submit_button("❌ Cancel"):
                                st.session_state[f"editing_{crop['id']}"] = False
                                st.rerun()
        else:
            st.info("You haven't listed any crops yet")

def show_price_comparison():
    """Display price comparison and market trends"""
    st.markdown('<h1 class="main-header">📊 Price Comparison</h1>', unsafe_allow_html=True)
    
    # Sample data for demonstration
    sample_data = {
        'Rice': {'current': 45, 'last_week': 42, 'last_month': 40},
        'Wheat': {'current': 35, 'last_week': 36, 'last_month': 32},
        'Maize': {'current': 28, 'last_week': 30, 'last_month': 26},
        'Cotton': {'current': 85, 'last_week': 82, 'last_month': 80},
        'Sugarcane': {'current': 15, 'last_week': 15, 'last_month': 14},
    }
    
    # Current prices comparison
    st.subheader("💰 Current Market Prices ($/kg)")
    
    cols = st.columns(5)
    for i, (crop, prices) in enumerate(sample_data.items()):
        with cols[i % 5]:
            change = prices['current'] - prices['last_week']
            change_color = "green" if change >= 0 else "red"
            arrow = "↗️" if change >= 0 else "↘️"
            
            st.markdown(f"""
            <div style="background: white; padding: 1rem; border-radius: 10px; text-align: center; border: 1px solid #ddd;">
                <h4>{crop}</h4>
                <h2 style="color: #2E8B57;">${prices['current']}</h2>
                <p style="color: {change_color};">{arrow} ${abs(change)} from last week</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Price trend chart
    st.subheader("📈 Price Trends (Last 30 Days)")
    
    # Generate sample trend data
    import numpy as np
    dates = pd.date_range(start='2024-01-01', end='2024-01-30', freq='D')
    
    trend_data = {}
    for crop in sample_data.keys():
        base_price = sample_data[crop]['current']
        # Generate realistic price fluctuations
        prices = base_price + np.random.normal(0, 2, len(dates))
        trend_data[crop] = prices
    
    trend_df = pd.DataFrame(trend_data, index=dates)
    
    fig = px.line(trend_df, x=trend_df.index, y=trend_df.columns, 
                  title="Crop Price Trends", 
                  labels={'index': 'Date', 'value': 'Price ($/kg)'})
    st.plotly_chart(fig, use_container_width=True)
    
    # Regional price comparison
    st.subheader("🌍 Regional Price Comparison")
    
    regions = ['Tbilisi', 'Kutaisi', 'Puti', 'Batumi', 'Signagi']
    selected_crop = st.selectbox("Select Crop for Regional Comparison", list(sample_data.keys()))
    
    regional_prices = {
        'Region': regions,
        'Price ($/kg)': [sample_data[selected_crop]['current'] + np.random.randint(-5, 6) for _ in regions]
    }
    
    regional_df = pd.DataFrame(regional_prices)
    
    fig_bar = px.bar(regional_df, x='Region', y='Price ($/kg)', 
                     title=f"{selected_crop} Prices Across Regions",
                     color='Price ($/kg)', color_continuous_scale='Viridis')
    st.plotly_chart(fig_bar, use_container_width=True)
    
    # Price alerts
    st.subheader("🔔 Price Alerts")
    
    col1, col2 = st.columns(2)
    with col1:
        alert_crop = st.selectbox("Crop", list(sample_data.keys()), key="alert_crop")
        target_price = st.number_input("Target Price ($/kg)", min_value=1.0, step=0.1)
        alert_type = st.selectbox("Alert Type", ["Price Drop Below", "Price Rise Above"])
    
    with col2:
        st.write("### Current Alerts")
        st.info("No active price alerts set")
        
    if st.button("🔔 Set Price Alert"):
        st.success(f"Alert set for {alert_crop} when price {alert_type.lower()} ${target_price}")

def show_weather():
    """Display weather information"""
    st.markdown('<h1 class="main-header">🌤️ Weather Information</h1>', unsafe_allow_html=True)
    
    # Location input
    col1, col2 = st.columns(2)
    with col1:
        latitude = st.number_input("🌐 Latitude", value=28.6139, format="%.4f")
    with col2:
        longitude = st.number_input("🌐 Longitude", value=77.2090, format="%.4f")
    
    if st.button("🔍 Get Weather Data"):
        weather_data = get_weather_data(latitude, longitude)
        
        if weather_data:
            # Current weather
            st.subheader("🌡️ Current Weather")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Temperature", f"{weather_data['main']['temp']:.1f}°C", 
                         f"Feels like {weather_data['main']['feels_like']:.1f}°C")
            
            with col2:
                st.metric("Humidity", f"{weather_data['main']['humidity']}%")
            
            with col3:
                st.metric("Pressure", f"{weather_data['main']['pressure']} hPa")
            
            with col4:
                st.metric("Wind Speed", f"{weather_data['wind']['speed']} m/s")
            
            # Weather description
            st.markdown(f"""
            <div class="success-box">
                <h4>☁️ {weather_data['weather'][0]['description'].title()}</h4>
                <p>Location: {weather_data['name']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Agricultural recommendations based on weather
            st.subheader("🌾 Agricultural Recommendations")
            
            temp = weather_data['main']['temp']
            humidity = weather_data['main']['humidity']
            
            recommendations = []
            
            if temp > 35:
                recommendations.append("🔥 High temperature alert! Ensure adequate irrigation.")
            elif temp < 10:
                recommendations.append("🥶 Low temperature warning! Protect crops from frost.")
            
            if humidity > 80:
                recommendations.append("💧 High humidity detected! Monitor for fungal diseases.")
            elif humidity < 30:
                recommendations.append("🏜️ Low humidity! Increase irrigation frequency.")
            
            if weather_data.get('rain'):
                recommendations.append("🌧️ Rain expected! Good for crop growth but monitor for waterlogging.")
            
            if not recommendations:
                recommendations.append("✅ Weather conditions are favorable for farming!")
            
            for rec in recommendations:
                st.info(rec)
        
        else:
            st.error("Unable to fetch weather data. Please check your coordinates or try again later.")
    
    # 7-day forecast (mock data)
    st.subheader("📅 7-Day Forecast")
    
    forecast_data = []
    for i in range(7):
        date = datetime.now() + timedelta(days=i)
        temp_high = 25 + np.random.randint(-5, 10)
        temp_low = temp_high - np.random.randint(5, 15)
        humidity = 50 + np.random.randint(-20, 30)
        
        forecast_data.append({
            'Date': date.strftime('%Y-%m-%d'),
            'Day': date.strftime('%A'),
            'High (°C)': temp_high,
            'Low (°C)': temp_low,
            'Humidity (%)': humidity,
            'Condition': np.random.choice(['Sunny', 'Cloudy', 'Rainy', 'Partly Cloudy'])
        })
    
    forecast_df = pd.DataFrame(forecast_data)
    st.dataframe(forecast_df, use_container_width=True)

def show_crop_recommendation():
    """Display crop recommendation system"""
    st.markdown('<h1 class="main-header">🌱 Crop Recommendation</h1>', unsafe_allow_html=True)
    
    st.info("Get personalized crop recommendations based on soil and climate conditions")
    
    with st.form("crop_recommendation_form"):
        st.subheader("🧪 Soil Parameters")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            nitrogen = st.number_input("Nitrogen (N)", min_value=0, max_value=200, value=50)
            phosphorus = st.number_input("Phosphorus (P)", min_value=0, max_value=200, value=50)
        
        with col2:
            potassium = st.number_input("Potassium (K)", min_value=0, max_value=200, value=50)
            ph = st.number_input("pH Level", min_value=0.0, max_value=14.0, value=7.0, step=0.1)
        
        with col3:
            temperature = st.number_input("Temperature (°C)", min_value=-10, max_value=50, value=25)
            humidity = st.number_input("Humidity (%)", min_value=0, max_value=100, value=60)
            rainfall = st.number_input("Rainfall (mm)", min_value=0, max_value=500, value=100)
        
        submitted = st.form_submit_button("🔍 Get Recommendation")
        
        if submitted:
            # Get crop prediction
            recommended_crop = predict_crop(nitrogen, phosphorus, potassium, temperature, humidity, ph, rainfall)
            
            st.success(f"### Recommended Crop: {recommended_crop}")
            
            # Display reasoning
            st.subheader("📋 Analysis Summary")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Soil Composition:**")
                st.write(f"- Nitrogen: {nitrogen} kg/ha")
                st.write(f"- Phosphorus: {phosphorus} kg/ha") 
                st.write(f"- Potassium: {potassium} kg/ha")
                st.write(f"- pH Level: {ph}")
            
            with col2:
                st.markdown("**Climate Conditions:**")
                st.write(f"- Temperature: {temperature}°C")
                st.write(f"- Humidity: {humidity}%")
                st.write(f"- Rainfall: {rainfall}mm")
            
            # Crop details
            crop_info = {
                'Rice': {
                    'season': 'Kharif (June-November)',
                    'water_req': 'High (1200-1800mm)',
                    'soil_type': 'Clay loam, well-drained',
                    'tips': 'Ensure proper water management and pest control'
                },
                'Wheat': {
                    'season': 'Rabi (November-April)', 
                    'water_req': 'Moderate (400-600mm)',
                    'soil_type': 'Well-drained loamy soil',
                    'tips': 'Plant after monsoon, ensure proper fertilization'
                },
                'Cotton': {
                    'season': 'Kharif (April-December)',
                    'water_req': 'Moderate (500-800mm)', 
                    'soil_type': 'Deep, well-drained black soil',
                    'tips': 'Monitor for bollworm attacks, proper spacing'
                },
                'Maize': {
                    'season': 'Kharif & Rabi',
                    'water_req': 'Moderate (500-800mm)',
                    'soil_type': 'Well-drained fertile soil',
                    'tips': 'Ensure proper seed spacing and weed control'
                },
                'Sugarcane': {
                    'season': 'Year-round',
                    'water_req': 'High (1500-2500mm)',
                    'soil_type': 'Deep, fertile, well-drained soil',
                    'tips': 'Requires consistent water supply and fertilization'
                }
            }
            
            if recommended_crop in crop_info:
                info = crop_info[recommended_crop]
                
                st.subheader(f"🌾 {recommended_crop} Cultivation Guide")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    **🗓️ Growing Season:** {info['season']}
                    
                    **💧 Water Requirement:** {info['water_req']}
                    """)
                
                with col2:
                    st.markdown(f"""
                    **🌱 Soil Type:** {info['soil_type']}
                    
                    **💡 Tips:** {info['tips']}
                    """)
            
            # Alternative crops
            st.subheader("🔄 Alternative Recommendations")
            alternatives = ['Rice', 'Wheat', 'Cotton', 'Maize', 'Barley', 'Potato']
            alternatives = [crop for crop in alternatives if crop != recommended_crop][:3]
            
            cols = st.columns(3)
            for i, alt_crop in enumerate(alternatives):
                with cols[i]:
                    st.markdown(f"""
                    <div style="background: #f0f8f0; padding: 1rem; border-radius: 10px; text-align: center;">
                        <h4>{alt_crop}</h4>
                        <p>Suitability: {np.random.randint(70, 90)}%</p>
                    </div>
                    """, unsafe_allow_html=True)

def show_fertilizer_recommendation():
    """Display fertilizer recommendation system"""
    st.markdown('<h1 class="main-header">🧪 Fertilizer Recommendation</h1>', unsafe_allow_html=True)
    
    st.info("Get optimal fertilizer recommendations for your crops")
    
    with st.form("fertilizer_recommendation_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🌾 Crop Information")
            crop_type = st.selectbox("Select Crop", 
                                   [ 'Wheat', 'Cotton', 'Maize', 'Sugarcane'])
            crop_stage = st.selectbox("Growth Stage", 
                                    ['Seedling', 'Vegetative', 'Flowering', 'Fruiting', 'Maturity'])
            area = st.number_input("Area (acres)", min_value=0.1, value=1.0, step=0.1)
        
        with col2:
            st.subheader("🧪 Soil Analysis")
            soil_n = st.number_input("Soil Nitrogen (kg/ha)", min_value=0, max_value=200, value=40)
            soil_p = st.number_input("Soil Phosphorus (kg/ha)", min_value=0, max_value=200, value=30)
            soil_k = st.number_input("Soil Potassium (kg/ha)", min_value=0, max_value=200, value=25)
            soil_ph = st.number_input("Soil pH", min_value=0.0, max_value=14.0, value=6.5, step=0.1)
            soil_type = st.selectbox("Soil Type", ['Loamy', 'Sandy', 'Clayey'])  # Update with actual types
            moisture = st.number_input("Soil Moisture (%)", min_value=0, max_value=100, value=40)
            temperature = st.number_input("Fertilizer Temperature (°C)", min_value=-10, max_value=50, value=26)
            humidity = st.number_input("Fertilizer Humidity (%)", min_value=0, max_value=100, value=52)

        submitted = st.form_submit_button("🔬 Get Fertilizer Recommendation")
        
        if submitted:
            # Get fertilizer prediction
            recommended_fertilizer = predict_fertilizer(soil_n, soil_p, soil_k, crop_type, soil_type, temperature, humidity, moisture)
            st.info(f"💡 Recommended Fertilizer: **{recommended_fertilizer}**")
            
            # Calculate nutrient requirements
            nutrient_requirements = {
                'Rice': {'N': 120, 'P': 60, 'K': 40},
                'Wheat': {'N': 120, 'P': 60, 'K': 40},
                'Cotton': {'N': 150, 'P': 75, 'K': 75},
                'Maize': {'N': 120, 'P': 60, 'K': 40},
                'Sugarcane': {'N': 200, 'P': 80, 'K': 60}
            }
            
            if crop_type in nutrient_requirements:
                req = nutrient_requirements[crop_type]
                
                # Calculate deficiency
                n_needed = max(0, req['N'] - soil_n)
                p_needed = max(0, req['P'] - soil_p) 
                k_needed = max(0, req['K'] - soil_k)
                
                st.subheader("📊 Nutrient Analysis")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Nitrogen Needed", f"{n_needed} kg/ha", 
                             f"{req['N'] - soil_n:+d} from current")
                
                with col2:
                    st.metric("Phosphorus Needed", f"{p_needed} kg/ha",
                             f"{req['P'] - soil_p:+d} from current")
                
                with col3:
                    st.metric("Potassium Needed", f"{k_needed} kg/ha",
                             f"{req['K'] - soil_k:+d} from current")
                
                # Fertilizer application schedule
                st.subheader("📅 Application Schedule")
                
                schedule_data = []
                if crop_stage == 'Seedling':
                    schedule_data = [
                        {'Stage': 'Basal (Before Planting)', 'Fertilizer': 'DAP + MOP', 'Quantity': '50% of total P & K'},
                        {'Stage': '15 Days After Planting', 'Fertilizer': 'Urea', 'Quantity': '25% of total N'},
                        {'Stage': '30 Days After Planting', 'Fertilizer': 'Urea', 'Quantity': '25% of total N'}
                    ]
                else:
                    schedule_data = [
                        {'Stage': 'Current Stage', 'Fertilizer': recommended_fertilizer, 'Quantity': f'{n_needed + p_needed + k_needed} kg/ha total'},
                        {'Stage': 'Next Application (15 days)', 'Fertilizer': 'Follow-up dose', 'Quantity': 'As per crop response'}
                    ]
                
                schedule_df = pd.DataFrame(schedule_data)
                st.dataframe(schedule_df, use_container_width=True)
                
                # Cost estimation
                st.subheader("💰 Cost Estimation")
                
                fertilizer_prices = {
                    'Urea': 6.5,  # per kg
                    'DAP': 27.0,
                    'MOP': 17.0,
                    'NPK': 20.0
                }
                
                estimated_cost = (n_needed * 2.2 * fertilizer_prices['Urea'] + 
                                p_needed * 2.2 * fertilizer_prices['DAP'] + 
                                k_needed * 1.7 * fertilizer_prices['MOP']) * area
                
                st.info(f"**Estimated Cost:** ${estimated_cost:.2f} for {area} acres")
                
                # Additional recommendations
                st.subheader("💡 Additional Recommendations")
                
                recommendations = []
                
                if soil_ph < 6.0:
                    recommendations.append("🟡 Soil is acidic. Consider applying lime to increase pH.")
                elif soil_ph > 8.0:
                    recommendations.append("🟡 Soil is alkaline. Consider applying gypsum to reduce pH.")
                
                if crop_stage == 'Flowering':
                    recommendations.append("🌸 During flowering stage, ensure adequate phosphorus for fruit development.")
                
                recommendations.append("🔄 Apply fertilizers in split doses for better nutrient uptake.")
                recommendations.append("💧 Ensure adequate moisture for nutrient absorption.")
                
                for rec in recommendations:
                    st.info(rec)

def show_orders():
    """Display order management"""
    st.markdown('<h1 class="main-header">📦 Order Management</h1>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📥 My Purchases", "📤 My Sales"])
    
    with tab1:
        st.subheader("Your Purchase Orders")
        
        conn = sqlite3.connect(DB_PATH)
        purchase_orders = pd.read_sql_query("""
            SELECT o.*, c.name as crop_name, c.price, u.name as seller_name, u.phone as seller_phone
            FROM orders o
            JOIN crops c ON o.crop_id = c.id  
            JOIN users u ON o.seller_id = u.id
            WHERE o.buyer_id = ?
            ORDER BY o.order_date DESC
        """, conn, params=[st.session_state.user_id])
        conn.close()
        
        if not purchase_orders.empty:
            for _, order in purchase_orders.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.write(f"**{order['crop_name']}**")
                        st.write(f"Seller: {order['seller_name']}")
                        st.write(f"Quantity: {order['quantity']} units")
                        st.write(f"Total: ${order['total_price']}")
                    
                    with col2:
                        status_color = {
                            'pending': '🟡',
                            'confirmed': '🟢', 
                            'delivered': '✅',
                            'cancelled': '🔴'
                        }
                        st.write(f"Status: {status_color.get(order['status'], '⚪')} {order['status'].title()}")
                        st.write(f"Date: {order['order_date'][:10]}")
                    
                    with col3:
                        if order['status'] == 'pending':
                            if st.button(f"❌ Cancel", key=f"cancel_purchase_{order['id']}"):
                                conn = sqlite3.connect(DB_PATH)
                                cursor = conn.cursor()
                                cursor.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order['id'],))
                                # Return quantity to crop
                                cursor.execute("UPDATE crops SET quantity = quantity + ? WHERE id = ?", 
                                             (order['quantity'], order['crop_id']))
                                conn.commit()
                                conn.close()
                                st.success("Order cancelled successfully!")
                                st.rerun()
                        
                        if order['status'] == 'confirmed':
                            st.write(f"📞 Contact: {order['seller_phone']}")
                    
                    st.markdown("---")
        else:
            st.info("No purchase orders found")
    
    with tab2:
        st.subheader("Your Sales Orders")
        
        conn = sqlite3.connect(DB_PATH)
        sales_orders = pd.read_sql_query("""
            SELECT o.*, c.name as crop_name, c.price, u.name as buyer_name, u.phone as buyer_phone
            FROM orders o
            JOIN crops c ON o.crop_id = c.id
            JOIN users u ON o.buyer_id = u.id  
            WHERE o.seller_id = ?
            ORDER BY o.order_date DESC
        """, conn, params=[st.session_state.user_id])
        conn.close()
        
        if not sales_orders.empty:
            for _, order in sales_orders.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.write(f"**{order['crop_name']}**")
                        st.write(f"Buyer: {order['buyer_name']}")
                        st.write(f"Contact: {order['buyer_phone']}")
                        st.write(f"Quantity: {order['quantity']} units")
                        st.write(f"Total: ${order['total_price']}")
                    
                    with col2:
                        status_color = {
                            'pending': '🟡',
                            'confirmed': '🟢',
                            'delivered': '✅', 
                            'cancelled': '🔴'
                        }
                        st.write(f"Status: {status_color.get(order['status'], '⚪')} {order['status'].title()}")
                        st.write(f"Date: {order['order_date'][:10]}")
                    
                    with col3:
                        if order['status'] == 'pending':
                            col_confirm, col_reject = st.columns(2)
                            with col_confirm:
                                if st.button("✅", key=f"confirm_sale_{order['id']}", help="Confirm Order"):
                                    conn = sqlite3.connect(DB_PATH)
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE orders SET status = 'confirmed' WHERE id = ?", (order['id'],))
                                    conn.commit()
                                    conn.close()
                                    st.success("Order confirmed!")
                                    st.rerun()
                            
                            with col_reject:
                                if st.button("❌", key=f"reject_sale_{order['id']}", help="Reject Order"):
                                    conn = sqlite3.connect(DB_PATH)
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order['id'],))
                                    # Return quantity to crop
                                    cursor.execute("UPDATE crops SET quantity = quantity + ? WHERE id = ?", 
                                                 (order['quantity'], order['crop_id']))
                                    conn.commit()
                                    conn.close()
                                    st.success("Order rejected!")
                                    st.rerun()
                        
                        elif order['status'] == 'confirmed':
                            if st.button("📦 Mark Delivered", key=f"deliver_{order['id']}"):
                                conn = sqlite3.connect(DB_PATH)
                                cursor = conn.cursor() 
                                cursor.execute("UPDATE orders SET status = 'delivered' WHERE id = ?", (order['id'],))
                                conn.commit()
                                conn.close()
                                st.success("Order marked as delivered!")
                                st.rerun()
                    
                    st.markdown("---")
        else:
            st.info("No sales orders found")

def show_profile():
    """Display user profile management"""
    st.markdown('<h1 class="main-header">👤 User Profile</h1>', unsafe_allow_html=True)
    
    # Get user data
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (st.session_state.user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 Profile Information")
            
            with st.form("profile_form"):
                name = st.text_input("Full Name", value=user[1])
                phone = st.text_input("Phone Number", value=user[2], disabled=True)
                email = st.text_input("Email", value=user[3] or "")
                location = st.text_input("Location", value=user[4] or "")
                
                if st.form_submit_button("💾 Update Profile"):
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE users SET name = ?, email = ?, location = ? WHERE id = ?
                    """, (name, email, location, st.session_state.user_id))
                    conn.commit()
                    conn.close()
                    
                    st.session_state.user_name = name
                    st.success("Profile updated successfully!")
                    st.rerun()
        
        with col2:
            st.subheader("📊 Account Statistics")
            
            # Get user statistics
            conn = sqlite3.connect(DB_PATH)
            
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM crops WHERE user_id = ?", (st.session_state.user_id,))
            total_listings = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM orders WHERE buyer_id = ?", (st.session_state.user_id,))
            total_purchases = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM orders WHERE seller_id = ?", (st.session_state.user_id,))
            total_sales = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(total_price) FROM orders WHERE seller_id = ? AND status = 'delivered'", (st.session_state.user_id,))
            total_earnings = cursor.fetchone()[0] or 0
            
            conn.close()
            
            st.metric("🌾 Total Crop Listings", total_listings)
            st.metric("🛒 Total Purchases", total_purchases)
            st.metric("📦 Total Sales", total_sales)
            st.metric("💰 Total Earnings", f"${total_earnings}")
            
            st.markdown("---")
            
            # Account actions
            st.subheader("⚙️ Account Actions")
            
            if st.button("📊 Download My Data", use_container_width=True):
                st.info("Data export functionality would be implemented here")
            
            if st.button("🗑️ Delete Account", use_container_width=True, type="secondary"):
                st.warning("This action cannot be undone!")
                if st.button("⚠️ Confirm Delete", type="secondary"):
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    
                    # Delete user data
                    cursor.execute("DELETE FROM orders WHERE buyer_id = ? OR seller_id = ?", 
                                 (st.session_state.user_id, st.session_state.user_id))
                    cursor.execute("DELETE FROM crops WHERE user_id = ?", (st.session_state.user_id,))
                    cursor.execute("DELETE FROM users WHERE id = ?", (st.session_state.user_id,))
                    
                    conn.commit()
                    conn.close()
                    
                    # Logout
                    st.session_state.logged_in = False
                    st.session_state.user_id = None
                    st.session_state.user_name = None
                    
                    st.success("Account deleted successfully!")
                    st.rerun()

# Run the application
if __name__ == "__main__":
    main()