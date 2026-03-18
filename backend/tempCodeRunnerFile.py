.route('/api/admin/add-student', methods=['POST'])
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
    