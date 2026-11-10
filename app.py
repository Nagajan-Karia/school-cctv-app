from flask import Flask, render_template, Response, request, redirect, url_for, session
import pandas as pd
import cv2

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_parents_portal'

EXCEL_FILE = 'parents_data.xlsx'

def get_user_data(username, password=None):
    try:
        df = pd.read_excel(EXCEL_FILE)
        if password:
            user_row = df[(df['username'].astype(str) == str(username)) & (df['password'].astype(str) == str(password))]
        else:
            user_row = df[df['username'].astype(str) == str(username)]
            
        if not user_row.empty:
            row = user_row.iloc[0].to_dict()
            # કોમાથી અલગ પડેલા નામો અને કેમેરા URL ને લિસ્ટમાં કન્વર્ટ કરો
            students = [s.strip() for s in str(row['student_names']).split(',')]
            cameras = [c.strip() for c in str(row['camera_urls']).split(',')]
            
            # બાળક અને કેમેરા ની જોડ (Pair) બનાવો
            children = []
            for i in range(len(students)):
                cam = cameras[i] if i < len(cameras) else "0"
                children.append({'name': students[i], 'cam_id': i, 'url': cam})
                
            return {
                'username': row['username'],
                'children': children
            }
    except Exception as e:
        print("Excel Read Error:", e)
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
        username = request.form['username']
        password = request.form['password']
        
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
    return render_template('dashboard.html', user=user_data['username'], children=user_data['children'])

@app.route('/video_feed/<int:child_id>')
def video_feed(child_id):
    if 'user' not in session:
        return "Unauthorized", 401
    
    user_data = get_user_data(session['user'])
    if user_data and child_id < len(user_data['children']):
        cam_url = user_data['children'][child_id]['url']
        return Response(generate_frames(cam_url), mimetype='multipart/x-mixed-replace; boundary=frame')
    return "Camera Not Found", 404

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)