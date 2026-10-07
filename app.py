from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from flask import Flask, render_template, request, redirect, url_for, session, send_file
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from pypdf import PdfReader
import os
from openai import OpenAI
import json
from config import DB_CONFIG
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.secret_key = "ai_assignment_secret_key"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def create_tables():
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            department VARCHAR(100)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            teacher_id VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            department VARCHAR(100),
            password VARCHAR(255) NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            teacher_id INT NOT NULL,
            subject VARCHAR(100) NOT NULL,
            topic VARCHAR(255) NOT NULL,
            total_questions INT NOT NULL,
            difficulty VARCHAR(50),
            total_marks INT NOT NULL,
            deadline DATE,
            pdf_path VARCHAR(255),
            status VARCHAR(50) DEFAULT 'Published',

            FOREIGN KEY (teacher_id)
            REFERENCES teachers(id)
            ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            assignment_id INT NOT NULL,
            question_number INT NOT NULL,
            question_text TEXT NOT NULL,
            marks INT NOT NULL,
            difficulty VARCHAR(50),
            answer_key TEXT,

            FOREIGN KEY (assignment_id)
            REFERENCES assignments(id)
            ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            assignment_id INT NOT NULL,
            student_id INT NOT NULL,
            file_name VARCHAR(255) NOT NULL,
            file_path VARCHAR(255) NOT NULL,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(50) DEFAULT 'Submitted',

            FOREIGN KEY (assignment_id)
            REFERENCES assignments(id)
            ON DELETE CASCADE,

            FOREIGN KEY (student_id)
            REFERENCES students(id)
            ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            submission_id INT NOT NULL,
            question_id INT NOT NULL,
            ai_marks DECIMAL(5,2) DEFAULT 0,
            teacher_marks DECIMAL(5,2),
            ai_feedback TEXT,
            teacher_feedback TEXT,
            teacher_approved BOOLEAN DEFAULT FALSE,

            FOREIGN KEY (submission_id)
            REFERENCES submissions(id)
            ON DELETE CASCADE,

            FOREIGN KEY (question_id)
            REFERENCES questions(id)
            ON DELETE CASCADE
        )
    """)

    db.commit()
    cursor.close()
    db.close()

    print("Database tables checked successfully!")
    
def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )
    
@app.route("/")
def home():
    return """
<!DOCTYPE html>
<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">

    <title>AI Assignment System</title>

    <style>

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: "Segoe UI", Arial, sans-serif;
            min-height: 100vh;

            background:
                radial-gradient(
                    circle at 15% 20%,
                    rgba(59, 130, 246, 0.35),
                    transparent 35%
                ),
                radial-gradient(
                    circle at 85% 80%,
                    rgba(124, 58, 237, 0.35),
                    transparent 35%
                ),
                linear-gradient(
                    135deg,
                    #0f172a,
                    #1e293b
                );

            color: white;
        }


        /* NAVBAR */

        .navbar {
            width: 100%;
            padding: 22px 7%;

            display: flex;
            justify-content: space-between;
            align-items: center;

            background: rgba(15, 23, 42, 0.55);

            border-bottom:
                1px solid rgba(255,255,255,0.08);

            backdrop-filter: blur(12px);
        }


        .logo {
            font-size: 22px;
            font-weight: 800;
        }


        .logo span {
            color: #60a5fa;
        }


        .login-btn {
            text-decoration: none;

            color: white;

            padding: 10px 22px;

            border: 1px solid
                rgba(255,255,255,0.25);

            border-radius: 9px;

            font-size: 14px;
            font-weight: 600;

            transition: 0.25s;
        }


        .login-btn:hover {
            background: white;
            color: #1e293b;
        }


        /* MAIN */

        .hero {
            min-height:
                calc(100vh - 75px);

            display: flex;

            align-items: center;
            justify-content: center;

            padding: 60px 7%;
        }


        .hero-content {
            width: 100%;
            max-width: 1100px;

            display: grid;

            grid-template-columns:
                1.1fr 0.9fr;

            gap: 70px;

            align-items: center;
        }


        /* LEFT */

        .hero-text h1 {
            font-size:
                clamp(42px, 5vw, 68px);

            line-height: 1.08;

            font-weight: 800;

            margin-bottom: 22px;
        }


        .hero-text h1 span {
            background:
                linear-gradient(
                    90deg,
                    #60a5fa,
                    #a78bfa
                );

            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }


        .hero-text p {
            max-width: 620px;

            color: #cbd5e1;

            font-size: 18px;

            line-height: 1.7;

            margin-bottom: 32px;
        }


        /* BUTTONS */

        .buttons {
            display: flex;

            gap: 14px;

            flex-wrap: wrap;
        }


        .btn {
            display: inline-block;

            padding: 14px 24px;

            border-radius: 10px;

            text-decoration: none;

            font-size: 15px;

            font-weight: 700;

            transition: 0.25s;
        }


        .student-btn {
            color: white;

            background:
                linear-gradient(
                    135deg,
                    #2563eb,
                    #7c3aed
                );

            box-shadow:
                0 10px 25px
                rgba(79,70,229,0.3);
        }


        .student-btn:hover {
            transform: translateY(-3px);
        }


        .teacher-btn {
            color: white;

            background:
                rgba(255,255,255,0.07);

            border:
                1px solid
                rgba(255,255,255,0.25);
        }


        .teacher-btn:hover {
            background:
                rgba(255,255,255,0.15);

            transform: translateY(-3px);
        }


        /* RIGHT CARD */

        .system-card {
            padding: 35px;

            border-radius: 24px;

            background:
                rgba(255,255,255,0.08);

            border:
                1px solid
                rgba(255,255,255,0.14);

            backdrop-filter: blur(15px);

            box-shadow:
                0 25px 60px
                rgba(0,0,0,0.25);
        }


        .system-icon {
            width: 70px;
            height: 70px;

            display: flex;

            align-items: center;
            justify-content: center;

            border-radius: 18px;

            font-size: 34px;

            background:
                linear-gradient(
                    135deg,
                    #2563eb,
                    #7c3aed
                );

            margin-bottom: 25px;
        }


        .system-card h2 {
            font-size: 25px;

            margin-bottom: 12px;
        }


        .system-card p {
            color: #cbd5e1;

            line-height: 1.6;

            margin-bottom: 22px;
        }


        /* FEATURES */

        .feature {
            display: flex;

            align-items: center;

            gap: 12px;

            padding: 12px 0;

            color: #e2e8f0;

            font-size: 14px;

            border-bottom:
                1px solid
                rgba(255,255,255,0.08);
        }


        .feature:last-child {
            border-bottom: none;
        }


        .check {
            width: 30px;
            height: 30px;

            display: flex;

            align-items: center;
            justify-content: center;

            border-radius: 8px;

            background:
                rgba(96,165,250,0.15);

            color: #60a5fa;
        }


        /* MOBILE */

        @media (max-width: 800px) {

            .hero {
                padding: 50px 5%;
            }

            .hero-content {
                grid-template-columns: 1fr;

                gap: 45px;
            }

            .hero-text {
                text-align: center;
            }

            .hero-text p {
                margin-left: auto;
                margin-right: auto;
            }

            .buttons {
                justify-content: center;
            }

        }


        @media (max-width: 480px) {

            .logo {
                font-size: 18px;
            }

            .login-btn {
                padding: 8px 15px;
            }

            .hero-text h1 {
                font-size: 40px;
            }

            .hero-text p {
                font-size: 15px;
            }

            .system-card {
                padding: 25px;
            }

        }

    </style>

