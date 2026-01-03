import sqlite3
import os
from pathlib import Path

# SQLite database path
DB_DIR = Path(__file__).parent
DB_NAME = os.environ.get('SQLITE_DATABASE', 'unicounsel_db.sqlite')
DB_PATH = DB_DIR / DB_NAME

def get_db_connection():
    """Get SQLite database connection with CSV fallback support"""
    try:
        # Ensure directory exists
        DB_DIR.mkdir(parents=True, exist_ok=True)
        
        connection = sqlite3.connect(str(DB_PATH))
        connection.row_factory = sqlite3.Row  # Enable dictionary-like access
        return connection
    except Exception as e:
        print(f"Error while connecting to SQLite: {e}")
        print("Will fallback to CSV data when needed")
        return None

def get_db_connection_safe():
    """Get database connection or use CSV fallback"""
    conn = get_db_connection()
    if conn is None:
        print("Database unavailable - using CSV fallback")
    return conn

def create_database():
    """Create the database file if it doesn't exist"""
    try:
        DB_DIR.mkdir(parents=True, exist_ok=True)
        # SQLite creates the file automatically on first connection
        conn = get_db_connection()
        if conn:
            conn.close()
            print(f"Database '{DB_PATH}' created or already exists")
    except Exception as e:
        print(f"Error creating database: {e}")
        raise

def create_tables():
    """Create all required tables"""
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to database. Cannot create tables.")
        print("Please check database file permissions.")
        return
    
    cursor = connection.cursor()
    
    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email VARCHAR(255) UNIQUE NOT NULL,
        username VARCHAR(100),
        password_hash VARCHAR(255),
        first_name VARCHAR(100),
        last_name VARCHAR(100),
        is_oauth_user BOOLEAN DEFAULT 0,
        oauth_provider VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Universities table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS universities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        university_id VARCHAR(50),
        university_name VARCHAR(255),
        official_website VARCHAR(500),
        email_inquiry VARCHAR(255),
        phone_number VARCHAR(50),
        address TEXT,
        country VARCHAR(100),
        state VARCHAR(100),
        city VARCHAR(100),
        zip_code VARCHAR(20),
        latitude REAL,
        longitude REAL,
        campus_type VARCHAR(50),
        established VARCHAR(20),
        duration_undergraduation_course VARCHAR(50),
        duration_postgraduation_course VARCHAR(50),
        duration_phd_course VARCHAR(50),
        duration_diploma_course VARCHAR(50),
        duration_online_course VARCHAR(50),
        admission_req TEXT,
        cgpa VARCHAR(20),
        ielts VARCHAR(20),
        sat_gre_gmat VARCHAR(50),
        deadline_sem1 VARCHAR(100),
        academic_calendar VARCHAR(50),
        medium VARCHAR(50),
        tuition_fee_annual VARCHAR(50),
        living_cost_annual VARCHAR(50),
        total_estimated_cost VARCHAR(50),
        scholarships TEXT,
        intl_services TEXT,
        accommodation TEXT,
        airport_pickup VARCHAR(20),
        pre_arrival TEXT,
        documents_required TEXT,
        image_url VARCHAR(500),
        program_level VARCHAR(50),
        course TEXT
    )
    ''')
    
    # Create indexes
    try:
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_country ON universities(country)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_city ON universities(city)')
    except Exception as e:
        print(f'Index creation warning: {e}')
    
    # Onboarding responses table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS onboarding_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_1_preferred_countries TEXT,
        question_2_study_level VARCHAR(100),
        question_3_preferred_stream VARCHAR(255),
        question_4_duration_years INTEGER,
        question_5_budget_min REAL,
        question_5_budget_max REAL,
        question_6_important_factors TEXT,
        question_7_admission_readiness VARCHAR(100),
        question_8_language_proficiency VARCHAR(100),
        question_9_campus_life VARCHAR(100),
        question_10_special_interests TEXT,
        question_11_scholarship_need BOOLEAN,
        question_12_start_date VARCHAR(50),
        completed BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    # University matches table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS university_matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        university_id INTEGER NOT NULL,
        match_score REAL,
        match_reason TEXT,
        is_favorite BOOLEAN DEFAULT 0,
        is_shortlisted BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (university_id) REFERENCES universities(id) ON DELETE CASCADE,
        UNIQUE(user_id, university_id)
    )
    ''')
    
    # User preferences table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        filter_countries TEXT,
        filter_budget_min REAL,
        filter_budget_max REAL,
        filter_study_level VARCHAR(100),
        filter_accommodation_type VARCHAR(100),
        filter_scholarship_required BOOLEAN,
        sort_by VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    # User favorites table - stores favorite universities
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        university_id_str VARCHAR(100) NOT NULL,
        university_name VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(user_id, university_id_str)
    )
    ''')
    
    # Fee comparisons table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fee_comparisons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        university_ids TEXT NOT NULL,
        comparison_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    # Visa assessments table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS visa_assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        country VARCHAR(100),
        visa_type VARCHAR(100),
        probability_score REAL,
        assessment_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    # Resume templates table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS resume_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_name VARCHAR(255) NOT NULL,
        template_description TEXT,
        template_html TEXT,
        template_css TEXT,
        preview_image VARCHAR(500),
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # User resumes table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_resumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        template_id INTEGER,
        resume_data TEXT NOT NULL,
        resume_title VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (template_id) REFERENCES resume_templates(id)
    )
    ''')
    
    # User documents table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        document_type VARCHAR(100),
        document_name VARCHAR(255),
        file_path VARCHAR(500),
        file_size INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    # Interview responses table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS interview_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_id INTEGER,
        response_text TEXT,
        score INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    connection.commit()
    cursor.close()
    connection.close()
    print("All tables created successfully")
