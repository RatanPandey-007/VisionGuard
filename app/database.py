import sqlite3
import os
from datetime import datetime, timedelta
import random

# Detect if running in Vercel serverless environment
IS_VERCEL = "VERCEL" in os.environ

if IS_VERCEL:
    DB_PATH = "/tmp/database.sqlite"
else:
    DB_PATH = os.path.join("data", "database.sqlite")

def init_db():
    """Initializes the SQLite database and creates the schema if it doesn't exist."""
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create inspections table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            product_id TEXT NOT NULL,
            result TEXT NOT NULL,          -- 'PASS' or 'FAIL'
            defect_type TEXT,             -- NULL, 'Missing Component', 'Component Misalignment', 'Solder Defect', 'Surface Anomaly'
            confidence REAL NOT NULL,      -- Percentage e.g. 96.4
            image_path TEXT NOT NULL,      -- Path to the saved inspection image
            model_version TEXT NOT NULL    -- Version of YOLO/detector used
        )
    """)
    conn.commit()
    conn.close()
    
    # Check if table is empty; if so, populate with mock history to make it look professional
    if is_db_empty():
        populate_mock_history()

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def is_db_empty() -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM inspections")
    count = cursor.fetchone()[0]
    conn.close()
    return count == 0

def log_inspection(product_id: str, result: str, defect_type: str | None, confidence: float, image_path: str, model_version: str = "YOLOv8n-PCB-v1.0") -> int:
    """Inserts a new inspection record into the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        INSERT INTO inspections (timestamp, product_id, result, defect_type, confidence, image_path, model_version)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, product_id, result, defect_type, confidence, image_path, model_version))
    
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def get_analytics_summary() -> dict:
    """Calculates summary statistics for the dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total inputs
    cursor.execute("SELECT COUNT(*) FROM inspections")
    total = cursor.fetchone()[0]
    
    if total == 0:
        conn.close()
        return {
            "total": 0, "passed": 0, "failed": 0, 
            "pass_rate": 100.0, "defect_rate": 0.0, 
            "defect_distribution": {}
        }
        
    # Passed
    cursor.execute("SELECT COUNT(*) FROM inspections WHERE result = 'PASS'")
    passed = cursor.fetchone()[0]
    
    # Failed
    failed = total - passed
    pass_rate = round((passed / total) * 100, 2)
    defect_rate = round((failed / total) * 100, 2)
    
    # Defect distribution
    cursor.execute("""
        SELECT defect_type, COUNT(*) 
        FROM inspections 
        WHERE result = 'FAIL' 
        GROUP BY defect_type
    """)
    defect_distribution = {}
    for defect, count in cursor.fetchall():
        if defect:
            defect_distribution[defect] = count
            
    conn.close()
    
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "defect_rate": defect_rate,
        "defect_distribution": defect_distribution
    }

def get_recent_inspections(limit: int = 50) -> list[dict]:
    """Retrieves recent inspections sorted by timestamp descending."""
    conn = get_db_connection()
    # Configure row factory to return dicts instead of tuples
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, timestamp, product_id, result, defect_type, confidence, image_path, model_version 
        FROM inspections 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def populate_mock_history():
    """Populates database with realistic mock data representing 5 days of factory runs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now()
    defects = [
        "Missing Component", 
        "Component Misalignment", 
        "Solder Defect", 
        "Surface Anomaly"
    ]
    
    # Generate 120 inspection records spread over the past 5 days
    records = []
    for i in range(120):
        # Evenly spread timestamps
        time_offset = timedelta(
            days=random.randint(0, 4),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        timestamp = (now - time_offset).strftime("%Y-%m-%d %H:%M:%S")
        
        # Product ID pattern "PCB-XXXX" where XXXX is index
        product_id = f"PCB-{1000 + i}"
        
        # 88% Pass Rate, 12% Defect Rate
        is_pass = random.random() > 0.12
        if is_pass:
            result = "PASS"
            defect_type = None
            confidence = round(random.uniform(92.0, 99.5), 1)
        else:
            result = "FAIL"
            defect_type = random.choice(defects)
            confidence = round(random.uniform(85.0, 97.0), 1)
            
        # Placeholders for paths (could represent mock saved files)
        image_path = f"data/inspections/mock_{product_id}.jpg"
        model_version = "YOLOv8n-PCB-v1.0"
        
        records.append((timestamp, product_id, result, defect_type, confidence, image_path, model_version))
    
    # Sort records by timestamp before writing so DB feels chronologically ordered
    records.sort(key=lambda x: x[0])
    
    cursor.executemany("""
        INSERT INTO inspections (timestamp, product_id, result, defect_type, confidence, image_path, model_version)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, records)
    
    conn.commit()
    conn.close()
    print("Database pre-populated with 120 mock factory quality events.")

if __name__ == "__main__":
    init_db()
    print("DB initialized at:", DB_PATH)
    print("Summarized Stats:", get_analytics_summary())