</head>


<body>


    <!-- NAVBAR -->

    <nav class="navbar">

        <div class="logo">
            🤖 <span>AI</span> Assignment System
        </div>

        <a
            href="/login"
            class="login-btn"
        >
            Login
        </a>

    </nav>


    <!-- HERO -->

    <section class="hero">

        <div class="hero-content">


            <!-- LEFT -->

            <div class="hero-text">

                <h1>
                    Smart
                    <span>Assignment</span>
                    Management
                </h1>


                <p>
                    An intelligent platform for managing
                    assignments, generating questions with AI,
                    submitting answers and evaluating student
                    performance efficiently.
                </p>


                <div class="buttons">

                    <a
                        href="/student/register"
                        class="btn student-btn"
                    >
                        🎓 Student Registration
                    </a>


                    <a
                        href="/teacher/register"
                        class="btn teacher-btn"
                    >
                        👨‍🏫 Teacher Registration
                    </a>

                </div>

            </div>


            <!-- RIGHT -->

            <div class="system-card">

                <div class="system-icon">
                    🤖
                </div>


                <h2>
                    AI-Powered Learning
                </h2>


                <p>
                    Manage the complete assignment workflow
                    from creation to final evaluation in one
                    intelligent system.
                </p>


                <div class="feature">

                    <div class="check">
                        ✓
                    </div>

                    AI Question Generation

                </div>


                <div class="feature">

                    <div class="check">
                        ✓
                    </div>

                    Online PDF Submission

                </div>


                <div class="feature">

                    <div class="check">
                        ✓
                    </div>

                    AI-Based Evaluation

                </div>


                <div class="feature">

                    <div class="check">
                        ✓
                    </div>

                    Teacher Final Evaluation

                </div>


                <div class="feature">

                    <div class="check">
                        ✓
                    </div>

                    Student Result Dashboard

                </div>

            </div>

        </div>

    </section>


</body>

