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

# Create tables
c.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        UserID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        FirstName TEXT NOT NULL,
        LastName TEXT NOT NULL,
        Email TEXT NOT NULL,
        PasswordHash TEXT NOT NULL,
        UserRole TEXT NOT NULL,
        SchoolID INTEGER NOT NULL,
        DateCreated DATE DEFAULT current_date NOT NULL
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

connection.commit()

def log_in():
    global current_user_token
    print("Welcome to the Revision App!")
    valid_option = False
    while not valid_option:
        existing_user = input("Are you an existing user Y/N: ")
        if existing_user.lower() == "y" or existing_user.lower() == "yes":
            existing_user = True
            valid_option = True
        elif existing_user.lower() == "n" or existing_user.lower() == "no":
            existing_user = False
            valid_option = True
            sign_up()
        elif existing_user.lower() == "q" or existing_user.lower() == "quit":
            print("Exiting the application.")
            exit()
        else:
            print("Invalid Option! Try again.")

    if existing_user:
        verified = False

        while not verified:
            email = input("Email: ")
            databaseHash = c.execute("SELECT passwordHash FROM Users WHERE email=?", (email,))
            data = databaseHash.fetchone()

            if data is None:
                print("Email not found. Please try again.")
                continue

            password_checked = False
            while not password_checked:
                password = input("Password: ")
                try:
                    if ph.verify(data[0], password):
                        print("Login successful!")
                        password_checked = True
                        verified = True
                        c.execute("SELECT userID FROM Users WHERE email=?", (email,))  # Set the current user token
                        current_user_token = c.fetchone()[0]
                        print(f"Current User Token: {current_user_token}")

                        c.execute("SELECT UserRole FROM Users WHERE UserID=?", (current_user_token,))
                        user_role = c.fetchone()[0].lower()
                        if user_role == "student":
                            student_options()
                        elif user_role == "teacher":
                            teacher_options()
                        else:
                            print("Invalid User Role. Please try again..")
                except Exception:
                    print("Incorrect password. Please try again.")
    else:
        sign_up()


def sign_up():
    global current_user_token
    print("Please fill in the following details to sign up:")
    # Additional sign-up logic can be added here if needed
    first_name = input("First Name: ")
    last_name = input("Last Name: ")
    email = input("Email: ")

    # Check if email already exists
    while True:
        email_check = c.execute("SELECT Email FROM Users WHERE Email=?", (email,))
        if email_check.fetchone() is not None:
            print("Email already exists. Please try a different email.")
            email = input("Email: ")
        else:
            break

    password = input("Password: ")
    user_role_verified = False

    while not user_role_verified:
        user_role = input("User Role (Student/Teacher): ").strip().capitalize()
        if user_role.lower() in ["student", "teacher"]:
            user_role_verified = True
        else:
            print("Invalid role. Please enter 'Student' or 'Teacher'.")
    school_id = int(input("School ID (provided by your teacher): "))
    hashed_password = ph.hash(password)
    c.execute("INSERT INTO Users(FirstName, LastName, Email, PasswordHash, UserRole, SchoolID) VALUES(?, ?, ?, ?, ?, ?);", 
              (first_name, last_name, email, hashed_password, user_role, school_id))
    
    if user_role.lower() == "student":
        year_group = int(input("Year Group: "))
        c.execute("INSERT INTO Students(YearGroup, UserID) VALUES(?, (SELECT UserID FROM Users WHERE Email=?));", 
                  (year_group, email))
    elif user_role.lower() == "teacher":
        c.execute("INSERT INTO Teachers(UserID) VALUES((SELECT UserID FROM Users WHERE Email=?));", 
                  (email,))
        
    connection.commit()
    print("Registration successful!")

def add_school():
    global current_user_token
    school_name = input("Enter the school name: ")
    c.execute("INSERT INTO Schools(SchoolName) VALUES(?);", (school_name,))
    connection.commit()
    print("School added successfully!")

