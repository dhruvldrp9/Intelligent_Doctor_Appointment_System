from flask import Flask, jsonify,render_template, request, redirect, url_for, flash, session
import psycopg2
from Doctor_Appointment_System.Intelligent_LLM.initialize_llm import GPTConversationSystem
import os

app = Flask(__name__, template_folder=os.path.join('Doctor_Appointment_System', 'Templates'))
# app.secret_key = 'your_secret_key_here'  # Change this to a secure secret key
# Set the secret key to a random, unique, and secret value
app.secret_key = 'your_secret_key_here'

# Alternatively, use a secure random value
app.secret_key = os.urandom(24)

# Database connection helper
def get_db_connection():
    try:
        return psycopg2.connect(
            host='localhost',
            database='patientapp',
            user='postgres',
            password='12345'
        )
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        return None
    
# Authentication decorator
def login_required(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# Routes for authentication
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/doctor_login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        doc_id = request.form['doc_id']
        password = request.form['password']
        
        conn = get_db_connection()
        conn = conn.cursor()
        doctor = conn.execute('SELECT * FROM doctors WHERE doc_id = %s AND password = %s',
                            (doc_id,password))
        doctor = conn.fetchone()
        conn.close()
        
        if doctor:
            session['user_id'] = doc_id
            session['user_type'] = 'doctor'
            flash('Login successful!')
            return redirect(url_for('doctor_dashboard'))
        flash('Invalid credentials')
    return render_template('doctor_login.html')

@app.route('/patient_login', methods=['GET', 'POST'])
def patient_login():
    if request.method == 'POST':
        phone_number = request.form['phone_number']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()  # Create a cursor object
        cursor.execute('SELECT * FROM patients WHERE phone_number = %s AND password = %s', 
                       (phone_number, password))
        patient = cursor.fetchone()  # Fetch the first matching row
        cursor.close()
        conn.close()
        
        if patient:  # Check if a record is found
            session['user_id'] = phone_number
            session['user_type'] = 'patient'
            flash('Login successful!')
            return redirect(url_for('patient_dashboard'))
        flash('Invalid credentials')
    return render_template('patient_login.html')

# Doctor routes
@app.route('/doctor_dashboard')
@login_required
def doctor_dashboard():
    if session['user_type'] != 'doctor':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    conn = conn.cursor()
    appointments = conn.execute('''
        SELECT * FROM doctorappointments 
        WHERE docid = %s AND appointmentdate >= date('now')
        ORDER BY appointmentdate
    ''', (session['user_id'],))
    
    appointments = conn.fetchall()
    conn.execute('SELECT first_name, last_name FROM doctors WHERE doc_id = %s', (session['user_id'],))
    user = conn.fetchone()
    conn.close()
    
    return render_template('doctor_dashboard.html', appointments=appointments, doctor=user)

@app.route('/admin/appointments')
@login_required
def view_all_appointments():
    if session['user_type'] != 'admin':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    conn = conn.cursor()
    appointments = conn.execute('''
        SELECT 
            da.appointmentdate,
            da.patientname,
            da.patientnum,
            d.first_name as doctor_first_name,
            d.last_name as doctor_last_name,
            d.speciality
        FROM doctorappointments da
        JOIN doctors d ON da.docid = d.doc_id
        WHERE da.appointmentdate >= date('now')
        ORDER BY da.appointmentdate
    ''')
    appointments = conn.fetchall()
    conn.close()
    
    return render_template('admin_appointments.html', appointments=appointments)

# Patient routes
@app.route('/patient_dashboard')
@login_required
def patient_dashboard():
    if session['user_type'] != 'patient':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    conn = conn.cursor()
    conn.execute('''
        SELECT d.first_name, d.last_name, d.speciality, da.appointmentdate
        FROM doctorappointments da
        JOIN doctors d ON da.docid = d.doc_id
        WHERE da.patientnum = %s
        AND appointmentdate >= date('now')
        ORDER BY appointmentdate
    ''', (session['user_id'],))

    appointments = conn.fetchall()
    conn.execute('SELECT first_name, last_name FROM patients WHERE phone_number = %s', (session['user_id'],))
    user = conn.fetchone()
    conn.close()
    
    return render_template('patient_dashboard.html', appointments=appointments, user=user)

@app.route('/book_appointment', methods=['GET', 'POST'])
@login_required
def book_appointment():
    if session['user_type'] != 'patient':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        doc_id = request.form['doctor']
        appointment_date = request.form['appointment_date']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        # Fetch patient details
        cursor.execute('SELECT first_name, last_name FROM patients WHERE phone_number = %s', (session['user_id'],))
        patient = cursor.fetchone()
        
        if patient is None:
            flash('Patient not found!')
            return redirect(url_for('book_appointment'))
        patient_name = f"{patient[0]} {patient[1]}"
        # Insert appointment
        cursor.execute('''
            INSERT INTO doctorappointments (docid, patientname, patientnum, appointmentdate)
            VALUES (%s, %s, %s, %s)
        ''', (doc_id, patient_name, session['user_id'], appointment_date))
        
        conn.commit()
        conn.close()
        
        flash('Appointment booked successfully!')
        return redirect(url_for('patient_dashboard'))
    
    conn = get_db_connection()
    conn = conn.cursor()
    doctors = conn.execute('SELECT * FROM doctors WHERE status = 1')
    doctors = conn.fetchall()
    conn.close()
    
    return render_template('book_appointment.html', doctors=doctors)

# Admin routes for managing doctors and patients
@app.route('/admin/doctors', methods=['GET', 'POST'])
@login_required
def manage_doctors():
    if session['user_type'] != 'admin':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        dob = request.form['dob']
        phone_number = request.form['phone_number']
        address = request.form['address']
        doc_id = request.form['doc_id']
        password = request.form['password']
        speciality = request.form['speciality']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO doctors (first_name, last_name, dob, phone_number, address, 
                               doc_id, password, speciality, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)
        ''', (first_name, last_name, dob, phone_number, address, doc_id, password, speciality))
        conn.commit()
        cursor.close()
        
        flash('Doctor added successfully!')
        return redirect(url_for('manage_doctors'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    doctors = cursor.execute('SELECT * FROM doctors')
    doctors = cursor.fetchall()
    conn.close()
    
    return render_template('manage_doctors.html', doctors=doctors)

@app.route('/admin/patients', methods=['GET', 'POST'])
@login_required
def manage_patients():
    if session['user_type'] != 'admin':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        dob = request.form['dob']
        phone_number = request.form['phone_number']
        password = request.form['password']
        address = request.form['address']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO patients (first_name, last_name, dob, phone_number, password, 
                                address, status)
            VALUES (%s, %s, %s, %s, %s, %s, 1)
        ''', (first_name, last_name, dob, phone_number, password, address))
        conn.commit()
        cursor.close()
        
        flash('Patient added successfully!')
        return redirect(url_for('manage_patients'))
    
    conn = get_db_connection()
    conn = conn.cursor()
    patients = conn.execute('SELECT * FROM patients')
    patients = conn.fetchall()
    conn.close()
    
    return render_template('manage_patients.html', patients=patients)