</html>
"""

@app.route("/student/register", methods=["GET", "POST"])
def student_register():

    if request.method == "POST":

        student_id = request.form["student_id"]
        name = request.form["name"]
        email = request.form["email"]
        department = request.form["department"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        try:
            db = get_db_connection()
            cursor = db.cursor()

            query = """
                INSERT INTO students
                (student_id, name, email, password, department)
                VALUES (%s, %s, %s, %s, %s)
            """

            values = (
                student_id,
                name,
                email,
                hashed_password,
                department
            )

            cursor.execute(query, values)

            db.commit()

            cursor.close()
            db.close()

            return """
            <h2>Student Registration Successful!</h2>
            <a href="/login">Go to Login</a>
            """

        except mysql.connector.Error as e:

            return f"""
            <h3>Registration Error</h3>
            <p>{e}</p>
            <a href="/student/register">Go Back</a>
            """

    return render_template("student_register.html")

@app.route("/teacher/register", methods=["GET", "POST"])
def teacher_register():

    if request.method == "POST":

        teacher_id = request.form["teacher_id"]
        name = request.form["name"]
        email = request.form["email"]
        department = request.form["department"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        try:
            db = get_db_connection()
            cursor = db.cursor()

            query = """
                INSERT INTO teachers
                (teacher_id, name, email, department, password)
                VALUES (%s, %s, %s, %s, %s)
            """

            values = (
                teacher_id,
                name,
                email,
                department,
                hashed_password
            )

            cursor.execute(query, values)

            db.commit()

            cursor.close()
            db.close()

            return """
            <h2>Teacher Registration Successful!</h2>
            <a href="/login">Go to Login</a>
            """

        except mysql.connector.Error as e:

            return f"""
            <h3>Registration Error</h3>
            <p>{e}</p>
            <a href="/teacher/register">Go Back</a>
            """

    return render_template("teacher_register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        user_id = request.form["user_id"]
        password = request.form["password"]
        role = request.form["role"]

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        if role == "student":

            cursor.execute(
                "SELECT * FROM students WHERE student_id = %s",
                (user_id,)
            )

            user = cursor.fetchone()

        else:

            cursor.execute(
                "SELECT * FROM teachers WHERE teacher_id = %s",
                (user_id,)
            )

            user = cursor.fetchone()

        cursor.close()
        db.close()

        # User check
        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["role"] = role
            session["name"] = user["name"]

            if role == "student":
                return redirect("/student/dashboard")

            else:
                return redirect("/teacher/dashboard")

        return """
        <h3>Invalid ID or Password</h3>
        <a href="/login">Try Again</a>
        """

    return render_template("login.html")

@app.route("/student/dashboard")
def student_dashboard():

    if "user_id" not in session or session.get("role") != "student":
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # =========================
    # Assignments + Submission Status
    # =========================

    cursor.execute("""
        SELECT
            a.*,
            s.id AS submission_id,
            s.status AS submission_status,
            (
                SELECT MAX(e.teacher_approved)
                FROM evaluations e
                WHERE e.submission_id = s.id
            ) AS teacher_approved
        FROM assignments a

        LEFT JOIN submissions s
            ON s.id = (
                SELECT s2.id
                FROM submissions s2
                WHERE s2.assignment_id = a.id
                AND s2.student_id = %s
                ORDER BY s2.submitted_at DESC, s2.id DESC
                LIMIT 1
            )

        ORDER BY a.id DESC
    """, (session["user_id"],))

    assignments = cursor.fetchall()

    # =========================
    # Total Assignments
    # =========================

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM assignments
    """)

    total_assignments = cursor.fetchone()["total"]

    # =========================
    # Submitted Assignments
    # =========================

    cursor.execute("""
        SELECT COUNT(DISTINCT assignment_id) AS total
        FROM submissions
        WHERE student_id = %s
    """, (session["user_id"],))

    submitted_assignments = cursor.fetchone()["total"]

    # =========================
    # Evaluated Assignments
    # =========================

    cursor.execute("""
        SELECT COUNT(DISTINCT submissions.assignment_id) AS total
        FROM submissions
        JOIN evaluations
            ON submissions.id = evaluations.submission_id
        WHERE submissions.student_id = %s
        AND evaluations.teacher_approved = 1
    """, (session["user_id"],))

    evaluated_assignments = cursor.fetchone()["total"]

    # =========================
    # Pending Assignments
    # =========================

    pending_assignments = (
        total_assignments - submitted_assignments
    )

    # =========================
    # Student Submission History
    # =========================

    cursor.execute("""
        SELECT
            submissions.id AS submission_id,
            submissions.assignment_id,
            submissions.file_name,
            submissions.submitted_at,
            submissions.status,
            assignments.subject,
            assignments.topic,
            assignments.total_marks,
            assignments.deadline
        FROM submissions
        JOIN assignments
            ON submissions.assignment_id = assignments.id
        WHERE submissions.student_id = %s
        ORDER BY submissions.submitted_at DESC
    """, (session["user_id"],))

    my_submissions = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "student_dashboard.html",
        name=session["name"],
        assignments=assignments,
        total_assignments=total_assignments,
        submitted_assignments=submitted_assignments,
        evaluated_assignments=evaluated_assignments,
        pending_assignments=pending_assignments,
        my_submissions=my_submissions
    )

