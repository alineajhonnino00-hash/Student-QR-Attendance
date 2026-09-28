from flask import Flask, request, jsonify, render_template_string
from database import Database
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import secrets
from threading import Lock


app = Flask(__name__)

# ============================================================
# DATABASE
# ============================================================

db = Database()
db.initialize()

PH_TIMEZONE = ZoneInfo("Asia/Manila")

# One physical scanner device/session is allowed at a time.
scanner_locked = False
scanner_owner_token = None
attendance_scan_lock = Lock()


# ============================================================
# HTML PAGE
# ============================================================

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>QR Attendance Scanner</title>

    <script src="https://unpkg.com/html5-qrcode"></script>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            background: #f2f4f7;
            color: #222;
        }

        .container {
            width: 100%;
            max-width: 520px;
            margin: auto;
            padding: 20px;
        }

        .header {
            background: #1f2937;
            color: white;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            margin-bottom: 15px;
        }

        .header h1 {
            margin: 0 0 8px 0;
            font-size: 25px;
        }

        .header p {
            margin: 0;
            font-size: 14px;
        }

        .clock-box {
            background: white;
            border-radius: 15px;
            padding: 15px;
            text-align: center;
            margin-bottom: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        .date {
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .time {
            font-size: 30px;
            font-weight: bold;
        }

        .schedule-box {
            background: white;
            border-radius: 15px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        .schedule-box h2 {
            margin-top: 0;
            font-size: 18px;
        }

        .schedule-item {
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 10px;
            margin-bottom: 8px;
            font-size: 14px;
        }

        #reader {
            width: 100%;
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        .scan-message {
            background: white;
            border-radius: 15px;
            padding: 15px;
            margin-top: 15px;
            text-align: center;
            font-size: 16px;
        }

        .success {
            background: #d1fae5;
            border: 2px solid #10b981;
            color: #065f46;
        }

        .error {
            background: #fee2e2;
            border: 2px solid #ef4444;
            color: #991b1b;
        }

        .warning {
            background: #fef3c7;
            border: 2px solid #f59e0b;
            color: #92400e;
        }

        .student-info {
            text-align: left;
            margin-top: 15px;
        }

        .student-info div {
            padding: 8px 0;
            border-bottom: 1px solid rgba(0,0,0,0.1);
        }

        .student-info div:last-child {
            border-bottom: none;
        }

        .status-present {
            font-size: 22px;
            font-weight: bold;
            text-align: center;
            margin-top: 15px;
        }

        .hidden {
            display: none !important;
        }

        .loading {
            text-align: center;
            padding: 15px;
            font-size: 14px;
        }

        .refresh-button {
            width: 100%;
            border: none;
            padding: 13px;
            border-radius: 10px;
            background: #1f2937;
            color: white;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }

        .refresh-button:active {
            transform: scale(0.98);
        }

        @media (max-width: 400px) {
            .container {
                padding: 12px;
            }

            .header h1 {
                font-size: 21px;
            }

            .time {
                font-size: 26px;
            }
        }
    </style>
</head>

<body>

<div class="container">

    <div class="header">
        <h1>QR ATTENDANCE</h1>
        <p>Scan your Student QR Code</p>
    </div>

    <div class="clock-box">
        <div class="date" id="phoneDate">
            Loading date...
        </div>

        <div class="time" id="phoneTime">
            Loading time...
        </div>
    </div>

    <div class="schedule-box">
        <h2>Today's Schedule</h2>

        <div id="scheduleList">
            <div class="loading">
                Loading schedules...
            </div>
        </div>
    </div>

    <div id="reader"></div>

    <div
        id="result"
        class="scan-message hidden"
    ></div>

</div>


<script>

    // ========================================================
    // VARIABLES
    // ========================================================

    let scanner = null;
    let scanningLocked = false;

    // Keep the attendance result visible before the scanner starts again.
    // The status polling runs every 2 seconds, so this prevents polling
    // from immediately clearing the result after a successful scan.
    let resultHoldUntil = 0;
    let scannerAvailable = false;

    // Student IDs that already completed attendance on this scanner page.
    // The server also checks this, so refreshing the page cannot bypass
    // the one-attendance-per-student-per-schedule rule.
    let scannedStudentIds = new Set();
    let currentScheduleId = null;

    function showScannerLocked(message) {
        scanningLocked = true;
        document.getElementById("reader").style.display = "none";
        showResult(
            "warning",
            "<h2>SCANNER LOCKED</h2><p>" +
            escapeHtml(message || "Please wait for the teacher to enable the next student.") +
            "</p>"
        );
    }

    async function claimScanner() {
        try {
            const response = await fetch("/claim-scanner", {
                method: "POST"
            });
            const data = await response.json();

            if (!data.success) {
                scannerAvailable = false;
                showScannerLocked(data.message || "This scanner device is already in use.");
                return false;
            }

            scannerAvailable = true;
            scanningLocked = false;
            return true;
        } catch (error) {
            console.error("CLAIM SCANNER ERROR:", error);
            showScannerLocked("Could not connect to the attendance server.");
            return false;
        }
    }

    async function pollScannerStatus() {
        try {
            const phone = updatePhoneClock();
            const response = await fetch(
                "/status?date=" + encodeURIComponent(phone.date) +
                "&time=" + encodeURIComponent(phone.time),
                { cache: "no-store" }
            );
            const data = await response.json();

            if (!data.success || !data.scanner_owner || !data.owner_is_this_device) {
                return;
            }

            // A new subject/schedule automatically unlocks the scanner.
            // Clear the per-student lock when the schedule changes so the
            // same student can attend the next subject.
            if (data.current_schedule_id !== currentScheduleId) {
                currentScheduleId = data.current_schedule_id;
                scannedStudentIds.clear();
            }

            if (data.scan_allowed) {
                if (scanner === null) {

                    // Do not let the 2-second status poll erase the
                    // attendance result before the student can read it.
                    if (Date.now() < resultHoldUntil) {
                        return;
                    }

                    scanningLocked = false;
                    document.getElementById("result").className = "scan-message hidden";
                    document.getElementById("result").innerHTML = "";
                    await startScanner();
                }
                return;
            }

            // No current subject or this subject has already used its one scan.
            if (scanner !== null) {
                await hideScanner();
            }

            scanningLocked = true;

            if (data.reason) {
                showResult("warning", "<h2>SCANNER LOCKED</h2><p>" +
                    escapeHtml(data.reason) + "</p>");
            }
        } catch (error) {
            console.error("STATUS ERROR:", error);
        }
    }



    // ========================================================
    // PHONE DATE AND TIME
    // ========================================================

    function updatePhoneClock() {

        const now = new Date();

        const dateText =
            now.getFullYear() +
            "-" +
            String(now.getMonth() + 1).padStart(2, "0") +
            "-" +
            String(now.getDate()).padStart(2, "0");

        const timeText =
            String(now.getHours()).padStart(2, "0") +
            ":" +
            String(now.getMinutes()).padStart(2, "0") +
            ":" +
            String(now.getSeconds()).padStart(2, "0");

        document.getElementById("phoneDate").textContent =
            dateText;

        document.getElementById("phoneTime").textContent =
            timeText;

        return {
            date: dateText,
            time: timeText
        };
    }


    setInterval(updatePhoneClock, 1000);

    updatePhoneClock();


    // ========================================================
    // GET TODAY'S SCHEDULES
    // ========================================================

    async function loadSchedules() {

        const phone = updatePhoneClock();

        try {

            const response = await fetch(
                "/schedules?date=" +
                encodeURIComponent(phone.date)
            );

            const data = await response.json();

            const list =
                document.getElementById("scheduleList");

            if (!data.success) {

                list.innerHTML =
                    "<div class='error'>" +
                    "Could not load schedules." +
                    "</div>";

                return;
            }


            if (!data.schedules ||
                data.schedules.length === 0) {

                list.innerHTML =
                    "<div class='warning'>" +
                    "NO SCHEDULE TODAY" +
                    "</div>";

                return;
            }


            let html = "";

            data.schedules.forEach(function(schedule) {

                html +=
                    "<div class='schedule-item'>" +

                    "<strong>" +
                    escapeHtml(schedule.subject_code) +
                    "</strong><br>" +

                    escapeHtml(schedule.subject_name) +
                    "<br>" +

                    escapeHtml(schedule.start_time) +
                    " - " +
                    escapeHtml(schedule.end_time) +

                    "<br>" +

                    "Room: " +
                    escapeHtml(schedule.room || "TBA") +

                    "</div>";
            });


            list.innerHTML = html;

        } catch (error) {

            document.getElementById("scheduleList").innerHTML =
                "<div class='error'>" +
                "Could not connect to server." +
                "</div>";

            console.error(error);
        }
    }


    // ========================================================
    // ESCAPE HTML
    // ========================================================

    function escapeHtml(value) {

        if (value === null ||
            value === undefined) {

            return "";
        }

        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }


    // ========================================================
    // HIDE SCANNER
    // ========================================================

    async function hideScanner() {

        const reader =
            document.getElementById("reader");

        // Hide immediately
        reader.style.display = "none";

        if (scanner !== null) {

            try {
                await scanner.stop();
            } catch (error) {
                console.log("Scanner stop:", error);
            }

            try {
                await scanner.clear();
            } catch (error) {
                console.log("Scanner clear:", error);
            }
        }

        scanner = null;
    }


    // ========================================================
    // SHOW RESULT
    // ========================================================

    function showResult(type, html) {

        const result =
            document.getElementById("result");

        result.className =
            "scan-message " + type;

        result.innerHTML = html;

        result.classList.remove("hidden");
    }


    // ========================================================
    // SEND ATTENDANCE
    // ========================================================

    async function sendAttendance(qrCode) {

        const phone = updatePhoneClock();

        showResult(
            "warning",
            "Checking student and schedule..."
        );

        try {

            const response = await fetch(
                "/record-attendance",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        qr_code: qrCode,
                        phone_date: phone.date,
                        phone_time: phone.time
                    })
                }
            );


            const data =
                await response.json();


            // =================================================
            // SUCCESS
            // =================================================

            if (data.success) {

                showResult(
                    "success",

                    "<h2>ATTENDANCE RECORDED</h2>" +

                    "<div class='student-info'>" +

                    "<div>" +
                    "<strong>Student ID:</strong><br>" +
                    escapeHtml(data.student_id) +
                    "</div>" +

                    "<div>" +
                    "<strong>Student Name:</strong><br>" +
                    escapeHtml(data.student_name) +
                    "</div>" +

                    "<div>" +
                    "<strong>Subject:</strong><br>" +
                    escapeHtml(data.subject_code) +
                    " - " +
                    escapeHtml(data.subject_name) +
                    "</div>" +

                    "<div>" +
                    "<strong>Schedule:</strong><br>" +
                    escapeHtml(data.start_time) +
                    " - " +
                    escapeHtml(data.end_time) +
                    "</div>" +

                    "<div>" +
                    "<strong>Room:</strong><br>" +
                    escapeHtml(data.room || "TBA") +
                    "</div>" +

                    "<div>" +
                    "<strong>Date:</strong><br>" +
                    escapeHtml(data.attendance_date) +
                    "</div>" +

                    "<div>" +
                    "<strong>Time In:</strong><br>" +
                    escapeHtml(data.time_in) +
                    "</div>" +

                    "</div>" +

                    "<div class='status-present'>" +
                    escapeHtml((data.status || "Present").toUpperCase()) +
                    (data.minutes_late > 0
                        ? "<br><small>" + escapeHtml(data.minutes_late + " minute(s) late") + "</small>"
                        : "") +
                    "</div>"
                );

                return data;
            }


            // =================================================
            // DUPLICATE
            // =================================================

            if (data.already_recorded) {

                showResult(
                    "warning",

                    "<h2>ATTENDANCE ALREADY RECORDED</h2>" +

                    "<div class='student-info'>" +

                    "<div>" +
                    "<strong>Student ID:</strong><br>" +
                    escapeHtml(data.student_id) +
                    "</div>" +

                    "<div>" +
                    "<strong>Student Name:</strong><br>" +
                    escapeHtml(data.student_name) +
                    "</div>" +

                    "<div>" +
                    "<strong>Subject:</strong><br>" +
                    escapeHtml(data.subject_code) +
                    " - " +
                    escapeHtml(data.subject_name) +
                    "</div>" +

                    "<div>" +
                    "<strong>Date:</strong><br>" +
                    escapeHtml(data.attendance_date) +
                    "</div>" +

                    "<div>" +
                    "<strong>Time In:</strong><br>" +
                    escapeHtml(data.time_in) +
                    "</div>" +

                    "</div>" +

                    "<p><strong>" +
                    "ATTENDANCE ALREADY RECORDED FOR THIS SCHEDULE" +
                    "</strong></p>"
                );

                return data;
            }


            // =================================================
            // ABSENT - 30 MINUTES OR MORE LATE
            // =================================================

            if (data.attendance_closed) {
                showResult(
                    "error",
                    "<h2>ABSENT</h2>" +
                    "<div class='student-info'>" +
                    "<div><strong>Student ID:</strong><br>" + escapeHtml(data.student_id) + "</div>" +
                    "<div><strong>Student Name:</strong><br>" + escapeHtml(data.student_name) + "</div>" +
                    "<div><strong>Subject:</strong><br>" + escapeHtml(data.subject_code) + " - " + escapeHtml(data.subject_name) + "</div>" +
                    "<div><strong>Schedule:</strong><br>" + escapeHtml(data.start_time) + " - " + escapeHtml(data.end_time) + "</div>" +
                    "<div><strong>Time In:</strong><br>" + escapeHtml(data.time_in) + "</div>" +
                    "</div>" +
                    "<p><strong>" + escapeHtml(data.message) + "</strong></p>" +
                    "<div class='status-present'>ABSENT<br><small>" +
                    escapeHtml((data.minutes_late || 0) + " minute(s) late") +
                    "</small></div>"
                );
                return data;
            }


            // =================================================
            // NO SCHEDULE
            // =================================================

            showResult(
                "error",

                "<h2>NO SCHEDULE TODAY</h2>" +

                "<p>" +
                escapeHtml(
                    data.message ||
                    "There is no active schedule at this time."
                ) +
                "</p>"
            );

            return data;


        } catch (error) {

            console.error(error);

            showResult(
                "error",

                "<h2>CONNECTION ERROR</h2>" +

                "<p>" +
                "Could not connect to attendance server." +
                "</p>"
            );

            return null;
        }
    }


    // ========================================================
    // QR SCAN SUCCESS
    // ========================================================

    function getStudentIdFromQr(decodedText) {
        // Expected QR format: STUDENT:<student_id>:<unique_token>
        const parts = String(decodedText || "").split(":");

        if (parts.length >= 2 && parts[0] === "STUDENT") {
            return parts[1].trim();
        }

        return null;
    }


    async function onScanSuccess(decodedText) {

        // Prevent multiple scans while the current scan is being processed.
        if (scanningLocked) {
            return;
        }

        const studentId = getStudentIdFromQr(decodedText);

        // IMPORTANT: if this student already completed attendance for the
        // current scanner session, do not open/send the QR again.
        // Other students can still scan normally.
        if (studentId && scannedStudentIds.has(studentId)) {
            showResult(
                "warning",
                "<h2>ATTENDANCE ALREADY RECORDED</h2>" +
                "<p>This student has already scanned for this subject.</p>"
            );
            return;
        }

        scanningLocked = true;

        // IMPORTANT:
        // Hide camera immediately after successful scan.
        await hideScanner();

        // Send QR to server. The server remains the final authority and
        // also blocks duplicate attendance after a page refresh.
        const result = await sendAttendance(decodedText);

        // Keep the result visible for 10 seconds. This is also checked
        // by pollScannerStatus(), so the automatic status polling cannot
        // clear the result early.
        resultHoldUntil = Date.now() + 10000;

        // Mark the student as completed only when the server confirms that
        // this student already has an attendance record (including Absent).
        if (studentId && result &&
            (result.success || result.already_recorded || result.attendance_closed)) {
            scannedStudentIds.add(studentId);
        }

        // Automatically prepare the scanner for another student.
        // There is NO NEXT STUDENT button.
        setTimeout(async function() {
            scanningLocked = false;
            document.getElementById("result").className = "scan-message hidden";
            document.getElementById("result").innerHTML = "";
            if (scanner === null && scannerAvailable) {
                await startScanner();
            }
        }, 10000);
    }


    // ========================================================
    // QR SCAN ERROR
    // ========================================================

    function onScanFailure(error) {

        // Ignore normal scanner errors.
        // Camera keeps scanning until a QR is found.
    }


    // ========================================================
    // START SCANNER
    // ========================================================

    async function startScanner() {

        const reader =
            document.getElementById("reader");

        reader.style.display = "block";

        scanner =
            new Html5Qrcode("reader");


        const config = {

            fps: 10,

            qrbox: function(viewfinderWidth,
                             viewfinderHeight) {

                const size =
                    Math.min(
                        viewfinderWidth,
                        viewfinderHeight
                    ) * 0.70;

                return {
                    width: Math.floor(size),
                    height: Math.floor(size)
                };
            },

            aspectRatio: 1.0
        };


        try {

            await scanner.start(
                {
                    facingMode: "environment"
                },

                config,

                onScanSuccess,

                onScanFailure
            );

        } catch (error) {

            console.error(error);

            reader.style.display = "none";

            showResult(
                "error",

                "<h2>CAMERA ERROR</h2>" +

                "<p>" +
                "Please allow camera permission " +
                "and reload this page." +
                "</p>"
            );
        }
    }


    // ========================================================
    // START PAGE
    // ========================================================

    window.addEventListener(
        "load",
        async function() {

            await loadSchedules();

            const claimed = await claimScanner();

            if (claimed) {
                await pollScannerStatus();
            }

            setInterval(pollScannerStatus, 2000);
        }
    );

