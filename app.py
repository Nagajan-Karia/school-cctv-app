from flask import Flask, render_template, Response, request, redirect, url_for, session
import pandas as pd
import cv2

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_parents_portal'

# તમારી Published Google Sheet ની CSV Link
GOOGLE_SHEET_CSV_URL = 'https://docs.google.com/spreadsheets/d/1TQPwH5gYpQ9u-KjRcnHUCCXZJy340NVkAkr-AH6DVAw/export?format=csv'

def get_user_data(username, password=None):
    try:
        # ઓનલાઈન ડેટા વાંચવા માટે read_csv નો ઉપયોગ
        df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        
        if password:
            user_row = df[(df['username'].astype(str) == str(username)) & (df['password'].astype(str) == str(password))]
        else:
            user_row = df[df['username'].astype(str) == str(username)]
            
        if not user_row.empty:
            row = user_row.iloc[0].to_dict()
            students = [s.strip() for s in str(row['student_names']).split(',')]
            cameras = [c.strip() for c in str(row['camera_urls']).split(',')]
            
            children = []
            for i in range(len(students)):
                cam = cameras[i] if i < len(cameras) else "0"
                children.append({'name': students[i], 'cam_id': i, 'url': cam})
                
            return {
                'username': row['username'],
                'children': children
            }
    except Exception as e:
        print("Google Sheet Read Error:", e)
    return None

@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        # strip() થી આગળ-પાછળની સ્પેસ દૂર થશે
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            error = 'યુઝરનેમ અથવા પાસવર્ડ ખાલી ન હોઈ શકે!'
            return render_template('login.html', error=error)
        
        user = get_user_data(username, password)
        if user:
            session['user'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            error = 'ખોટો યુઝરનેમ અથવા પાસવર્ડ!'
            
    return render_template('login.html', error=error)

def generate_frames(camera_source):
    if str(camera_source) == '0':
        cam_id = 0
    else:
        cam_id = camera_source
        
    camera = cv2.VideoCapture(cam_id)
    
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_data = get_user_data(session['user'])
    return render_template('dashboard.html', user