@app.route("/teacher/dashboard")
def teacher_dashboard():

    if "user_id" not in session or session.get("role") != "teacher":
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    teacher_id = session["user_id"]

    # -----------------------------------
    # 1. Total Assignments
    # -----------------------------------
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM assignments
        WHERE teacher_id = %s
    """, (teacher_id,))

    total_assignments = cursor.fetchone()["total"]


    # -----------------------------------
    # 2. Total Students
    # -----------------------------------
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM students
    """)

    total_students = cursor.fetchone()["total"]


    # -----------------------------------
    # 3. Total Submissions
    # -----------------------------------
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM submissions
        JOIN assignments
            ON submissions.assignment_id = assignments.id
        WHERE assignments.teacher_id = %s
    """, (teacher_id,))

    total_submissions = cursor.fetchone()["total"]


    # -----------------------------------
    # 4. Average Score
    # -----------------------------------
    cursor.execute("""
        SELECT
            AVG(evaluations.teacher_marks) AS average_score
        FROM evaluations
        JOIN submissions
            ON evaluations.submission_id = submissions.id
        JOIN assignments
            ON submissions.assignment_id = assignments.id
        WHERE assignments.teacher_id = %s
        AND evaluations.teacher_marks IS NOT NULL
    """, (teacher_id,))

    result = cursor.fetchone()

    average_score = result["average_score"]

    if average_score is None:
        average_score = 0
    else:
        average_score = round(float(average_score), 1)


    cursor.close()
    db.close()


    return render_template(
        "teacher_dashboard.html",
        name=session["name"],
        teacher_id=teacher_id,
        total_assignments=total_assignments,
        total_students=total_students,
        total_submissions=total_submissions,
        average_score=average_score
    )
    
@app.route("/teacher/students")
def teacher_students():

    if "user_id" not in session or session.get("role") != "teacher":
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    teacher_id = session["user_id"]

    cursor.execute("""
        SELECT
            students.name AS student_name,
            students.student_id AS student_code,
            assignments.id AS assignment_id,
            assignments.subject,
            assignments.topic,
            assignments.total_marks,
            submissions.id AS submission_id,
            submissions.file_name,
            submissions.submitted_at,
            submissions.status,

            COALESCE(
                (
                    SELECT SUM(e.teacher_marks)
                    FROM evaluations e
                    WHERE e.submission_id = submissions.id
                ),
                0
            ) AS teacher_marks

        FROM submissions

        JOIN students
            ON submissions.student_id = students.id

        JOIN assignments
            ON submissions.assignment_id = assignments.id

        WHERE assignments.teacher_id = %s

        ORDER BY submissions.submitted_at DESC
    """, (teacher_id,))

    submitted_students = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "teacher_students.html",
        submitted_students=submitted_students
    )    
    
@app.route("/teacher/assignments")
def teacher_assignments():

    if "user_id" not in session or session.get("role") != "teacher":
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM assignments
        WHERE teacher_id = %s
        ORDER BY id DESC
    """, (session["user_id"],))

    assignments = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "teacher_assignments.html",
        assignments=assignments
    )
    
@app.route("/teacher/generate-questions/<int:assignment_id>", methods=["GET", "POST"])
def generate_questions(assignment_id):

    if "user_id" not in session or session.get("role") != "teacher":
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM assignments
        WHERE id = %s AND teacher_id = %s
    """, (assignment_id, session["user_id"]))

    assignment = cursor.fetchone()

    if not assignment:
        cursor.close()
        db.close()
        return "Assignment not found", 404

    questions = []

    if request.method == "POST":

        # -----------------------------------
        # 1. Generate questions using AI
        # -----------------------------------
        prompt = f"""
Generate exactly {assignment['total_questions']} educational questions.

Subject: {assignment['subject']}
Topic: {assignment['topic']}
Difficulty: {assignment['difficulty']}

