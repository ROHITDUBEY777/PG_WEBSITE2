

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import json
import random
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Try to import Twilio (optional)
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("⚠️ Twilio not installed. SMS features will be disabled.")

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, 
     origins=["*"],
     allow_headers=["Content-Type", "Accept"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     supports_credentials=False)




# Enable CORS for all routes with proper configuration
# CORS(app, resources={
#     r"/api/*": {
#         "origins": ["*"],
#         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
#         "allow_headers": ["Content-Type"],
#         "supports_credentials": False
#     }
# })

# Database setup
DB_FILE = 'arpg_database.db'

# Email configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'sagarpatil684077@gmail.com')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', 'MSdhoni@77')
SENDER_NAME = os.getenv('SENDER_NAME', 'sagar')

# SMS configuration (Twilio)
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')

# Owner contact (for payment notifications)
OWNER_PHONE = os.getenv('OWNER_PHONE', '+919110672090')
OWNER_EMAIL = os.getenv('OWNER_EMAIL', 'spatil77436@gmail.com')
OWNER_NAME = os.getenv('OWNER_NAME', 'AR PG Owner')

# Initialize Twilio client
twilio_client = None
if TWILIO_AVAILABLE and TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    try:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        print("✅ Twilio SMS enabled!")
    except Exception as e:
        print(f"⚠️ Twilio initialization failed: {str(e)}")
else:
    print("⚠️ Twilio SMS disabled (not installed or credentials not found)")

