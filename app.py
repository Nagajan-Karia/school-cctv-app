import time
from flask import Flask, render_template, Response, request, redirect, url_for, session
import pandas as pd
import cv2

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_parents_portal'

# Tamari sachi Google Sheet ni Export CSV link cache buster sathe
GOOGLE_SHEET_CSV_URL = 'https://docs.google.com/spreadsheets/d/1TQPwH5gYpQ9u-KjRcnHUCCXZJy340NVkAkr-AH6DVAw/export?format=csv'

def get_user_data(username, password=None):
    try:
        # Link pachhal timestamp add karva thi google server cache nahi rakhe ane turant navo data avse
        cache_buster = f"{GOOGLE_SHEET_CSV_URL}&t={int(time.time())}"
        df = pd.read_csv(cache_buster)
        
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
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            error = 'Username athva password khali na hoi shake!'
            return render_template('login.html', error=error)
        
        user = get_user_data(username, password)
        if user:
            session