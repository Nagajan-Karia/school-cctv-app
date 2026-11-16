import os
import time
import csv
import io
import requests
from flask import Flask, render_template, request, redirect, url_for, session, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

# 1. Environment variable mathi Secret Key ane Sheet URL load karo
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
GOOGLE_SHEET_CSV_URL = os.environ.get('GOOGLE_SHEET_CSV_URL')

# 2. Session Cookie Security (Cookie Hijacking ane XSS protection mate)
app.config.update(
    SESSION_COOKIE_SECURE=True,      # Fakt HTTPS par j cookie mokalse
    SESSION_COOKIE_HTTPONLY=True,    # JavaScript thi cookie access nahi thay
    SESSION_COOKIE_SAMESITE='Lax',   # CSRF protection mate
)

# 3. Rate Limiter Setup (Brute-force attack rokva mate)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def get_user_data(username, password=None):
    if not GOOGLE_SHEET_CSV_URL:
        print("Error: GOOGLE_SHEET_CSV_URL set nathi!")
        return None
    try:
        separator = "&" if "?" in GOOGLE_SHEET_CSV_URL else "?"
        cache_buster_url = f"{GOOGLE_SHEET_CSV_URL}{separator}t={int(time.time())}"
        
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
        response = requests.get(cache_buster_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            f = io.StringIO(response.text)
            reader = csv.DictReader(f)
            
            clean_user = str(username).strip()
            clean_pass = str(password).strip() if password is not None else None
            
            for row in reader:
                cleaned_row = {}
                for k, v in row.items():
                    if k:
                        new_key = k.replace('\ufeff', '').strip().lower()
                        cleaned_row[new_key] = v.strip() if v else ''
                
                row_user = str(cleaned_row.get('username', '')).strip()
                row_pass = str(cleaned_row.get('password', '')).strip()
                
                if row_user == clean_user:
                    if clean_pass is None or row_pass == clean_pass:
                        student_raw = cleaned_row.get('student_names', 'Student')
                        camera_raw = cleaned_row.get('camera_urls', '0')
                        
                        students = [item.strip() for item in student_raw.split(',') if item.strip()]
                        cameras = [item.strip() for item in camera_raw.split(',') if item.strip()]
                        
                        children = []
                        for i in range(len(students)):
                            cam = cameras[i] if i < len(cameras) else "0"
                            children.append({'name': students[i], 'cam_id': i, 'url': cam})
                            
                        return {
                            'username': row_user,
                            'children': children
                        }
    except Exception as e:
        print("Google Sheet Read Error:", e)
    return None

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # 1 મિનિટમાં ફક્ત 5 જ વાર લોગઈન ટ્રાય કરી શકાશે (Brute-force protection)
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        user_data = get_user_data(username, password)
        if user_data:
            session.clear() # Session fixation attack rokva mate
            session['user'] = user_data['username']
            return redirect(url_for('dashboard'))
        else:
            error = 'ખોટો યુઝરનેમ અથવા પાસવર્ડ!'
            
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    username = session['user']
    user_data = get_user_data(username)
    
    if not user_data:
        session.clear()
        return redirect(url_for('login'))
        
    return render_template('dashboard.html', user_data=user_data)

# Secure Proxy Route (Direct URL leak thavathi rokva mate)
@app.route('/stream/<int:cam_id>')
def stream(cam_id):
    if 'user' not in session:
        return "Unauthorized Access", 403
        
    username = session['user']
    user_data = get_user_data(username)
    
    if not user_data or cam_id >= len(user_data['children']):
        return "Access Denied", 403
        
    camera_url = user_data['children'][cam_id]['url']
    
    if not camera_url or camera_url == '0':
        return "Camera not available", 404

    def generate():
        try:
            req = requests.get(camera_url, stream=True, timeout=10)
            for chunk in req.iter_content(chunk_size=1024):
                if chunk:
                    yield chunk
        except Exception as e:
            print("Stream Error:", e)

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)