def send_email(recipient_email, subject, body, is_html=False):
    """Send email to recipient"""
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg['To'] = recipient_email

        # Attach body
        if is_html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))

        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        print(f"✅ Email sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"❌ Error sending email: {str(e)}")
        return False

def send_payment_reminder_email(student_name, student_email, amount, due_date):
    """Send payment reminder email"""
    subject = f"Payment Reminder - AR PG Monthly Rent Due"
    
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px;">
                <h2>💳 Payment Reminder</h2>
            </div>
            
            <div style="padding: 20px; background: #f9f9f9;">
                <p>Hello <strong>{student_name}</strong>,</p>
                
                <p>This is a friendly reminder that your monthly rent payment is due.</p>
                
                <div style="background: white; padding: 15px; border-left: 4px solid #667eea; margin: 20px 0;">
                    <p><strong>Payment Details:</strong></p>
                    <p>💰 <strong>Amount:</strong> ₹{amount}</p>
                    <p>📅 <strong>Due Date:</strong> {due_date}</p>
                    <p>🏢 <strong>PG Name:</strong> AR PG</p>
                </div>
                
                <p><strong>Payment Methods:</strong></p>
                <ul>
                    <li>💳 Online Payment (Credit/Debit Card, UPI)</li>
                    <li>🏦 Bank Transfer</li>
                    <li>📱 Mobile Wallet</li>
                </ul>
                
                <p>Please make the payment at your earliest convenience. You can login to your dashboard to pay online.</p>
                
                <p>If you have any questions, please contact us.</p>
                
                <p style="color: #666; font-size: 12px; margin-top: 30px;">
                    <strong>AR PG Management System</strong><br>
                    This is an automated message. Please do not reply to this email.
                </p>
            </div>
        </body>
    </html>
    """
    
    return send_email(student_email, subject, body, is_html=True)

def send_announcement_email(student_name, student_email, announcement_title, announcement_body):
    """Send announcement email"""
    subject = f"Announcement - {announcement_title}"
    
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px;">
                <h2>📢 {announcement_title}</h2>
            </div>
            
            <div style="padding: 20px; background: #f9f9f9;">
                <p>Hello <strong>{student_name}</strong>,</p>
                
                <div style="background: white; padding: 15px; border-left: 4px solid #27ae60; margin: 20px 0;">
                    {announcement_body}
                </div>
                
                <p>If you have any questions, please contact us.</p>
                
                <p style="color: #666; font-size: 12px; margin-top: 30px;">
                    <strong>AR PG Management System</strong><br>
                    This is an automated message. Please do not reply to this email.
                </p>
            </div>
        </body>
    </html>
    """
    
    return send_email(student_email, subject, body, is_html=True)

def send_sms(phone_number, message):
    """Send SMS to student"""
    try:
        if not twilio_client:
            print("❌ Twilio not configured")
            return False
        
        # Format phone number (add country code if needed)
        if not phone_number.startswith('+'):
            phone_number = '+91' + phone_number  # India country code
        
        message_obj = twilio_client.messages.create(
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number,
            body=message
        )
        
        print(f"✅ SMS sent to {phone_number}: {message_obj.sid}")
        return True
    except Exception as e:
        print(f"❌ Error sending SMS: {str(e)}")
        return False

def send_payment_reminder_sms(student_name, phone_number, amount, due_date):
    """Send payment reminder SMS"""
    message = f"Hi {student_name}, Your monthly rent of ₹{amount} is due on {due_date}. Please pay at your earliest. AR PG Management"
    return send_sms(phone_number, message)

def send_announcement_sms(student_name, phone_number, announcement):
    """Send announcement SMS"""
    message = f"Hi {student_name}, {announcement} - AR PG Management"
    return send_sms(phone_number, message)

def notify_owner_payment(student_name, student_phone, room_number, amount, payment_method='Online'):
    """Notify owner when student makes payment"""
    try:
        # Send SMS to owner
        sms_message = f"PAYMENT RECEIVED!\nStudent: {student_name}\nPhone: {student_phone}\nRoom: {room_number}\nAmount: ₹{amount}\nMethod: {payment_method}\nDate: {datetime.now().strftime('%d-%b-%Y %H:%M')}"
        
        sms_sent = False
        if twilio_client and OWNER_PHONE:
            sms_sent = send_sms(OWNER_PHONE, sms_message)
        
        # Send email to owner
        email_subject = f"💰 Payment Received - {student_name}"
        email_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="background: linear-gradient(135deg, #27ae60 0%, #229954 100%); color: white; padding: 20px; border-radius: 10px;">
                    <h2>💰 Payment Received!</h2>
                </div>
                
                <div style="padding: 20px; background: #f9f9f9;">
                    <p>Hello <strong>{OWNER_NAME}</strong>,</p>
                    
                    <p>A student has successfully made a payment. Here are the details:</p>
                    
                    <div style="background: white; padding: 20px; border-left: 4px solid #27ae60; margin: 20px 0;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Student Name:</td>
                                <td style="padding: 8px;">{student_name}</td>
                            </tr>
                            <tr style="background: #f9f9f9;">
                                <td style="padding: 8px; font-weight: bold;">Phone Number:</td>
                                <td style="padding: 8px;">{student_phone}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Room Number:</td>
                                <td style="padding: 8px;">{room_number}</td>
                            </tr>
                            <tr style="background: #f9f9f9;">
                                <td style="padding: 8px; font-weight: bold;">Amount Paid:</td>
                                <td style="padding: 8px; color: #27ae60; font-weight: bold; font-size: 1.2em;">₹{amount}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Payment Method:</td>
                                <td style="padding: 8px;">{payment_method}</td>
                            </tr>
                            <tr style="background: #f9f9f9;">
                                <td style="padding: 8px; font-weight: bold;">Payment Date:</td>
                                <td style="padding: 8px;">{datetime.now().strftime('%d-%b-%Y %H:%M')}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <p>You can verify this payment in the admin dashboard.</p>
                    
                    <p style="color: #666; font-size: 12px; margin-top: 30px;">
                        <strong>AR PG Management System</strong><br>
                        This is an automated notification. Please do not reply to this email.
                    </p>
                </div>
            </body>
        </html>
        """
        
        email_sent = False
        if OWNER_EMAIL:
            email_sent = send_email(OWNER_EMAIL, email_subject, email_body, is_html=True)
        
        if sms_sent or email_sent:
            print(f"✅ Owner notified about payment from {student_name}")
            return True
        else:
            print(f"⚠️ Failed to notify owner about payment")
            return False
            
    except Exception as e:
        print(f"❌ Error notifying owner: {str(e)}")
        return False

# @app.before_request
# def handle_preflight():
#     """Handle CORS preflight requests"""
#     if request.method == "OPTIONS":
#         response = jsonify({'status': 'ok'})
#         response.headers['Access-Control-Allow-Origin'] = '*'
#         response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
#         response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
#         return response, 200

def init_db():
    """Initialize database with tables"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullName TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            college TEXT NOT NULL,
            course TEXT NOT NULL,
            year TEXT NOT NULL,
            roomType TEXT NOT NULL,
            password TEXT NOT NULL,
            registrationDate TEXT NOT NULL,
            status TEXT DEFAULT 'Active',
            roomNumber INTEGER,
            monthlyRent INTEGER DEFAULT 8000,
            paymentStatus TEXT DEFAULT 'pending'
        )
    ''')
    
    # Create payments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            studentPhone TEXT NOT NULL,
            amount INTEGER NOT NULL,
            dueDate TEXT NOT NULL,
            paymentDate TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (studentPhone) REFERENCES students(phone)
        )
    ''')
    
    # Create messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            studentPhone TEXT NOT NULL,
            messageType TEXT NOT NULL,
            message TEXT NOT NULL,
            sentDate TEXT NOT NULL,
            FOREIGN KEY (studentPhone) REFERENCES students(phone)
        )
    ''')
    
    # Create announcements table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'notice',
            priority TEXT DEFAULT 'low',
            date TEXT NOT NULL,
            createdBy TEXT DEFAULT 'Admin',
            createdAt TEXT NOT NULL
        )
    ''')
       # Create table for storing reset codes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            code TEXT,
            expires_at TEXT
        )
    ''')


        # Create inquiries table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            room TEXT,
            message TEXT,
            date TEXT NOT NULL
        )
    ''')

    
    conn.commit()
    conn.close()
    print("✅ Database initialized!")

