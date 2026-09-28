# qr_scanner.py

from database import Database
from datetime import datetime
from zoneinfo import ZoneInfo


class QRScanner:
    def __init__(self):
        self.db = Database()
        self.db.initialize()

    def get_current_ph_time(self):
        """
        Get the current Philippine date and time.
        """
        now = datetime.now(ZoneInfo("Asia/Manila"))

        attendance_date = now.strftime("%Y-%m-%d")
        time_in = now.strftime("%I:%M:%S %p")

        return attendance_date, time_in

    def find_student(self, qr_code):
        """
        Find a student using the QR code.
        """

        student = self.db.fetch_one(
            """
            SELECT *
            FROM users
            WHERE qr_code = ?
              AND role = 'student'
            """,
            (qr_code,)
        )

        return student

    def scan_qr(self, qr_code):
        """
        Check the scanned QR code and show student information.
        """

        student = self.find_student(qr_code)

        if not student:
            print()
            print("QR CODE NOT FOUND.")
            print()
            return None

        print()
        print("==============================")
        print("       STUDENT FOUND")
        print("==============================")
        print("Student ID :", student["student_id"])
        print(
            "Name       :",
            student["first_name"],
            student["last_name"]
        )

        return student

    def record_attendance(self, qr_code, schedule_id):
        """
        Record attendance automatically using
        the current Philippine date and time.
        """

        student = self.find_student(qr_code)

        if not student:
            print()
            print("INVALID QR CODE.")
            return False

        # Get current Philippine date and time
        attendance_date, time_in = self.get_current_ph_time()

        try:
            self.db.execute(
                """
                INSERT INTO attendance
                (
                    user_id,
                    schedule_id,
                    attendance_date,
                    time_in,
                    status
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    student["id"],
                    schedule_id,
                    attendance_date,
                    time_in,
                    "Present"
                )
            )

            print()
            print("==============================")
            print("   ATTENDANCE RECORDED")
            print("==============================")
            print(
                "Student :",
                student["first_name"],
                student["last_name"]
            )
            print("ID      :", student["student_id"])
            print("Date    :", attendance_date)
            print("Time In :", time_in)
            print("Status  : Present")
            print("==============================")
            print()

            return True

        except Exception as error:
            print()
            print("ATTENDANCE COULD NOT BE RECORDED.")
            print("Error:", error)
            print()

            return False

    def scan_and_record(self, qr_code, schedule_id):
        """
        Scan QR code, identify the student,
        and automatically record attendance.
        """

        student = self.scan_qr(qr_code)

        if student is None:
            return False

        return self.record_attendance(
            qr_code,
            schedule_id
        )

    def close(self):
        """
        Close the database connection.
        """
        self.db.close()


# ---------------------------------------------------------
# TESTING
# ---------------------------------------------------------

if __name__ == "__main__":

    scanner = QRScanner()

    try:
        print("==============================")
        print("    QR ATTENDANCE SCANNER")
        print("==============================")

        qr_code = input("Scan or enter QR Code: ").strip()

        if not qr_code:
            print("No QR code entered.")
        else:
            # For testing only.
            # Replace 1 with the actual schedule ID.
            schedule_id = 1

            scanner.scan_and_record(
                qr_code,
                schedule_id
            )

    finally:
        scanner.close()