</script>

</body>
</html>
"""


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_phone_datetime(phone_date=None, phone_time=None):
    """
    Use the date and time sent by the cellphone.

    If the phone values are missing or invalid,
    use Asia/Manila server time as fallback.
    """

    if phone_date and phone_time:

        try:

            date_obj = datetime.strptime(
                phone_date,
                "%Y-%m-%d"
            )

            time_obj = datetime.strptime(
                phone_time,
                "%H:%M:%S"
            )

            return (
                date_obj.strftime("%Y-%m-%d"),
                time_obj.strftime("%H:%M:%S")
            )

        except ValueError:
            pass


    now = datetime.now(PH_TIMEZONE)

    return (
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M:%S")
    )


def parse_time(time_string):
    """
    Convert schedule time such as:
    8:00 AM
    10:30 AM
    12:00 PM
    3:30 PM

    into a datetime time object.
    """

    if not time_string:
        return None


    formats = [
        "%I:%M %p",
        "%I:%M:%S %p",
        "%H:%M",
        "%H:%M:%S"
    ]


    for fmt in formats:

        try:

            dt = datetime.strptime(
                time_string.strip(),
                fmt
            )

            return dt.time()

        except ValueError:
            continue


    return None


def format_time_for_display(time_string):
    """
    Convert stored schedule time into readable format.
    """

    parsed = parse_time(time_string)

    if parsed is None:
        return time_string or ""


    return parsed.strftime("%I:%M %p").lstrip("0")


def is_time_inside_schedule(
    current_time,
    start_time,
    end_time
):
    """
    Check if the phone time is inside the schedule.
    """

    start = parse_time(start_time)
    end = parse_time(end_time)

    if start is None or end is None:
        return False


    return start <= current_time <= end


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def home():

    return render_template_string(
        HTML_PAGE
    )


# ============================================================
# GET TODAY'S SCHEDULES
# ============================================================

@app.route("/schedules", methods=["GET"])
def get_schedules():

    requested_date = request.args.get(
        "date"
    )


    if not requested_date:

        now = datetime.now(PH_TIMEZONE)

        requested_date = now.strftime(
            "%Y-%m-%d"
        )


    try:

        schedules = db.fetch_all(
            """
            SELECT
                schedules.id,
                schedules.schedule_date,
                schedules.start_time,
                schedules.end_time,
                schedules.room,

                subjects.subject_code,
                subjects.subject_name

            FROM schedules

            INNER JOIN subjects
                ON schedules.subject_id = subjects.id

            WHERE schedules.schedule_date = ?

            ORDER BY
                schedules.start_time ASC
            """,
            (requested_date,)
        )


        result = []


        for schedule in schedules:

            result.append(
                {
                    "id": schedule["id"],

                    "schedule_date":
                        schedule["schedule_date"],

                    "start_time":
                        format_time_for_display(
                            schedule["start_time"]
                        ),

                    "end_time":
                        format_time_for_display(
                            schedule["end_time"]
                        ),

                    "room":
                        schedule["room"] or "TBA",

                    "subject_code":
                        schedule["subject_code"],

                    "subject_name":
                        schedule["subject_name"]
                }
            )


        return jsonify(
            {
                "success": True,
                "schedules": result
            }
        )


    except Exception as error:

        print(
            "GET SCHEDULE ERROR:",
            error
        )

        return jsonify(
            {
                "success": False,
                "message":
                    "Could not load schedules."
            }
        ), 500


# ============================================================
# SCANNER DEVICE CLAIM / LOCK CONTROL
# ============================================================

@app.route("/claim-scanner", methods=["POST"])
def claim_scanner():
    global scanner_owner_token

    token = request.cookies.get("scanner_device_id")

    if not token:
        token = secrets.token_urlsafe(32)

    # The latest device that opens the scanner becomes the authorized
    # scanner device. This allows switching from one cellphone/device
    # to another without getting permanently locked out.
    scanner_owner_token = token

    response = jsonify({
        "success": True,
        "scanner_locked": False,
        "scanner_owner": True
    })
    response.set_cookie(
        "scanner_device_id",
        token,
        httponly=True,
        samesite="Lax"
    )
    return response


@app.route("/next-student", methods=["POST"])
def next_student_blocked():
    return jsonify({
        "success": False,
        "message": "NEXT STUDENT IS CONTROLLED BY THE TEACHER DEVICE."
    }), 403


def is_local_admin_request():
    remote = request.remote_addr or ""
    return remote in ("127.0.0.1", "::1")


@app.route("/admin-scanner", methods=["GET"])
def admin_scanner_page():
    if not is_local_admin_request():
        return "Access denied. Open this page on the attendance PC.", 403

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Teacher Scanner Control</title>
<style>
body{font-family:Arial,sans-serif;background:#f2f4f7;margin:0;padding:30px;text-align:center}
.card{max-width:520px;margin:auto;background:white;padding:30px;border-radius:16px;box-shadow:0 2px 12px rgba(0,0,0,.12)}
h1{margin-top:0}.status{font-size:22px;font-weight:bold;margin:20px 0}
button{width:100%;padding:16px;border:0;border-radius:10px;background:#2563eb;color:white;font-size:18px;font-weight:bold;cursor:pointer;margin-top:10px}
.release{background:#dc2626}.note{font-size:14px;color:#555;line-height:1.5}
</style>
</head>
<body>
<div class="card">
<h1>Teacher Scanner Control</h1>
<div id="status" class="status">Checking...</div>
<p class="note">The cellphone scanner is always ready. There is no NEXT STUDENT button.</p>
<button class="release" onclick="releaseDevice()">RELEASE SCANNER DEVICE</button>
</div>
<script>
async function refreshStatus(){
 const r=await fetch('/status',{cache:'no-store'});
 const d=await r.json();
 document.getElementById('status').textContent=d.scanner_owner ? 'READY — waiting for student scan' : 'NO DEVICE CLAIMED';
}
async function nextStudent(){
 const r=await fetch('/admin-next-student',{method:'POST'});
 const d=await r.json(); alert(d.message); refreshStatus();
}
async function releaseDevice(){
 if(!confirm('Release the current scanner device?')) return;
 const r=await fetch('/admin-release-device',{method:'POST'});
 const d=await r.json(); alert(d.message); refreshStatus();
}
refreshStatus(); setInterval(refreshStatus,2000);
</script>
</body>
</html>
""")


