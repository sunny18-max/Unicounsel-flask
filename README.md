# 🎓 UniCounsel - University Matching Platform

A complete Flask-based web application for matching students with perfect universities based on their preferences, with AI-powered recommendations.

## 📋 Quick Setup Guide

### Prerequisites
- Python 3.8+
- MySQL Server (download: https://dev.mysql.com/downloads/mysql/)
- Git (optional)

### Installation Steps

#### Step 1: Ensure MySQL is Running

**Windows:**
```powershell
# Check if MySQL service is running
net start MySQL80

# Or verify:
mysql -u root
```

If MySQL is not installed, download and install it from: https://dev.mysql.com/downloads/mysql/

---

#### Step 2: Set MySQL Password (If Needed)

If your MySQL root user has a password:

```powershell
# Set environment variable (temporary - only for this session)
$env:MYSQL_PASSWORD = "your_mysql_password"

# Or set it permanently via System Settings:
# Windows Key > Edit environment variables > New User Variable
# Name: MYSQL_PASSWORD
# Value: your_mysql_password
```

If you DON'T have a password for MySQL root, no action needed.

---

#### Step 3: Install Python Dependencies

```powershell
cd C:\Users\saath\Downloads\unicounsel\uni_flask
pip install -r requirements.txt
```

---

#### Step 4: Initialize Database

```powershell
python setup.py
```

This will:
- ✅ Create the `unicounsel_db` database
- ✅ Create all necessary tables
- ✅ Load university data from CSV files

---

#### Step 5: Start the Flask Application

```powershell
python flask_app.py
```

You should see:
```
 * Running on http://127.0.0.1:5000
```

---

#### Step 6: Open in Browser

Navigate to: **http://localhost:5000**

---

## 🚀 Features

### ✨ Implemented Features

1. **User Authentication**
   - Email/Password signup & login
   - Google OAuth integration
   - Secure password hashing

2. **Onboarding Process**
   - 12-question personalized questionnaire
   - Covers: countries, study level, budget, scholarships, etc.
   - Progressive form with visual feedback

3. **Smart University Matching**
   - AI-powered matching algorithm
   - Considers: budget, location, programs, scholarships
   - Match score (0-100%) for each university
   - Only shows relevant matches

4. **Perfect Matches Page**
   - Browse all matched universities
   - Advanced filtering:
     - By country
     - By budget
     - By study level
     - By field of study
   - Sort by: Best Match, Lowest Cost, Name
   - Save/Shortlist functionality

5. **Interactive Dashboard**
   - Summary statistics
   - Top 5 matches display
   - Quick access to all features
   - Modern dark theme UI

6. **Data Management**
   - MySQL database integration
   - Real-time user preferences
   - Match history tracking
   - Favorite/Shortlist management

---

## 📂 Project Structure

```
uni_flask/
├── flask_app.py              # Main Flask application
├── db_config.py              # Database configuration
├── load_universities.py      # CSV data loader
├── setup.py                  # Setup script
├── requirements.txt          # Python dependencies
├── MYSQL_SETUP.md           # MySQL setup guide
├── README.md                # This file
│
├── templates/               # HTML templates
│   ├── landing.html        # Landing page
│   ├── login.html          # Login form
│   ├── signup.html         # Registration form
│   ├── onboarding.html     # Onboarding questions
│   ├── perfect_matches.html # Matches browser with filters
│   └── dashboard.html      # User dashboard
│
├── static/                  # Static files
│   ├── css/
│   │   ├── landing.css     # Landing page styles
│   │   ├── login.css       # Login/signup styles
│   │   └── onboarding.css  # Onboarding styles
│   └── js/
│       ├── landing.js      # Landing interactions
│       └── onboarding.js   # Onboarding logic
│
└── data/                   # University CSV data
    ├── argentina.csv
    └── australia.csv
```

---

## 🔧 Configuration

### Environment Variables

```powershell
# Set MySQL password (if you have one)
$env:MYSQL_PASSWORD = "your_password"

# Or set Flask debug mode
$env:FLASK_ENV = "development"
$env:FLASK_DEBUG = "1"
```

### Database Settings

Edit `db_config.py` to change:
- MySQL host (default: localhost)
- MySQL user (default: root)
- MySQL password (via environment variable)
- Database name (default: unicounsel_db)

---

## 🔌 API Endpoints

### Authentication
- `POST /login` - User login
- `POST /signup` - User registration
- `GET /auth/google` - Google OAuth login
- `GET /auth/google/callback` - OAuth callback
- `GET /logout` - User logout

### Onboarding
- `GET /onboarding` - Onboarding page
- `GET /api/onboarding/questions` - Get all questions
- `POST /api/onboarding/save` - Save responses

### Matching & Dashboard
- `GET /perfect-matches` - View all matches
- `GET /dashboard` - User dashboard
- `GET /api/matches` - Get matches (with filtering)
- `POST /api/matches/<id>/favorite` - Toggle favorite
- `POST /api/matches/<id>/shortlist` - Toggle shortlist
- `GET /api/dashboard/stats` - Dashboard statistics
- `GET /api/user/profile` - User profile

---

## 🗄️ Database Schema

### Users Table
```sql
- id (INT, PRIMARY KEY)
- email (VARCHAR, UNIQUE)
- username (VARCHAR)
- password_hash (VARCHAR)
- first_name (VARCHAR)
- last_name (VARCHAR)
- is_oauth_user (BOOLEAN)
- created_at (TIMESTAMP)
```

### Universities Table
```sql
- id (INT, PRIMARY KEY)
- university_id (VARCHAR, UNIQUE)
- name (VARCHAR)
- country (VARCHAR)
- city (VARCHAR)
- tuition_fee_annual (DECIMAL)
- total_cost_annual (DECIMAL)
- scholarships (VARCHAR)
- popular_courses (TEXT)
- image_url (VARCHAR)
```

### Onboarding Responses Table
```sql
- id (INT, PRIMARY KEY)
- user_id (INT, FOREIGN KEY)
- question_1_preferred_countries (TEXT)
- question_2_study_level (VARCHAR)
- question_3_preferred_stream (VARCHAR)
- question_4_duration_years (INT)
- question_5_budget_min/max (DECIMAL)
- ... (other questions)
- completed (BOOLEAN)
```

### University Matches Table
```sql
- id (INT, PRIMARY KEY)
- user_id (INT, FOREIGN KEY)
- university_id (INT, FOREIGN KEY)
- match_score (DECIMAL)
- match_reason (TEXT)
- is_favorite (BOOLEAN)
- is_shortlisted (BOOLEAN)
```

---

## 🎨 UI/UX Features

- **Modern Dark Theme** - Sleek, professional appearance
- **Responsive Design** - Works on desktop, tablet, mobile
- **Smooth Animations** - Gradient buttons, hover effects
- **Interactive Cards** - Expandable university cards
- **Real-time Filtering** - Instant search and filter results
- **Progress Indicators** - Visual feedback for onboarding
- **Color-coded Elements** - Cyan/Blue gradients for primary actions

---

## 🐛 Troubleshooting

### "Access denied for user 'root'@'localhost'"

**Solution:**
1. Ensure MySQL is running: `net start MySQL80`
2. Set your MySQL password: `$env:MYSQL_PASSWORD = "your_password"`
3. Run setup script: `python setup.py`

### "Connection refused"

**Solution:**
1. MySQL is not running
2. Check if MySQL service is started: `tasklist | findstr mysqld`
3. Start MySQL: `net start MySQL80`

### "Module not found"

**Solution:**
```powershell
pip install -r requirements.txt
```

### Database tables not created

**Solution:**
```powershell
# Delete old database (if exists)
mysql -u root -p -e "DROP DATABASE unicounsel_db;"

# Run setup again
python setup.py
```

---

## 📊 University Data

The app comes with university data from:
- **Argentina** (50+ universities)
- **Australia** (sample data)

Each university record includes:
- Official name and website
- Location (country, city, coordinates)
- Tuition and living costs
- Admission requirements
- Scholarships and facilities
- Contact information
- Popular programs

Data is automatically loaded into MySQL when you run `setup.py`

---

## 🔐 Security Notes

- Passwords are hashed with SHA-256
- Google OAuth for secure authentication
- Session-based access control
- CSRF protection ready
- SQL injection prevention via parameterized queries

**⚠️ For production:**
- Change `app.secret_key` to a secure random value
- Use environment variables for all secrets
- Enable HTTPS
- Use a production WSGI server (Gunicorn, uWSGI)
- Implement rate limiting

---

## 📱 User Flow

```
Landing Page
    ↓
[Login / Signup / Google OAuth]
    ↓
Onboarding (12 questions)
    ↓
Perfect Matches (with filtering)
    ↓
Dashboard (view stats, top matches)
    ↓
Select & Shortlist Universities
```

---

## 🚀 Next Steps

After setup, you can:

1. **Create a test account** - Sign up or use Google OAuth
2. **Complete onboarding** - Answer 12 questions
3. **View matches** - See universities matched to you
4. **Apply filters** - Narrow down by budget, country, etc.
5. **Save favorites** - Add to your favorites list
6. **Visit university websites** - Click on any university

---

## 📞 Support

For detailed MySQL setup help, see: [MYSQL_SETUP.md](./MYSQL_SETUP.md)

---

## 🎯 Features Coming Soon

- Interview preparation trainer
- Scholarship finder tools
- Document vault (SOP, Resume)
- AI mentor chatbot
- Cost calculator
- Visa checklist
- Safety & city insights
- Job market analysis
- And more!

---

## 📄 License

This project is part of the UniCounsel platform.

---

**Happy university hunting! 🎓✨**
