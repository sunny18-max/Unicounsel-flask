#!/usr/bin/env python3
"""
Script to load universities from CSV files into the SQLite database
"""

import csv
import os
from db_config import create_database, create_tables, get_db_connection
from pathlib import Path

def parse_csv_file(file_path):
    """Parse CSV file and return list of university dictionaries"""
    universities = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                university = {
                    'university_id': row.get('University ID', ''),
                    'university_name': row.get('University Name', ''),
                    'official_website': row.get('Official Website', ''),
                    'email_inquiry': row.get('Email (Inquiry)', ''),
                    'phone_number': row.get('Phone Number', ''),
                    'address': row.get('Address', ''),
                    'country': row.get('Country', ''),
                    'state': row.get('State', ''),
                    'city': row.get('City', ''),
                    'zip_code': row.get('Zip Code', ''),
                    'latitude': row.get('Latitude', ''),
                    'longitude': row.get('Longitude', ''),
                    'campus_type': row.get('Campus Type', ''),
                    'established': row.get('Established', ''),
                    'duration_undergraduation_course': row.get('duration of undergraduation course', ''),
                    'duration_postgraduation_course': row.get('duration of postgraduation course', ''),
                    'duration_phd_course': row.get('duration of phd course', ''),
                    'duration_diploma_course': row.get('duration of diploma course', ''),
                    'duration_online_course': row.get('duration of online course', ''),
                    'admission_req': row.get('Admission Req', ''),
                    'cgpa': row.get('CGPA', ''),
                    'ielts': row.get('IELTS', ''),
                    'sat_gre_gmat': row.get('SAT/GRE/GMAT', ''),
                    'deadline_sem1': row.get('Deadline (Sem 1)', ''),
                    'academic_calendar': row.get('Academic Calendar', ''),
                    'medium': row.get('Medium', ''),
                    'tuition_fee_annual': row.get('Tuition Fee (Annual)', ''),
                    'living_cost_annual': row.get('Living Cost (Annual)', ''),
                    'total_estimated_cost': row.get('Total Estimated Cost', ''),
                    'scholarships': row.get('Scholarships', ''),
                    'intl_services': row.get('Intl Services', ''),
                    'accommodation': row.get('Accommodation', ''),
                    'airport_pickup': row.get('Airport Pickup', ''),
                    'pre_arrival': row.get('Pre-arrival', ''),
                    'documents_required': row.get('Documents Required', ''),
                    'image_url': row.get('Image URL', ''),
                    'program_level': row.get('Program Level', ''),
                    'course': row.get('Course', '')
                }
                universities.append(university)
    except Exception as e:
        print(f"Error reading CSV file {file_path}: {e}")
    
    return universities

def parse_float(value):
    """Parse float value from string"""
    if not value:
        return None
    try:
        return float(value)
    except:
        return None

def parse_cost(cost_str):
    """Parse cost string and return average as decimal"""
    if not cost_str:
        return None
    
    try:
        # Remove common separators and spaces, handle currency symbols
        cost_str = str(cost_str).strip().replace('$', '').replace(',', '').replace(' ', '').replace('AUS', '').replace('USD', '')
        
        # Handle ranges like "8500-12000" or "AUS $45000-68000"
        if '-' in cost_str:
            parts = cost_str.split('-')
            if len(parts) == 2:
                min_val = float(parts[0])
                max_val = float(parts[1])
                return (min_val + max_val) / 2
        
        # Try direct conversion
        return float(cost_str)
    except:
        return None

def insert_universities(universities):
    """Insert universities into the SQLite database"""
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to database")
        return

    cursor = connection.cursor()

    # Define columns in exact order as in the universities table / CSV
    columns = [
        'university_id',
        'university_name',
        'official_website',
        'email_inquiry',
        'phone_number',
        'address',
        'country',
        'state',
        'city',
        'zip_code',
        'latitude',
        'longitude',
        'campus_type',
        'established',
        'duration_undergraduation_course',
        'duration_postgraduation_course',
        'duration_phd_course',
        'duration_diploma_course',
        'duration_online_course',
        'admission_req',
        'cgpa',
        'ielts',
        'sat_gre_gmat',
        'deadline_sem1',
        'academic_calendar',
        'medium',
        'tuition_fee_annual',
        'living_cost_annual',
        'total_estimated_cost',
        'scholarships',
        'intl_services',
        'accommodation',
        'airport_pickup',
        'pre_arrival',
        'documents_required',
        'image_url',
        'program_level',
        'course',
    ]

    placeholders = ', '.join(['?'] * len(columns))
    insert_query = f'''
    INSERT OR REPLACE INTO universities (
        {', '.join(columns)}
    ) VALUES ({placeholders})
    '''

    count = 0
    for uni in universities:
        try:
            values = [uni.get(col) for col in columns]
            cursor.execute(insert_query, values)
            count += 1
        except Exception as e:
            print(f"Error inserting university {uni.get('university_name', 'Unknown')}: {e}")

    connection.commit()
    cursor.close()
    connection.close()

    print(f"Successfully inserted/updated {count} universities")

def main():
    """Main function to load all CSV data from data folder"""
    print("Starting university data import...")
    
    # Create database and tables
    create_database()
    create_tables()
    
    # Find and load all CSV files - check both parent data folder and local data folder
    parent_data_dir = Path(__file__).parent.parent / 'data'
    local_data_dir = Path(__file__).parent / 'data'
    
    csv_files = []
    if parent_data_dir.exists():
        csv_files.extend(list(parent_data_dir.glob('*_final.csv')))
    if local_data_dir.exists():
        csv_files.extend(list(local_data_dir.glob('*.csv')))
    
    if not csv_files:
        print(f"No CSV files found in {parent_data_dir} or {local_data_dir}")
        print("Please ensure CSV files are in the 'data' folder")
        return
    
    print(f"Found {len(csv_files)} CSV files in data folder")
    
    all_universities = []
    for csv_file in csv_files:
        print(f"Processing {csv_file.name}...")
        universities = parse_csv_file(str(csv_file))
        print(f"  - Found {len(universities)} universities in {csv_file.name}")
        all_universities.extend(universities)
    
    print(f"\nTotal universities to import: {len(all_universities)}")
    
    if all_universities:
        insert_universities(all_universities)
        print("\nData import completed successfully!")
    else:
        print("No universities found to import")

if __name__ == '__main__':
    main()
