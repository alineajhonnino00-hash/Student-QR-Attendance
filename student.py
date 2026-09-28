# student.py

from database import Database


class Student:
    def __init__(self):
        self.db = Database()

    def get_student(self, student_id):
        return self.db.fetch_one(
            """
            SELECT *
            FROM users
            WHERE student_id = ? AND role = 'student'
            """,
            (student_id,)
        )

    def get_qr_code(self, student_id):
        student = self.get_student(student_id)

        if student:
            return student["qr_code"]

        return None

    def get_attendance(self, student_id):
        student = self.get_student(student_id)

        if not student:
            return []

        return self.db.fetch_all(
            """
            SELECT
                attendance.id,
                subjects.subject_code,
                subjects.subject_name,
                attendance.attendance_date,
                attendance.time_in,
                attendance.status
            FROM attendance
            JOIN schedules
                ON attendance.schedule_id = schedules.id
            JOIN subjects
                ON schedules.subject_id = subjects.id
            WHERE attendance.user_id = ?
            ORDER BY attendance.attendance_date DESC
            """,
            (student["id"],)
        )

    def display_student_info(self, student_id):
        student = self.get_student(student_id)

        if not student:
            print("Student not found.")
            return

        print("Student Information")
        print("-------------------")
        print("Student ID:", student["student_id"])
        print("Name:", student["first_name"], student["last_name"])
        print("Email:", student["email"])
        print("QR Code:", student["qr_code"])

    def close(self):
        self.db.close()


if __name__ == "__main__":
    student = Student()

    student_id = input("Enter Student ID: ")

    student.display_student_info(student_id)

    student.close()