Return only the questions as a numbered list.
Do not provide answers.
Do not provide marks.
"""

        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt
        )

        generated_text = response.output_text

        # -----------------------------------
        # 2. Clean generated questions
        # -----------------------------------
        generated_questions = []

        for line in generated_text.split("\n"):

            line = line.strip()

            if line:
                generated_questions.append(line)

        # -----------------------------------
        # 3. Make sure question count matches
        # -----------------------------------
        generated_questions = generated_questions[
            :assignment["total_questions"]
        ]

        # -----------------------------------
        # 4. Calculate marks per question
        # -----------------------------------
        total_marks = int(assignment["total_marks"])
        total_questions = int(assignment["total_questions"])

        base_marks = total_marks // total_questions
        remaining_marks = total_marks % total_questions

        # -----------------------------------
        # 5. Delete old questions
        # -----------------------------------
        cursor.execute("""
            DELETE FROM questions
            WHERE assignment_id = %s
        """, (assignment_id,))

        # -----------------------------------
        # 6. Save questions with marks
        # -----------------------------------
        question_number = 1

        for question_text in generated_questions:

            # Distribute remaining marks among
            # the first few questions
            question_marks = base_marks

            if question_number <= remaining_marks:
                question_marks += 1

            cursor.execute("""
                INSERT INTO questions
                (
                    assignment_id,
                    question_number,
                    question_text,
                    marks
                )
                VALUES (%s, %s, %s, %s)
            """, (
                assignment_id,
                question_number,
                question_text,
                question_marks
            ))

            question_number += 1

        db.commit()

        # -----------------------------------
        # 7. Show generated questions
        # -----------------------------------
        questions = generated_questions

    cursor.close()
    db.close()

    return render_template(
        "generate_questions.html",
        assignment=assignment,
        questions=questions
    )
@app.route("/teacher/assignment-pdf/<int:assignment_id>")
def assignment_pdf(assignment_id):

    if "user_id" not in session or session.get("role") != "teacher":
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Get assignment
    cursor.execute("""
        SELECT *
        FROM assignments
        WHERE id = %s AND teacher_id = %s
    """, (assignment_id, session["user_id"]))

    assignment = cursor.fetchone()

    if not assignment:
        cursor.close()
        db.close()
        return "Assignment not found", 404

    # Get questions
    cursor.execute("""
        SELECT *
        FROM questions
        WHERE assignment_id = %s
        ORDER BY question_number ASC
    """, (assignment_id,))

    questions = cursor.fetchall()
    
        # Student submission status
    student_id = session["user_id"]

    cursor.execute("""
        SELECT *
        FROM submissions
        WHERE assignment_id = %s
        AND student_id = %s
        ORDER BY submitted_at DESC
        LIMIT 1
    """, (assignment_id, student_id))

    submission = cursor.fetchone()

    cursor.close()
    db.close()

    # Create PDF in memory
    from io import BytesIO
    from flask import send_file

    buffer = BytesIO()

    pdf = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    y = height - 50

    # Title
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(
        width / 2,
        y,
        "AI Assignment"
    )

    y -= 40

    # Assignment details
    pdf.setFont("Helvetica-Bold", 11)

    pdf.drawString(
        50, y,
        f"Subject: {assignment['subject']}"
    )
    y -= 20

    pdf.drawString(
        50, y,
        f"Topic: {assignment['topic']}"
    )
    y -= 20

    pdf.drawString(
        50, y,
        f"Difficulty: {assignment['difficulty']}"
    )
    y -= 20

    pdf.drawString(
        50, y,
        f"Total Marks: {assignment['total_marks']}"
    )
    y -= 20

    pdf.drawString(
        50, y,
        f"Deadline: {assignment['deadline']}"
    )
    y -= 35

    # Questions heading
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Questions")

    y -= 25

    pdf.setFont("Helvetica", 11)

    for question in questions:

        question_text = question["question_text"]
        marks = question["marks"]
        number = question["question_number"]

        text = f"{number}. {question_text} ({marks} Marks)"

        words = text.split()
        line = ""

        for word in words:

            test_line = line + word + " "

            if pdf.stringWidth(
                test_line,
                "Helvetica",
                11
            ) < 490:

                line = test_line

            else:

                pdf.drawString(
                    50,
                    y,
                    line
                )

                y -= 18
                line = word + " "

        if line:

            pdf.drawString(
                50,
                y,
                line
            )

            y -= 25

        # New page
        if y < 60:

            pdf.showPage()

            y = height - 50

            pdf.setFont(
                "Helvetica",
                11
            )

    pdf.save()

    # Move buffer to beginning
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"assignment_{assignment_id}.pdf",
        mimetype="application/pdf"
    )
        
@app.route("/teacher/create-assignment", methods=["GET", "POST"])
def create_assignment():

    if "user_id" not in session or session.get("role") != "teacher":
        return redirect("/login")

    if request.method == "POST":

        subject = request.form["subject"]
        topic = request.form["topic"]
        total_questions = request.form["total_questions"]
        difficulty = request.form["difficulty"]
        total_marks = request.form["total_marks"]
        deadline = request.form["deadline"]

        db = get_db_connection()
        cursor = db.cursor()

        query = """
        INSERT INTO assignments
        (teacher_id, subject, topic, total_questions,
         difficulty, total_marks, deadline)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            session["user_id"],
            subject,
            topic,
            total_questions,
            difficulty,
            total_marks,
            deadline
        )

        cursor.execute(query, values)
        db.commit()

        cursor.close()
        db.close()

        return """
        <h2>Assignment Created Successfully!</h2>
        <a href="/teacher/dashboard">Go to Teacher Dashboard</a>
        """

    return render_template("create_assignment.html")
@app.route("/student/assignments")
def student_assignments():

    if "user_id" not in session or session.get("role") != "student":
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM assignments
        ORDER BY id DESC
    """)

    assignments = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "student_assignments.html",
        assignments=assignments
    )
    
@app.route("/student/assignment/<int:assignment_id>", methods=["GET", "POST"])
def student_assignment(assignment_id):

    if "user_id" not in session or session.get("role") != "student":
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Assignment details
    cursor.execute("""
        SELECT *
        FROM assignments
        WHERE id = %s
    """, (assignment_id,))

    assignment = cursor.fetchone()

    if not assignment:
        cursor.close()
        db.close()
        return "Assignment not found", 404

    # Questions
    cursor.execute("""
        SELECT *
        FROM questions
        WHERE assignment_id = %s
        ORDER BY question_number ASC
    """, (assignment_id,))

    questions = cursor.fetchall()

    # Student ID
    student_id = session["user_id"]

    # Existing submission status
    cursor.execute("""
        SELECT *
        FROM submissions
        WHERE assignment_id = %s
        AND student_id = %s
        ORDER BY submitted_at DESC
        LIMIT 1
    """, (assignment_id, student_id))

    submission = cursor.fetchone()

    # ------------------------------------------------
    # PDF SUBMISSION
    # ------------------------------------------------
    if request.method == "POST":

        # Deadline check
        from datetime import date

        if assignment["deadline"] is not None:
            if date.today() > assignment["deadline"]:

                cursor.close()
                db.close()

                return """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Deadline Passed</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            background: #f5f7fa;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                        }

                        .box {
                            background: white;
                            padding: 40px;
                            border-radius: 15px;
                            text-align: center;
                            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
                        }

                        h2 {
                            color: #dc2626;
                        }

                        a {
                            display: inline-block;
                            margin-top: 20px;
                            padding: 10px 20px;
                            background: #2563eb;
                            color: white;
                            text-decoration: none;
                            border-radius: 8px;
                        }
                    </style>
                </head>

                <body>

                    <div class="box">

                        <h2>⏰ Submission Deadline Passed</h2>

                        <p>
                            Sorry, the submission deadline for this assignment
                            has passed.
                        </p>

                        <p>
                            You can no longer submit this assignment.
                        </p>

                        <a href="/student/dashboard">
                            Go to Student Dashboard
                        </a>

                    </div>

                </body>
                </html>
                """

        # PDF file check
        if "assignment_pdf" not in request.files:
            cursor.close()
            db.close()
            return "Please select a PDF file."

        file = request.files["assignment_pdf"]

        if file.filename == "":
            cursor.close()
            db.close()
            return "Please select a PDF file."

        if not allowed_file(file.filename):
            cursor.close()
            db.close()
            return "Only PDF files are allowed."

        filename = secure_filename(file.filename)

        filename = f"student_{student_id}_assignment_{assignment_id}_{filename}"

        file_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        file.save(file_path)

        cursor.execute("""
            INSERT INTO submissions
            (assignment_id, student_id, file_name, file_path, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            assignment_id,
            student_id,
            filename,
            file_path,
            "Submitted"
        ))

        db.commit()

        cursor.close()
        db.close()

        return """
        <h2>✅ Assignment Submitted Successfully!</h2>
        <br>
        <a href="/student/dashboard">
            Go to Student Dashboard
        </a>
        """

    cursor.close()
    db.close()

    return render_template(
        "student_assignment.html",
        assignment=assignment,
        questions=questions,
        submission=submission
    )
    
