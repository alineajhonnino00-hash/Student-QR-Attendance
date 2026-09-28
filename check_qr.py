from database import Database

db = Database()
db.initialize()

rows = db.fetch_all("""
    SELECT student_id, first_name, last_name, qr_code
    FROM users
    WHERE role = 'student'
""")

print()
print("========== STUDENTS / QR CODES ==========")

for row in rows:
    print("Student ID :", row["student_id"])
    print("Name       :", row["first_name"], row["last_name"])
    print("QR Code    :", repr(row["qr_code"]))
    print("----------------------------------------")

db.close()