def add_class():
    global current_user_token
    if current_user_token is None:
        print("You must be logged in to add a class.")
        return False
    
    if c.execute("SELECT UserRole FROM Users WHERE UserID=?", (current_user_token,)).fetchone()[0].lower() != "teacher":
        print("Entry denied! Only teachers can add classes.")
        return False
    
    local_class_identifier = input("Enter the local class identifier: ")
    school_id = int(input("Enter the school ID: "))
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
    
    if c.execute("SELECT UserRole FROM Users WHERE UserID=?", (current_user_token,)).fetchone()[0].lower() != "teacher":
        print("Entry denied! Only teachers can add teachers to classes.")
        return False
    class_id = int(input("Enter the class ID: "))
    teacher_id = int(input("Enter the teacher ID (or leave blank to select yourself): ") or current_user_token)
    if teacher_id == current_user_token:
        c.execute("SELECT TeacherID FROM Teachers WHERE UserID=?", (current_user_token,))
        if c.fetchone() is None:
            print("You are not registered as a teacher. Please register first.")
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
    
    if c.execute("SELECT UserRole FROM Users WHERE UserID=?", (current_user_token,)).fetchone()[0].lower() != "teacher":
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
    
    if c.execute("SELECT UserRole FROM Users WHERE UserID=?", (current_user_token,)).fetchone()[0].lower() != "student":
        print("Entry denied! Only students can request to join classes.")
        return False
    
    class_id = int(input("Enter the class ID you want to join: "))

    class_exists = c.execute("SELECT ClassID FROM Classes WHERE ClassID=?", (class_id,)).fetchone()
    if class_exists is None:
        print("Class does not exist. Please check the class ID and try again.")
        return False
    

    student_id = c.execute("SELECT StudentID FROM Students WHERE UserID=?", (current_user_token,)).fetchone()[0]
    
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
    
    if c.execute("SELECT UserRole FROM Users WHERE UserID=?", (current_user_token,)).fetchone()[0].lower() != "teacher":
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
    
    if request is None:
        print("Request not found. Please check the request ID and try again.")
        return False
    
    student_id, class_id = request
    c.execute("INSERT INTO Enrollment(StudentID, ClassID) VALUES(?, ?);", (student_id, class_id))
    c.execute("DELETE FROM EnrollmentRequests WHERE RequestID=?;", (request_id,))
    
    connection.commit()
    print("Enrollment request approved successfully!")
    return True
    

def add_busy_time():
    global current_user_token
    if current_user_token is None:
        print("You must be logged in to add the times when you are busy.")
        return False
    
    if c.execute("SELECT UserRole FROM Users WHERE UserID=?", (current_user_token,)).fetchone()[0].lower() != "student":
        print("Entry denied! Only students can add their busy periods.")
        return False
    
    start_time = input("Enter the start time (HH:MM): ")
    start_time = datetime.strptime(start_time, "%H:%M").strftime("%H:%M")
    end_time = input("Enter the end time (HH:MM): ")
    end_time = datetime.strptime(end_time, "%H:%M").strftime("%H:%M")   
    student_id = c.execute("SELECT StudentID FROM Students WHERE UserID=?", (current_user_token,)).fetchone()[0]

    c.execute("INSERT INTO StudentBusyTimes(StudentID, StartTime, EndTime) VALUES(?, ?);", 
              (student_id, start_time, end_time))
    connection.commit()
    print("Student availability added successfully!")

def add_period():
    global current_user_token
    if current_user_token is None:
        print("You must be logged in to add a period.")
        return False
    
    if c.execute("SELECT UserRole FROM Users WHERE UserID=?", (current_user_token,)).fetchone()[0].lower() != "teacher":
        print("Entry denied! Only teachers can add periods.")
        return False
    
    start_time = input("Enter the start time (HH:MM): ")
    end_time = input("Enter the end time (HH:MM): ")
    class_id = int(input("Enter the class ID: "))
    teacher_id = c.execute("SELECT TeacherID FROM Teachers WHERE UserID=?", (current_user_token,)).fetchone()[0]
    
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

def student_options():
    global current_user_token
    choice_verified = False
    while not choice_verified:
        print("Welcome to the Student Portal!")
        print("1. Request to join a class")
        print("2. Add busy time")
        print("3. Log out")
        choice = input("Choose an option: ")
        if choice == "1":
            request_to_join_class()
            choice_verified = True
        elif choice == "2":
            add_busy_time()
            choice_verified = True
        elif choice == "3":
            global current_user_token
            current_user_token = None
            print("Logged out successfully.")
            choice_verified = True
        else:
            print("Invalid option. Please try again.")
    student_options() if current_user_token is not None else log_in()


def teacher_options():
    global current_user_token
    choice_verified = False
    while not choice_verified:
        print("1. Add a school")
        print("2. Add a class")
        print("3. Add a teacher to a class")
        print("4. Add a student to a class")
        print("5. Approve enrollment requests")
        print("6. Add a period")
        print("7. Log out")
        choice = input("Choose an option: ")
        if choice == "1":
            add_school()
        elif choice == "2":
            add_class()
        elif choice == "3":
            add_teacher_to_class()
        elif choice == "4":
            add_student_to_class()
        elif choice == "5":
            approve_enrollment_request()
        elif choice == "6":
            add_period()
        elif choice == "7":
            global current_user_token
            current_user_token = None
            print("Logged out successfully.")
        else:
            print("Invalid option. Please try again.")
    teacher_options() if current_user_token is not None else log_in()


log_in()