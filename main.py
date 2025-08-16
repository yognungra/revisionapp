import sqlite3
import hashlib
from argon2 import PasswordHasher
from datetime import datetime
import json
import random
import pandas as pd
import os

ph = PasswordHasher()
from session import session

# Connect to the SQLite database
connection = sqlite3.connect("tables.db")
c = connection.cursor()
c.execute("PRAGMA foreign_keys = ON;")

connection.commit()

global current_user_token
current_user_token = None


# Helper functions
def get_user_role(user_id):
    return c.execute("SELECT UserRole FROM Users WHERE UserID=?", (user_id,)).fetchone()[0].lower()

def get_school_id(user_id):
    return c.execute("SELECT SchoolID FROM Users WHERE UserID=?", (user_id,)).fetchone()[0]

def get_teacher_id(user_id):
    return c.execute("SELECT TeacherID FROM Teachers WHERE UserID=?", (user_id,)).fetchone()[0]

def get_student_id(user_id):
    return c.execute("SELECT StudentID FROM Students WHERE UserID=?", (user_id,)).fetchone()[0]

def ensure_logged_in():
    if current_user_token is None:
        print("❌ You must be logged in to perform this action.")
        return False
    return True

def create_indexes():
    # Creating indexes to speed up queries
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_school_id ON Users(SchoolID);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_class_id ON Enrollment(ClassID);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON Users(UserID);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_student_id ON Enrollment(StudentID);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_teacher_id ON ClassTeachers(TeacherID);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_classes_class_id ON Classes(ClassID);")
        connection.commit()
        print("Indexes created successfully!")
    except sqlite3.DatabaseError as e:
        print(f"Error creating indexes: {e}")