@app.route("/admin-next-student", methods=["POST"])
def admin_next_student():
    global scanner_locked
    if not is_local_admin_request():
        return jsonify({"success": False, "message": "Access denied."}), 403

    if scanner_owner_token is None:
        return jsonify({
            "success": False,
            "message": "No scanner device is currently connected."
        }), 400

    return jsonify({
        "success": False,
        "message": "NEXT STUDENT is not used. The scanner unlocks automatically when the next subject starts."
    })


@app.route("/admin-release-device", methods=["POST"])
def admin_release_device():
    global scanner_locked, scanner_owner_token
    if not is_local_admin_request():
        return jsonify({"success": False, "message": "Access denied."}), 403

    scanner_locked = False
    scanner_owner_token = None
    return jsonify({
        "success": True,
        "locked": False,
        "message": "Scanner device released. The next cellphone to open the scanner can claim it."
    })


# RECORD ATTENDANCE
# ============================================================

@app.route(
    "/record-attendance",
    methods=["POST"]
)
def record_attendance():

    global scanner_locked, scanner_owner_token

    try:

        token = request.cookies.get("scanner_device_id")

        if scanner_owner_token is None or token != scanner_owner_token:
            return jsonify({
                "success": False,
                "scanner_locked": True,
                "message": "THIS DEVICE IS NOT THE AUTHORIZED SCANNER."
            }), 403

        # Scanner is always ready. There is no NEXT STUDENT lock.
        scanner_locked = False

        data = request.get_json()


        if not data:

            return jsonify(
                {
                    "success": False,
                    "message":
                        "No attendance data received."
                }
            ), 400


        qr_code = str(
            data.get("qr_code", "")
        ).strip()


        phone_date = data.get(
            "phone_date"
        )


        phone_time = data.get(
            "phone_time"
        )


        if not qr_code:

            return jsonify(
                {
                    "success": False,
                    "message":
                        "QR code is empty."
                }
            ), 400

        # ====================================================
        # PHONE DATE/TIME
        # ====================================================

        attendance_date, time_in = \
            get_phone_datetime(
                phone_date,
                phone_time
            )


        current_time = datetime.strptime(
            time_in,
            "%H:%M:%S"
        ).time()


        # ====================================================
        # FIND STUDENT
        # ====================================================

        student = db.fetch_one(
            """
            SELECT
                id,
                student_id,
                first_name,
                last_name,
                qr_code

            FROM users

            WHERE qr_code = ?

              AND role = 'student'
            """,
            (qr_code,)
        )


        if not student:

            return jsonify(
                {
                    "success": False,
                    "message":
                        "QR CODE NOT FOUND."
                }
            ), 404


        student_name = (
            str(student["first_name"]) +
            " " +
            str(student["last_name"])
        )


        # ====================================================
        # FIND TODAY'S SCHEDULES
        # ====================================================

        schedules = db.fetch_all(
            """
            SELECT
                schedules.id,
                schedules.subject_id,
                schedules.schedule_date,
                schedules.start_time,
                schedules.end_time,
                schedules.room,

                subjects.subject_code,
                subjects.subject_name

            FROM schedules

            INNER JOIN subjects
                ON schedules.subject_id =
                   subjects.id

            WHERE schedules.schedule_date = ?

            ORDER BY
                schedules.start_time ASC
            """,
            (attendance_date,)
        )


        if not schedules:

            return jsonify(
                {
                    "success": False,

                    "message":
                        "NO SCHEDULE TODAY",

                    "student_id":
                        student["student_id"],

                    "student_name":
                        student_name,

                    "attendance_date":
                        attendance_date,

                    "time_in":
                        time_in
                }
            )


        # ====================================================
        # FIND THE MOST RECENT SCHEDULE THAT HAS ALREADY STARTED
        # ====================================================
        # We intentionally do NOT require the current time to be
        # before the schedule end time. This is important because
        # a student who scans 30+ minutes after the start must still
        # be matched to that class so we can record ABSENT.

        current_minutes = current_time.hour * 60 + current_time.minute
        active_schedule = None
        active_start_minutes = None

        for schedule in schedules:

            schedule_start = parse_time(schedule["start_time"])

            if schedule_start is None:
                continue

            start_minutes = (
                schedule_start.hour * 60 +
                schedule_start.minute
            )

            # Only schedules that have already started are candidates.
            # Pick the one with the latest start time. This also makes
            # back-to-back classes work correctly.
            if start_minutes <= current_minutes:

                if (
                    active_start_minutes is None
                    or start_minutes > active_start_minutes
                ):
                    active_schedule = schedule
                    active_start_minutes = start_minutes


        # ====================================================
        # NO SCHEDULE THAT HAS STARTED YET
        # ====================================================

        if active_schedule is None:

            return jsonify(
                {
                    "success": False,
                    "message":
                        "NO ACTIVE SCHEDULE AT THIS TIME.",
                    "student_id":
                        student["student_id"],
                    "student_name":
                        student_name,
                    "attendance_date":
                        attendance_date,
                    "time_in":
                        time_in
                }
            )


        # Each student may scan ONLY ONCE for the current schedule.
        # Do NOT lock the whole scanner after the first student.
        # The duplicate check below prevents the same student from
        # recording attendance twice.

        schedule_id = active_schedule["id"]

        schedule_start = parse_time(
            active_schedule["start_time"]
        )

        if schedule_start is None:
            return jsonify({
                "success": False,
                "message": "INVALID SCHEDULE START TIME.",
                "student_id": student["student_id"],
                "student_name": student_name,
                "attendance_date": attendance_date,
                "time_in": time_in
            })

        start_minutes = (
            schedule_start.hour * 60 +
            schedule_start.minute
        )

        minutes_late = current_minutes - start_minutes


        # ====================================================
        # CHECK DUPLICATE ATTENDANCE BEFORE INSERTING
        # ====================================================

        existing = db.fetch_one(
            """
            SELECT
                attendance.id,
                attendance.attendance_date,
                attendance.time_in,
                attendance.status,

                subjects.subject_code,
                subjects.subject_name,

                schedules.start_time,
                schedules.end_time,
                schedules.room

            FROM attendance

            INNER JOIN schedules
                ON attendance.schedule_id =
                   schedules.id

            INNER JOIN subjects
                ON schedules.subject_id =
                   subjects.id

            WHERE attendance.user_id = ?
              AND attendance.schedule_id = ?
              AND attendance.attendance_date = ?

            LIMIT 1
            """,
            (
                student["id"],
                schedule_id,
                attendance_date
            )
        )


        if existing:

            return jsonify(
                {
                    "success": False,
                    "already_recorded": True,
                    "message":
                        "ATTENDANCE ALREADY RECORDED FOR THIS SCHEDULE",
                    "student_id":
                        student["student_id"],
                    "student_name":
                        student_name,
                    "subject_code":
                        existing["subject_code"],
                    "subject_name":
                        existing["subject_name"],
                    "start_time":
                        format_time_for_display(
                            existing["start_time"]
                        ),
                    "end_time":
                        format_time_for_display(
                            existing["end_time"]
                        ),
                    "room":
                        existing["room"] or "TBA",
                    "attendance_date":
                        existing["attendance_date"],
                    "time_in":
                        existing["time_in"],
                    "status":
                        existing["status"]
                }
            )


        # ====================================================
        # 0-14 MINUTES = PRESENT
        # 15-29 MINUTES = LATE
        # 30+ MINUTES = ABSENT
        # ====================================================

        if minutes_late >= 30:

            # Save an ABSENT record so it appears in the Dashboard.
            # The scan is NOT accepted as attendance.
            db.execute(
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
                    "Absent"
                )
            )

            return jsonify({
                "success": False,
                "attendance_closed": True,
                "absent": True,
                "minutes_late": minutes_late,
                "message":
                    "ABSENT. YOU ARE 30 MINUTES OR MORE LATE. ATTENDANCE IS NO LONGER ALLOWED.",
                "student_id": student["student_id"],
                "student_name": student_name,
                "subject_code": active_schedule["subject_code"],
                "subject_name": active_schedule["subject_name"],
                "start_time": format_time_for_display(active_schedule["start_time"]),
                "end_time": format_time_for_display(active_schedule["end_time"]),
                "room": active_schedule["room"] or "TBA",
                "attendance_date": attendance_date,
                "time_in": time_in,
                "status": "Absent"
            })


        status = "Late" if minutes_late >= 15 else "Present"


        # ====================================================
        # INSERT PRESENT / LATE ATTENDANCE
        # ====================================================

        db.execute(
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
                status
            )
        )


        # ====================================================
        # SUCCESS RESPONSE
        # ====================================================

        return jsonify(
            {
                "success": True,
                "message":
                    "ATTENDANCE RECORDED",
                "student_id":
                    student["student_id"],
                "student_name":
                    student_name,
                "subject_code":
                    active_schedule["subject_code"],
                "subject_name":
                    active_schedule["subject_name"],
                "start_time":
                    format_time_for_display(
                        active_schedule["start_time"]
                    ),
                "end_time":
                    format_time_for_display(
                        active_schedule["end_time"]
                    ),
                "room":
                    active_schedule["room"] or "TBA",
                "attendance_date":
                    attendance_date,
                "time_in":
                    time_in,
                "status":
                    status,
                "minutes_late":
                    minutes_late
            }
        )


        # ====================================================
        # CHECK DUPLICATE ATTENDANCE
        # ====================================================

        existing = db.fetch_one(
            """
            SELECT
                attendance.id,
                attendance.attendance_date,
                attendance.time_in,
                attendance.status,

                subjects.subject_code,
                subjects.subject_name,

                schedules.start_time,
                schedules.end_time,
                schedules.room

            FROM attendance

            INNER JOIN schedules
                ON attendance.schedule_id =
                   schedules.id

            INNER JOIN subjects
                ON schedules.subject_id =
                   subjects.id

            WHERE attendance.user_id = ?

              AND attendance.schedule_id = ?

              AND attendance.attendance_date = ?

            LIMIT 1
            """,
            (
                student["id"],
                schedule_id,
                attendance_date
            )
        )


        if existing:

            return jsonify(
                {
                    "success": False,

                    "already_recorded": True,

                    "message":
                        "ATTENDANCE ALREADY RECORDED FOR THIS SCHEDULE",

                    "student_id":
                        student["student_id"],

                    "student_name":
                        student_name,

                    "subject_code":
                        existing["subject_code"],

                    "subject_name":
                        existing["subject_name"],

                    "start_time":
                        format_time_for_display(
                            existing["start_time"]
                        ),

                    "end_time":
                        format_time_for_display(
                            existing["end_time"]
                        ),

                    "room":
                        existing["room"] or "TBA",

                    "attendance_date":
                        existing["attendance_date"],

                    "time_in":
                        existing["time_in"],

                    "status":
                        existing["status"]
                }
            )


        # ====================================================
        # INSERT ATTENDANCE
        # ====================================================

        db.execute(
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


        # ====================================================
        # SUCCESS RESPONSE
        # ====================================================

        return jsonify(
            {
                "success": True,

                "message":
                    "ATTENDANCE RECORDED",

                "student_id":
                    student["student_id"],

                "student_name":
                    student_name,

                "subject_code":
                    active_schedule["subject_code"],

                "subject_name":
                    active_schedule["subject_name"],

                "start_time":
                    format_time_for_display(
                        active_schedule["start_time"]
                    ),

                "end_time":
                    format_time_for_display(
                        active_schedule["end_time"]
                    ),

                "room":
                    active_schedule["room"] or "TBA",

                "attendance_date":
                    attendance_date,

                "time_in":
                    time_in,

                "status":
                    "Present"
            }
        )


    except Exception as error:

        print()
        print(
            "================================"
        )
        print(
            "ATTENDANCE SERVER ERROR"
        )
        print(
            "================================"
        )
        print(
            "Error:",
            error
        )
        print(
            "================================"
        )
        print()


        return jsonify(
            {
                "success": False,

                "message":
                    "Attendance could not be recorded.",

                "error":
                    str(error)
            }
        ), 500


# ============================================================
# SERVER STATUS
# ============================================================

@app.route(
    "/status",
    methods=["GET"]
)
def status():
    token = request.cookies.get("scanner_device_id")
    owner_exists = scanner_owner_token is not None
    owner_is_this_device = owner_exists and token == scanner_owner_token

    phone_date = request.args.get("date")
    phone_time = request.args.get("time")

    if not phone_date or not phone_time:
        now = datetime.now(PH_TIMEZONE)
        phone_date = now.strftime("%Y-%m-%d")
        phone_time = now.strftime("%H:%M:%S")

    current_time = parse_time(phone_time)
    current_schedule = None

    if current_time is not None:
        schedules = db.fetch_all(
            """
            SELECT
                schedules.id,
                schedules.schedule_date,
                schedules.start_time,
                schedules.end_time,
                schedules.room,
                subjects.subject_code,
                subjects.subject_name
            FROM schedules
            INNER JOIN subjects
                ON schedules.subject_id = subjects.id
            WHERE schedules.schedule_date = ?
            ORDER BY schedules.start_time ASC
            """,
            (phone_date,)
        )

        current_minutes = current_time.hour * 60 + current_time.minute
        latest_start = None

        for schedule in schedules:
            start_time = parse_time(schedule["start_time"])
            if start_time is None:
                continue

            start_minutes = start_time.hour * 60 + start_time.minute

            if start_minutes <= current_minutes and (
                latest_start is None or start_minutes > latest_start
            ):
                latest_start = start_minutes
                current_schedule = schedule

    # IMPORTANT:
    # The scanner must NOT lock after one student scans.
    # Each student's QR is locked individually by the duplicate check
    # in /record-attendance. The scanner remains available for all
    # other students during the current schedule.
    scan_allowed = current_schedule is not None
    reason = (
        "READY FOR SCAN. STUDENTS WHO HAVE NOT ATTENDED MAY SCAN."
        if current_schedule is not None
        else "WAITING FOR THE NEXT SUBJECT."
    )

    attendance_count = 0
    if current_schedule is not None:
        attendance_count_row = db.fetch_one(
            """
            SELECT COUNT(*) AS total
            FROM attendance
            WHERE schedule_id = ?
              AND attendance_date = ?
            """,
            (current_schedule["id"], phone_date)
        )
        attendance_count = int(attendance_count_row["total"] or 0)

    return jsonify(
        {
            "success": True,
            "server": "QR Attendance Server",
            "status": "running",
            "scanner_locked": not scan_allowed,
            "scanner_owner": owner_exists,
            "owner_is_this_device": owner_is_this_device,
            "scan_allowed": scan_allowed,
            "reason": reason,
            "current_schedule_id": (
                current_schedule["id"] if current_schedule else None
            ),
            "subject_code": (
                current_schedule["subject_code"] if current_schedule else None
            ),
            "subject_name": (
                current_schedule["subject_name"] if current_schedule else None
            ),
            "attendance_count": attendance_count
        }
    )


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print(
        "=========================================="
    )
    print(
        "       QR ATTENDANCE SERVER"
    )
    print(
        "=========================================="
    )
    print(
        "CELL PHONE SCANNER:"
    )
    print(
        "Use the Cloudflare URL on the authorized cellphone."
    )
    print()
    print(
        "TEACHER CONTROL (ON THIS PC):"
    )
    print(
        "https://127.0.0.1:5000/admin-scanner"
    )
    print()
    print(
        "Cloudflare Tunnel can also be used for the cellphone."
    )
    print(
        "=========================================="
    )
    print()


    try:

        app.run(
            host="0.0.0.0",
            port=5000,
            debug=False,
            ssl_context="adhoc"
        )

    except KeyboardInterrupt:

        print()
        print(
            "Server stopped."
        )

    finally:

        db.close()