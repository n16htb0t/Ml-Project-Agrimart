import sqlite3
import random
from datetime import datetime, timedelta

def setup_sample_data():
    """Setup sample data for demonstration"""
    
    # Connect to database
    conn = sqlite3.connect('smart_agriculture.db')
    cursor = conn.cursor()
    
    # Create tables (same as in main app)
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
    
    # Sample users
    sample_users = [
        ('Rajesh Kumar', '9876543210', 'rajesh@email.com', 'Delhi'),
        ('Priya Sharma', '9876543211', 'priya@email.com', 'Mumbai'),
        ('Arjun Singh', '9876543212', 'arjun@email.com', 'Bangalore'),
        ('Meera Patel', '9876543213', 'meera@email.com', 'Ahmedabad'),
        ('Vikram Reddy', '9876543214', 'vikram@email.com', 'Hyderabad'),
    ]
    
    for user in sample_users:
        try:
            cursor.execute("INSERT INTO users (name, phone, email, location) VALUES (?, ?, ?, ?)", user)
        except sqlite3.IntegrityError:
            pass  # User already exists
    
    # Sample crops
    crop_names = ['Rice', 'Wheat', 'Cotton', 'Maize', 'Sugarcane', 'Potato', 'Tomato', 'Onion', 'Barley', 'Soybean']
    categories = ['Grains', 'Vegetables', 'Fruits', 'Pulses', 'Spices']
    units = ['kg', 'quintal', 'ton']
    
    for i in range(20):
        crop_name = random.choice(crop_names)
        category = random.choice(categories)
        price = round(random.uniform(10, 100), 2)
        quantity = random.randint(10, 1000)
        unit = random.choice(units)
        user_id = random.randint(1, 5)
        harvest_date = datetime.now() + timedelta(days=random.randint(-30, 60))
        description = f"Fresh {crop_name.lower()} from organic farming"
        
        try:
            cursor.execute("""
                INSERT INTO crops (name, description, price, quantity, unit, user_id, category, harvest_date)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (crop_name, description, price, quantity, unit, user_id, category, harvest_date.date()))
        except sqlite3.IntegrityError:
            pass

    # Sample orders
    for _ in range(15):
        crop_id = random.randint(1, 20)
        buyer_id = random.randint(1, 5)
        seller_id = random.randint(1, 5)
        while buyer_id == seller_id:
            seller_id = random.randint(1, 5)
        quantity = random.randint(1, 100)
        
        # Fetch crop price
        cursor.execute("SELECT price FROM crops WHERE id = ?", (crop_id,))
        result = cursor.fetchone()
        if result:
            price = result[0]
            total_price = round(price * quantity, 2)
            status = random.choice(['pending', 'shipped', 'delivered', 'cancelled'])
            
            try:
                cursor.execute("""
                    INSERT INTO orders (crop_id, buyer_id, seller_id, quantity, total_price, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (crop_id, buyer_id, seller_id, quantity, total_price, status))
            except sqlite3.IntegrityError:
                pass

    # Sample price history
    markets = ['Delhi Mandi', 'Mumbai Market', 'Chennai Yard', 'Kolkata Bazaar']
    for _ in range(30):
        crop_name = random.choice(crop_names)
        price = round(random.uniform(10, 150), 2)
        market = random.choice(markets)
        date = datetime.now().date() - timedelta(days=random.randint(0, 60))
        
        try:
            cursor.execute("""
                INSERT INTO price_history (crop_name, price, market, date)
                VALUES (?, ?, ?, ?)
            """, (crop_name, price, market, date))
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()

# Run setup
if __name__ == "__main__":
    setup_sample_data()
