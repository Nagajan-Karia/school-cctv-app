import time
import csv
import io
import requests
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here'

# Google Sheet CSV Export Link
GOOGLE_SHEET_CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vS728I7LC85EHEzmjI2CGuVKmqQunHBPDPyUpEeir4ohxGcUvSovxh8qH-AI0_lNqqCbKiXMG16POS5/pub?output=csv'

def get_user_data(username, password=None):
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
                row = {k.replace('\ufeff', '').strip().lower(): v.strip() for k, v in row.items() if k}
                
                row_user = str(row.get('username', '')).strip()
                row_pass = str(row.get('password', '')).strip().replace('.0', '')
                
                if row_user == clean_user:
                    if clean_pass is None or row_pass == clean_pass:
                        students = [s.strip() for s in row.get('student_names', 'Student').split(',') if s.strip()]
                        cameras = [c.strip() for c in row.get('camera_urls', '0').split(',') if s.strip()]
                        
                        children = []
                        for i in range(len(students)):
                            cam = cameras[i] if i < len(cameras) else "0"
                            children.append({'name': students[i], 'cam_id': i, 'url': cam})
                            
                        return {
                            'username': row_user,
                            'children': children
                        }
        else:
            print(f"Google Sheet HTTP Error: {response.status_code}")
    except Exception as e:
        print("Google Sheet Read Error:", e)
    return None

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_data = get_user_data(username, password)
        if user_data:
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
        session.pop('user', None)
        return redirect(url_for('login'))
        
    return render_template('dashboard.html', user_data=user_data)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)