# Initialize database on startup
init_db()

# ==================== AUTHENTICATION ROUTES ====================

@app.route('/api/signup', methods=['POST'])
def signup():
    """Handle student signup"""
    try:
        data = request.json
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if phone already exists
        cursor.execute('SELECT * FROM students WHERE phone = ?', (data['phone'],))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Phone number already registered!'}), 400
        
        # Insert new student
        cursor.execute('''
            INSERT INTO students (fullName, email, phone, college, course, year, roomType, password, registrationDate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['fullName'],
            data['email'],
            data['phone'],
            data['college'],
            data['course'],
            data['year'],
            data['roomType'],
            data['password'],
            datetime.now().strftime('%d-%b-%Y')
        ))
        
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Signup successful!'}), 201
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Handle student login using email OR phone"""
    try:
        data = request.json
        # ✅ FIX: Accept both 'phone' and 'identifier'
        identifier = data.get('phone') or data.get('identifier') or data.get('email')
        password = data.get('password')

        if not identifier or not password:
            return jsonify({'success': False, 'message': 'Email/Phone and password are required'}), 400

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Check using phone OR email
        cursor.execute('''
            SELECT * FROM students
            WHERE (phone = ? OR email = ?) AND password = ?
        ''', (identifier, identifier, password))

        student = cursor.fetchone()
        conn.close()

        if student:
            return jsonify({
                'success': True,
                'message': 'Login successful!',
                'student': {
                    'fullName': student[1],
                    'email': student[2],
                    'phone': student[3],
                    'college': student[4],
                    'course': student[5],
                    'year': student[6],
                    'roomType': student[7],
                    'registrationDate': student[9],
                    'roomNumber': student[11]
                }
            }), 200
        else:
            return jsonify({'success': False, 'message': 'Invalid email/phone or password!'}), 401

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== STUDENT ROUTES ====================

@app.route('/api/student/<phone>', methods=['GET'])
def get_student(phone):
    """Get student details"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM students WHERE phone = ?', (phone,))
        student = cursor.fetchone()
        conn.close()
        
        if student:
            return jsonify({
                'success': True,
                'student': {
                    'fullName': student[1],
                    'email': student[2],
                    'phone': student[3],
                    'college': student[4],
                    'course': student[5],
                    'year': student[6],
                    'roomType': student[7],
                    'registrationDate': student[9],
                    'roomNumber': student[11] or 'N/A',
                    'monthlyRent': student[12],
                    'paymentStatus': student[13]
                }
            }), 200
        else:
            return jsonify({'success': False, 'message': 'Student not found!'}), 404
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/student/<phone>/payments', methods=['GET'])
def get_student_payments(phone):
    """Get student payment history"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, amount, dueDate, paymentDate, status 
            FROM payments WHERE studentPhone = ?
            ORDER BY dueDate DESC
        ''', (phone,))
        
        payments = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'payments': [
                {
                    'id': p[0],
                    'amount': p[1],
                    'dueDate': p[2],
                    'paymentDate': p[3],
                    'status': p[4]
                }
                for p in payments
            ]
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/student/<phone>/messages', methods=['GET'])
def get_student_messages(phone):
    """Get messages for student"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, messageType, message, sentDate 
            FROM messages WHERE studentPhone = ?
            ORDER BY sentDate DESC
        ''', (phone,))
        
        messages = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'messages': [
                {
                    'id': m[0],
                    'type': m[1],
                    'message': m[2],
                    'date': m[3]
                }
                for m in messages
            ]
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== ANNOUNCEMENTS ROUTES ====================

@app.route('/api/announcements', methods=['GET'])
def get_announcements():
    """Get all announcements for students"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, message, type, priority, date, createdBy, createdAt
            FROM announcements
            ORDER BY createdAt DESC
        ''')
        
        announcements = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'announcements': [
                {
                    'id': a[0],
                    'title': a[1],
                    'message': a[2],
                    'type': a[3],
                    'priority': a[4],
                    'date': a[5],
                    'createdBy': a[6],
                    'createdAt': a[7]
                }
                for a in announcements
            ]
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/announcements', methods=['POST'])
def create_announcement():
    """Create new announcement (Admin only)"""
    try:
        data = request.json
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO announcements (title, message, type, priority, date, createdBy, createdAt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('title', 'Announcement'),
            data.get('message'),
            data.get('type', 'notice'),
            data.get('priority', 'low'),
            data.get('date', datetime.now().strftime('%Y-%m-%d')),
            data.get('createdBy', 'Admin'),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        announcement_id = cursor.lastrowid
        conn.commit()
        
        # Get the created announcement
        cursor.execute('SELECT * FROM announcements WHERE id = ?', (announcement_id,))
        announcement = cursor.fetchone()
        
        sent_count = 0
        
        # Send announcement to students via email if requested
        if data.get('sendEmail', True):
            send_to_all = data.get('sendToAll', True)
            phones = data.get('phones', [])
            
            if send_to_all:
                cursor.execute('SELECT fullName, email, phone FROM students')
            else:
                if phones:
                    placeholders = ','.join('?' * len(phones))
                    cursor.execute(f'SELECT fullName, email, phone FROM students WHERE phone IN ({placeholders})', phones)
                else:
                    cursor.execute('SELECT fullName, email, phone FROM students LIMIT 0')
            
            students = cursor.fetchall()
            conn.close()
            
            for student in students:
                student_name = student[0]
                student_email = student[1]
                student_phone = student[2]
                
                # Send email
                email_sent = send_announcement_email(
                    student_name,
                    student_email,
                    data.get('title', 'Announcement'),
                    data.get('message')
                )
                
                # Send SMS if enabled
                if data.get('sendSMS', False) and twilio_client:
                    send_announcement_sms(student_name, student_phone, data.get('message')[:100])
                
                if email_sent:
                    sent_count += 1
        else:
            conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Announcement created successfully! Sent to {sent_count} student(s).',
            'announcement': {
                'id': announcement[0],
                'title': announcement[1],
                'message': announcement[2],
                'type': announcement[3],
                'priority': announcement[4],
                'date': announcement[5]
            }
        }), 201
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/announcements/<int:announcement_id>', methods=['DELETE'])
def delete_announcement(announcement_id):
    """Delete announcement (Admin only)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM announcements WHERE id = ?', (announcement_id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Announcement deleted successfully'
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/announcements/<int:announcement_id>', methods=['PUT'])
def update_announcement(announcement_id):
    """Update announcement (Admin only)"""
    try:
        data = request.json
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE announcements 
            SET title = ?, message = ?, type = ?, priority = ?
            WHERE id = ?
        ''', (
            data.get('title'),
            data.get('message'),
            data.get('type'),
            data.get('priority'),
            announcement_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Announcement updated successfully'
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== ADMIN ROUTES ====================

@app.route('/api/admin/students', methods=['GET'])
def get_all_students():
    """Get all students (for admin)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT fullName, email, phone, college, roomNumber, paymentStatus FROM students')
        students = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'students': [
                {
                    'fullName': s[0],
                    'email': s[1],
                    'phone': s[2],
                    'college': s[3],
                    'roomNumber': s[4],
                    'paymentStatus': s[5]
                }
                for s in students
            ]
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/add-student', methods=['POST'])
def admin_add_student():
    """Admin add student"""
    try:
        data = request.json
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO students (fullName, email, phone, college, course, year, roomType, password, registrationDate, roomNumber, monthlyRent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['fullName'],
            data['email'],
            data['phone'],
            data.get('college', 'N/A'),
            data.get('course', 'N/A'),
            data.get('year', 'N/A'),
            data.get('roomType', 'Single'),
            'password123',
            datetime.now().strftime('%d-%b-%Y'),
            data.get('roomNumber'),
            data.get('monthlyRent', 8000)
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Student added successfully!'}), 201
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/payments', methods=['GET'])
def get_all_payments():
    """Get all payments (for admin)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.fullName, s.phone, p.amount, p.dueDate, p.status, s.monthlyRent
            FROM payments p
            JOIN students s ON p.studentPhone = s.phone
            ORDER BY p.dueDate DESC
        ''')
        
        payments = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'payments': [
                {
                    'studentName': p[0],
                    'phone': p[1],
                    'amount': p[2],
                    'dueDate': p[3],
                    'status': p[4],
                    'monthlyRent': p[5]
                }
                for p in payments
            ]
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/mark-paid', methods=['POST'])
def mark_payment_paid():
    """Mark payment as paid"""
    try:
        data = request.json
        phone = data.get('phone')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get student details
        cursor.execute('SELECT fullName, roomNumber, monthlyRent FROM students WHERE phone = ?', (phone,))
        student = cursor.fetchone()
        
        if not student:
            conn.close()
            return jsonify({'success': False, 'message': 'Student not found!'}), 404
        
        student_name = student[0]
        room_number = student[1] or 'N/A'
        amount = student[2]
        
        cursor.execute('''
            UPDATE payments SET status = 'paid', paymentDate = ?
            WHERE studentPhone = ? AND status = 'pending'
            LIMIT 1
        ''', (datetime.now().strftime('%d-%b-%Y'), phone))
        
        # Also update student payment status
        cursor.execute('''
            UPDATE students SET paymentStatus = 'paid'
            WHERE phone = ?
        ''', (phone,))
        
        conn.commit()
        conn.close()
        
        # Notify owner about the payment (Manual verification)
        notify_owner_payment(student_name, phone, room_number, amount, 'Manual/Cash')
        
        return jsonify({'success': True, 'message':'Payment marked as paid! Owner notified.'}), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/create-payment-order', methods=['POST'])
def create_payment_order():
    """Create a payment order for Razorpay"""
    try:
        data = request.json
        phone = data.get('phone')
        amount = data.get('amount', 8000)  # in rupees
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get student details
        cursor.execute('SELECT fullName, email FROM students WHERE phone = ?', (phone,))
        student = cursor.fetchone()
        conn.close()
        
        if not student:
            return jsonify({'success': False, 'message': 'Student not found!'}), 404
        
        # In real scenario, you'd create order in Razorpay
        # For now, we'll return a mock order
        order_id = f"order_{phone}_{int(datetime.now().timestamp())}"
        
        return jsonify({
            'success': True,
            'orderId': order_id,
            'amount': amount * 100,  # Razorpay expects amount in paise
            'currency': 'INR',
            'studentName': student[0],
            'studentEmail': student[1],
            'studentPhone': phone
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/verify-payment', methods=['POST'])
def verify_payment():
    """Verify payment from Razorpay"""
    try:
        data = request.json
        phone = data.get('phone')
        amount = data.get('amount', 8000)
        payment_method = data.get('paymentMethod', 'Online')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get student details
        cursor.execute('SELECT fullName, roomNumber FROM students WHERE phone = ?', (phone,))
        student = cursor.fetchone()
        
        if not student:
            conn.close()
            return jsonify({'success': False, 'message': 'Student not found!'}), 404
        
        student_name = student[0]
        room_number = student[1] or 'N/A'
        
        # Mark payment as paid
        cursor.execute('''
            UPDATE students SET paymentStatus = 'paid'
            WHERE phone = ?
        ''', (phone,))
        
        # Create payment record
        cursor.execute('''
            INSERT INTO payments (studentPhone, amount, dueDate, paymentDate, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (phone, amount, datetime.now().strftime('%d-%b-%Y'), datetime.now().strftime('%d-%b-%Y'), 'paid'))
        
        conn.commit()
        conn.close()
        
        # Notify owner about the payment
        notify_owner_payment(student_name, phone, room_number, amount, payment_method)
        
        return jsonify({
            'success': True,
            'message': 'Payment verified and recorded successfully! Owner has been notified.'
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/send-reminder', methods=['POST'])
def send_reminder():
    """Send reminder to students"""
    try:
        data = request.json
        phones = data.get('phones', [])
        message = data.get('message', '')
        messageType = data.get('messageType', 'reminder')
        send_sms_flag = data.get('sendSMS', True)
        send_email_flag = data.get('sendEmail', True)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        sent_count = 0
        email_errors = []
        sms_errors = []
        
        for phone in phones:
            # Get student details
            cursor.execute('SELECT fullName, email FROM students WHERE phone = ?', (phone,))
            student = cursor.fetchone()
            
            if student:
                student_name = student[0]
                student_email = student[1]
                
                # Save message to database
                cursor.execute('''
                    INSERT INTO messages (studentPhone, messageType, message, sentDate)
                    VALUES (?, ?, ?, ?)
                ''', (phone, messageType, message, datetime.now().strftime('%d-%b-%Y %H:%M')))
                
                # Send email if enabled
                if send_email_flag and messageType == 'payment':
                    email_sent = send_payment_reminder_email(
                        student_name, 
                        student_email, 
                        8000, 
                        datetime.now().strftime('%d-%b-%Y')
                    )
                    if not email_sent:
                        email_errors.append(student_name)
                elif send_email_flag:
                    email_sent = send_announcement_email(
                        student_name,
                        student_email,
                        "Message from AR PG",
                        message
                    )
                    if not email_sent:
                        email_errors.append(student_name)
                
                # Send SMS if enabled
                if send_sms_flag:
                    if messageType == 'payment':
                        sms_sent = send_payment_reminder_sms(student_name, phone, 8000, datetime.now().strftime('%d-%b-%Y'))
                    else:
                        sms_sent = send_announcement_sms(student_name, phone, message[:100])  # SMS limit
                    
                    if sms_sent:
                        sent_count += 1
                    else:
                        sms_errors.append(student_name)
                else:
                    if send_email_flag:
                        sent_count += 1
        
        conn.commit()
        conn.close()
        
        response_message = f'Reminder sent to {sent_count} student(s)!'
        errors = []
        if email_errors:
            errors.append(f"Email errors: {len(email_errors)}")
        if sms_errors:
            errors.append(f"SMS errors: {len(sms_errors)}")
        
        if errors:
            response_message += f' ({", ".join(errors)})'
        
        return jsonify({
            'success': True,
            'message': response_message,
            'sent': sent_count,
            'email_errors': email_errors,
            'sms_errors': sms_errors
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/send-payment-reminder/<phone>', methods=['POST'])
def send_payment_reminder(phone):
    """Send payment reminder to specific student"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT fullName, email, monthlyRent FROM students WHERE phone = ?', (phone,))
        student = cursor.fetchone()
        conn.close()
        
        if not student:
            return jsonify({'success': False, 'message': 'Student not found!'}), 404
        
        student_name = student[0]
        student_email = student[1]
        amount = student[2]
        
        # Send payment reminder email
        email_sent = send_payment_reminder_email(
            student_name,
            student_email,
            amount,
            datetime.now().strftime('%d-%b-%Y')
        )
        
        # Send SMS
        sms_sent = send_payment_reminder_sms(student_name, phone, amount, datetime.now().strftime('%d-%b-%Y'))
        
        message = []
        if email_sent:
            message.append(f"Email sent to {student_email}")
        if sms_sent:
            message.append(f"SMS sent to {phone}")
        
        if message:
            return jsonify({
                'success': True,
                'message': '; '.join(message)
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send reminder'
            }), 500
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/send-sms', methods=['POST'])
def send_sms_route():
    """Send SMS to students"""
    try:
        data = request.json
        phones = data.get('phones', [])
        message = data.get('message', '')
        
        if not twilio_client:
            return jsonify({
                'success': False,
                'message': 'SMS service not configured. Please add Twilio credentials to .env'
            }), 500
        
        sent_count = 0
        errors = []
        
        for phone in phones:
            # Limit message to 160 characters for SMS
            sms_message = message[:160]
            if send_sms(phone, sms_message):
                sent_count += 1
            else:
                errors.append(phone)
        
        return jsonify({
            'success': True,
            'message': f'SMS sent to {sent_count} student(s)!',
            'sent': sent_count,
            'errors': errors
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== PASSWORD RESET ROUTES ====================

# Store reset codes temporarily (in production, use Redis or database with expiry)
reset_codes = {}
# ==================== PASSWORD RESET ROUTES ====================

@app.route('/api/forgot-password/send-code', methods=['POST'])
def send_reset_code():
    """Send password reset code to student's email using email address"""
    try:
        data = request.json
        email = data.get('email')

        if not email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Find student by email
        cursor.execute('SELECT fullName, email FROM students WHERE email = ?', (email,))
        student = cursor.fetchone()

        if not student:
            conn.close()
            return jsonify({'success': False, 'message': 'No account found with this email'}), 404

        student_name = student[0]
        student_email = student[1]

        # Generate 6-digit reset code
        code = str(random.randint(100000, 999999))

        # Expire in 10 minutes
        expires_at = (datetime.now() + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')

        # Clear previous codes for this email
        cursor.execute('DELETE FROM password_resets WHERE email = ?', (student_email,))

        # Save new code
        cursor.execute('''
            INSERT INTO password_resets (email, code, expires_at)
            VALUES (?, ?, ?)
        ''', (student_email, code, expires_at))

        conn.commit()
        conn.close()

        # Send email
        subject = "Password Reset Code - AR PG"
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px;">
                    <h2>🔐 Password Reset Request</h2>
                </div>
                
                <div style="padding: 20px; background: #f9f9f9;">
                    <p>Hello <strong>{student_name}</strong>,</p>
                    
                    <p>We received a request to reset your AR PG password. Use the code below to continue:</p>
                    
                    <div style="background: white; padding: 20px; border-left: 4px solid #667eea; margin: 20px 0; text-align: center;">
                        <h1 style="color: #667eea; font-size: 2.5em; letter-spacing: 6px; margin: 10px 0;">{code}</h1>
                        <p style="color: #999; font-size: 0.9em;">This code is valid for 10 minutes.</p>
                    </div>
                    
                    <p><strong>⚠️ Security tips:</strong></p>
                    <ul>
                        <li>Do not share this code with anyone.</li>
                        <li>If you didn't request this, you can ignore this email.</li>
                    </ul>
                    
                    <p style="color: #666; font-size: 12px; margin-top: 30px;">
                        <strong>AR PG Management System</strong><br>
                        This is an automated message. Please do not reply to this email.
                    </p>
                </div>
            </body>
        </html>
        """

        send_email(student_email, subject, body, is_html=True)

        return jsonify({
            'success': True,
            'message': f'Reset code sent to {student_email}'
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/forgot-password/verify-code', methods=['POST'])
def verify_reset_code():
    """Verify password reset code using email and code"""
    try:
        data = request.json
        email = data.get('email')
        code = data.get('code')

        if not email or not code:
            return jsonify({'success': False, 'message': 'Email and code are required'}), 400

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute('SELECT code, expires_at FROM password_resets WHERE email = ?', (email,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return jsonify({'success': False, 'message': 'No reset request found. Please try again.'}), 404

        stored_code, expires_at_str = row

        # Check expiry
        expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d %H:%M:%S')
        if datetime.now() > expires_at:
            cursor.execute('DELETE FROM password_resets WHERE email = ?', (email,))
            conn.commit()
            conn.close()
            return jsonify({'success': False, 'message': 'Reset code expired. Please request a new one.'}), 400

        # Check code
        if stored_code != code:
            conn.close()
            return jsonify({'success': False, 'message': 'Invalid reset code'}), 400

        conn.close()
        return jsonify({'success': True, 'message': 'Code verified successfully!'}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/forgot-password/reset', methods=['POST'])
def reset_password():
    """Reset student password using email"""
    try:
        data = request.json
        email = data.get('email')
        new_password = data.get('newPassword')

        if not email or not new_password:
            return jsonify({'success': False, 'message': 'Email and new password are required'}), 400

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Make sure there is a valid reset entry (extra safety)
        cursor.execute('SELECT expires_at FROM password_resets WHERE email = ?', (email,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return jsonify({'success': False, 'message': 'Reset session expired. Please start again.'}), 400

        expires_at_str = row[0]
        expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d %H:%M:%S')
        if datetime.now() > expires_at:
            cursor.execute('DELETE FROM password_resets WHERE email = ?', (email,))
            conn.commit()
            conn.close()
            return jsonify({'success': False, 'message': 'Reset code expired. Please request a new one.'}), 400

        # Update student password by email
        cursor.execute('''
            UPDATE students SET password = ?
            WHERE email = ?
        ''', (new_password, email))

        conn.commit()

        # Remove reset entry
        cursor.execute('DELETE FROM password_resets WHERE email = ?', (email,))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Password reset successful!'}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/send-announcement', methods=['POST'])
def send_announcement():
    """Send announcement to all or selected students"""
    try:
        data = request.json
        phones = data.get('phones', [])
        title = data.get('title', 'Announcement')
        content = data.get('content', '')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # If no phones specified, send to all
        if not phones:
            cursor.execute('SELECT phone FROM students')
            phones = [row[0] for row in cursor.fetchall()]
        
        sent_count = 0
        
        for phone in phones:
            cursor.execute('SELECT fullName, email FROM students WHERE phone = ?', (phone,))
            student = cursor.fetchone()
            
            if student:
                student_name = student[0]
                student_email = student[1]
                
                # Send announcement email
                email_sent = send_announcement_email(
                    student_name,
                    student_email,
                    title,
                    content
                )
                
                if email_sent:
                    sent_count += 1
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Announcement sent to {sent_count} student(s)!',
            'sent': sent_count
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    """Get admin dashboard statistics"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Total students
        cursor.execute('SELECT COUNT(*) FROM students')
        total_students = cursor.fetchone()[0]
        
        # Paid students this month
        cursor.execute("SELECT COUNT(*) FROM students WHERE paymentStatus = 'paid'")
        paid_students = cursor.fetchone()[0]
        
        # Pending payments
        cursor.execute("SELECT COUNT(*) FROM students WHERE paymentStatus = 'pending'")
        pending_students = cursor.fetchone()[0]
        
        # Total revenue
        cursor.execute('SELECT SUM(monthlyRent) FROM students')
        total_revenue = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'totalStudents': total_students,
                'paidThisMonth': paid_students,
                'pendingPayments': pending_students,
                'totalRevenue': total_revenue
            }
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== TEST ROUTE ====================

@app.route('/api/test', methods=['GET'])
def test():
    """Test if backend is running"""
    return jsonify({'success': True, 'message': 'Backend is running! ✅'}), 200

# ==================== ERROR HANDLING ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Route not found!'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': 'Internal server error!'}), 500

# ==================== RUN SERVER ====================
# ==================== INQUIRY ROUTE ====================
@app.route('/api/inquiry', methods=['POST'])
def handle_inquiry():
    """Save inquiry from the contact form"""
    try:
        data = request.json

        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        room = data.get('room')
        message = data.get('message')

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO inquiries (name, email, phone, room, message, date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, email, phone, room, message, datetime.now().strftime('%d-%b-%Y %H:%M')))

        conn.commit()
        conn.close()

        # Optional: send email notification to owner
        subject = f"New Inquiry from {name}"
        body = f"""
        Name: {name}
        Email: {email}
        Phone: {phone}
        Room: {room}
        Message: {message}
        """
        send_email(OWNER_EMAIL, subject, body)

        return jsonify({'success': True, 'message': 'Inquiry submitted successfully!'}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ✅ NEW route for Admin Dashboard to view inquiries
@app.route('/api/inquiries', methods=['GET'])
def get_inquiries():
    """Fetch all inquiries for admin dashboard"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM inquiries ORDER BY id DESC')
        inquiries = cursor.fetchall()
        conn.close()

        # Convert to list of dicts
        inquiries_list = [
            {
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'phone': row[3],
                'room': row[4],
                'message': row[5],
                'date': row[6]
            }
            for row in inquiries
        ]

        return jsonify({'success': True, 'inquiries': inquiries_list}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    print("🚀 Starting AR PG Backend Server...")
    print("📍 Server running at: http://localhost:5000")
    print("🛑 Press CTRL+C to stop the server")
    app.run(debug=True, host='localhost', port=5000)
