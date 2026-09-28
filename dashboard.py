# dashboard.py

import tkinter as tk
from tkinter import messagebox

from student import Student


class Dashboard:
    def __init__(self, student_id):
        self.student = Student()
        self.student_id = student_id

        self.window = tk.Tk()
        self.window.title("Student Dashboard")
        self.window.geometry("500x500")
        self.window.resizable(False, False)

        self.create_dashboard()

    def create_dashboard(self):
        student = self.student.get_student(self.student_id)

        if not student:
            messagebox.showerror(
                "Error",
                "Student information not found."
            )
            self.window.destroy()
            return

        # Title
        tk.Label(
            self.window,
            text="Student Dashboard",
            font=("Arial", 20, "bold")
        ).pack(pady=20)

        # Student name
        tk.Label(
            self.window,
            text=f"Name: {student['first_name']} {student['last_name']}",
            font=("Arial", 12)
        ).pack(pady=5)

        # Student ID
        tk.Label(
            self.window,
            text=f"Student ID: {student['student_id']}",
            font=("Arial", 12)
        ).pack(pady=5)

        # QR Code
        tk.Label(
            self.window,
            text="My Personal QR Code",
            font=("Arial", 13, "bold")
        ).pack(pady=(20, 5))

        qr_label = tk.Label(
            self.window,
            text=student["qr_code"],
            wraplength=450,
            font=("Arial", 10)
        )
        qr_label.pack(pady=5)

        # Attendance button
        tk.Button(
            self.window,
            text="View Attendance",
            width=20,
            command=self.show_attendance
        ).pack(pady=20)

        # Close button
        tk.Button(
            self.window,
            text="Close",
            width=20,
            command=self.close
        ).pack(pady=10)

    def show_attendance(self):
        records = self.student.get_attendance(self.student_id)

        attendance_window = tk.Toplevel(self.window)
        attendance_window.title("My Attendance")
        attendance_window.geometry("600x400")

        tk.Label(
            attendance_window,
            text="My Attendance Records",
            font=("Arial", 16, "bold")
        ).pack(pady=15)

        if not records:
            tk.Label(
                attendance_window,
                text="No attendance records found.",
                font=("Arial", 11)
            ).pack(pady=20)
            return

        for record in records:
            text = (
                f"{record['subject_code']} - "
                f"{record['attendance_date']} - "
                f"{record['time_in']} - "
                f"{record['status']}"
            )

            tk.Label(
                attendance_window,
                text=text,
                font=("Arial", 10)
            ).pack(pady=3)

    def close(self):
        self.student.close()
        self.window.destroy()

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    student_id = input("Enter Student ID: ")

    dashboard = Dashboard(student_id)
    dashboard.run()