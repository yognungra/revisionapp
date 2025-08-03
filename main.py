import sqlite3
import hashlib
from argon2 import PasswordHasher
from datetime import datetime


ph = PasswordHasher()


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
            current_user_token = user_id
            print(f"✅ Login successful! User ID: {current_user_token}")
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
                 VALUES (?, ?, ?, ?, ?, ?)""", (first_name, last_name, email, hashed_password, user_role))
    connection.commit()
    
    user_id = c.execute("SELECT UserID FROM Users WHERE Email=?", (email,)).fetchone()[0]
    current_user_token = user_id

    if school_id:
        c.execute("INSERT INTO SchoolJoinRequests (UserID, SchoolID) VALUES (?, ?)", (current_user_token, school_id))
    connection.commit()

    if user_role == "student":
        year_group = int(input("Year Group: "))
        c.execute("INSERT INTO Students (YearGroup, UserID) VALUES (?, ?)", (year_group, user_id))
    else:
        c.execute("INSERT INTO Teachers (UserID) VALUES (?)", (user_id,))

    if school_id:
        c.execute("INSERT INTO SchoolJoinRequests (UserID, SchoolID) VALUES (?, ?)", (user_id, school_id))
    
    connection.commit()
    print("🎉 Registration complete!")
    return student_options() if user_role == "student" else teacher_options()

def add_school():
    global current_user_token
    if current_user_token is None:
        print("You must be logged in to add a school.")
        return False
    if get_user_role(current_user_token) != "teacher":
        print("Entry denied! Only teachers can add schools.")
        return False
    if c.execute("SELECT IsSchoolAdmin FROM Users WHERE UserID=?", (current_user_token,)).fetchone()[0]:
        print("Entry denied! You are already a school admin. Leave the school admin role to add a new school.")
        return False
    
    # Check if the user is a teacher and not already a school admin
    c.execute("UPDATE Users SET IsSchoolAdmin = TRUE WHERE UserID = ?", (current_user_token,))
    print("You are now a school admin.")

    school_name = input("Enter the school name: ")
    c.execute("INSERT INTO Schools(SchoolName) VALUES(?);", (school_name,))
    c.execute("UPDATE Users SET SchoolID = (SELECT SchoolID FROM Schools WHERE SchoolName = ?) WHERE UserID = ?;", 
              (school_name, current_user_token))
    connection.commit()
    print("School added successfully!")

def add_class():
    global current_user_token
    if current_user_token is None:
        print("You must be logged in to add a class.")
        return False
    
    if get_user_role(current_user_token) != "teacher":
        print("Entry denied! Only teachers can add classes.")
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
    school_id = get_school_id(current_user_token)
    c.execute("INSERT INTO Classes(LocalClassIdentifier, SchoolID) VALUES(?, ?);", 
              (local_class_identifier, school_id))
    connection.commit()
    print("Class added successfully!")

    return True

def add_teacher_to_class():
    global current_user_token
    if current_user_token is None:
        print("You must be logged in to add a teacher to a class.")
        return
    
    if get_user_role(current_user_token) != "teacher":
        print("Entry denied! Only teachers can add teachers to classes.")
        return False
    
    if not c.execute("SELECT IsSchoolAdmin FROM Users WHERE UserID=?", (current_user_token,)).fetchone()[0]:
        print("Entry denied! You must be a school admin to add teachers to your classes.")
        return False
    

    class_id = int(input("Enter the class ID: "))
    teacher_id = int(input("Enter the teacher ID (or leave blank to select yourself): ") or get_teacher_id(current_user_token))

    c.execute("SELECT SchoolID FROM Classes WHERE ClassID=?", (class_id,))
    school_id = c.fetchone()
    if c.execute("SELECT SchoolID FROM Users WHERE UserID=?", (teacher_id,)).fetchone()[0] != school_id[0]:
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
    if current_user_token is None:
        print("You must be logged in to add a student to a class.")
        return
    
    if get_user_role(current_user_token) != "teacher":
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
    if current_user_token is None:
        print("You must be logged in to request to join a class.")
        return
    
    if get_user_role(current_user_token) != "student":
        print("Entry denied! Only students can request to join classes.")
        return False
    
    class_id = int(input("Enter the class ID you want to join: "))

    class_exists = c.execute("SELECT ClassID FROM Classes WHERE ClassID=?", (class_id,)).fetchone()
    if class_exists is None:
        print("Class does not exist. Please check the class ID and try again.")
        return False
    

    student_id = get_student_id(current_user_token)
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
    if current_user_token is None:
        print("You must be logged in to approve enrollment requests.")
        return
    
    if get_user_role(current_user_token) != "teacher":
        print("Entry denied! Only teachers can approve enrollment requests.")
        return False
    
    list_requests = c.execute("SELECT RequestID, StudentID, ClassID FROM EnrollmentRequests WHERE ClassID IN (SELECT ClassID FROM ClassTeachers WHERE TeacherID=(SELECT TeacherID FROM Teachers WHERE UserID=?));", (current_user_token,)).fetchall()
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
    if current_user_token is None:
        print("You must be logged in to add the times when you are busy.")
        return False
    
    if get_user_role(current_user_token) != "student":
        print("Entry denied! Only students can add their busy periods.")
        return False
    
    start_time = input("Enter the start time (HH:MM): ")
    start_time = datetime.strptime(start_time, "%H:%M").strftime("%H:%M")
    end_time = input("Enter the end time (HH:MM): ")
    end_time = datetime.strptime(end_time, "%H:%M").strftime("%H:%M")   
    student_id = get_student_id(current_user_token)

    c.execute("INSERT INTO StudentBusyTimes(StudentID, StartTime, EndTime) VALUES(?, ?, ?);", 
              (student_id, start_time, end_time))
    connection.commit()
    print("Student availability added successfully!")

def add_period():
    global current_user_token
    if current_user_token is None:
        print("You must be logged in to add a period.")
        return False
    
    if get_user_role(current_user_token) != "teacher":
        print("Entry denied! Only teachers can add periods.")
        return False
    
    start_time = input("Enter the start time (HH:MM): ")
    end_time = input("Enter the end time (HH:MM): ")
    class_id = int(input("Enter the class ID: "))
    teacher_id = get_teacher_id(current_user_token)
    
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
    if current_user_token is None:
        print("You must be logged in to add a teacher to a school.")
        return
    
    if get_user_role(current_user_token) != "teacher":
        print("Entry denied! Only teachers can add teachers to schools.")
        return False
    
    if not c.execute("SELECT IsSchoolAdmin FROM Users WHERE UserID=?", (current_user_token,)).fetchone()[0]:
        print("Entry denied! You must be a school admin to add teachers to your school.")
        return False
    
    teacher_email = input("Enter the email of the teacher you want to add: ")
    if c.execute("SELECT UserID FROM Users WHERE Email=?", (teacher_email,)).fetchone() is None:
        print("Teacher not found. Please check the email and try again.")
        return False
    
    teacher_id = c.execute("SELECT UserID FROM Users WHERE Email=?", (teacher_email,)).fetchone()[0]
    school_id = get_school_id(current_user_token)
    c.execute("UPDATE Users SET SchoolID = ? WHERE UserID = ?;", (school_id, c.execute("SELECT UserID FROM Users WHERE Email=?", (teacher_email,)).fetchone()[0]))

def request_to_join_school():
    global current_user_token
    if current_user_token is None:
        print("You must be logged in to request to join a school.")
        return False
    
    school_id = int(input("Enter the school ID you want to join: "))
    school_exists = get_school_id(school_id)
    if school_exists is None:
        print("School does not exist. Please check the school ID and try again.")
        return False
    c.execute("INSERT INTO SchoolJoinRequests(UserID, SchoolID) VALUES(?, ?);", 
          (current_user_token, school_id))
    connection.commit()
    print("Request to join school submitted successfully!")

def approve_school_join_request():
    if current_user_token is None:
        print("You must be logged in to approve school join requests.")
        return
    if c.execute("SELECT isSchoolAdmin FROM Users WHERE UserID=?", (current_user_token,)).fetchone()[0] is False:
        print("Entry denied! Only school admins can approve school join requests.")
        return False
    
    requests = c.execute("SELECT RequestID, UserID FROM SchoolJoinRequests WHERE Status='Pending' AND SchoolID=(SELECT SchoolID FROM Users WHERE UserID=?);", (current_user_token,)).fetchall()
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

def logout():
    global current_user_token
    if current_user_token is None:
        print("You are not logged in.")
        log_in()
    print("Logging out...")
    current_user_token = None
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
        "10": logout
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

log_in()