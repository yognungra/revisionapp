from databasee import c, connection
from session import session
from databasee import get_school_id, get_teacher_id, get_student_id
from datetime import datetime


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
        c.execute("SELECT LocalClassIdentifier FROM Classes WHERE LocalClassIdentifier=? AND SchoolId=?", (local_class_identifier, get_school_id(session.get_user_id())))
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
    
    verified = False
    while not verified:
        try:
            class_id = int(input("Enter the class ID: "))
            if class_id <= 0:
                raise ValueError("Class ID must be a positive integer.")
            if class_id is None:
                raise ValueError("Class ID cannot be empty.")
            verified = True
        except ValueError:
            print("Invalid input. Please enter a valid class ID.")
    class_id = int(input("Enter the class ID: "))

    verified = False
    while not verified:
        try:
            teacher_id = int(input("Enter the teacher ID (or leave blank to select yourself): ") or get_teacher_id(session.get_user_id()))
            if teacher_id <= 0:
                raise ValueError("Teacher ID must be a positive integer.")
            if teacher_id is None:
                raise ValueError("Teacher ID cannot be empty.")
            verified = True
        except ValueError:
            print("Invalid input. Please enter a valid teacher ID.")

    c.execute("SELECT ClassID FROM Classes WHERE ClassID=?", (class_id,))
    if c.fetchone() is None:
        print("Class does not exist. Please check the class ID and try again.")
        return False

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
              SELECT StudentID FROM Enrollment
                WHERE ClassID=?;
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
            print("Invalid input. Please enter a valid school ID.")#
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