@app.route('/admin/doctor/edit/<doc_id>', methods=['GET', 'POST'])
@login_required
def edit_doctor(doc_id):
    if session['user_type'] != 'admin':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        dob = request.form['dob']
        phone_number = request.form['phone_number']
        address = request.form['address']
        speciality = request.form['speciality']
        status = int(request.form.get('status', 1))
        
        cursor.execute('''
            UPDATE doctors 
            SET first_name = %s, last_name = %s, dob = %s, phone_number = %s,
                address = %s, speciality = %s, status = %s
            WHERE doc_id = %s
        ''', (first_name, last_name, dob, phone_number, address, speciality, status, doc_id))
        
        if request.form.get('password'):  # Only update password if provided
            password = request.form['password']
            cursor.execute('UPDATE doctors SET password = %s WHERE doc_id = %s', (password, doc_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        flash('Doctor updated successfully!')
        return redirect(url_for('manage_doctors'))
    
    doctor = cursor.execute('SELECT * FROM doctors WHERE doc_id = %s', (doc_id,))
    doctor = cursor.fetchone()
    conn.close()
    
    if doctor is None:
        flash('Doctor not found!')
        return redirect(url_for('manage_doctors'))
    
    return render_template('manage_doctors.html', edit_doctor=doctor,doctors = get_all_doctors())

def get_all_doctors():
    conn = get_db_connection()
    conn = conn.cursor()
    patients = conn.execute('SELECT * FROM doctors')
    patients = conn.fetchall()
    conn.close()

    return patients

@app.route('/admin/doctor/delete/<doc_id>', methods=['POST'])
@login_required
def delete_doctor(doc_id):
    if session['user_type'] != 'admin':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE doctors SET status = 0 WHERE doc_id = %s', (doc_id,))
    conn.commit()
    cursor.close()
    
    flash('Doctor deactivated successfully!')
    return redirect(url_for('manage_doctors'))

@app.route('/admin/patient/delete/<phone_number>', methods=['POST'])
@login_required
def delete_patient(phone_number):
    if session['user_type'] != 'admin':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE patients SET status = 0 WHERE phone_number = %s', (phone_number,))
    conn.commit()
    cursor.close()
    
    flash('Patient deactivated successfully!')
    return redirect(url_for('manage_patients'))

@app.route('/admin/patient/edit/<phone_number>', methods=['GET', 'POST'])
@login_required
def edit_patient(phone_number):
    if session['user_type'] != 'admin':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        dob = request.form['dob']
        new_phone_number = request.form['phone_number']
        address = request.form['address']
        status = int(request.form.get('status', 1))
        
        cursor.execute('''
            UPDATE patients 
            SET first_name = %s, last_name = %s, dob = %s, phone_number = %s,
                address = %s, status = %s
            WHERE phone_number = %s
        ''', (first_name, last_name, dob, new_phone_number, address, status, phone_number))
        
        if request.form.get('password'):  # Only update password if provided
            password = request.form['password']
            cursor.execute('UPDATE patients SET password = %s WHERE phone_number = %s', 
                        (password, new_phone_number))
        
        conn.commit()
        cursor.close()
        conn.close()
        flash('Patient updated successfully!')
        return redirect(url_for('manage_patients'))
    
    # For GET request, fetch patient data
    cursor.execute('SELECT * FROM patients WHERE phone_number = %s', (phone_number,))
    patient = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return render_template('manage_patients.html', edit_patient=patient, patients=get_all_patients())

def get_all_patients():
    conn = get_db_connection()
    conn = conn.cursor()
    patients = conn.execute('SELECT * FROM patients')
    patients = conn.fetchall()
    conn.close()

    return patients

    
# Add these routes to your Flask application

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        conn = conn.cursor()
        admin = conn.execute('SELECT * FROM superusercreds WHERE username = %s AND password = %s',
                           (username, password))
        admin = conn.fetchone()
        conn.close()
        
        if admin:
            session['user_id'] = username
            session['user_type'] = 'admin'
            flash('Admin login successful!')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials')
    return render_template('admin_login.html')

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if session['user_type'] != 'admin':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()  # Fixed: separate cursor and connection variables
    
    # Access first element of tuple using index [0]
    cursor.execute('SELECT COUNT(*) as count FROM doctors WHERE status = 1')
    doctors_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) as count FROM patients WHERE status = 1')
    patients_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) as count FROM doctorappointments WHERE appointmentdate >= CURRENT_DATE')
    appointments_count = cursor.fetchone()[0]
    
    cursor.close()  # Close cursor
    conn.close()    # Close connection
    
    return render_template('admin_dashboard.html', 
                         doctors_count=doctors_count,
                         patients_count=patients_count,
                         appointments_count=appointments_count)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message', '')
    conn = getConversationAgent()
    response = conn.get_gpt_response(message)
    # For now, simply return "hi" as requested
    return jsonify({'response': response})

def getConversationAgent():
    Conversation = GPTConversationSystem()
    return Conversation

# Utility routes
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)