@app.route("/student/delete-submission/<int:submission_id>", methods=["POST"])
def delete_student_submission(submission_id):

    if "user_id" not in session or session.get("role") != "student":
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Check that submission belongs to logged-in student
    cursor.execute("""
        SELECT *
        FROM submissions
        WHERE id = %s
        AND student_id = %s
    """, (
        submission_id,
        session["user_id"]
    ))

    submission = cursor.fetchone()

    if not submission:
        cursor.close()
        db.close()
        return "Submission not found", 404

    # Delete AI/teacher evaluations first
    cursor.execute("""
        DELETE FROM evaluations
        WHERE submission_id = %s
    """, (submission_id,))

    # Delete submission from database
    cursor.execute("""
        DELETE FROM submissions
        WHERE id = %s
        AND student_id = %s
    """, (
        submission_id,
        session["user_id"]
    ))

    db.commit()

    cursor.close()
    db.close()

    # Delete uploaded PDF file
    file_path = submission["file_path"]

    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    return redirect(
        "/student/assignment/" +
        str(submission["assignment_id"])
    )    
    
@app.route("/teacher/submissions")
def teacher_submissions():

    if "user_id" not in session or session.get("role") != "teacher":
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            submissions.id,
            submissions.assignment_id,
            submissions.student_id,
            submissions.file_name,
            submissions.file_path,
            submissions.submitted_at,
            submissions.status,
            assignments.subject,
            assignments.topic,
            students.name AS student_name,
            students.student_id AS student_code
        FROM submissions
        JOIN assignments
            ON submissions.assignment_id = assignments.id
        JOIN students
            ON submissions.student_id = students.id
        WHERE assignments.teacher_id = %s
        ORDER BY submissions.submitted_at DESC
    """, (session["user_id"],))

    submissions = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "teacher_submissions.html",
        submissions=submissions
    )
    
@app.route("/teacher/evaluate-submission/<int:submission_id>")
def evaluate_submission(submission_id):

    if "user_id" not in session or session.get("role") != "teacher":
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # ---------------------------------
    # 1. Get submission + assignment
    # ---------------------------------
    cursor.execute("""
        SELECT
            submissions.*,
            assignments.subject,
            assignments.topic,
            assignments.total_marks,
            assignments.teacher_id
        FROM submissions
        JOIN assignments
            ON submissions.assignment_id = assignments.id
        WHERE submissions.id = %s
        AND assignments.teacher_id = %s
    """, (submission_id, session["user_id"]))

    submission = cursor.fetchone()

    if not submission:
        cursor.close()
        db.close()
        return "Submission not found", 404

    # ---------------------------------
    # 2. Check PDF
    # ---------------------------------
    file_path = os.path.abspath(submission["file_path"])

    if not os.path.exists(file_path):
        cursor.close()
        db.close()
        return f"PDF file not found: {file_path}", 404

    # ---------------------------------
    # 3. Extract student answers
    # ---------------------------------
    reader = PdfReader(file_path)

    student_answers = ""

    for page in reader.pages:

        text = page.extract_text()

        if text:
            student_answers += text + "\n"

    # ---------------------------------
    # 4. Get assignment questions
    # ---------------------------------
    cursor.execute("""
        SELECT
            id,
            question_number,
            question_text,
            marks
        FROM questions
        WHERE assignment_id = %s
        ORDER BY question_number ASC
    """, (submission["assignment_id"],))

    questions = cursor.fetchall()

    if not questions:
        cursor.close()
        db.close()
        return "No questions found for this assignment.", 404

    # ---------------------------------
    # 5. Prepare questions for AI
    # ---------------------------------
    question_text = ""

    for question in questions:

        question_text += f"""
Question {question['question_number']}:
{question['question_text']}

Maximum Marks: {question['marks']}
--------------------------------
"""

    # ---------------------------------
    # 6. AI Evaluation Prompt
    # ---------------------------------
    evaluation_prompt = f"""
You are an expert college assignment evaluator.

Assignment Subject:
{submission['subject']}

Assignment Topic:
{submission['topic']}

Assignment Total Marks:
{submission['total_marks']}

