# Import compatibility patch for Python 3.14+
try:
    import flask_compat_patch
except Exception as e:
    print(f"Warning: Could not import flask_compat_patch: {e}")
    pass

from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
import os
import json
import hashlib
import re
import secrets
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from authlib.integrations.flask_client import OAuth
from db_config import get_db_connection, create_database, create_tables
from csv_data_service import csv_service

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Session configuration to prevent data leakage
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Google OAuth configuration
app.config['GOOGLE_CLIENT_ID'] = '1073684776924-jne5g1aprbrdb4qqc9mj3lhjqalcndd9.apps.googleusercontent.com'
app.config['GOOGLE_CLIENT_SECRET'] = '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'

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Initialize database on startup
with app.app_context():
    try:
        print("Attempting to connect to database...")
        create_database()
        create_tables()
        # Check if universities exist, if not try loading them
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM universities")
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            print(f"Database initialized with {count} universities")
        else:
            print("Warning: Could not connect to database. Using CSV fallback.")
    except Exception as e:
        print(f"Warning: Error initializing database: {e}")
        print("App will use CSV fallback for data operations.")

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hash):
    """Verify password against hash"""
    return hash_password(password) == hash

# Add response headers to prevent caching of user-specific pages
@app.after_request
def add_no_cache_headers(response):
    """Add headers to prevent caching of sensitive pages"""
    if request.endpoint and request.endpoint in ['dashboard', 'profile', 'perfect_matches', 'favorites']:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_user_by_id(user_id):
    """Fetch user from database"""
    conn = get_db_connection()
    if not conn:
        return None
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        return dict(row)
    return None

def get_onboarding_answers(user_id):
    """Get user's onboarding answers"""
    conn = get_db_connection()
    if not conn:
        return None
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM onboarding_responses WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        result = dict(row)
        # Ensure completed is properly converted to int for consistent checking
        if 'completed' in result:
            # Convert to int: 1 for completed, 0 for not completed
            result['completed'] = 1 if result['completed'] else 0
        else:
            result['completed'] = 0
        return result
    return None

def parse_cost_str(cost_str):
    """Parse a cost string like 'AUD $40000-60000' into a float (average of range)."""
    if not cost_str:
        return None
    try:
        s = str(cost_str).strip()
        
        # Check for N/A or similar
        if s.upper() in ['N/A', 'NA', 'TBD', 'TBA', 'VARIES', '-', '']:
            return None
        
        # If there are semicolons, take the first value (e.g., "$1800 (UG); $1200 (PG)")
        if ';' in s:
            s = s.split(';')[0].strip()
        
        # Remove common tokens and symbols
        s = s.replace('~', '').replace('≈', '')  # Handle approximate symbols
        
        # Remove text in parentheses like "(International UG)"
        import re
        s = re.sub(r'\([^)]*\)', '', s)
        
        # Remove currency symbols and separators (but keep spaces for now to handle "35000 - 55000")
        for token in ['$', 'AUD', 'USD', 'EUR', 'ETB', 'Birr', ',']:
            s = s.replace(token, '')
        
        s = s.strip()
        
        # Handle ranges like "8500-12000" or "35000 - 55000" (with or without spaces)
        if '-' in s:
            # Split and strip spaces from each part
            parts = [p.strip() for p in s.split('-')]
            if len(parts) == 2 and parts[0] and parts[1]:
                try:
                    val1 = float(parts[0])
                    val2 = float(parts[1])
                    return (val1 + val2) / 2.0
                except:
                    pass
        
        # Remove any remaining spaces
        s = s.replace(' ', '')
        
        # Try to parse as a number
        return float(s) if s else None
    except Exception:
        return None

# ============ Authentication Routes ============

@app.route('/')
def index():
    if 'user_id' in session:
        # Check if onboarding is completed
        user_id = session['user_id']
        answers = get_onboarding_answers(user_id)
        if answers:
            completed = answers.get('completed')
            if completed == 1 or completed is True or str(completed) == '1':
                return redirect(url_for('dashboard'))
        return redirect(url_for('check_onboarding'))
    return redirect(url_for('landing'))

