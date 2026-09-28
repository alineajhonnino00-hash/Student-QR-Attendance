import sqlite3
import uuid


class Database:
    def __init__(self, db_name="attendance.db"):
        # Connect to SQLite database.
        # check_same_thread=False allows Flask to use
        # the database connection from different threads.
        self.connection = sqlite3.connect(
            db_name,
            check_same_thread=False
        )

        # Access columns using their names.
        self.connection.row_factory = sqlite3.Row

        # Enable foreign keys.
        self.connection.execute(
            "PRAGMA foreign_keys = ON"
        )

    def initialize(self):
        """Create all required database tables."""

        cursor = self.connection.cursor()

        # -------------------------------------------------
        # USERS TABLE
        # -------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE,
                password TEXT,
                role TEXT NOT NULL DEFAULT 'student',
                qr_code TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # -------------------------------------------------
        # SUBJECTS TABLE
        # -------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_code TEXT UNIQUE NOT NULL,
                subject_name TEXT NOT NULL,
                description TEXT
            )
        """)

        # -------------------------------------------------
        # ASSIGNMENTS TABLE
        # -------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (subject_id)
                    REFERENCES subjects(id)
                    ON DELETE CASCADE,

                UNIQUE(user_id, subject_id)
            )
        """)

        # -------------------------------------------------
        # SCHEDULES TABLE
        # -------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                schedule_date TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT,
                room TEXT,

                FOREIGN KEY (subject_id)
                    REFERENCES subjects(id)
                    ON DELETE CASCADE
            )
        """)

        # -------------------------------------------------
        # ATTENDANCE TABLE
        # -------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                schedule_id INTEGER NOT NULL,
                attendance_date TEXT NOT NULL,
                time_in TEXT,
                status TEXT NOT NULL DEFAULT 'Present',

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (schedule_id)
                    REFERENCES schedules(id)
                    ON DELETE CASCADE,

                UNIQUE(
                    user_id,
                    schedule_id,
                    attendance_date
                )
            )
        """)

        self.connection.commit()

    # -----------------------------------------------------
    # GENERAL DATABASE FUNCTIONS
    # -----------------------------------------------------

    def execute(self, query, parameters=()):
        """Execute INSERT, UPDATE, or DELETE queries."""

        cursor = self.connection.cursor()

        cursor.execute(
            query,
            parameters
        )

        self.connection.commit()

        return cursor

    def fetch_one(self, query, parameters=()):
        """Get one record."""

        cursor = self.connection.cursor()

        cursor.execute(
            query,
            parameters
        )

        return cursor.fetchone()

    def fetch_all(self, query, parameters=()):
        """Get multiple records."""

        cursor = self.connection.cursor()

        cursor.execute(
            query,
            parameters
        )

        return cursor.fetchall()

    def close(self):
        """Close database connection."""

        if self.connection:
            self.connection.close()

    # -----------------------------------------------------
    # STUDENT FUNCTIONS
    # -----------------------------------------------------

    def create_student(
        self,
        student_id,
        first_name,
        last_name,
        email=None,
        password=None
    ):
        """
        Create a student and generate a unique QR code.
        """

        qr_code = (
            f"STUDENT:{student_id}:"
            f"{uuid.uuid4().hex}"
        )

        query = """
            INSERT INTO users
            (
                student_id,
                first_name,
                last_name,
                email,
                password,
                role,
                qr_code
            )
            VALUES (?, ?, ?, ?, ?, 'student', ?)
        """

        self.execute(
            query,
            (
                student_id,
                first_name,
                last_name,
                email,
                password,
                qr_code
            )
        )

        return qr_code

    def get_student_by_qr(self, qr_code):
        """Find student using QR code."""

        query = """
            SELECT *
            FROM users
            WHERE qr_code = ?
              AND role = 'student'
        """

        return self.fetch_one(
            query,
            (qr_code,)
        )

    def get_student_by_id(self, student_id):
        """Find student using Student ID."""

        query = """
            SELECT *
            FROM users
            WHERE student_id = ?
              AND role = 'student'
        """

        return self.fetch_one(
            query,
            (student_id,)
        )

    def get_student_qr(self, student_id):
        """Get student's QR code."""

        query = """
            SELECT qr_code
            FROM users
            WHERE student_id = ?
              AND role = 'student'
        """

        result = self.fetch_one(
            query,
            (student_id,)
        )

        if result:
            return result["qr_code"]

        return None

    # -----------------------------------------------------
    # ATTENDANCE
    # -----------------------------------------------------

    def record_attendance(
        self,
        qr_code,
        schedule_id,
        attendance_date,
        time_in,
        status="Present"
    ):
        """Record student attendance."""

        student = self.get_student_by_qr(
            qr_code
        )

        if student is None:
            raise ValueError(
                "Invalid or unregistered QR code."
            )

        # Check duplicate attendance first.
        existing = self.fetch_one(
            """
            SELECT *
            FROM attendance
            WHERE user_id = ?
              AND schedule_id = ?
              AND attendance_date = ?
            """,
            (
                student["id"],
                schedule_id,
                attendance_date
            )
        )

        if existing:
            raise ValueError(
                "This student is already marked present today."
            )

        query = """
            INSERT INTO attendance
            (
                user_id,
                schedule_id,
                attendance_date,
                time_in,
                status
            )
            VALUES (?, ?, ?, ?, ?)
        """

        self.execute(
            query,
            (
                student["id"],
                schedule_id,
                attendance_date,
                time_in,
                status
            )
        )

        return student

    # -----------------------------------------------------
    # STUDENT ATTENDANCE
    # -----------------------------------------------------

    def get_student_attendance(self, student_id):
        """Get attendance records of a student."""

        query = """
            SELECT
                attendance.id,
                users.student_id,
                users.first_name,
                users.last_name,
                subjects.subject_code,
                subjects.subject_name,
                schedules.schedule_date,
                schedules.start_time,
                schedules.end_time,
                schedules.room,
                attendance.attendance_date,
                attendance.time_in,
                attendance.status

            FROM attendance

            INNER JOIN users
                ON attendance.user_id = users.id

            INNER JOIN schedules
                ON attendance.schedule_id = schedules.id

            INNER JOIN subjects
                ON schedules.subject_id = subjects.id

            WHERE users.student_id = ?

            ORDER BY attendance.attendance_date DESC
        """

        return self.fetch_all(
            query,
            (student_id,)
        )


# ---------------------------------------------------------
# INITIALIZE DATABASE WHEN RUN DIRECTLY
# ---------------------------------------------------------

if __name__ == "__main__":

    db = Database()

    db.initialize()

    db.close()

    print(
        "Database initialized successfully."
    )
    