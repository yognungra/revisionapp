from datetime import datetime

import sqlite3
from session import session

global current_user_token
current_user_token = None


# Connect to the SQLite database
connection = sqlite3.connect("tables.db")
c = connection.cursor()
c.execute("PRAGMA foreign_keys = ON;")
connection.commit()


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
        FOREIGN KEY (SchoolID) REFERENCES Schools(SchoolID) ON DELETE CASCADE ON UPDATE CASCADE,
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