@app.route('/landing')
def landing():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('login.html')
        
        conn = get_db_connection()
        if not conn:
            flash('Database connection error', 'error')
            return render_template('login.html')
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            user = dict(row)
            if verify_password(password, user['password_hash']):
                # Clear any existing session data first
                session.clear()
                # Set new session data
                session['user_id'] = user['id']
                session['email'] = user['email']
                session['username'] = user['username']
                flash('Login successful!', 'success')
                # Check if onboarding is already completed
                answers = get_onboarding_answers(user['id'])
                if answers and answers.get('completed') == 1:
                    # User has completed onboarding, go to dashboard
                    return redirect(url_for('dashboard'))
                # User hasn't completed onboarding yet
                return redirect(url_for('check_onboarding'))
        
        flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        username = request.form.get('username', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        
        # Validation
        if not all([email, password, confirm_password, username]):
            flash('All fields are required', 'error')
            return render_template('signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('signup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('signup.html')
        
        conn = get_db_connection()
        if not conn:
            flash('Database connection error', 'error')
            return render_template('signup.html')
        
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            flash('Email already registered', 'error')
            cursor.close()
            conn.close()
            return render_template('signup.html')
        
        try:
            cursor.execute('''
                INSERT INTO users (email, username, password_hash, first_name, last_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (email, username, hash_password(password), first_name, last_name))
            conn.commit()
            
            # Get the new user's ID
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            user_id = row[0] if row else None
            
            session['user_id'] = user_id
            session['email'] = email
            session['username'] = username
            
            cursor.close()
            conn.close()
            
            # Clear any existing session and set new user session
            session.clear()
            session['user_id'] = user_id
            session['email'] = email
            session['username'] = username
            
            flash('Account created successfully!', 'success')
            return redirect(url_for('onboarding'))
        except Exception as e:
            flash(f'Error creating account: {str(e)}', 'error')
        
        cursor.close()
        conn.close()
    
    return render_template('signup.html')

@app.route('/auth/google')
def google_login():
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_callback():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if not user_info:
            flash('Failed to get user information', 'error')
            return redirect(url_for('login'))
        
        email = user_info.get('email')
        username = user_info.get('name', email.split('@')[0])
        
        conn = get_db_connection()
        if not conn:
            flash('Database connection error', 'error')
            return redirect(url_for('login'))
        
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        
        if not row:
            # Create new user
            cursor.execute('''
                INSERT INTO users (email, username, is_oauth_user, oauth_provider)
                VALUES (?, ?, 1, 'google')
            ''', (email, username))
            conn.commit()
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
        
        user_id = row[0] if row else None
        # Clear any existing session data first
        session.clear()
        # Set new session data
        session['user_id'] = user_id
        session['email'] = email
        session['username'] = username
        
        cursor.close()
        conn.close()
        
        # Check if onboarding is already completed for Google users
        answers = get_onboarding_answers(user_id)
        if answers:
            completed = answers.get('completed')
            if completed == 1 or completed is True or str(completed) == '1':
                return redirect(url_for('dashboard'))
        return redirect(url_for('check_onboarding'))
    
    except Exception as e:
        flash(f'Google login failed: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('landing'))

# ============ Onboarding Routes ============

@app.route('/check-onboarding')
@login_required
def check_onboarding():
    """Check if user has completed onboarding"""
    user_id = session['user_id']
    answers = get_onboarding_answers(user_id)
    
    if answers and answers.get('completed') == 1:
        # Onboarding completed, go to dashboard
        return redirect(url_for('dashboard'))
    
    # Onboarding not completed, go to onboarding page
    return redirect(url_for('onboarding'))

@app.route('/onboarding')
@login_required
def onboarding():
    """Onboarding page - redirect to dashboard if already completed"""
    user_id = session['user_id']
    
    # Check if onboarding is already completed
    answers = get_onboarding_answers(user_id)
    if answers and answers.get('completed') == 1:
        # Already completed, redirect to dashboard
        return redirect(url_for('dashboard'))
    
    # Show onboarding form
    user = get_user_by_id(user_id)
    return render_template('onboarding.html', username=user['username'] if user else 'Student')


@app.route('/api/filters', methods=['GET'])
@login_required
def get_filter_data():
    """Return filter options (countries, budget range) using DB if available, else CSV fallback."""
    try:
        # Prefer CSV service for consistent filter extraction
        countries = csv_service.get_countries() or []
        universities = csv_service.get_all_universities()
        costs = []
        for u in universities:
            try:
                c = parse_cost_str(u.get('total_estimated_cost'))
                if c is None:
                    # try tuition + living
                    t = parse_cost_str(u.get('tuition_fee_annual'))
                    l = parse_cost_str(u.get('living_cost_annual'))
                    if t is not None or l is not None:
                        c = (t or 0) + (l or 0)
                if c is not None:
                    costs.append(c)
            except Exception:
                continue

        budget_min = min(costs) if costs else 0
        budget_max = max(costs) if costs else 100000

        # Average cost per country
        country_costs = {}
        for u in universities:
            country = (u.get('country') or '').strip()
            if not country:
                continue
            val = parse_cost_str(u.get('total_estimated_cost'))
            if val is None:
                t = parse_cost_str(u.get('tuition_fee_annual'))
                l = parse_cost_str(u.get('living_cost_annual'))
                if t is not None or l is not None:
                    val = (t or 0) + (l or 0)
            if val is None:
                continue
            country_costs.setdefault(country, []).append(val)

        avg_cost_by_country = {c: (sum(vals) / len(vals)) for c, vals in country_costs.items()} if country_costs else {}

        return jsonify({'countries': countries, 'budget_min': budget_min, 'budget_max': budget_max, 'avg_cost_by_country': avg_cost_by_country})
    except Exception as e:
        return jsonify({'countries': [], 'budget_min': 0, 'budget_max': 100000})


@app.route('/api/scholarships', methods=['GET'])
@login_required
def get_scholarships():
    """Aggregate scholarship entries from CSV and return deduplicated list."""
    try:
        universities = csv_service.get_all_universities()
        seen = {}
        for u in universities:
            s = u.get('scholarships') or ''
            if not s:
                continue
            # split by common separators
            parts = [p.strip() for p in re.split(r"[;|\\n\\r]+", s) if p.strip()]
            for p in parts:
                key = p.lower()
                if key in seen:
                    seen[key]['count'] += 1
                else:
                    seen[key] = {'text': p, 'count': 1, 'sample_university': u.get('university_name')}

        scholarships = list(seen.values())
        # Sort by frequency
        scholarships.sort(key=lambda x: x['count'], reverse=True)
        return jsonify({'scholarships': scholarships})
    except Exception as e:
        return jsonify({'scholarships': []})

@app.route('/api/onboarding/questions', methods=['GET'])
@login_required
def get_onboarding_questions():
    """Get all onboarding questions"""
    questions = [
        {
            'id': 1,
            'question': 'Which countries are you interested in studying?',
            'type': 'multi-select',
            'options': ['Canada', 'USA', 'UK', 'Australia', 'Germany', 'France', 'Netherlands', 'Sweden', 'Ethiopia', 'Argentina', 'Other']
        },
        {
            'id': 2,
            'question': 'What level of study are you interested in?',
            'type': 'single-select',
            'options': ['Undergraduate', 'Postgraduate', 'Masters', 'PhD', 'Diploma']
        },
        {
            'id': 3,
            'question': 'What is your preferred field of study?',
            'type': 'text',
            'placeholder': 'e.g., Computer Science, Engineering, Business'
        },
        {
            'id': 4,
            'question': 'How many years do you plan to study?',
            'type': 'number',
            'placeholder': '2-5'
        },
        {
            'id': 5,
            'question': 'What is your annual budget for tuition and living (in USD)?',
            'type': 'range',
            'min': 5000,
            'max': 100000,
            'step': 1000,
            'currency': 'USD'
        },
        {
            'id': 6,
            'question': 'What factors are most important to you? (Select all that apply)',
            'type': 'multi-select',
            'options': ['Good Rankings', 'Affordable', 'Scholarship Opportunities', 'Work Opportunities', 'Campus Life', 'Location', 'Specific Specialization']
        },
        {
            'id': 7,
            'question': 'How confident are you about your academic readiness?',
            'type': 'single-select',
            'options': ['Very Confident', 'Confident', 'Somewhat Confident', 'Need Preparation']
        },
        {
            'id': 8,
            'question': 'English language proficiency:',
            'type': 'single-select',
            'options': ['Native Speaker', 'Fluent', 'Intermediate', 'Beginner', 'Need to Prepare']
        },
        {
            'id': 9,
            'question': 'What aspect of campus life is most important?',
            'type': 'single-select',
            'options': ['Academic Excellence', 'Diverse Community', 'Social Activities', 'Research Opportunities', 'Sports and Recreation']
        },
        {
            'id': 10,
            'question': 'Do you have any special interests or requirements?',
            'type': 'text',
            'placeholder': 'e.g., Sports, Music, Religious Community'
        },
        {
            'id': 11,
            'question': 'Are you looking for scholarship opportunities?',
            'type': 'single-select',
            'options': ['Essential', 'Important', 'Nice to Have', 'Not Required']
        },
        {
            'id': 12,
            'question': 'When do you plan to start your studies?',
            'type': 'single-select',
            'options': ['Next Month', 'Next 3 Months', 'Next 6 Months', 'Next Year']
        }
    ]
    return jsonify(questions)

@app.route('/api/onboarding/save', methods=['POST'])
@login_required
def save_onboarding_responses():
    """Save user's onboarding responses"""
    data = request.get_json()
    user_id = session['user_id']
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection error'}), 500
    
    cursor = conn.cursor()
    
    try:
        # Check if user already has onboarding data
        cursor.execute("SELECT id FROM onboarding_responses WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()
        
        values = {
            'user_id': user_id,
            'question_1_preferred_countries': data.get('q1'),
            'question_2_study_level': data.get('q2'),
            'question_3_preferred_stream': data.get('q3'),
            'question_4_duration_years': int(data.get('q4', 0)) if data.get('q4') else None,
            'question_5_budget_min': float(data.get('q5_min', 0)) if data.get('q5_min') else None,
            'question_5_budget_max': float(data.get('q5_max', 0)) if data.get('q5_max') else None,
            'question_6_important_factors': data.get('q6'),
            'question_7_admission_readiness': data.get('q7'),
            'question_8_language_proficiency': data.get('q8'),
            'question_9_campus_life': data.get('q9'),
            'question_10_special_interests': data.get('q10'),
            'question_11_scholarship_need': 1 if data.get('q11') == 'Essential' else 0,
            'question_12_start_date': data.get('q12'),
            'completed': 1
        }
        
        if existing:
            update_parts = []
            update_values = []
            for key, value in values.items():
                if key != 'user_id':
                    col_name = key
                    update_parts.append(f"{col_name} = ?")
                    update_values.append(value)
            update_values.append(user_id)
            
            update_query = f"UPDATE onboarding_responses SET {', '.join(update_parts)} WHERE user_id = ?"
            cursor.execute(update_query, update_values)
        else:
            cols = list(values.keys())
            placeholders = ', '.join(['?'] * len(values))
            insert_query = f"INSERT INTO onboarding_responses ({', '.join(cols)}) VALUES ({placeholders})"
            cursor.execute(insert_query, list(values.values()))
        
        conn.commit()
        
        # Calculate and save matches - with CSV fallback
        calculate_and_save_matches_with_fallback(user_id, values)
        
        return jsonify({'success': True, 'message': 'Onboarding responses saved successfully'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

def calculate_and_save_matches_with_fallback(user_id, answers):
    """Calculate university matches with CSV fallback"""
    conn = get_db_connection()
    
    # Try database first
    if conn:
        try:
            cursor = conn.cursor()
            # Get all universities from database
            cursor.execute("SELECT * FROM universities")
            universities_rows = cursor.fetchall()
            
            if universities_rows and len(universities_rows) > 0:
                # Database has data, use it
                # Ensure Row objects are properly converted to dicts with all columns including 'id'
                universities = []
                for row in universities_rows:
                    uni_dict = dict(row)
                    # Verify 'id' field exists
                    if 'id' not in uni_dict:
                        print(f"ERROR: Row factory not working! Row keys: {uni_dict.keys()}")
                    universities.append(uni_dict)
                save_matches_to_db(user_id, answers, universities, conn, cursor)
                cursor.close()
                conn.close()
                print(f"Matches calculated from database: {len(universities)} universities")
                return
            else:
                # Database is empty, use CSV fallback
                cursor.close()
                conn.close()
                print("Database empty, using CSV fallback")
        except Exception as e:
            print(f"Database error during match calculation: {e}")
            import traceback
            traceback.print_exc()
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    # CSV Fallback
    print("Using CSV fallback for match calculation")
    matches = csv_service.calculate_matches_from_csv(answers, parse_cost_str)
    
    # Try to save to database if available
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Clear existing matches for this user first
            cursor.execute("DELETE FROM university_matches WHERE user_id = ?", (user_id,))
            conn.commit()
            print(f"Cleared existing matches for user {user_id}")
            
            for match in matches:
                # Insert university if it doesn't exist
                uni = match['university']
                cursor.execute('''
                    INSERT OR IGNORE INTO universities (
                        university_id, university_name, official_website, email_inquiry, phone_number,
                        address, country, state, city, zip_code, latitude, longitude,
                        campus_type, established, duration_undergraduation_course,
                        duration_postgraduation_course, duration_phd_course,
                        duration_diploma_course, duration_online_course, admission_req,
                        cgpa, ielts, sat_gre_gmat, deadline_sem1, academic_calendar,
                        medium, tuition_fee_annual, living_cost_annual, total_estimated_cost,
                        scholarships, intl_services, accommodation, airport_pickup,
                        pre_arrival, documents_required, image_url, program_level, course
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    uni.get('university_id'), uni.get('university_name'), uni.get('official_website'),
                    uni.get('email_inquiry'), uni.get('phone_number'), uni.get('address'),
                    uni.get('country'), uni.get('state'), uni.get('city'), uni.get('zip_code'),
                    uni.get('latitude'), uni.get('longitude'), uni.get('campus_type'),
                    uni.get('established'), uni.get('duration_undergraduation_course'),
                    uni.get('duration_postgraduation_course'), uni.get('duration_phd_course'),
                    uni.get('duration_diploma_course'), uni.get('duration_online_course'),
                    uni.get('admission_req'), uni.get('cgpa'), uni.get('ielts'),
                    uni.get('sat_gre_gmat'), uni.get('deadline_sem1'), uni.get('academic_calendar'),
                    uni.get('medium'), uni.get('tuition_fee_annual'), uni.get('living_cost_annual'),
                    uni.get('total_estimated_cost'), uni.get('scholarships'), uni.get('intl_services'),
                    uni.get('accommodation'), uni.get('airport_pickup'), uni.get('pre_arrival'),
                    uni.get('documents_required'), uni.get('image_url'), uni.get('program_level'),
                    uni.get('course')
                ))
                
                # Get university ID
                cursor.execute("SELECT id FROM universities WHERE university_id = ?", (uni.get('university_id'),))
                uni_row = cursor.fetchone()
                if uni_row:
                    uni_id = uni_row[0]
                    # Insert match
                    cursor.execute('''
                        INSERT OR REPLACE INTO university_matches (user_id, university_id, match_score, match_reason)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, uni_id, match['match_score'], match['match_reason']))
            
            conn.commit()
            cursor.close()
            conn.close()
            print(f"Saved {len(matches)} matches from CSV to database")
        except Exception as e:
            print(f"Error saving CSV matches to database: {e}")
            import traceback
            traceback.print_exc()
            if conn:
                try:
                    conn.close()
                except:
                    pass

def save_matches_to_db(user_id, answers, universities, conn, cursor):
    """Save calculated matches to database"""
    
    # First, delete all existing matches for this user to ensure fresh calculation
    try:
        cursor.execute("DELETE FROM university_matches WHERE user_id = ?", (user_id,))
        conn.commit()
        print(f"Cleared existing matches for user {user_id}")
    except Exception as e:
        print(f"Error clearing old matches: {e}")
    
    matches = []
    
    for uni in universities:
        score = calculate_match_score(answers, uni)
        
        # Only save universities with a minimum match score of 30
        if score >= 30:
            # Get university ID safely
            uni_id = uni.get('id')
            if uni_id is None:
                print(f"Warning: University missing 'id' field: {uni.get('university_name', 'Unknown')}")
                continue
                
            matches.append({
                'user_id': user_id,
                'university_id': uni_id,
                'match_score': round(score, 2),
                'match_reason': generate_match_reason(answers, uni, score)
            })
    
    # Save matches
    for match in matches:
        cursor.execute('''
            INSERT OR REPLACE INTO university_matches (user_id, university_id, match_score, match_reason)
            VALUES (?, ?, ?, ?)
        ''', (match['user_id'], match['university_id'], match['match_score'], match['match_reason']))
    
    conn.commit()

def calculate_match_score(answers, university):
    """Calculate match score between user and university (0-100)"""
    score = 0
    weights = {
        'country': 0.25,
        'budget': 0.25,
        'level': 0.15,
        'stream': 0.15,
        'scholarships': 0.10,
        'services': 0.10
    }
    
    # Country match
    preferred_countries_str = answers.get('question_1_preferred_countries') or ''
    if preferred_countries_str:
        if preferred_countries_str.startswith('['):
            try:
                preferred_countries = json.loads(preferred_countries_str)
            except:
                preferred_countries = [c.strip() for c in preferred_countries_str.replace('[', '').replace(']', '').split(',') if c.strip()]
        else:
            preferred_countries = [c.strip() for c in preferred_countries_str.split(',') if c.strip()]
    else:
        preferred_countries = []
    
    uni_country = (university.get('country') or '').strip()
    if uni_country and preferred_countries:
        if any(uni_country.lower() == pc.lower() or uni_country.lower() in pc.lower() or pc.lower() in uni_country.lower() for pc in preferred_countries):
            score += 100 * weights['country']
        else:
            score += 20 * weights['country']
    elif not preferred_countries:
        score += 70 * weights['country']
    else:
        score += 20 * weights['country']
    
    # Budget match
    budget_min = answers.get('question_5_budget_min') or 0
    budget_max = answers.get('question_5_budget_max') or 100000
    total_cost = parse_cost_str(university.get('total_estimated_cost'))
    
    # If no cost data available, give neutral score
    if total_cost is None:
        score += 50 * weights['budget']
    elif budget_min <= total_cost <= budget_max:
        score += 100 * weights['budget']
    elif total_cost < budget_min:
        score += 80 * weights['budget']
    elif total_cost <= budget_max * 1.2:
        score += 60 * weights['budget']
    else:
        score += 20 * weights['budget']
    
    # Study level match
    study_level = (answers.get('question_2_study_level') or '').lower()
    program_level = (university.get('program_level') or '').lower()
    course = (university.get('course') or '').lower()
    
    if study_level and (study_level in program_level or study_level in course):
        score += 100 * weights['level']
    else:
        score += 70 * weights['level']
    
    # Stream/Field match
    preferred_stream = (answers.get('question_3_preferred_stream') or '').lower()
    uni_courses = (university.get('course') or '').lower()
    
    if preferred_stream and preferred_stream in uni_courses:
        score += 100 * weights['stream']
    elif not preferred_stream:
        score += 70 * weights['stream']
    else:
        score += 40 * weights['stream']
    
    # Scholarships
    scholarships = university.get('scholarships') or ''
    scholarship_need = answers.get('question_11_scholarship_need')
    needs_scholarship = scholarship_need == 1 or scholarship_need == True or str(scholarship_need).lower() == 'true'
    
    if needs_scholarship and scholarships:
        score += 100 * weights['scholarships']
    elif scholarships:
        score += 50 * weights['scholarships']
    elif needs_scholarship and not scholarships:
        score += 10 * weights['scholarships']
    
    # International services
    intl_services = university.get('intl_services') or ''
    if intl_services:
        score += 100 * weights['services']
    
    return min(score, 100)

def generate_match_reason(answers, university, score):
    """Generate a reason for the match"""
    reasons = []
    
    if score >= 80:
        reasons.append(f"Excellent match for your profile")
    elif score >= 60:
        reasons.append(f"Good match for your preferences")
    else:
        reasons.append(f"Fair match")
    
    preferred_countries_str = answers.get('question_1_preferred_countries') or ''
    uni_country = university.get('country') or ''
    if preferred_countries_str and uni_country and uni_country in preferred_countries_str:
        reasons.append(f"Located in your preferred country: {uni_country}")
    
    return "; ".join(reasons)

# ============ Perfect Matches & Dashboard Routes ============

@app.route('/perfect-matches')
@login_required
def perfect_matches():
    user = get_user_by_id(session['user_id'])
    return render_template('perfect_matches_updated.html', username=user.get('username') if user else 'Student', user=user)

@app.route('/api/matches', methods=['GET'])
@login_required
def get_matches():
    """Get matched universities with CSV fallback"""
    user_id = session['user_id']
    
    # Get filter parameters
    filter_countries = request.args.get('countries', '')
    filter_budget_min = request.args.get('budget_min', type=float, default=0)
    filter_budget_max = request.args.get('budget_max', type=float, default=1000000)
    sort_by = request.args.get('sort_by', 'match_score')
    page = request.args.get('page', type=int, default=1)
    per_page = 10
    
    conn = get_db_connection()
    
    # Try database first
    if conn:
        try:
            cursor = conn.cursor()
            # Check if user has matches
            cursor.execute("SELECT COUNT(*) FROM university_matches WHERE user_id = ?", (user_id,))
            count_result = cursor.fetchone()
            
            if count_result and count_result[0] > 0:
                # User has matches, return from database
                query = '''
                    SELECT u.*, m.match_score, m.match_reason, m.is_favorite, m.is_shortlisted
                    FROM universities u
                    JOIN university_matches m ON u.id = m.university_id
                    WHERE m.user_id = ?
                '''
                params = [user_id]
                
                # Apply filters
                if filter_countries:
                    countries = [c.strip() for c in filter_countries.split(',')]
                    placeholders = ', '.join(['?'] * len(countries))
                    query += f" AND u.country IN ({placeholders})"
                    params.extend(countries)
                
                # Sorting
                if sort_by == 'budget':
                    query += " ORDER BY CAST(u.total_estimated_cost AS REAL) ASC"
                elif sort_by == 'name':
                    query += " ORDER BY u.university_name ASC"
                else:
                    query += " ORDER BY m.match_score DESC"
                
                # Count
                count_query = query.replace(
                    'SELECT u.*, m.match_score, m.match_reason, m.is_favorite, m.is_shortlisted',
                    'SELECT COUNT(*) as count'
                )
                cursor.execute(count_query, params)
                total = cursor.fetchone()[0]
                
                # Paginate
                offset = (page - 1) * per_page
                query += f" LIMIT ? OFFSET ?"
                params.extend([per_page, offset])
                
                cursor.execute(query, params)
                matches_rows = cursor.fetchall()
                matches = [dict(row) for row in matches_rows]
                
                cursor.close()
                conn.close()
                
                # Format results
                results = []
                for match in matches:
                    results.append({
                        'id': match['id'],
                        'name': match.get('university_name') or 'University',
                        'country': match.get('country') or 'N/A',
                        'city': match.get('city') or 'N/A',
                        'match_score': float(match.get('match_score') or 0),
                        'match_reason': match.get('match_reason') or 'Good match',
                        'tuition_fee': parse_cost_str(match.get('tuition_fee_annual')),
                        'living_cost': parse_cost_str(match.get('living_cost_annual')),
                        'total_cost': parse_cost_str(match.get('total_estimated_cost')),
                        'scholarships': match.get('scholarships'),
                        'website': match.get('official_website'),
                        'course': match.get('course'),
                        'is_favorite': bool(match.get('is_favorite') or 0),
                        'is_shortlisted': bool(match.get('is_shortlisted') or 0),
                        'image_url': match.get('image_url')
                    })
                
                return jsonify({
                    'matches': results,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'pages': (total + per_page - 1) // per_page
                })
        except Exception as e:
            print(f"Database error in get_matches: {e}")
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    # CSV Fallback
    print("Using CSV fallback for get_matches")
    answers = get_onboarding_answers(user_id)
    if not answers:
        return jsonify({'matches': [], 'total': 0, 'page': 1, 'per_page': per_page, 'pages': 0})
    
    all_matches = csv_service.calculate_matches_from_csv(answers, parse_cost_str)
    print(f"Found {len(all_matches)} unique matched universities (after deduplication and filtering)")
    
    # Get user favorites to mark them
    favorite_ids = set()
    conn_fav = get_db_connection()
    if conn_fav:
        try:
            cursor_fav = conn_fav.cursor()
            cursor_fav.execute('SELECT university_id_str FROM user_favorites WHERE user_id = ?', (user_id,))
            favorite_ids = set(row[0] for row in cursor_fav.fetchall())
            cursor_fav.close()
            conn_fav.close()
        except:
            pass
    
    # Apply filters
    filtered_matches = all_matches
    if filter_countries:
        countries = [c.strip().lower() for c in filter_countries.split(',')]
        filtered_matches = [m for m in filtered_matches if m['university'].get('country', '').lower() in countries]
    
    # Sort
    if sort_by == 'budget':
        filtered_matches.sort(key=lambda x: parse_cost_str(x['university'].get('total_estimated_cost')) or 0)
    elif sort_by == 'name':
        filtered_matches.sort(key=lambda x: x['university'].get('university_name', ''))
    
    # Paginate
    total = len(filtered_matches)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_matches = filtered_matches[start_idx:end_idx]
    
    # Format results
    results = []
    for match in paginated_matches:
        uni = match['university']
        uni_id = uni.get('university_id') or str(uni.get('id', ''))
        results.append({
            'id': uni_id,  # Use university_id for CSV compatibility
            'name': uni.get('university_name') or 'University',
            'country': uni.get('country') or 'N/A',
            'city': uni.get('city') or 'N/A',
            'match_score': float(match.get('match_score') or 0),
            'match_reason': match.get('match_reason') or 'Good match',
            'tuition_fee': parse_cost_str(uni.get('tuition_fee_annual')),
            'living_cost': parse_cost_str(uni.get('living_cost_annual')),
            'total_cost': parse_cost_str(uni.get('total_estimated_cost')),
            'scholarships': uni.get('scholarships'),
            'website': uni.get('official_website'),
            'course': uni.get('course'),
            'is_favorite': uni_id in favorite_ids,
            'is_shortlisted': match.get('is_shortlisted', False),
            'image_url': uni.get('image_url')
        })
    
    return jsonify({
        'matches': results,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    })

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_user_by_id(session['user_id'])
    return render_template('dashboard_updated.html', user=user)

@app.route('/api/dashboard/stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    """Get dashboard statistics with CSV fallback"""
    user_id = session['user_id']
    
    conn = get_db_connection()
    
    # Try database first
    if conn:
        try:
            cursor = conn.cursor()
            # Check if user has matches
            cursor.execute("SELECT COUNT(*) FROM university_matches WHERE user_id = ?", (user_id,))
            count_result = cursor.fetchone()
            
            if count_result and count_result[0] > 0:
                # Get stats from database
                cursor.execute("SELECT COUNT(*) as total FROM university_matches WHERE user_id = ?", (user_id,))
                total_matches = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM university_matches WHERE user_id = ? AND match_score >= 80", (user_id,))
                top_matches = cursor.fetchone()[0]
                
                # Count favorites from user_favorites table
                cursor.execute("SELECT COUNT(*) FROM user_favorites WHERE user_id = ?", (user_id,))
                favorites = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM university_matches WHERE user_id = ? AND is_shortlisted = 1", (user_id,))
                shortlisted = cursor.fetchone()[0]
                
                # Top 5
                cursor.execute('''
                    SELECT u.*, m.match_score, m.match_reason, m.is_favorite, m.is_shortlisted
                    FROM universities u
                    JOIN university_matches m ON u.id = m.university_id
                    WHERE m.user_id = ?
                    ORDER BY m.match_score DESC
                    LIMIT 5
                ''', (user_id,))
                top_5_rows = cursor.fetchall()
                top_5 = [dict(row) for row in top_5_rows]
                
                cursor.close()
                conn.close()
                
                # Format top 5
                top_5_formatted = []
                for m in top_5:
                    top_5_formatted.append({
                        'id': m.get('id'),
                        'name': m.get('university_name') or 'University',
                        'country': m.get('country') or 'N/A',
                        'city': m.get('city') or 'N/A',
                        'match_score': float(m.get('match_score') or 0),
                        'match_reason': m.get('match_reason') or 'Good match',
                        'tuition_fee': parse_cost_str(m.get('tuition_fee_annual')),
                        'living_cost': parse_cost_str(m.get('living_cost_annual')),
                        'total_cost': parse_cost_str(m.get('total_estimated_cost')),
                        'scholarships': m.get('scholarships'),
                        'website': m.get('official_website'),
                        'course': m.get('course'),
                        'is_favorite': bool(m.get('is_favorite') or 0),
                        'is_shortlisted': bool(m.get('is_shortlisted') or 0),
                        'image_url': m.get('image_url')
                    })
                
                return jsonify({
                    'total_matches': total_matches,
                    'top_matches': top_matches,
                    'favorites': favorites,
                    'shortlisted': shortlisted,
                    'top_5_matches': top_5_formatted
                })
        except Exception as e:
            print(f"Database error in dashboard stats: {e}")
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    # CSV Fallback
    print("Using CSV fallback for dashboard stats")
    answers = get_onboarding_answers(user_id)
    if not answers:
        return jsonify({
            'total_matches': 0,
            'top_matches': 0,
            'favorites': 0,
            'shortlisted': 0,
            'top_5_matches': []
        })
    
    all_matches = csv_service.calculate_matches_from_csv(answers, parse_cost_str)
    
    total_matches = len(all_matches)
    top_matches = len([m for m in all_matches if m['match_score'] >= 80])
    
    # Count favorites from user_favorites table
    favorites = 0
    shortlisted = 0
    favorite_ids = set()
    conn_fav = get_db_connection()
    if conn_fav:
        try:
            cursor_fav = conn_fav.cursor()
            cursor_fav.execute('SELECT COUNT(*) FROM user_favorites WHERE user_id = ?', (user_id,))
            favorites = cursor_fav.fetchone()[0]
            cursor_fav.execute('SELECT university_id_str FROM user_favorites WHERE user_id = ?', (user_id,))
            favorite_ids = set(row[0] for row in cursor_fav.fetchall())
            cursor_fav.close()
            conn_fav.close()
        except Exception as e:
            print(f"Error counting favorites: {e}")
    
    # Top 5
    top_5_matches = all_matches[:5]
    top_5_formatted = []
    for match in top_5_matches:
        uni = match['university']
        uni_id = uni.get('university_id') or str(uni.get('id', ''))
        top_5_formatted.append({
            'id': uni_id,  # Use university_id for CSV compatibility
            'name': uni.get('university_name') or 'University',
            'country': uni.get('country') or 'N/A',
            'city': uni.get('city') or 'N/A',
            'match_score': float(match.get('match_score') or 0),
            'match_reason': match.get('match_reason') or 'Good match',
            'tuition_fee': parse_cost_str(uni.get('tuition_fee_annual')),
            'living_cost': parse_cost_str(uni.get('living_cost_annual')),
            'total_cost': parse_cost_str(uni.get('total_estimated_cost')),
            'scholarships': uni.get('scholarships'),
            'website': uni.get('official_website'),
            'course': uni.get('course'),
            'is_favorite': uni_id in favorite_ids,
            'is_shortlisted': False,
            'image_url': uni.get('image_url')
        })
    
    return jsonify({
        'total_matches': total_matches,
        'top_matches': top_matches,
        'favorites': favorites,
        'shortlisted': shortlisted,
        'top_5_matches': top_5_formatted
    })

# ============ Other Dashboard Routes ============

@app.route('/cost-calculator')
@login_required
def cost_calculator():
    user = get_user_by_id(session['user_id'])
    return render_template('cost_calculator.html', user=user)

@app.route('/fee-comparison')
@login_required
def fee_comparison():
    user = get_user_by_id(session['user_id'])
    return render_template('fee_comparison.html', user=user)

@app.route('/visa-probability')
@login_required
def visa_probability():
    user = get_user_by_id(session['user_id'])
    return render_template('visa_probability_custom.html', user=user)

@app.route('/location-explorer')
@login_required
def location_explorer():
    user = get_user_by_id(session['user_id'])
    return render_template('location_explorer.html', user=user)

@app.route('/map-explorer')
@login_required
def map_explorer():
    user = get_user_by_id(session['user_id'])
    return render_template('map_explorer.html', user=user)

@app.route('/scholarships')
@login_required
def scholarships():
    user = get_user_by_id(session['user_id'])
    return render_template('scholarship_finder.html', user=user)

@app.route('/accommodation')
@login_required
def accommodation():
    user = get_user_by_id(session['user_id'])
    return render_template('accommodation_finder.html', user=user)

@app.route('/job-market')
@login_required
def job_market():
    user = get_user_by_id(session['user_id'])
    return render_template('job_market.html', user=user)

@app.route('/career-roadmap')
@login_required
def career_roadmap():
    user = get_user_by_id(session['user_id'])
    return render_template('course_to_career.html', user=user)

@app.route('/visa-checklist')
@login_required
def visa_checklist():
    user = get_user_by_id(session['user_id'])
    return render_template('visa_checklist.html', user=user)

@app.route('/safety-score')
@login_required
def safety_score():
    user = get_user_by_id(session['user_id'])
    return render_template('safety_city_insights.html', user=user)

@app.route('/ai-mentor')
@login_required
def ai_mentor():
    user = get_user_by_id(session['user_id'])
    return render_template('ai_mentor.html', user=user)

@app.route('/interview-trainer')
@login_required
def interview_trainer():
    user = get_user_by_id(session['user_id'])
    return render_template('interview_trainer.html', user=user)

@app.route('/resume-builder')
@login_required
def resume_builder():
    user = get_user_by_id(session['user_id'])
    return render_template('resume_builder.html', user=user)

@app.route('/profile')
@login_required
def profile():
    user = get_user_by_id(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/settings')
@login_required
def settings():
    user = get_user_by_id(session['user_id'])
    return render_template('settings.html', user=user)

@app.route('/favorites')
@login_required
def favorites():
    user = get_user_by_id(session['user_id'])
    return render_template('favorites.html', user=user)

@app.route('/api/favorites', methods=['GET'])
@login_required
def get_favorites():
    """Get user's favorited universities from user_favorites table with CSV fallback"""
    user_id = session['user_id']
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'favorites': [], 'total': 0})
    
    try:
        cursor = conn.cursor()
        
        # Get favorited university IDs from user_favorites
        cursor.execute('''
            SELECT university_id_str, university_name 
            FROM user_favorites 
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        favorite_rows = cursor.fetchall()
        
        if not favorite_rows or len(favorite_rows) == 0:
            cursor.close()
            conn.close()
            return jsonify({'favorites': [], 'total': 0})
        
        favorites = []
        
        # Get university details for each favorited university
        for fav in favorite_rows:
            uni_id_str = fav[0]
            uni_name = fav[1]
            
            # Try to get from database first
            cursor.execute('''
                SELECT * FROM universities WHERE university_id = ?
            ''', (uni_id_str,))
            uni_row = cursor.fetchone()
            
            if uni_row:
                uni = dict(uni_row)
            else:
                # Fallback to CSV
                all_unis = csv_service.get_all_universities()
                uni = None
                for u in all_unis:
                    if u.get('university_id') == uni_id_str:
                        uni = u
                        break
                
                if not uni:
                    # Can't find university, use minimal info
                    uni = {
                        'university_id': uni_id_str,
                        'university_name': uni_name,
                        'country': 'N/A',
                        'city': 'N/A'
                    }
            
            favorites.append({
                'id': uni.get('university_id') or uni_id_str,
                'name': uni.get('university_name') or uni_name,
                'country': uni.get('country') or 'N/A',
                'city': uni.get('city') or 'N/A',
                'tuition_fee': parse_cost_str(uni.get('tuition_fee_annual')),
                'living_cost': parse_cost_str(uni.get('living_cost_annual')),
                'total_cost': parse_cost_str(uni.get('total_estimated_cost')),
                'scholarships': uni.get('scholarships'),
                'website': uni.get('official_website'),
                'course': uni.get('course'),
                'image_url': uni.get('image_url'),
                'is_favorite': True
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'favorites': favorites,
            'total': len(favorites)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error in get_favorites: {str(e)}")
        if conn:
            try:
                conn.close()
            except:
                pass
        return jsonify({'favorites': [], 'total': 0, 'error': str(e)})

@app.route('/api/matches/<university_id>/favorite', methods=['POST'])
@login_required
def toggle_favorite(university_id):
    """Toggle favorite status for a university"""
    user_id = session['user_id']
    print(f"Toggle favorite called: user_id={user_id}, university_id={university_id}")
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection error'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Get university name for storing
        university_name = None
        cursor.execute('SELECT university_name FROM universities WHERE university_id = ?', (str(university_id),))
        uni = cursor.fetchone()
        if uni:
            university_name = uni[0]
        else:
            # Try from CSV if not in DB
            all_unis = csv_service.get_all_universities()
            for u in all_unis:
                if u.get('university_id') == str(university_id):
                    university_name = u.get('university_name')
                    break
        
        # Check if already favorited in user_favorites table
        cursor.execute('''
            SELECT id FROM user_favorites 
            WHERE user_id = ? AND university_id_str = ?
        ''', (user_id, str(university_id)))
        
        result = cursor.fetchone()
        
        if result:
            # Already favorited, remove it
            cursor.execute('''
                DELETE FROM user_favorites 
                WHERE user_id = ? AND university_id_str = ?
            ''', (user_id, str(university_id)))
            new_status = False
            print(f"Removed from favorites: user_id={user_id}, university_id={university_id}")
        else:
            # Not favorited, add it
            cursor.execute('''
                INSERT INTO user_favorites (user_id, university_id_str, university_name)
                VALUES (?, ?, ?)
            ''', (user_id, str(university_id), university_name))
            new_status = True
            print(f"Added to favorites: user_id={user_id}, university_id={university_id}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'is_favorite': bool(new_status)
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error in toggle_favorite: {str(e)}")
        if conn:
            try:
                conn.close()
            except:
                pass
        return jsonify({'error': str(e)}), 500

@app.route('/api/matches/<university_id>/shortlist', methods=['POST'])
@login_required
def toggle_shortlist(university_id):
    """Toggle shortlist status for a university"""
    user_id = session['user_id']
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection error'}), 500
    
    try:
        cursor = conn.cursor()
        
        # First check if the university exists by university_id string
        cursor.execute('SELECT id FROM universities WHERE university_id = ?', (str(university_id),))
        uni_exists = cursor.fetchone()
        
        # If not found by id, try by university_id (for CSV compatibility)
        actual_db_id = university_id
        if not uni_exists:
            cursor.execute('SELECT id FROM universities WHERE university_id = ?', (str(university_id),))
            uni_exists = cursor.fetchone()
            if uni_exists:
                # Use the database id instead
                actual_db_id = uni_exists[0]
        
        if not uni_exists:
            cursor.close()
            conn.close()
            return jsonify({'error': 'University not found'}), 404
        
        # Check if match exists
        cursor.execute('''
            SELECT is_shortlisted FROM university_matches 
            WHERE user_id = ? AND university_id = ?
        ''', (user_id, actual_db_id))
        
        result = cursor.fetchone()
        
        if not result:
            # Match doesn't exist yet, create it with shortlisted status
            cursor.execute('''
                INSERT INTO university_matches (user_id, university_id, match_score, match_reason, is_shortlisted)
                VALUES (?, ?, 0, 'Added to shortlist', 1)
            ''', (user_id, actual_db_id))
            new_status = 1
        else:
            # Toggle the existing shortlist status
            current_status = result[0]
            new_status = 0 if current_status else 1
            
            cursor.execute('''
                UPDATE university_matches 
                SET is_shortlisted = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND university_id = ?
            ''', (new_status, user_id, actual_db_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'is_shortlisted': bool(new_status)
        })
    
    except Exception as e:
        if conn:
            try:
                conn.close()
            except:
                pass
        return jsonify({'error': str(e)}), 500

# ============ Fee Comparison Tool ============

@app.route('/api/fee-comparison', methods=['POST'])
@login_required
def compare_fees():
    """Compare fees between selected universities"""
    user_id = session['user_id']
    data = request.get_json()
    university_ids = data.get('university_ids', [])
    
    if not university_ids or len(university_ids) < 2:
        return jsonify({'error': 'Please select at least 2 universities to compare'}), 400
    
    universities = []
    conn = get_db_connection()
    
    # Get university details
    for uni_id in university_ids:
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM universities WHERE university_id = ?', (str(uni_id),))
                uni_row = cursor.fetchone()
                if uni_row:
                    universities.append(dict(uni_row))
                cursor.close()
            except:
                pass
        
        # Fallback to CSV
        if not universities or len(universities) < len(university_ids):
            all_unis = csv_service.get_all_universities()
            for u in all_unis:
                if u.get('university_id') == str(uni_id):
                    universities.append(u)
                    break
    
    if conn:
        conn.close()
    
    # Calculate comparison data
    comparison = []
    for uni in universities:
        tuition = parse_cost_str(uni.get('tuition_fee_annual'))
        living = parse_cost_str(uni.get('living_cost_annual'))
        total = parse_cost_str(uni.get('total_estimated_cost'))
        
        comparison.append({
            'id': uni.get('university_id'),
            'name': uni.get('university_name'),
            'country': uni.get('country'),
            'city': uni.get('city'),
            'tuition_fee': tuition,
            'living_cost': living,
            'total_cost': total or ((tuition or 0) + (living or 0)),
            'scholarships': uni.get('scholarships'),
            'program_level': uni.get('program_level'),
            'course': uni.get('course')
        })
    
    # Save comparison
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO fee_comparisons (user_id, university_ids, comparison_data)
                VALUES (?, ?, ?)
            ''', (user_id, json.dumps(university_ids), json.dumps(comparison)))
            conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Error saving comparison: {e}")
        finally:
            conn.close()
    
    return jsonify({'comparison': comparison, 'success': True})

# ============ Visa Probability Calculator ============

@app.route('/api/visa-probability', methods=['POST'])
@login_required
def calculate_visa_probability():
    """Calculate visa probability based on user profile"""
    user_id = session['user_id']
    data = request.get_json()
    
    country = data.get('country', '')
    visa_type = data.get('visa_type', 'Student')
    
    # Get user onboarding data
    answers = get_onboarding_answers(user_id)
    
    # Calculate probability score (0-100)
    score = 50  # Base score
    factors = []
    
    # Language proficiency
    lang_prof = (answers.get('question_8_language_proficiency') or '') if answers else ''
    if 'Native' in lang_prof or 'Fluent' in lang_prof:
        score += 20
        factors.append({'factor': 'Strong language proficiency', 'impact': '+20%'})
    elif 'Intermediate' in lang_prof:
        score += 10
        factors.append({'factor': 'Intermediate language skills', 'impact': '+10%'})
    
    # Academic readiness
    readiness = (answers.get('question_7_admission_readiness') or '') if answers else ''
    if 'Very Confident' in readiness:
        score += 15
        factors.append({'factor': 'Strong academic profile', 'impact': '+15%'})
    elif 'Confident' in readiness:
        score += 10
        factors.append({'factor': 'Good academic profile', 'impact': '+10%'})
    
    # Financial capability
    budget_max = answers.get('question_5_budget_max', 0) if answers else 0
    if budget_max > 50000:
        score += 15
        factors.append({'factor': 'Strong financial capability', 'impact': '+15%'})
    elif budget_max > 30000:
        score += 10
        factors.append({'factor': 'Good financial capability', 'impact': '+10%'})
    
    # Country-specific adjustments
    if country in ['Australia', 'Canada', 'UK']:
        score += 5
        factors.append({'factor': f'{country} has streamlined student visa process', 'impact': '+5%'})
    
    score = min(100, max(0, score))
    
    # Determine status
    if score >= 80:
        status = 'Excellent'
        status_color = 'green'
    elif score >= 60:
        status = 'Good'
        status_color = 'blue'
    elif score >= 40:
        status = 'Fair'
        status_color = 'yellow'
    else:
        status = 'Needs Improvement'
        status_color = 'red'
    
    result = {
        'score': round(score, 1),
        'status': status,
        'status_color': status_color,
        'factors': factors,
        'recommendations': [
            'Improve language proficiency (IELTS/TOEFL)' if score < 70 else 'Maintain strong language skills',
            'Strengthen financial documentation' if budget_max < 30000 else 'Ensure all financial documents are ready',
            'Prepare statement of purpose and recommendation letters',
            'Check specific visa requirements for ' + country
        ]
    }
    
    # Save assessment
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO visa_assessments (user_id, country, visa_type, probability_score, assessment_data)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, country, visa_type, score, json.dumps(result)))
            conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Error saving visa assessment: {e}")
        finally:
            conn.close()
    
    return jsonify(result)

# ============ Resume Builder ============

@app.route('/api/resume/templates', methods=['GET'])
@login_required
def get_resume_templates():
    """Get available resume templates"""
    templates = [
        {
            'id': 1,
            'name': 'Modern Professional',
            'description': 'Clean, ATS-friendly design perfect for tech and corporate roles',
            'preview': '/static/images/resume-modern.png',
            'color_scheme': 'blue'
        },
        {
            'id': 2,
            'name': 'Creative Designer',
            'description': 'Eye-catching layout ideal for creative industries',
            'preview': '/static/images/resume-creative.png',
            'color_scheme': 'purple'
        },
        {
            'id': 3,
            'name': 'Academic Scholar',
            'description': 'Traditional format suited for academic and research positions',
            'preview': '/static/images/resume-academic.png',
            'color_scheme': 'green'
        },
        {
            'id': 4,
            'name': 'Minimalist',
            'description': 'Simple and elegant design that highlights your achievements',
            'preview': '/static/images/resume-minimal.png',
            'color_scheme': 'gray'
        }
    ]
    return jsonify({'templates': templates})

@app.route('/api/resume/save', methods=['POST'])
@login_required
def save_resume():
    """Save user resume"""
    user_id = session['user_id']
    data = request.get_json()
    
    template_id = data.get('template_id')
    resume_data = data.get('resume_data')
    resume_title = data.get('resume_title', 'My Resume')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database error'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_resumes (user_id, template_id, resume_data, resume_title)
            VALUES (?, ?, ?, ?)
        ''', (user_id, template_id, json.dumps(resume_data), resume_title))
        conn.commit()
        resume_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'resume_id': resume_id})
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/resume/list', methods=['GET'])
@login_required
def list_resumes():
    """List user's saved resumes"""
    user_id = session['user_id']
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'resumes': []})
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, template_id, resume_title, created_at, updated_at
            FROM user_resumes
            WHERE user_id = ?
            ORDER BY updated_at DESC
        ''', (user_id,))
        rows = cursor.fetchall()
        resumes = [dict(row) for row in rows]
        cursor.close()
        conn.close()
        
        return jsonify({'resumes': resumes})
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'resumes': [], 'error': str(e)})

# ============ Location Explorer ============

@app.route('/api/nearby-places', methods=['GET'])
@login_required
def get_nearby_places():
    """Get nearby places for a university"""
    university_id = request.args.get('university_id', '')
    place_type = request.args.get('type', 'all')  # restaurants, jobs, tourist, accommodation, transport
    
    # Get university coordinates
    conn = get_db_connection()
    university = None
    
    if conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM universities WHERE university_id = ?', (str(university_id),))
        uni_row = cursor.fetchone()
        if uni_row:
            university = dict(uni_row)
        cursor.close()
        conn.close()
    
    if not university:
        # Try CSV fallback
        all_unis = csv_service.get_all_universities()
        for u in all_unis:
            if u.get('university_id') == str(university_id):
                university = u
                break
    
    if not university:
        return jsonify({'places': [], 'error': 'University not found'}), 404
    
    # Simulate nearby places data (in production, use Google Places API or similar)
    places = []
    
    # Restaurants
    if place_type in ['all', 'restaurants']:
        places.extend([
            {'name': 'International Cuisine Hub', 'type': 'restaurant', 'distance': '0.5 km', 'rating': 4.5, 'icon': 'fas fa-utensils'},
            {'name': 'Local Food Market', 'type': 'restaurant', 'distance': '0.8 km', 'rating': 4.3, 'icon': 'fas fa-utensils'},
            {'name': 'Budget-Friendly Cafe', 'type': 'restaurant', 'distance': '0.3 km', 'rating': 4.2, 'icon': 'fas fa-coffee'},
            {'name': 'Fine Dining Restaurant', 'type': 'restaurant', 'distance': '1.2 km', 'rating': 4.7, 'icon': 'fas fa-utensils'},
        ])
    
    # Part-time Job Spots
    if place_type in ['all', 'jobs']:
        places.extend([
            {'name': 'Shopping Mall - Jobs Available', 'type': 'jobs', 'distance': '0.6 km', 'rating': 4.0, 'icon': 'fas fa-briefcase', 'details': '100+ job openings'},
            {'name': 'Student Placement Office', 'type': 'jobs', 'distance': '0.2 km', 'rating': 4.8, 'icon': 'fas fa-briefcase'},
            {'name': 'Tech Startup Hub', 'type': 'jobs', 'distance': '1.5 km', 'rating': 4.6, 'icon': 'fas fa-code'},
            {'name': 'Retail Centers', 'type': 'jobs', 'distance': '0.9 km', 'rating': 3.9, 'icon': 'fas fa-store'},
        ])
    
    # Accommodation
    if place_type in ['all', 'accommodation']:
        places.extend([
            {'name': 'University Hostel', 'type': 'accommodation', 'distance': '0.1 km', 'rating': 4.2, 'icon': 'fas fa-building', 'price': '$150-200/month'},
            {'name': 'Private Student Housing', 'type': 'accommodation', 'distance': '0.7 km', 'rating': 4.4, 'icon': 'fas fa-home', 'price': '$200-350/month'},
            {'name': 'Apartment Rentals', 'type': 'accommodation', 'distance': '1.1 km', 'rating': 4.1, 'icon': 'fas fa-door-open', 'price': '$250-450/month'},
            {'name': 'Shared Student Flats', 'type': 'accommodation', 'distance': '0.5 km', 'rating': 4.3, 'icon': 'fas fa-users', 'price': '$180-280/month'},
        ])
    
    # Tourist Attractions
    if place_type in ['all', 'tourist']:
        places.extend([
            {'name': 'Historical Museum', 'type': 'tourist', 'distance': '2.0 km', 'rating': 4.6, 'icon': 'fas fa-landmark'},
            {'name': 'City Park', 'type': 'tourist', 'distance': '1.2 km', 'rating': 4.5, 'icon': 'fas fa-tree'},
            {'name': 'Cultural Center', 'type': 'tourist', 'distance': '1.8 km', 'rating': 4.4, 'icon': 'fas fa-theater-masks'},
            {'name': 'Shopping District', 'type': 'tourist', 'distance': '0.8 km', 'rating': 4.3, 'icon': 'fas fa-shopping-bags'},
        ])
    
    # Transportation
    if place_type in ['all', 'transport']:
        places.extend([
            {'name': 'Bus Station', 'type': 'transport', 'distance': '0.4 km', 'rating': 4.0, 'icon': 'fas fa-bus'},
            {'name': 'Metro Station', 'type': 'transport', 'distance': '0.9 km', 'rating': 4.5, 'icon': 'fas fa-train'},
            {'name': 'Taxi Stand', 'type': 'transport', 'distance': '0.3 km', 'rating': 3.8, 'icon': 'fas fa-taxi'},
            {'name': 'Bike Rental', 'type': 'transport', 'distance': '0.6 km', 'rating': 4.2, 'icon': 'fas fa-bicycle'},
        ])
    
    return jsonify({
        'university': {
            'name': university.get('university_name'),
            'city': university.get('city'),
            'country': university.get('country'),
            'lat': university.get('latitude') or 40.7128,
            'lng': university.get('longitude') or -74.0060
        },
        'places': places
    })

@app.route('/api/accommodation-comparison', methods=['GET'])
@login_required
def get_accommodation_comparison():
    """Compare accommodation options near universities"""
    user_id = session['user_id']
    university_ids = request.args.getlist('university_ids')
    
    if not university_ids:
        return jsonify({'comparison': []})
    
    comparisons = []
    conn = get_db_connection()
    
    for uni_id in university_ids:
        university = None
        
        if conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM universities WHERE university_id = ?', (str(uni_id),))
            uni_row = cursor.fetchone()
            if uni_row:
                university = dict(uni_row)
            cursor.close()
        
        if not university:
            all_unis = csv_service.get_all_universities()
            for u in all_unis:
                if u.get('university_id') == str(uni_id):
                    university = u
                    break
        
        if university:
            comparisons.append({
                'id': university.get('university_id'),
                'name': university.get('university_name'),
                'city': university.get('city'),
                'country': university.get('country'),
                'accommodations': [
                    {'name': 'University Hostel', 'type': 'Hostel', 'price': 150, 'distance': '0.1 km', 'rating': 4.2, 'capacity': 'Shared'},
                    {'name': 'Private Housing', 'type': 'Private', 'price': 300, 'distance': '0.7 km', 'rating': 4.4, 'capacity': 'Private'},
                    {'name': 'Shared Flat', 'type': 'Shared', 'price': 220, 'distance': '0.5 km', 'rating': 4.3, 'capacity': 'Shared'},
                    {'name': 'Apartment', 'type': 'Apartment', 'price': 400, 'distance': '1.1 km', 'rating': 4.1, 'capacity': 'Private'},
                ]
            })
    
    if conn:
        conn.close()
    
    # Calculate statistics
    all_prices = []
    for comp in comparisons:
        all_prices.extend([a['price'] for a in comp['accommodations']])
    
    stats = {
        'min_price': min(all_prices) if all_prices else 0,
        'max_price': max(all_prices) if all_prices else 0,
        'avg_price': sum(all_prices) / len(all_prices) if all_prices else 0
    }
    
    return jsonify({'comparison': comparisons, 'stats': stats})


# ==================== JOB MARKET & CAREER ==================== 
@app.route('/api/job-market', methods=['GET'])
@login_required
def get_job_market():
    """Get job market data by country/city"""
    country = request.args.get('country', '')
    city = request.args.get('city', '')
    
    # Job market data by region
    job_data = {
        'Australia': {
            'Melbourne': {
                'jobs': [
                    {'title': 'Software Engineer', 'salary': '90K-120K AUD', 'companies': 15, 'growth': '+12%', 'demand': 'Very High'},
                    {'title': 'Data Scientist', 'salary': '95K-130K AUD', 'companies': 12, 'growth': '+18%', 'demand': 'Very High'},
                    {'title': 'Product Manager', 'salary': '85K-125K AUD', 'companies': 8, 'growth': '+8%', 'demand': 'High'},
                    {'title': 'UX/UI Designer', 'salary': '75K-105K AUD', 'companies': 10, 'growth': '+15%', 'demand': 'High'},
                    {'title': 'Cloud Architect', 'salary': '100K-140K AUD', 'companies': 7, 'growth': '+22%', 'demand': 'Very High'},
                    {'title': 'Business Analyst', 'salary': '70K-100K AUD', 'companies': 14, 'growth': '+5%', 'demand': 'Medium'},
                ],
                'top_employers': ['Google Australia', 'Microsoft Australia', 'Amazon Australia', 'IBM Australia', 'Atlassian'],
                'avg_salary': 95000,
                'job_growth': '12%',
                'unemployment_rate': '3.5%'
            },
            'Sydney': {
                'jobs': [
                    {'title': 'Software Engineer', 'salary': '92K-125K AUD', 'companies': 18, 'growth': '+13%', 'demand': 'Very High'},
                    {'title': 'Finance Analyst', 'salary': '80K-115K AUD', 'companies': 20, 'growth': '+6%', 'demand': 'High'},
                    {'title': 'Marketing Manager', 'salary': '78K-110K AUD', 'companies': 16, 'growth': '+9%', 'demand': 'High'},
                    {'title': 'Data Engineer', 'salary': '98K-135K AUD', 'companies': 11, 'growth': '+20%', 'demand': 'Very High'},
                ],
                'top_employers': ['Commonwealth Bank', 'Westpac', 'NAB', 'ANZ', 'Telstra'],
                'avg_salary': 105000,
                'job_growth': '13%',
                'unemployment_rate': '3.2%'
            }
        },
        'Ethiopia': {
            'Addis Ababa': {
                'jobs': [
                    {'title': 'Software Developer', 'salary': '6K-10K ETB', 'companies': 8, 'growth': '+25%', 'demand': 'Very High'},
                    {'title': 'IT Support', 'salary': '4K-6K ETB', 'companies': 12, 'growth': '+15%', 'demand': 'High'},
                    {'title': 'Database Admin', 'salary': '7K-11K ETB', 'companies': 6, 'growth': '+20%', 'demand': 'Very High'},
                    {'title': 'Business Analyst', 'salary': '5K-8K ETB', 'companies': 10, 'growth': '+18%', 'demand': 'High'},
                ],
                'top_employers': ['Ethio Telecom', 'Commercial Bank of Ethiopia', 'Addis Software', 'Tech Innovation Hub'],
                'avg_salary': 7500,
                'job_growth': '25%',
                'unemployment_rate': '4.8%'
            }
        }
    }
    
    result = job_data.get(country, {}).get(city, {
        'jobs': [],
        'top_employers': [],
        'avg_salary': 0,
        'job_growth': '0%',
        'unemployment_rate': 'N/A'
    })
    
    return jsonify(result)


# ==================== SAFETY & CITY INSIGHTS ====================
@app.route('/api/safety-insights', methods=['GET'])
@login_required
def get_safety_insights():
    """Get safety and city insights data"""
    country = request.args.get('country', '')
    city = request.args.get('city', '')
    
    safety_data = {
        'Australia': {
            'Melbourne': {
                'safety_score': 8.5,
                'crime_rate': 'Low',
                'safety_index': 82,
                'nightlife_safety': 8.2,
                'women_safety': 8.8,
                'neighborhoods': [
                    {'name': 'Southbank', 'safety': 9.0, 'vibe': 'Cultural & Modern', 'cost': '$', 'students': 'High'},
                    {'name': 'Carlton', 'safety': 8.5, 'vibe': 'Academic & Vibrant', 'cost': '$', 'students': 'Very High'},
                    {'name': 'Fitzroy', 'safety': 8.0, 'vibe': 'Artsy & Alternative', 'cost': '$', 'students': 'Medium'},
                    {'name': 'Brunswick', 'safety': 8.3, 'vibe': 'Trendy & Young', 'cost': '$$', 'students': 'High'},
                ],
                'health_facilities': 15,
                'public_transport_safety': 9.0,
                'emergency_services': 'Excellent',
                'student_resources': ['24/7 Campus Security', 'Student Counseling', 'Emergency Hotlines', 'Campus Patrols'],
                'tips': ['Avoid walking alone late at night', 'Use well-lit areas', 'Trust local advice', 'Keep valuables hidden']
            },
            'Sydney': {
                'safety_score': 8.7,
                'crime_rate': 'Low',
                'safety_index': 85,
                'nightlife_safety': 8.5,
                'women_safety': 9.0,
                'neighborhoods': [
                    {'name': 'Darling Harbour', 'safety': 9.2, 'vibe': 'Entertainment Hub', 'cost': '$$', 'students': 'Very High'},
                    {'name': 'Newtown', 'safety': 8.1, 'vibe': 'Bohemian & Diverse', 'cost': '$', 'students': 'Very High'},
                    {'name': 'Parramatta', 'safety': 8.4, 'vibe': 'Growing Hub', 'cost': '$', 'students': 'Medium'},
                ],
                'health_facilities': 22,
                'public_transport_safety': 9.1,
                'emergency_services': 'Excellent',
                'student_resources': ['Campus Guard Service', 'Mental Health Support', 'Emergency Ride Home', 'Safety Workshops'],
                'tips': ['Beaches are safe during daylight', 'Use Opal card for transport', 'Beach safety flags available', 'Check local advice']
            }
        },
        'Ethiopia': {
            'Addis Ababa': {
                'safety_score': 7.2,
                'crime_rate': 'Moderate',
                'safety_index': 72,
                'nightlife_safety': 6.8,
                'women_safety': 7.0,
                'neighborhoods': [
                    {'name': 'Bole', 'safety': 8.0, 'vibe': 'Upscale & Modern', 'cost': '$$', 'students': 'Medium'},
                    {'name': 'Nifas Silk', 'safety': 7.5, 'vibe': 'University Area', 'cost': '$', 'students': 'Very High'},
                    {'name': 'Atlas', 'safety': 7.2, 'vibe': 'Mixed Use', 'cost': '$', 'students': 'Medium'},
                ],
                'health_facilities': 8,
                'public_transport_safety': 7.0,
                'emergency_services': 'Good',
                'student_resources': ['University Security', 'International Student Support', 'Emergency Hotline', 'Community Alerts'],
                'tips': ['Stay in student-friendly areas', 'Avoid traveling at night alone', 'Keep copies of documents', 'Register with embassy']
            }
        }
    }
    
    result = safety_data.get(country, {}).get(city, {
        'safety_score': 0,
        'crime_rate': 'Unknown',
        'neighborhoods': [],
        'student_resources': []
    })
    
    return jsonify(result)


# ==================== VISA CHECKLIST ====================
@app.route('/api/visa-checklist', methods=['GET'])
@login_required
def get_visa_checklist():
    """Get visa requirements and checklist"""
    country = request.args.get('country', '')
    
    visa_data = {
        'Australia': {
            'visa_type': 'Student Visa (Subclass 500)',
            'processing_time': '1-3 months',
            'validity': '5 years',
            'cost': 'AUD 550',
            'requirements': [
                {'item': 'Valid Passport', 'status': 'Mandatory', 'importance': 'Critical'},
                {'item': 'Confirmed Enrollment Letter', 'status': 'Mandatory', 'importance': 'Critical'},
                {'item': 'IELTS/TOEFL Score', 'status': 'Mandatory', 'importance': 'Critical'},
                {'item': 'Financial Evidence (AUD 50K+)', 'status': 'Mandatory', 'importance': 'Critical'},
                {'item': 'Medical Certificate (Form I693)', 'status': 'Mandatory', 'importance': 'Critical'},
                {'item': 'Police Clearance', 'status': 'Mandatory', 'importance': 'Critical'},
                {'item': 'Purpose of Stay Letter', 'status': 'Recommended', 'importance': 'High'},
                {'item': 'Bank Statements (6 months)', 'status': 'Mandatory', 'importance': 'High'},
                {'item': 'Tax Records', 'status': 'If applicable', 'importance': 'Medium'},
                {'item': 'Travel Insurance', 'status': 'Recommended', 'importance': 'Medium'},
            ],
            'work_rights': 'Can work up to 20 hours/week during study, full-time during breaks',
            'family_members': 'Can bring dependents',
            'post_study': 'Post-study work visa available for 2-5 years depending on qualification',
            'key_dates': [
                {'event': 'Application Opens', 'date': '2024-01-01'},
                {'event': 'Recommended Deadline', 'date': '2024-06-30'},
                {'event': 'Processing Begins', 'date': 'Upon Complete Submission'},
                {'event': 'Typical Decision', 'date': '6-12 weeks'},
            ],
            'contacts': {
                'embassy': 'Australian High Commission',
                'website': 'immi.homeaffairs.gov.au',
                'helpline': '+61-2-6261-3305'
            }
        },
        'Ethiopia': {
            'visa_type': 'Student Visa',
            'processing_time': '2-4 weeks',
            'validity': '1 year',
            'cost': 'Variable by nationality',
            'requirements': [
                {'item': 'Valid Passport', 'status': 'Mandatory', 'importance': 'Critical'},
                {'item': 'Enrollment Letter', 'status': 'Mandatory', 'importance': 'Critical'},
                {'item': 'Financial Proof', 'status': 'Mandatory', 'importance': 'Critical'},
                {'item': 'Medical Certificate', 'status': 'Required', 'importance': 'Critical'},
                {'item': 'Police Clearance', 'status': 'Recommended', 'importance': 'High'},
                {'item': 'Yellow Fever Vaccination', 'status': 'Mandatory', 'importance': 'Critical'},
                {'item': 'Travel Insurance', 'status': 'Recommended', 'importance': 'Medium'},
                {'item': 'Bank Statements', 'status': 'Recommended', 'importance': 'High'},
            ],
            'work_rights': 'Part-time work may be allowed with special permission',
            'family_members': 'Dependents possible with additional documents',
            'post_study': 'Work visa options available',
            'key_dates': [
                {'event': 'Application Opens', 'date': '2024-01-15'},
                {'event': 'Submission Deadline', 'date': '2024-07-15'},
                {'event': 'Initial Review', 'date': '1-2 weeks'},
                {'event': 'Approval Decision', 'date': '2-4 weeks'},
            ],
            'contacts': {
                'embassy': 'Ethiopian Immigration Office',
                'website': 'immigration.gov.et',
                'helpline': '+251-11-123-4567'
            }
        }
    }
    
    result = visa_data.get(country, {
        'visa_type': 'Student Visa',
        'requirements': [],
        'contacts': {}
    })
    
    return jsonify(result)


# ==================== AI INTERVIEW TRAINER ====================
@app.route('/api/interview-questions', methods=['GET'])
@login_required
def get_interview_questions():
    """Get interview questions by category"""
    category = request.args.get('category', 'general')
    
    questions_db = {
        'general': [
            {'id': 1, 'question': 'Tell me about yourself', 'category': 'Icebreaker', 'difficulty': 'Easy', 'tips': 'Keep it 2-3 minutes, focus on education and relevant experience'},
            {'id': 2, 'question': 'Why do you want to study abroad?', 'category': 'Motivation', 'difficulty': 'Easy', 'tips': 'Show genuine interest in their program and the country'},
            {'id': 3, 'question': 'What are your strengths and weaknesses?', 'category': 'Self-Assessment', 'difficulty': 'Medium', 'tips': 'Be honest but frame weaknesses positively'},
            {'id': 4, 'question': 'What is your 5-year plan?', 'category': 'Career Goals', 'difficulty': 'Medium', 'tips': 'Show ambition and how their program fits your goals'},
        ],
        'technical': [
            {'id': 5, 'question': 'Explain a technical project you worked on', 'category': 'Problem Solving', 'difficulty': 'Medium', 'tips': 'Use STAR method: Situation, Task, Action, Result'},
            {'id': 6, 'question': 'How do you approach learning new technologies?', 'category': 'Learning', 'difficulty': 'Medium', 'tips': 'Mention continuous learning and specific examples'},
            {'id': 7, 'question': 'Describe how you would solve a real-world problem', 'category': 'Critical Thinking', 'difficulty': 'Hard', 'tips': 'Think aloud, show your problem-solving process'},
        ],
        'behavioral': [
            {'id': 8, 'question': 'Tell me about a time you overcame a challenge', 'category': 'Resilience', 'difficulty': 'Medium', 'tips': 'Use STAR method, focus on what you learned'},
            {'id': 9, 'question': 'How do you handle working with people from different cultures?', 'category': 'Diversity', 'difficulty': 'Medium', 'tips': 'Show respect, adaptability, and cross-cultural communication'},
            {'id': 10, 'question': 'Describe a time you failed and how you handled it', 'category': 'Growth Mindset', 'difficulty': 'Hard', 'tips': 'Be honest, focus on learning and improvement'},
        ]
    }
    
    questions = questions_db.get(category, questions_db['general'])
    
    return jsonify({'questions': questions})


@app.route('/api/profile/stats', methods=['GET'])
@login_required
def get_profile_stats():
    """Get user profile statistics"""
    user_id = session['user_id']
    
    # Get user data
    user = get_user_by_id(user_id)
    answers = get_onboarding_answers(user_id)
    
    conn = get_db_connection()
    
    # Count matches
    perfect_matches = 0
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM university_matches WHERE user_id = ?", (user_id,))
            count_result = cursor.fetchone()
            perfect_matches = count_result[0] if count_result else 0
            
            # Count favorites
            cursor.execute("SELECT COUNT(*) FROM user_favorites WHERE user_id = ?", (user_id,))
            favorites_count = cursor.fetchone()[0]
            
            # Count scholarships found (estimated based on matches with scholarships)
            cursor.execute('''
                SELECT COUNT(DISTINCT m.university_id) 
                FROM university_matches m
                JOIN universities u ON u.id = m.university_id
                WHERE m.user_id = ? AND u.scholarships IS NOT NULL AND u.scholarships != ''
            ''', (user_id,))
            scholarships_with_unis = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error getting profile stats from DB: {e}")
            favorites_count = 0
            scholarships_with_unis = 0
    else:
        favorites_count = 0
        scholarships_with_unis = 0
    
    # If no matches in DB, use CSV fallback
    if perfect_matches == 0 and answers:
        all_matches = csv_service.calculate_matches_from_csv(answers, parse_cost_str)
        perfect_matches = len(all_matches)
        scholarships_with_unis = len([m for m in all_matches if m['university'].get('scholarships')])
    
    # Calculate profile completion percentage
    profile_complete = 0
    profile_items = 0
    
    if user:
        profile_items += 3  # username, email, first_name
        if user.get('username'):
            profile_complete += 1
        if user.get('email'):
            profile_complete += 1
        if user.get('first_name'):
            profile_complete += 1
    
    if answers:
        profile_items += 12  # onboarding questions
        profile_complete += 12  # All answers saved means 12 questions answered
    
    profile_percentage = int((profile_complete / max(profile_items, 1)) * 100) if profile_items > 0 else 0
    
    return jsonify({
        'perfect_matches': perfect_matches,
        'saved_universities': favorites_count,
        'scholarships_found': scholarships_with_unis,
        'profile_complete': profile_percentage,
        'user_joined': user.get('created_at') if user else 'Just now'
    })


@app.route('/api/interview-feedback', methods=['POST'])
@login_required
def submit_interview_feedback():
    """Submit interview response and get AI feedback"""
    data = request.get_json()
    question_id = data.get('question_id')
    response = data.get('response')
    
    if not response:
        return jsonify({'error': 'No response provided'}), 400
    
    # Analyze response with simple AI metrics
    word_count = len(response.split())
    has_examples = any(word in response.lower() for word in ['example', 'project', 'achieved', 'accomplished'])
    has_metrics = any(char.isdigit() for char in response)
    has_learning = any(word in response.lower() for word in ['learned', 'improved', 'realized', 'understood'])
    
    # Calculate score
    score = 0
    feedback_points = []
    
    if 100 <= word_count <= 200:
        score += 25
    elif 200 < word_count <= 300:
        score += 30
    else:
        feedback_points.append('Aim for 100-300 words for a complete answer')
    
    if has_examples:
        score += 25
    else:
        feedback_points.append('Include specific examples from your experience')
    
    if has_metrics:
        score += 20
    else:
        feedback_points.append('Use quantifiable metrics or results when possible')
    
    if has_learning:
        score += 15
    else:
        feedback_points.append('Mention what you learned from the experience')
    
    if not feedback_points:
        feedback_points.append('Excellent response! Keep up the great work.')
    
    # Save to database
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO interview_responses 
                (user_id, question_id, response_text, score, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (session['user_id'], question_id, response, score, datetime.now()))
            conn.commit()
        except Exception as e:
            print(f"Error saving response: {e}")
        finally:
            cursor.close()
            conn.close()
    
    return jsonify({
        'score': score,
        'feedback': feedback_points,
        'metrics': {
            'word_count': word_count,
            'has_examples': has_examples,
            'has_metrics': has_metrics,
            'has_learning': has_learning
        }
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)