IMPORTANT RULES:

1. Evaluate every question separately.
2. Use the student's submitted answer only.
3. Do not invent any answer that is not present in the student's PDF.
4. Compare the student's answer with the actual question.
5. Award marks according to the quality, correctness, completeness,
   relevance and accuracy of the student's answer.
6. The marks for each question MUST NOT exceed that question's
   Maximum Marks.
7. If the student did not answer a question, give 0 marks.
8. Do not automatically give full marks.
9. Do not automatically give 1 mark.
10. Partial marks are allowed.
11. The sum of all question marks should never exceed the assignment
    total marks.

ASSIGNMENT QUESTIONS:

{question_text}

STUDENT'S SUBMITTED ANSWER SHEET:

{student_answers}

Return ONLY valid JSON.

Do not use markdown.
Do not use ```json.
Do not write any explanation outside JSON.

Use exactly this structure:

[
    {{
        "question_number": 1,
        "marks": 8,
        "feedback": "Good answer with correct explanation."
    }},
    {{
        "question_number": 2,
        "marks": 6,
        "feedback": "Answer is partially correct but lacks some important points."
    }}
]

IMPORTANT:

- "marks" means marks awarded to the student.
- Never give more marks than the Maximum Marks of that question.
- Keep question_number exactly the same as the assignment.
- Evaluate ALL questions.
"""

    # ---------------------------------
    # 7. Send to OpenAI
    # ---------------------------------
    response = client.responses.create(
        model="gpt-5-mini",
        input=evaluation_prompt
    )

    evaluation_result = response.output_text.strip()

    # ---------------------------------
    # 8. Convert JSON
    # ---------------------------------
    try:

        evaluations = json.loads(evaluation_result)

    except json.JSONDecodeError:

        cursor.close()
        db.close()

        return f"""
        <h2>❌ AI returned invalid evaluation format</h2>
        <pre>{evaluation_result}</pre>
        """

    # ---------------------------------
    # 9. Delete old evaluation
    # ---------------------------------
    cursor.execute("""
        DELETE FROM evaluations
        WHERE submission_id = %s
    """, (submission_id,))

    # ---------------------------------
    # 10. Save AI evaluation
    # ---------------------------------
    total_ai_marks = 0

    for item in evaluations:

        question_number = item.get("question_number")
        ai_marks = item.get("marks", 0)
        ai_feedback = item.get("feedback", "")

        # Find actual question
        cursor.execute("""
            SELECT
                id,
                marks
            FROM questions
            WHERE assignment_id = %s
            AND question_number = %s
        """, (
            submission["assignment_id"],
            question_number
        ))

        question = cursor.fetchone()

        if not question:
            continue

        # ---------------------------------
        # Safety check:
        # AI marks cannot exceed max marks
        # ---------------------------------
        max_marks = question["marks"]

        try:
            ai_marks = float(ai_marks)
        except (TypeError, ValueError):
            ai_marks = 0

        if ai_marks < 0:
            ai_marks = 0

        if ai_marks > max_marks:
            ai_marks = max_marks

        # Remove .0 for whole numbers
        if ai_marks.is_integer():
            ai_marks = int(ai_marks)

        total_ai_marks += ai_marks

        # ---------------------------------
        # Insert evaluation
        # ---------------------------------
        cursor.execute("""
            INSERT INTO evaluations
            (
                submission_id,
                question_id,
                ai_marks,
                ai_feedback
            )
            VALUES (%s, %s, %s, %s)
        """, (
            submission_id,
            question["id"],
            ai_marks,
            ai_feedback
        ))

    db.commit()

    cursor.close()
    db.close()

    # ---------------------------------
    # 11. Show AI total
    # ---------------------------------
    return f"""
    <html>
    <head>
        <title>AI Evaluation</title>
    </head>

    <body style="font-family: Arial; padding: 40px;">

        <h2>🤖 AI Evaluation Completed</h2>

        <p>
            Evaluation successfully saved.
        </p>

        <hr>

        <h3>
            AI Total Marks:
            {total_ai_marks} / {submission['total_marks']}
        </h3>

        <hr>

        <h3>Question-wise Evaluation</h3>

        <pre>{evaluation_result}</pre>

        <br>

        <a href="/teacher/evaluation/{submission_id}">
            📊 View Full Evaluation
        </a>

    </body>
    </html>
    """
@app.route("/teacher/evaluation/<int:submission_id>")
def teacher_evaluation(submission_id):

    if "user_id" not in session or session.get("role") != "teacher":
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            evaluations.id,
            evaluations.submission_id,
            evaluations.question_id,
            evaluations.ai_marks,
            evaluations.teacher_marks,
            evaluations.ai_feedback,
            evaluations.teacher_feedback,
            evaluations.teacher_approved,
            questions.question_number,
            questions.question_text,
            questions.marks
        FROM evaluations
        JOIN questions
            ON evaluations.question_id = questions.id
        JOIN submissions
            ON evaluations.submission_id = submissions.id
        JOIN assignments
            ON submissions.assignment_id = assignments.id
        WHERE evaluations.submission_id = %s
        AND assignments.teacher_id = %s
        ORDER BY questions.question_number ASC
    """, (submission_id, session["user_id"]))

    evaluations = cursor.fetchall()

    cursor.close()
    db.close()

    if not evaluations:
        return "No evaluation found.", 404

    return render_template(
        "teacher_evaluation.html",
        evaluations=evaluations,
        submission_id=submission_id
    )
@app.route("/teacher/update-evaluation/<int:evaluation_id>", methods=["POST"])
def update_evaluation(evaluation_id):

    if "user_id" not in session or session.get("role") != "teacher":
        return redirect("/login")

    teacher_marks = request.form.get("teacher_marks")
    teacher_feedback = request.form.get("teacher_feedback")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Check evaluation belongs to this teacher
    cursor.execute("""
        SELECT evaluations.id
        FROM evaluations
        JOIN submissions
            ON evaluations.submission_id = submissions.id
        JOIN assignments
            ON submissions.assignment_id = assignments.id
        WHERE evaluations.id = %s
        AND assignments.teacher_id = %s
    """, (
        evaluation_id,
        session["user_id"]
    ))

    evaluation = cursor.fetchone()

    if not evaluation:
        cursor.close()
        db.close()
        return "Evaluation not found", 404

    # Update teacher marks and feedback
    cursor.execute("""
        UPDATE evaluations
        SET teacher_marks = %s,
            teacher_feedback = %s
        WHERE id = %s
    """, (
        teacher_marks,
        teacher_feedback,
        evaluation_id
    ))

    db.commit()

    cursor.close()
    db.close()

    return redirect(
        request.referrer or "/teacher/submissions"
    )
@app.route("/teacher/approve-evaluation/<int:evaluation_id>", methods=["POST"])
def approve_evaluation(evaluation_id):

    if "user_id" not in session or session.get("role") != "teacher":
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Check evaluation belongs to this teacher
    cursor.execute("""
        SELECT evaluations.id
        FROM evaluations
        JOIN submissions
            ON evaluations.submission_id = submissions.id
        JOIN assignments
            ON submissions.assignment_id = assignments.id
        WHERE evaluations.id = %s
        AND assignments.teacher_id = %s
    """, (
        evaluation_id,
        session["user_id"]
    ))

    evaluation = cursor.fetchone()

    if not evaluation:
        cursor.close()
        db.close()
        return "Evaluation not found", 404

    # Approve evaluation
    cursor.execute("""
        UPDATE evaluations
        SET teacher_approved = 1
        WHERE id = %s
    """, (evaluation_id,))

    db.commit()

    cursor.close()
    db.close()

    return redirect(
        request.referrer or "/teacher/submissions"
    )
@app.route("/student/result/<int:submission_id>")
def student_result(submission_id):

    if "user_id" not in session or session.get("role") != "student":
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            evaluations.id,
            evaluations.submission_id,
            evaluations.ai_marks,
            evaluations.teacher_marks,
            evaluations.ai_feedback,
            evaluations.teacher_feedback,
            evaluations.teacher_approved,
            questions.question_number,
            questions.question_text,
            questions.marks,
            assignments.subject,
            assignments.topic
        FROM evaluations
        JOIN questions
            ON evaluations.question_id = questions.id
        JOIN submissions
            ON evaluations.submission_id = submissions.id
        JOIN assignments
            ON submissions.assignment_id = assignments.id
        WHERE evaluations.submission_id = %s
        AND submissions.student_id = %s
        ORDER BY questions.question_number ASC
    """, (
        submission_id,
        session["user_id"]
    ))

    evaluations = cursor.fetchall()

    cursor.close()
    db.close()

    if not evaluations:
        return "Result not available yet.", 404

    # Calculate final marks
    total_marks = 0
    final_marks = 0

    for evaluation in evaluations:

        total_marks += evaluation["marks"]

        if evaluation["teacher_marks"] is not None:
            final_marks += evaluation["teacher_marks"]

    return render_template(
        "student_result.html",
        evaluations=evaluations,
        submission_id=submission_id,
        total_marks=total_marks,
        final_marks=final_marks
    )       
@app.route("/teacher/submission/<int:submission_id>")
def view_submission(submission_id):

    if "user_id" not in session or session.get("role") != "teacher":
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT submissions.file_path
        FROM submissions
        JOIN assignments
            ON submissions.assignment_id = assignments.id
        WHERE submissions.id = %s
        AND assignments.teacher_id = %s
    """, (submission_id, session["user_id"]))

    submission = cursor.fetchone()

    cursor.close()
    db.close()

    if not submission:
        return "Submission not found", 404

    file_path = os.path.abspath(submission["file_path"])

    if not os.path.exists(file_path):
        return f"PDF file not found: {file_path}", 404

    return send_file(
        file_path,
        as_attachment=False,
        mimetype="application/pdf"
    )
    
@app.route("/teacher/submission-status/<int:submission_id>/<status>")
def update_submission_status(submission_id, status):

    if "user_id" not in session or session.get("role") != "teacher":
        return redirect("/login")

    if status not in ["Pending", "Reviewed", "Rejected"]:
        return "Invalid status", 400

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE submissions
        SET status = %s
        WHERE id = %s
        AND assignment_id IN (
            SELECT id
            FROM assignments
            WHERE teacher_id = %s
        )
    """, (
        status,
        submission_id,
        session["user_id"]
    ))

    db.commit()

    cursor.close()
    db.close()

    return redirect("/teacher/submissions")
    
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")

if __name__ == "__main__":

    create_tables()

    app.run(debug=True)