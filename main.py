import sqlite3

connection = sqlite3.connect("Users.db")
c = connection.cursor()
print(c)

c.execute("""
    CREATE TABLE IF NOT EXISTS
Users (
        UserID INTEGER PRIMARY KEY NOT NULL,
        FirstName TEXT NOT NULL,
        LastName TEXT NOT NULL,
        Email TEXT NOT NULL,
        PasswordHarsh TEXT NOT NULL,
        UserRole TEXT NOT NULL,
        SchoolID INTEGER NOT NULL,
        DateCreated INTEGER NOT NULL
            )
          """)


def log_in():
    existing_user = input("Are you an existing user Y/N: ")
    if existing_user.lower() == "y":
        existing_user = True
    elif existing_user.lower() == "n":
        existing_user = False

    if existing_user:
        email = input("Email: ")
        password = input("Password: ")

    