#!/usr/bin/env python3
"""
CSV Data Service - Fallback when SQLite database is unavailable
Provides data fetching from CSV files as a backup mechanism
"""

import csv
import os
import json
from pathlib import Path

class CSVDataService:
    """Service to read data from CSV files when database is unavailable"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.data_dir = self.base_dir / 'data'
        self.parent_data_dir = self.base_dir.parent / 'data'
        self._universities_cache = None
    
    def _parse_cost_str(self, cost_str):
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
    
    def _parse_float(self, value):
        """Parse float value from string"""
        if not value:
            return None
        try:
            return float(value)
        except:
            return None
    
    def _load_universities_from_csv(self):
        """Load universities from all CSV files in the data folder"""
        if self._universities_cache is not None:
            return self._universities_cache
        
        universities = []
        idx_counter = 1
        
        # Find all CSV files in both data directories
        csv_files = []
        if self.parent_data_dir.exists():
            csv_files.extend(list(self.parent_data_dir.glob('*_final.csv')))
            print(f"Found {len(list(self.parent_data_dir.glob('*_final.csv')))} CSV file(s) in parent data folder")
        if self.data_dir.exists():
            csv_files.extend(list(self.data_dir.glob('*.csv')))
            print(f"Found {len(list(self.data_dir.glob('*.csv')))} CSV file(s) in local data folder")
        
        if not csv_files:
            print(f"No CSV files found in {self.data_dir} or {self.parent_data_dir}")
            return universities
        
        print(f"Total: {len(csv_files)} CSV file(s) to process")
        
        # Load from each CSV file
        for csv_path in csv_files:
            try:
                print(f"Loading from {csv_path.name}...")
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Check if this CSV has the detailed format (australia_courses_clean_final.csv)
                        if 'University ID' in row and 'University Name' in row:
                            university = {
                                'id': idx_counter,
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
                                'latitude': self._parse_float(row.get('Latitude')),
                                'longitude': self._parse_float(row.get('Longitude')),
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
                        else:
                            # Basic CSV format fallback
                            university = {
                                'id': idx_counter,
                                'university_id': row.get('University ID', ''),
                                'university_name': row.get('University Name', '') or row.get('University name', '') or row.get('name', ''),
                                'official_website': row.get('Official Website', '') or row.get('URL', '') or row.get('website', ''),
                                'email_inquiry': row.get('Email (Inquiry)', '') or row.get('email', ''),
                                'phone_number': row.get('Phone Number', '') or row.get('phone', ''),
                                'address': row.get('Address', '') or row.get('address', ''),
                                'country': row.get('Country', '') or row.get('country', ''),
                                'state': row.get('State', '') or row.get('state', ''),
                                'city': row.get('City', '') or row.get('city', ''),
                                'zip_code': row.get('Zip Code', '') or row.get('zip_code', ''),
                                'latitude': self._parse_float(row.get('Latitude') or row.get('latitude')),
                                'longitude': self._parse_float(row.get('Longitude') or row.get('longitude')),
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
                        idx_counter += 1
                
                print(f"  Loaded universities from {csv_path.name}")
            except Exception as e:
                print(f"Error reading CSV {csv_path.name}: {e}")
        
        print(f"Total loaded: {len(universities)} universities from CSV files")
        self._universities_cache = universities
        return universities
    
    def get_all_universities(self):
        """Get all universities from CSV"""
        return self._load_universities_from_csv()
    
    def get_countries(self):
        """Get unique countries from universities"""
        universities = self._load_universities_from_csv()
        countries = set()
        for uni in universities:
            country = uni.get('country')
            if country and country.strip():
                countries.add(country.strip())
        return sorted(list(countries))
    
    def search_universities(self, filters=None):
        """Search universities with filters"""
        universities = self._load_universities_from_csv()
        
        if not filters:
            return universities
        
        filtered = universities
        
        # Filter by country
        if filters.get('country'):
            filtered = [u for u in filtered if u.get('country', '').lower() == filters['country'].lower()]
        
        # Filter by budget
        if filters.get('budget_min') or filters.get('budget_max'):
            budget_min = filters.get('budget_min', 0)
            budget_max = filters.get('budget_max', 999999999)
            filtered = [u for u in filtered 
                       if budget_min <= self._parse_cost_str(u.get('total_estimated_cost', '0')) <= budget_max]
        
        # Filter by program level
        if filters.get('program_level'):
            filtered = [u for u in filtered 
                       if filters['program_level'].lower() in u.get('program_level', '').lower()]
        
        # Filter by course/stream
        if filters.get('stream'):
            stream = filters['stream'].lower()
            filtered = [u for u in filtered 
                       if stream in u.get('course', '').lower()]
        
        return filtered
    
    def calculate_matches_from_csv(self, user_answers, parse_cost_func=None):
        """Calculate matches directly from CSV data based on user onboarding answers"""
        if parse_cost_func is None:
            parse_cost_func = self._parse_cost_str
        
        universities = self._load_universities_from_csv()
        matches = []
        
        # Extract user preferences
        preferred_countries_str = user_answers.get('question_1_preferred_countries') or ''
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
        
        budget_min = user_answers.get('question_5_budget_min') or 0
        budget_max = user_answers.get('question_5_budget_max') or 100000
        study_level = (user_answers.get('question_2_study_level') or '').lower()
        preferred_stream = (user_answers.get('question_3_preferred_stream') or '').lower()
        scholarship_need = user_answers.get('question_11_scholarship_need')
        needs_scholarship = scholarship_need == 1 or scholarship_need == True or str(scholarship_need).lower() == 'true'
        
        weights = {
            'country': 0.25,
            'budget': 0.25,
            'level': 0.15,
            'stream': 0.15,
            'scholarships': 0.10,
            'services': 0.10
        }
        
        for uni in universities:
            score = 0
            
            # Country match
            uni_country = (uni.get('country') or '').strip()
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
            total_cost_val = None
            if uni.get('total_estimated_cost'):
                total_cost_val = parse_cost_func(uni.get('total_estimated_cost'))
            
            # Try to calculate from tuition + living if total not available
            if total_cost_val is None:
                tuition_val = parse_cost_func(uni.get('tuition_fee_annual'))
                living_val = parse_cost_func(uni.get('living_cost_annual'))
                if tuition_val is not None or living_val is not None:
                    total_cost_val = (tuition_val or 0) + (living_val or 0)
            
            # Score based on budget match
            if total_cost_val is None:
                score += 50 * weights['budget']  # Neutral score for missing data
            elif budget_min <= total_cost_val <= budget_max:
                score += 100 * weights['budget']
            elif total_cost_val < budget_min:
                score += 80 * weights['budget']
            elif total_cost_val <= budget_max * 1.2:
                score += 60 * weights['budget']
            else:
                score += 20 * weights['budget']
            
            # Study level match
            program_level = (uni.get('program_level') or '').lower()
            if study_level and study_level in program_level:
                score += 100 * weights['level']
            else:
                score += 70 * weights['level']
            
            # Stream/Field match
            uni_courses = (uni.get('course') or '').lower()
            if preferred_stream and preferred_stream in uni_courses:
                score += 100 * weights['stream']
            elif not preferred_stream:
                score += 70 * weights['stream']
            else:
                score += 40 * weights['stream']
            
            # Scholarships
            scholarships = uni.get('scholarships') or ''
            if needs_scholarship and scholarships:
                score += 100 * weights['scholarships']
            elif scholarships:
                score += 50 * weights['scholarships']
            elif needs_scholarship and not scholarships:
                score += 10 * weights['scholarships']
            
            # International services
            intl_services = uni.get('intl_services') or ''
            if intl_services:
                score += 100 * weights['services']
            
            final_score = min(score, 100)
            
            # Only include universities with a reasonable match score (20+)
            if final_score < 20:
                continue
            
            # Generate match reason
            reasons = []
            if final_score >= 80:
                reasons.append("Excellent match for your profile")
            elif final_score >= 60:
                reasons.append("Good match for your preferences")
            else:
                reasons.append("Fair match")
            
            if uni_country and preferred_countries and any(uni_country.lower() == pc.lower() or uni_country.lower() in pc.lower() or pc.lower() in uni_country.lower() for pc in preferred_countries):
                reasons.append(f"Located in your preferred country: {uni_country}")
            
            matches.append({
                'university': uni,
                'match_score': round(final_score, 2),
                'match_reason': "; ".join(reasons),
                'is_favorite': False,
                'is_shortlisted': False
            })
        
        # Deduplicate by university_id, keeping the best match score for each university
        unique_matches = {}
        for match in matches:
            uni_id = match['university'].get('university_id')
            if not uni_id:
                uni_id = match['university'].get('university_name', '').lower().strip()
            
            if uni_id not in unique_matches or match['match_score'] > unique_matches[uni_id]['match_score']:
                unique_matches[uni_id] = match
        
        # Convert back to list and sort by match score descending
        final_matches = list(unique_matches.values())
        final_matches.sort(key=lambda x: x['match_score'], reverse=True)
        return final_matches

# Global instance
csv_service = CSVDataService()