# Create tables
c.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        UserID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        FirstName TEXT NOT NULL,
        LastName TEXT NOT NULL,
        Email TEXT NOT NULL,
        PasswordHash TEXT NOT NULL,
        UserRole TEXT NOT NULL,
        SchoolID INTEGER,
        IsSchoolAdmin BOOLEAN DEFAULT FALSE NOT NULL,
        DateCreated DATE DEFAULT current_timestamp NOT NULL,
        FOREIGN KEY(SchoolID) REFERENCES Schools(SchoolID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")

c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON Users(Email);")


c.execute("""
    CREATE TABLE IF NOT EXISTS Students (
        StudentID INTEGER PRIMARY KEY NOT NULL,
        YearGroup INTEGER NOT NULL,
        UserID INTEGER NOT NULL,
        FOREIGN KEY(UserID) REFERENCES Users(UserID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")

c.execute("""
    CREATE TABLE IF NOT EXISTS Teachers (
        TeacherID INTEGER PRIMARY KEY NOT NULL,
        UserID INTEGER NOT NULL,
        FOREIGN KEY(UserID) REFERENCES Users(UserID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")

c.execute("""
    CREATE TABLE IF NOT EXISTS Classes (
        ClassID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        LocalClassIdentifier TEXT NOT NULL,
        SchoolID INTEGER NOT NULL,
        FOREIGN KEY(SchoolID) REFERENCES Schools(SchoolID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")

c.execute("""
    CREATE TABLE IF NOT EXISTS ClassTeachers (
        ClassTeacherID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        ClassID INTEGER NOT NULL,
        TeacherID INTEGER NOT NULL,
        FOREIGN KEY(ClassID) REFERENCES Classes(ClassID) ON DELETE CASCADE ON UPDATE CASCADE,
        FOREIGN KEY(TeacherID) REFERENCES Teachers(TeacherID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")

c.execute("""
    CREATE TABLE IF NOT EXISTS Enrollment (
        EnrollmentID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        StudentID INTEGER NOT NULL,
        ClassID INTEGER NOT NULL,
        DateEnrolled DATE DEFAULT current_date NOT NULL,
        FOREIGN KEY(StudentID) REFERENCES Students(StudentID) ON DELETE CASCADE ON UPDATE CASCADE,
        FOREIGN KEY(ClassID) REFERENCES Classes(ClassID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")

c.execute("""
    CREATE TABLE IF NOT EXISTS StudentBusyTimes (
        BusyID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        StudentID INTEGER NOT NULL,
        StartTime TEXT NOT NULL,
        EndTime TEXT NOT NULL,
        FOREIGN KEY(StudentID) REFERENCES Students(StudentID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")


c.execute("""
    CREATE TABLE IF NOT EXISTS Schools (
        SchoolID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        SchoolName TEXT NOT NULL
    );
""")

c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_schools_name ON Schools(SchoolName);")

c.execute("""
    CREATE TABLE IF NOT EXISTS Periods (
        PeriodID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        StartTime TEXT NOT NULL,
        EndTime TEXT NOT NULL,
        ClassID INTEGER NOT NULL,
        TeacherID INTEGER NOT NULL,
        FOREIGN KEY(TeacherID) REFERENCES Teachers(TeacherID) ON DELETE CASCADE ON UPDATE CASCADE,
        FOREIGN KEY(ClassID) REFERENCES Classes(ClassID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")

c.execute("""
    CREATE TABLE IF NOT EXISTS EnrollmentRequests (
        RequestID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        StudentID INTEGER NOT NULL,
        ClassID INTEGER NOT NULL,
        RequestDate DATE DEFAULT current_date NOT NULL,
        Status TEXT DEFAULT 'Pending' NOT NULL,
        FOREIGN KEY(StudentID) REFERENCES Students(StudentID) ON DELETE CASCADE ON UPDATE CASCADE,
        FOREIGN KEY(ClassID) REFERENCES Classes(ClassID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")

c.execute("""
    CREATE TABLE IF NOT EXISTS SchoolJoinRequests (
        RequestID INTEGER PRIMARY KEY AUTOINCREMENT,
        UserID INTEGER NOT NULL,
        SchoolID INTEGER NOT NULL,
        Status TEXT DEFAULT 'Pending' NOT NULL,
        RequestDate DATE DEFAULT current_date,
        FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE,
        FOREIGN KEY (SchoolID) REFERENCES Schools(SchoolID) ON DELETE CASCADE
    );
""")

c.execute("""
    CREATE TABLE IF NOT EXISTS HomeworkTasks (
        HomeworkID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        Title TEXT NOT NULL,
        Description TEXT NOT NULL,
        TimeToComplete INTEGER NOT NULL,
        DueDate DATE NOT NULL,
        HomeworkType TEXT NOT NULL,  -- Type of the homework (e.g., Quiz, Assignment, etc.),
        DateAssigned DATE DEFAULT current_date NOT NULL,
        ClassID INTEGER NOT NULL,
        TeacherID INTEGER NOT NULL,
        AssignmentID INTEGER DEFAULT NULL,
        FOREIGN KEY(ClassID) REFERENCES Classes(ClassID) ON DELETE CASCADE ON UPDATE CASCADE,
        FOREIGN KEY(TeacherID) REFERENCES Teachers(TeacherID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")

c.execute("""
    CREATE TABLE IF NOT EXISTS StudentQuizResults (
        ResultID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        StudentID INTEGER NOT NULL,
        HomeworkID INTEGER NOT NULL,
        QuestionID INTEGER NOT NULL,
        AnswerGiven TEXT,
        FOREIGN KEY(StudentID) REFERENCES Students(StudentID) ON DELETE CASCADE ON UPDATE CASCADE,
        FOREIGN KEY(HomeworkID) REFERENCES HomeworkTasks(HomeworkID) ON DELETE CASCADE ON UPDATE CASCADE,
        FOREIGN KEY(QuestionID) REFERENCES QuizQuestions(QuestionID) ON DELETE CASCADE ON UPDATE CASCADE
    );            
""")


# Topics belong to a school
c.execute("""
    CREATE TABLE IF NOT EXISTS QuestionTopics (
        TopicID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        SchoolID INTEGER NOT NULL,
        TopicName TEXT NOT NULL,
        UNIQUE(SchoolID, TopicName),
        FOREIGN KEY (SchoolID) REFERENCES Schools(SchoolID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")

# Questions belong to a school and a topic
c.execute("""
    CREATE TABLE IF NOT EXISTS QuizQuestions (
        QuestionID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        SchoolID INTEGER NOT NULL,
        TopicID INTEGER NOT NULL,
        QuestionText TEXT NOT NULL,
        DifficultyLevel TEXT CHECK(DifficultyLevel IN ('Easy', 'Medium', 'Hard')) NOT NULL,
        AnswerOptions TEXT NOT NULL,  -- JSON string containing answer options
        CorrectAnswer TEXT NOT NULL,
        DateAdded DATE DEFAULT current_date NOT NULL,
        FOREIGN KEY (SchoolID) REFERENCES Schools(SchoolID) ON DELETE CASCADE ON UPDATE CASCADE,
        FOREIGN KEY (TopicID) REFERENCES QuestionTopics(TopicID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")

# Quizzes belong to a class (and therefore a school)
c.execute("""
    CREATE TABLE IF NOT EXISTS Quizzes (
        QuizID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        Title TEXT NOT NULL,
        ClassID INTEGER NOT NULL,
        TeacherID INTEGER NOT NULL,
        DateAssigned DATE DEFAULT current_date NOT NULL,
        FOREIGN KEY(ClassID) REFERENCES Classes(ClassID) ON DELETE CASCADE,
        FOREIGN KEY(TeacherID) REFERENCES Teachers(TeacherID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")

# Link table for quiz-question assignments
c.execute("""
    CREATE TABLE IF NOT EXISTS QuizQuestionAssignments (
        AssignmentID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        QuizID INTEGER NOT NULL,
        QuestionID INTEGER NOT NULL,
        FOREIGN KEY(QuizID) REFERENCES Quizzes(QuizID) ON DELETE CASCADE ON UPDATE CASCADE,
        FOREIGN KEY(QuestionID) REFERENCES QuizQuestions(QuestionID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")

connection.commit()

def log_in():
    global current_user_token
    print("Welcome to the Revision App!")
    while True:
        choice = input("Are you an existing user (Y/N)? Or type 'Q' to quit: ").strip().lower()
        if choice == 'y':
            return login_flow()
        elif choice == 'n':
            return sign_up()
        elif choice == 'q':
            print("Exiting the application.")
            exit()
        else:
            print("Invalid option. Try again.")

def login_flow():
    global current_user_token
    while True:
        email = input("Email: ")
        row = c.execute("SELECT UserID, PasswordHash, UserRole FROM Users WHERE Email=?", (email,)).fetchone()
        if not row:
            print("Email not found. Please try again.")
            continue

        user_id, password_hash, role = row
        password = input("Password: ")
        try:
            ph.verify(password_hash, password)
            session.login(user_id, role)
            print(f"✅ Login successful! User ID: {session.get_user_id()}")
            return student_options() if role.lower() == "student" else teacher_options()
        except:
            print("❌ Incorrect password. Please try again.")

def sign_up():
    global current_user_token
    print("Please fill in the following details to sign up:")
    first_name = input("First Name: ")
    last_name = input("Last Name: ")

    # Email uniqueness
    while True:
        email = input("Email: ")
        if c.execute("SELECT 1 FROM Users WHERE Email=?", (email,)).fetchone():
            print("⚠️ Email already exists. Try a different one.")
        else:
            break

    # Password and Role
    password = input("Password: ")
    hashed_password = ph.hash(password)

    while True:
        user_role = input("User Role (Student/Teacher): ").strip().lower()
        if user_role in ["student", "teacher"]:
            break
        print("Invalid role. Please enter 'Student' or 'Teacher'.")

    # Optional School ID
    school_id = None
    school_input = input("School ID (leave blank if none): ").strip()
    if school_input:
        try:
            school_id = int(school_input)
            if not c.execute("SELECT 1 FROM Schools WHERE SchoolID=?", (school_id,)).fetchone():
                print("⚠️ Invalid school ID. Ignoring.")
                school_id = None
        except:
            print("⚠️ Invalid input. Ignoring school ID.")

    # Insert User
    c.execute("""INSERT INTO Users (FirstName, LastName, Email, PasswordHash, UserRole)
                 VALUES (?, ?, ?, ?, ?)""", (first_name, last_name, email, hashed_password, user_role))
    connection.commit()
    
    user_id = c.execute("SELECT UserID FROM Users WHERE Email=?", (email,)).fetchone()[0]
    current_user_token = user_id
    session.login(user_id, user_role)

    if school_id:
        c.execute("INSERT INTO SchoolJoinRequests (UserID, SchoolID) VALUES (?, ?)", (current_user_token, school_id))
    connection.commit()

    if user_role == "student":
        year_group = int(input("Year Group: "))
        c.execute("INSERT INTO Students (YearGroup, UserID) VALUES (?, ?)", (year_group, user_id))
    else:
        c.execute("INSERT INTO Teachers (UserID) VALUES (?)", (user_id,))

    connection.commit()
    print("🎉 Registration complete!")
    return student_options() if user_role == "student" else teacher_options()

def add_school():
    global current_user_token
    if session.is_logged_in() is False:
        print("You must be logged in to add a school.")
        return False
    if not session.require_role("teacher"):
        print("Entry denied! Only teachers can add schools.")
        return False
    if c.execute("SELECT IsSchoolAdmin FROM Users WHERE UserID=?", (session.get_user_id(),)).fetchone()[0]:
        print("Entry denied! You are already a school admin. Leave the school admin role to add a new school.")
        return False
    
    # Check if the user is a teacher and not already a school admin
    c.execute("UPDATE Users SET IsSchoolAdmin = TRUE WHERE UserID = ?", (session.get_user_id(),))
    print("You are now a school admin.")

    school_name = input("Enter the school name: ")
    c.execute("INSERT INTO Schools(SchoolName) VALUES(?);", (school_name,))
    c.execute("UPDATE Users SET SchoolID = (SELECT SchoolID FROM Schools WHERE SchoolName = ?) WHERE UserID = ?;", 
              (school_name, session.get_user_id()))
    connection.commit()
    print("School added successfully!")

def add_class():
    global current_user_token
    if session.is_logged_in() is False:
        print("You must be logged in to add a class.")
        return False
    
    if not session.require_role("teacher"):
        print("Entry denied! Only teachers can add classes.")
        return False
    
    if get_school_id(session.get_user_id()) is None:
        print("You must be associated with a school to add a class.")
        return False
    
    input_verified = False
    while not input_verified:
        local_class_identifier = input("Enter the local class identifier: ")
        if not local_class_identifier.strip():
            print("Local class identifier cannot be empty. Please try again.")
            continue
        c.execute("SELECT LocalClassIdentifier FROM Classes WHERE LocalClassIdentifier=?", (local_class_identifier,))
        if c.fetchone() is not None:
            print("This class identifier already exists. Please choose a different one.")
            continue
        else:
            input_verified = True
    school_id = get_school_id(session.get_user_id())
    c.execute("INSERT INTO Classes(LocalClassIdentifier, SchoolID) VALUES(?, ?);", 
              (local_class_identifier, school_id))
    connection.commit()
    print("Class added successfully!")

    return True

def add_teacher_to_class():
    global current_user_token
    if session.is_logged_in() is False:
        print("You must be logged in to add a teacher to a class.")
        return
    
    if not session.require_role("teacher"):
        print("Entry denied! Only teachers can add teachers to classes.")
        return False
    
    if not c.execute("SELECT IsSchoolAdmin FROM Users WHERE UserID=?", (session.get_user_id(),)).fetchone()[0]:
        print("Entry denied! You must be a school admin to add teachers to your classes.")
        return False
    

    class_id = int(input("Enter the class ID: "))
    teacher_id = int(input("Enter the teacher ID (or leave blank to select yourself): ") or get_teacher_id(session.get_user_id()))

    c.execute("SELECT SchoolID FROM Classes WHERE ClassID=?", (class_id,))
    school_id = c.fetchone()
    if c.execute("SELECT SchoolID FROM Users WHERE UserID=?", (session.get_user_id(),)).fetchone()[0] != school_id[0]:
        print("Entry denied! The teacher must belong to the same school as the class.")
        return False
    
    if c.execute("SELECT ClassID FROM ClassTeachers WHERE ClassID=? AND TeacherID=?", (class_id, teacher_id)).fetchone() is not None:
        print("This teacher is already assigned to this class.")
        return False


    c.execute("INSERT INTO ClassTeachers(ClassID, TeacherID) VALUES(?, ?);", 
              (class_id, teacher_id))
    connection.commit()
    print("Teacher added to class successfully!")
    return True

def add_student_to_class():
    global current_user_token
    if session.is_logged_in() is False:
        print("You must be logged in to add a student to a class.")
        return
    
    if not session.require_role("teacher"):
        print("Entry denied! Only teachers can add students to classes.")
        return False
    
    student_id = int(input("Enter the student ID: "))
    class_id = int(input("Enter the class ID: "))
    c.execute("INSERT INTO Enrollment(StudentID, ClassID) VALUES(?, ?);", 
              (student_id, class_id))
    connection.commit()
    print("Student added to class successfully!")
    return True

def request_to_join_class():
    global current_user_token
    if session.is_logged_in() is False:
        print("You must be logged in to request to join a class.")
        return
    
    if not session.require_role("student"):
        print("Entry denied! Only students can request to join classes.")
        return False
    
    class_id = int(input("Enter the class ID you want to join: "))

    class_exists = c.execute("SELECT ClassID FROM Classes WHERE ClassID=?", (class_id,)).fetchone()
    if class_exists is None:
        print("Class does not exist. Please check the class ID and try again.")
        return False
    
    if c.execute("SELECT SchoolID FROM Classes WHERE ClassID=?", (class_id,)).fetchone()[0] != get_school_id(session.get_user_id()):
        print("Entry denied! You can only request to join classes in your school.")
        return False

    student_id = get_student_id(session.get_user_id())
    if c.execute("SELECT StudentID FROM Enrollment WHERE StudentID=? AND ClassID=?", (student_id, class_id)).fetchone() is not None:
        print("You are already enrolled in this class.")
        return False
    
    c.execute("INSERT INTO EnrollmentRequests(StudentID, ClassID) VALUES(?, ?);", 
              (student_id, class_id))
    
    connection.commit()
    print("Request to join class submitted successfully!") 
    return True

def approve_enrollment_request():
    global current_user_token
    if session.is_logged_in() is False:
        print("You must be logged in to approve enrollment requests.")
        return
    
    if not session.require_role("teacher"):
        print("Entry denied! Only teachers can approve enrollment requests.")
        return False
    
    list_requests = c.execute("SELECT RequestID, StudentID, ClassID FROM EnrollmentRequests WHERE ClassID IN (SELECT ClassID FROM ClassTeachers WHERE TeacherID=(SELECT TeacherID FROM Teachers WHERE UserID=?));", (session.get_user_id(),)).fetchall()
    if not list_requests:
        print("No enrollment requests to approve.")
        return False
    
    print("Enrollment Requests:")
    for request in list_requests:
        print(f"Request ID: {request[0]}, Student ID: {request[1]}, Class ID: {request[2]}")
        choice_approved = False
        while not choice_approved:
            choice = input("Do you want to approve this request? (Y/N): ").strip().lower()
            if choice == 'y':
                c.execute("INSERT INTO Enrollment(StudentID, ClassID) VALUES(?, ?);", (request[1], request[2]))
                c.execute("UPDATE EnrollmentRequests SET Status='Approved' WHERE RequestID=?;", (request[0],))
                print(f"Request ID {request[0]} approved successfully!")
                connection.commit()
                choice_approved = True
            elif choice == 'n':
                print(f"Request ID {request[0]} not approved.")
                c.execute("UPDATE EnrollmentRequests SET Status='Denied' WHERE RequestID=?;", (request[0],))
                connection.commit()
                choice_approved = True
            else:
                print("Invalid choice. Please enter 'Y' or 'N'.")
    
    connection.commit()
    print("Enrollment request approved successfully!")
    return True
    

def add_busy_time():
    global current_user_token
    if session.is_logged_in() is False:
        print("You must be logged in to add the times when you are busy.")
        return False
    
    if not session.require_role("student"):
        print("Entry denied! Only students can add their busy periods.")
        return False
    
    start_time = input("Enter the start time (HH:MM): ")
    start_time = datetime.strptime(start_time, "%H:%M").strftime("%H:%M")
    end_time = input("Enter the end time (HH:MM): ")
    end_time = datetime.strptime(end_time, "%H:%M").strftime("%H:%M")   
    student_id = get_student_id(session.get_user_id())

    c.execute("INSERT INTO StudentBusyTimes(StudentID, StartTime, EndTime) VALUES(?, ?, ?);", 
              (student_id, start_time, end_time))
    connection.commit()
    print("Student availability added successfully!")

def add_period():
    global current_user_token
    if session.is_logged_in() is False:
        print("You must be logged in to add a period.")
        return False
    
    if not session.require_role("teacher"):
        print("Entry denied! Only teachers can add periods.")
        return False
    
    start_time = input("Enter the start time (HH:MM): ")
    end_time = input("Enter the end time (HH:MM): ")
    class_id = int(input("Enter the class ID: "))
    teacher_id = get_teacher_id(session.get_user_id())
    
    c.execute("INSERT INTO Periods(StartTime, EndTime, ClassID, TeacherID) VALUES(?, ?, ?, ?);", 
              (start_time, end_time, class_id, teacher_id))
    connection.commit()
    print("Period added successfully!")

    c.execute("""
              SELECT StudentID FROM Students
                WHERE UserID IN (SELECT UserID FROM Users WHERE SchoolID = (SELECT SchoolID FROM Classes WHERE ClassID = ?));
                """, (class_id,))
    students = c.fetchall()
    for student in students:
        c.execute("INSERT INTO StudentBusyTimes(StudentID, StartTime, EndTime) VALUES(?, ?, ?);", 
                  (student[0], start_time, end_time))
    connection.commit()
    print("Busy times for students in the class have been updated successfully!")

    return True

def add_teacher_to_school():
    global current_user_token
    if session.is_logged_in() is False:
        print("You must be logged in to add a teacher to a school.")
        return
    
    if not session.require_role("teacher"):
        print("Entry denied! Only teachers can add teachers to schools.")
        return False
    
    if not c.execute("SELECT IsSchoolAdmin FROM Users WHERE UserID=?", (session.get_user_id(),)).fetchone()[0]:
        print("Entry denied! You must be a school admin to add teachers to your school.")
        return False
    
    teacher_email = input("Enter the email of the teacher you want to add: ")
    if c.execute("SELECT UserID FROM Users WHERE Email=?", (teacher_email,)).fetchone() is None:
        print("Teacher not found. Please check the email and try again.")
        return False
    
    teacher_id = c.execute("SELECT UserID FROM Users WHERE Email=?", (teacher_email,)).fetchone()[0]
    school_id = get_school_id(session.get_user_id())
    c.execute("UPDATE Users SET SchoolID = ? WHERE UserID = ?;", (school_id, c.execute("SELECT UserID FROM Users WHERE Email=?", (teacher_email,)).fetchone()[0]))

def request_to_join_school():
    global current_user_token
    if session.is_logged_in() is False:
        print("You must be logged in to request to join a school.")
        return False
    
    school_id_verified = False
    while not school_id_verified:
        try:
            school_id = int(input("Enter the school ID you want to join: "))
            if school_id <= 0:
                raise ValueError("School ID must be a positive integer.")
            if school_id is None:
                raise ValueError("School ID cannot be empty.")
            school_id_verified = True
        except ValueError:
            print("Invalid input. Please enter a valid school ID.")
    school_id = int(input("Enter the school ID you want to join: "))
    school_exists = c.execute("SELECT SchoolID FROM Schools WHERE SchoolID=?", (school_id,)).fetchone()
    if school_exists is None:
        print("School does not exist. Please check the school ID and try again.")
        return False
    c.execute("INSERT INTO SchoolJoinRequests(UserID, SchoolID) VALUES(?, ?);", 
          (session.get_user_id(), school_id))
    connection.commit()
    print("Request to join school submitted successfully!")

def approve_school_join_request():
    if current_user_token is None:
        print("You must be logged in to approve school join requests.")
        return
    if c.execute("SELECT isSchoolAdmin FROM Users WHERE UserID=?", (session.get_user_id(),)).fetchone()[0] is False:
        print("Entry denied! Only school admins can approve school join requests.")
        return False
    
    requests = c.execute("SELECT RequestID, UserID FROM SchoolJoinRequests WHERE Status='Pending' AND SchoolID=(SELECT SchoolID FROM Users WHERE UserID=?);", (session.get_user_id(),)).fetchall()
    if not requests:
        print("No school join requests to approve.")
        return False
    print("School Join Requests:")
    for request in requests:
        c.execute("SELECT FirstName, LastName, Email FROM Users WHERE UserID=?", (request[1],))
        user = c.fetchone()
        if user is None:
            print(f"Request ID: {request[0]} - User not found.")
            continue
        print(f"Request ID: {request[0]}, User: {user[0]} {user[1]} {user[2]}")
        choice_approved = False
        while not choice_approved:
            choice = input("Do you want to approve this request? (Y/N): ").strip().lower()
            if choice == 'y':
                c.execute("UPDATE SchoolJoinRequests SET Status='Approved' WHERE RequestID=?;", (request[0],))
                c.execute("UPDATE Users SET SchoolID=(SELECT SchoolID FROM SchoolJoinRequests WHERE RequestID=?) WHERE UserID=?;", (request[0], request[1]))
                connection.commit()
                print(f"Request ID {request[0]} approved successfully!")
                choice_approved = True
            elif choice == 'n':
                c.execute("UPDATE SchoolJoinRequests SET Status='Denied' WHERE RequestID=?;", (request[0],))
                connection.commit()
                print(f"Request ID {request[0]} not approved.")
                choice_approved = True
            else:
                print("Invalid choice. Please enter 'Y' or 'N'.")


def add_homework_task():
    global current_user_token
    if session.is_logged_in() is False:
        print("You must be logged in to add a homework task.")
        return
    
    if not session.require_role("teacher"):
        print("Entry denied! Only teachers can add homework tasks.")
        return False
    
    teacher_id = get_teacher_id(session.get_user_id())
    classes = c.execute("SELECT ClassID, LocalClassIdentifier FROM Classes WHERE SchoolID=(SELECT SchoolID FROM Users WHERE UserID=?)", (session.get_user_id(),)).fetchall()

    if not classes:
        print("You are not associated with any classes. Please create a class first.")
        return False
    
    print("Classes you are associated with:")
    for index, (class_id, local_class_identifier) in enumerate(classes, start=1):
        print(f"{index}. Class ID: {class_id}, Local Class Identifier: {local_class_identifier}")

    class_choice_verified = False
    while not class_choice_verified:
        class_choice = int(input("Select the class by number: ")) - 1
        if class_choice < 0 or class_choice >= len(classes):
            print("Invalid choice. Please try again.")
        else:
            class_choice_verified = True
    
    selected_class_id = classes[class_choice][0]

    title = input("Enter the homework task title: ")
    description = input("Enter the homework task description: ")

    while True:
        try:
            time_to_complete = int(input("Enter the estimated time to complete (in minutes): "))
            if time_to_complete <= 0:
                raise ValueError("Time must be a positive integer.")
            break
        except ValueError as e:
            print(f"Invalid input: {e}. Please enter a valid number.")
            continue

        

    due_date_verified = False

    while not due_date_verified:
        due_date_input = input("Enter the due date (DD-MM-YY): ")
        try:
            due_date = datetime.strptime(due_date_input, "%d-%m-%Y").date()
            if due_date < datetime.now().date():
                print("Due date cannot be in the past. Please enter a valid date.")
                continue
            due_date_verified = True
        except ValueError:
            print("Invalid date format. Please use DD-MM-YYYY format.")
            continue
    
    homework_type_choice_verified = False
    homework_types = ["Quiz", "Assignment", "Project", "Other"]
    
    while not homework_type_choice_verified:
        print("Select the type of homework task:")
        for index, homework_type in enumerate(homework_types, start=1):
            print(f"{index}. {homework_type}")
        
        try:
            homework_type_choice = int(input("Enter the number corresponding to the homework type: ")) - 1
            if homework_type_choice < 0 or homework_type_choice >= len(homework_types):
                raise ValueError("Invalid choice. Please select a valid option.")
            homework_type_choice = homework_types[homework_type_choice]
            homework_type_choice_verified = True
        except ValueError as e:
            print(f"Error: {e}. Please try again.")

    if homework_type_choice == "Quiz":
        assignment_id = input("Enter the Quiz ID (or leave blank to create a new quiz): ").strip()
        if assignment_id:
            try:
                assignment_id = int(assignment_id)
                c.execute("SELECT AssignmentID FROM QuizQuestionAssignmnts WHERE QuizID=?", (assignment_id,))
                if c.fetchone() is None:
                    print("Quiz ID does not exist. Creating a new quiz.")
                    assignment_id = None
            except ValueError:
                print("Invalid Quiz ID. Creating a new quiz.")
                assignment_id = None
        if not assignment_id:
            print("Create a new quiz first then come back to add the homework task.")
            return False
    
    c.execute("INSERT INTO HomeworkTasks(Title, Description, TimeToComplete, DueDate, HomeworkType, ClassID, TeacherID, AssignmentID) VALUES(?, ?, ?, ?, ?, ?, ?, ?);",
                  (title, description, time_to_complete, due_date, homework_type_choice, selected_class_id, teacher_id, assignment_id))


    connection.commit()
    return True 
    




def create_quiz_from_pool():
    global current_user_token
    if session.is_logged_in() is False:
        print("You must be logged in to create a quiz.")
        return
    if get_user_role(session.get_user_id()) != "teacher":
        print("Only teachers can create quizzes.")
        return
    
    teacher_id = get_teacher_id(session.get_user_id())
    school_id = get_school_id(session.get_user_id())

    # Select class
    classes = c.execute("""
        SELECT ClassID, LocalClassIdentifier
        FROM Classes
        WHERE SchoolID = ?
    """, (school_id,)).fetchall()
    
    if not classes:
        print("No classes found in your school.")
        return
    
    print("Select a class for the quiz:")
    for i, (class_id, name) in enumerate(classes, start=1):
        print(f"{i}. {name} (Class ID: {class_id})")
    choice = int(input("Enter number: ")) - 1
    class_id = classes[choice][0]
    
    quiz_title = input("Enter quiz title: ")
    c.execute("INSERT INTO Quizzes (Title, ClassID, TeacherID) VALUES (?, ?, ?)", (quiz_title, class_id, teacher_id))
    c.execute("""
    SELECT QuizID
    FROM Quizzes
    WHERE Title = ? AND ClassID = ? AND TeacherID = ?
    ORDER BY QuizID ASC
""", (quiz_title, class_id, teacher_id))
    quiz_id = c.fetchone()[-1]

    # Select topic
    topics = c.execute("SELECT TopicID, TopicName FROM QuestionTopics WHERE SchoolID=?", (school_id,)).fetchall()
    if not topics:
        print("No topics found for your school.")
        return
    print("Available Topics:")
    for tid, tname in topics:
        print(f"{tid}. {tname}")
    topic_id = int(input("Enter topic ID: "))

    # Select questions from topic
    questions = c.execute("""
        SELECT QuestionID, QuestionText, DifficultyLevel
        FROM QuizQuestions
        WHERE SchoolID=? AND TopicID=?
    """, (school_id, topic_id)).fetchall()
    if not questions:
        print("No questions found for that topic.")
        return
    for qid, text, diff in questions:
        print(f"QID {qid} [{diff}]: {text}")
    
    selected_ids = input("Enter question IDs to add (comma-separated): ").split(",")
    for qid in selected_ids:
        c.execute("INSERT INTO QuizQuestionAssignments (QuizID, QuestionID) VALUES (?, ?)", (quiz_id, int(qid)))
    
    connection.commit()

    print(f"✅ Quiz '{quiz_title}' created successfully with ID {quiz_id}")

def get_next_question(student_id, quiz_id):
    # Get last answered question
    last_result = c.execute("""
        SELECT sr.QuestionID, q.DifficultyLevel, q.CorrectAnswer, sr.AnswerGiven
        FROM StudentQuizResults sr
        JOIN QuizQuestions q ON sr.QuestionID = q.QuestionID
        WHERE sr.StudentID = ? AND sr.HomeworkID = ?
        ORDER BY sr.ResultID DESC LIMIT 1
    """, (student_id, quiz_id)).fetchone()
    
    if last_result is None:
        # Start with Medium difficulty
        return c.execute("""
            SELECT q.QuestionID, q.QuestionText, q.AnswerOptions
            FROM QuizQuestionAssignments qa
            JOIN QuizQuestions q ON qa.QuestionID = q.QuestionID
            WHERE qa.QuizID = ? AND q.DifficultyLevel = 'Medium'
            LIMIT 1
        """, (quiz_id,)).fetchone()
    
    last_qid, last_diff, correct_answer, answer_given = last_result
    was_correct = (correct_answer.strip().lower() == (answer_given or "").strip().lower())
    
    # Difficulty adjustment
    diff_levels = ["Easy", "Medium", "Hard"]
    idx = diff_levels.index(last_diff)
    if was_correct and idx < 2:
        next_diff = diff_levels[idx + 1]
    elif not was_correct and idx > 0:
        next_diff = diff_levels[idx - 1]
    else:
        next_diff = last_diff
    
    # Get next unused question of adjusted difficulty
    return c.execute("""
        SELECT q.QuestionID, q.QuestionText, q.AnswerOptions
        FROM QuizQuestionAssignments qa
        JOIN QuizQuestions q ON qa.QuestionID = q.QuestionID
        WHERE qa.QuizID = ?
          AND q.DifficultyLevel = ?
          AND q.QuestionID NOT IN (
              SELECT QuestionID
              FROM StudentQuizResults
              WHERE StudentID = ? AND HomeworkID = ?
          )
        LIMIT 1
    """, (quiz_id, next_diff, student_id, quiz_id)).fetchone()

def add_topic():
    if session.is_logged_in() is False:
        print("You must be logged in to add a topic.")
        return
    if not session.require_role("teacher"):
        print("Only teachers can add topics.")
        return

    school_id = get_school_id(session.get_user_id())
    topic_name = input("Enter topic name: ").strip()

    try:
        c.execute("""
            INSERT INTO QuestionTopics (SchoolID, TopicName)
            VALUES (?, ?)
        """, (school_id, topic_name))
        connection.commit()
        print(f"✅ Topic '{topic_name}' added to your school’s pool.")
    except sqlite3.IntegrityError:
        print(f"⚠️ Topic '{topic_name}' already exists in your school.")


def add_quiz_question():
    if session.is_logged_in() is False:
        print("You must be logged in to add a quiz question.")
        return
    if not session.require_role("teacher"):
        print("Only teachers can add quiz questions.")
        return

    school_id = get_school_id(session.get_user_id())

    # Select topic
    topics = c.execute("""
        SELECT TopicID, TopicName
        FROM QuestionTopics
        WHERE SchoolID = ?
    """, (school_id,)).fetchall()

    if not topics:
        print("⚠️ No topics available. Please add a topic first.")
        return

    print("\nAvailable Topics:")
    for tid, tname in topics:
        print(f"{tid}. {tname}")

    topic_id = int(input("Enter Topic ID: "))

    # Question details
    question_text = input("Enter the question text: ").strip()
    difficulty = input("Enter difficulty (Easy, Medium, Hard): ").capitalize()
    if difficulty not in ["Easy", "Medium", "Hard"]:
        print("❌ Invalid difficulty.")
        return

    options = []
    print("Enter 4 answer options:")
    for i in range(4):
        options.append(input(f"Option {i+1}: ").strip())

    correct_answer = input("Enter the correct answer exactly as written above: ").strip()

    # Store as JSON
    answer_options_json = json.dumps(options)

    c.execute("""
        INSERT INTO QuizQuestions (
            SchoolID, TopicID, QuestionText, DifficultyLevel, AnswerOptions, CorrectAnswer
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (school_id, topic_id, question_text, difficulty, answer_options_json, correct_answer))

    connection.commit()
    print("✅ Question added successfully to your school’s question pool.")

def bulk_upload_questions():
    if session.is_logged_in() is False:
        print("You must be logged in to upload questions.")
        return
    if not session.require_role("teacher"):
        print("Only teachers can upload questions.")
        return

    school_id = get_school_id(session.get_user_id())
    file_path = input("Enter path to your CSV or Excel file: ").strip()

    if not os.path.exists(file_path):
        print("❌ File not found.")
        return

    try:
        if file_path.lower().endswith(".csv"):
            df = pd.read_csv(file_path)
        elif file_path.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path)
        else:
            print("❌ Unsupported file format. Use CSV or Excel.")
            return
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    required_cols = ["TopicName", "Difficulty", "QuestionText",
                     "Option1", "Option2", "Option3", "Option4", "CorrectAnswer"]

    if not all(col in df.columns for col in required_cols):
        print(f"❌ Missing required columns. Must include: {', '.join(required_cols)}")
        return

    added_count = 0
    updated_count = 0

    for _, row in df.iterrows():
        topic_name = str(row["TopicName"]).strip()
        difficulty = str(row["Difficulty"]).capitalize()
        if difficulty not in ["Easy", "Medium", "Hard"]:
            print(f"⚠️ Skipping invalid difficulty '{difficulty}' for question: {row['QuestionText']}")
            continue

        # Ensure topic exists
        topic_row = c.execute("""
            SELECT TopicID FROM QuestionTopics
            WHERE SchoolID = ? AND TopicName = ?
        """, (school_id, topic_name)).fetchone()

        if topic_row:
            topic_id = topic_row[0]
        else:
            c.execute("""
                INSERT INTO QuestionTopics (SchoolID, TopicName) VALUES (?, ?)
            """, (school_id, topic_name))
            topic_id = c.lastrowid

        options = [str(row[f"Option{i}"]).strip() for i in range(1, 5)]
        correct_answer = str(row["CorrectAnswer"]).strip()

        # Check if question already exists
        existing_question = c.execute("""
            SELECT QuestionID FROM QuizQuestions
            WHERE SchoolID = ? AND TopicID = ? AND QuestionText = ?
        """, (school_id, topic_id, row["QuestionText"])).fetchone()

        if existing_question:
            # Update existing question
            c.execute("""
                UPDATE QuizQuestions
                SET DifficultyLevel = ?, AnswerOptions = ?, CorrectAnswer = ?
                WHERE QuestionID = ?
            """, (difficulty, json.dumps(options), correct_answer, existing_question[0]))
            updated_count += 1
        else:
            # Insert new question
            c.execute("""
                INSERT INTO QuizQuestions (
                    SchoolID, TopicID, QuestionText, DifficultyLevel, AnswerOptions, CorrectAnswer
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (school_id, topic_id, row["QuestionText"], difficulty, json.dumps(options), correct_answer))
            added_count += 1

    connection.commit()
    print(f"✅ Bulk upload complete — Added: {added_count}, Updated: {updated_count}")

def generate_question_template():
    import pandas as pd

    template_data = {
        "TopicName": ["Example: Algebra"],
        "Difficulty": ["Easy"],  # Options: Easy, Medium, Hard
        "QuestionText": ["Example: What is 2+2?"],
        "Option1": ["3"],
        "Option2": ["4"],
        "Option3": ["5"],
        "Option4": ["6"],
        "CorrectAnswer": ["4"]
    }

    df = pd.DataFrame(template_data)

    # Ask teacher for file format
    file_type = input("Save as CSV or Excel? (csv/xlsx): ").strip().lower()
    file_name = input("Enter file name (without extension): ").strip()

    if file_type == "csv":
        file_path = f"{file_name}.csv"
        df.to_csv(file_path, index=False)
    elif file_type == "xlsx":
        file_path = f"{file_name}.xlsx"
        df.to_excel(file_path, index=False)
    else:
        print("❌ Invalid file type. Please choose 'csv' or 'xlsx'.")
        return

    print(f"✅ Template saved as {file_path}. Fill it out and use Bulk Upload Questions.")

from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation

def generate_upload_template():
    global current_user_token
    if session.is_logged_in() is False:
        print("❌ You must be logged in to generate the template.")
        return

    role = session.role.lower()
    if role != "teacher":
        print("❌ Only teachers can generate the upload template.")
        return

    school_id = get_school_id(session.get_user_id())

    # Get topic names for dropdown
    topic_rows = c.execute("SELECT TopicName FROM QuestionTopics WHERE SchoolID=?", (school_id,)).fetchall()
    topics = [row[0] for row in topic_rows]

    wb = Workbook()
    ws = wb.active
    ws.title = "Upload Template"

    headers = ["TopicName", "Difficulty", "QuestionText",
               "Option1", "Option2", "Option3", "Option4", "CorrectAnswer"]
    ws.append(headers)

    # Dropdown for TopicName
    if topics:
        dv_topics = DataValidation(type="list", formula1=f'"{",".join(topics)}"', allow_blank=False)
        ws.add_data_validation(dv_topics)
        dv_topics.add("A2:A1048576")  # entire TopicName column

    # Dropdown for Difficulty
    difficulties = ["Easy", "Medium", "Hard"]
    dv_diff = DataValidation(type="list", formula1=f'"{",".join(difficulties)}"', allow_blank=False)
    ws.add_data_validation(dv_diff)
    dv_diff.add("B2:B1048576")

    filename = f"upload_template_school_{school_id}.xlsx"
    wb.save(filename)
    print(f"✅ Upload template generated: {filename}")


def logout():
    global current_user_token
    if session.is_logged_in() is False:
        print("You are not logged in.")
        log_in()
        return
    print("Logging out...")
    current_user_token = None
    session.logout()
    print("You have been logged out successfully.")
    log_in()  # Redirect to login after logout

def student_options():
    actions = {
        "1": request_to_join_class,
        "2": add_busy_time,
        "3": request_to_join_school,
        "4": logout
    }
    while current_user_token:
        print("\n📘 Student Menu:")
        print("1. Request to join a class")
        print("2. Add busy time")
        print("3. Request to join a school")
        print("4. Log out")
        action = input("Choose an option: ")
        if action in actions:
            actions[action]()
        else:
            print("❌ Invalid option.")

def teacher_options():
    actions = {
        "1": add_school,
        "2": add_class,
        "3": add_teacher_to_class,
        "4": add_student_to_class,
        "5": approve_enrollment_request,
        "6": add_period,
        "7": add_teacher_to_school,
        "8": approve_school_join_request,
        "9": request_to_join_school,
        "10": add_homework_task,
        "11": create_quiz_from_pool,
        "12": add_topic,
        "13": add_quiz_question,
        "14": bulk_upload_questions,  # NEW
        "15": logout
    }
    while current_user_token:
        print("\n📗 Teacher Menu:")
        for k, v in actions.items():
            label = v.__name__.replace("_", " ").title()
            print(f"{k}. {label}")
        action = input("Choose an option: ")
        if action in actions:
            actions[action]()
        else:
            print("❌ Invalid option.")



