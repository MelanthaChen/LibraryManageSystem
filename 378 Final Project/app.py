from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, abort
from datetime import datetime, timedelta
import json
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)


# Database connection
DATABASE = 'library.db'

# Function to check user role
def get_user_role(name, user_id):
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    # Check if user is a student
    cur.execute('SELECT * FROM Users WHERE Name = ? AND User_ID = ?', (name, user_id))
    check = cur.fetchone()
    if check:
        return ['user', check[2]]
    # Check if user is a librarian
    cur.execute('SELECT * FROM Librarians WHERE Name = ? AND Librarian_ID = ?', (name, user_id))
    if cur.fetchone():
        return ['librarian']
    # Check if user is a manager
    cur.execute('SELECT * FROM Managers WHERE Name = ? AND Manager_ID = ?', (name, user_id))
    check = cur.fetchone()
    if check:
        return ['manager']
    conn.close()
    return ['unknown']

@app.route('/')
def main_page():
    return render_template('main_page.html')  # You need to create this template

@app.route('/login', methods=['POST'])
def login():
    name = request.form['name']
    id = request.form['id']
    print("Login Attempt:", name, id)  # Check the terminal for this output after login attempt

    ret = get_user_role(name,id)
    role = ret[0]
    print("Determined Role:", role)  # This should show what role has been determined

    if role == 'user':
        print("Redirecting to user page.")
        session['name'] = name
        session['id'] = id
        # if ret[1] == "Faculty":
        #     session['name'] = "Prof. " + name
        return redirect(url_for('user_page'))
    elif role == 'librarian':
        print("Redirecting to librarian page.")
        session['name'] = name
        session['id'] = id
        return redirect(url_for('librarian_page'))
    elif role == 'manager':
        print("Redirecting to manager page.")
        session['name'] = name
        session['id'] = id
        return redirect(url_for('manager_page'))
    else:
        print("User not found!")
        return render_template('main_page.html', error="User not found!")
    
# View functions for each role

@app.route('/user')
def user_page():
    user_name = session.get('name', 'Default Name')
    user_id = session.get('id', 'Default ID')
    return render_template('user_page.html', name=user_name, id=user_id)

@app.route('/librarian')
def librarian_page():
    librarian_name = session.get('name', 'Default Name')
    librarian_id = session.get('id', 'Default ID')
    return render_template('librarian_page.html', name=librarian_name, id=librarian_id)

@app.route('/manager')
def manager_page():
    manager_name = session.get('name', 'Default Name')
    manager_id = session.get('id', 'Default ID')
    return render_template('manager_page.html', name=manager_name, id=manager_id)

@app.route('/add_book', methods=['POST'])
def add_book():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    title = request.form['title']
    author = request.form['author']
    category = request.form['category']
    isbn = request.form['isbn']
    year = request.form['year']

    # Adding a book
    cur.execute('INSERT INTO Books (Title, Authors, ISBN, PublicationYear, Category, Availability) VALUES  (?, ?, ?, ?, ?, ?)', (title, author, isbn, year, category, 'Yes'))
    conn.commit()
    return redirect_to_previous()


@app.route('/search_books', methods = ['GET'])
def search():
    query = request.args.get("query")
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute('SELECT * FROM Books WHERE Title LIKE ? OR Authors LIKE ? OR Category LIKE ? ', (f"%{query}%", f"%{query}%", f"%{query}%"))
    results = cur.fetchall()
    conn.close
    return render_template('search_results.html', results=results)





#Routes to the different pages
# @app.route('/update_book')
# def redirect_update():
#     return render_template('update.html')


@app.route('/sign_out')
def sign_out():
    return render_template('main_page.html')


@app.route('/requests')
def requests():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute('SELECT * FROM Requests')
    results = cur.fetchall()
    conn.close()
    return render_template('requests.html', results=results)





@app.route('/availabilityType', methods=['GET'])
def report_book_availability():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    choice = request.args.get('output')
    if choice == 'Yes' or choice == 'No':
     cur.execute('SELECT * FROM Books WHERE Availability = ?', (choice,))
    else:
     cur.execute('SELECT * FROM Books')
    results = cur.fetchall()
    conn.close
    return render_template('availability.html', results=results)


@app.route('/TransactionType', methods=['GET'])
def report_requests():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    choice = request.args.get('output')
    user_id = session.get('id')
    if choice == 'pending':
     cur.execute('SELECT * FROM Transactions WHERE User_ID = ? AND (Returned_Date = "" OR Returned_Date IS NULL)', (user_id))
    elif choice == 'completed':
     cur.execute('SELECT * FROM Transactions WHERE User_ID = ? AND Returned_Date IS TRUE', (user_id))
    else:
        cur.execute('SELECT * FROM Transactions WHERE User_ID = ?', (user_id))
    results = cur.fetchall()
    conn.close
    return render_template('borrowhistory.html', results=results)



@app.route('/borrowTrends', methods = ['GET'])
def report_book_trend():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute('SELECT Transactions.Book_ID, Books.Title, COUNT(Transactions.Book_ID) AS Count FROM Transactions INNER JOIN Books ON Books.BookID = Transactions.Book_ID GROUP BY Transactions.Book_ID ORDER BY Count DESC LIMIT 10')
    results = cur.fetchall()
    return render_template('borrowTrends.html', results = results)

@app.route('/overdue', methods = ['GET'])
def report_overdue():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    today = datetime.now()
    cur.execute('SELECT * FROM Transactions WHERE (Returned_Date IS NULL OR Returned_Date ="") AND Borrowed_Date < ?', (today - timedelta(days=30),)) 
    results = cur.fetchall()
    return render_template('overdue.html', results=results)

@app.route('/update_book', methods = ['POST'])
def update_book():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    bookid = request.form.get('BookID')
    fields = {}
    for field in ('Title', 'Authors', 'Category', 'ISBN', 'PublicationYear', 'Availability'):
        value = request.form.get(field)
        if value != "":
            fields[field] = value

    command = 'UPDATE Books SET '
    update_fields = []
    update_values = []
    for field, value in fields.items():
        update_fields.append(f'{field} = ?')
        update_values.append(value)
    command += ', '.join(update_fields) + ' WHERE BookID = ?'
    update_values.append(bookid)

    cur.execute(command, update_values)
    conn.commit()
    conn.close()
    return redirect_to_previous()

@app.route('/borrowHistory', methods = ['GET'])
def borrow_History():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    user_id = session.get('id')
    cur.execute('SELECT * FROM Transactions WHERE User_ID = ?', (user_id,))
    results = cur.fetchall()
    conn.close()
    return render_template('borrowhistory.html', results=results)

@app.route('/availability', methods = ['GET'])
def availability():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute('SELECT * FROM Books')
    results = cur.fetchall()
    conn.close()
    return render_template('availability.html', results=results)


@app.route('/borrow', methods=['POST'])
def borrow():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    bookID = request.form.get('BookID')
    user_id = session.get('id')
    title = request.form.get('Title')
    cur.execute('INSERT INTO Requests (Book_ID, Book_Title, User_ID) VALUES (?,?,?)', (bookID,title,user_id))
    conn.commit()
    conn.close()
    return redirect_to_previous()

@app.route('/return', methods=['POST'])
def return_books():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    transaction_id = request.form.get('transaction_id')
    session_user_id = session.get('id') 
    cur.execute('UPDATE Transactions SET Returned_Date = ? WHERE Transaction_ID = ? AND User_ID = ?', (datetime.now().date(), transaction_id, session_user_id))
    cur.execute('SELECT Book_ID FROM Transactions WHERE Transaction_ID = ?', (transaction_id,))
    book_id = cur.fetchone()[0]
    cur.execute('UPDATE Books SET Availability = "Yes" WHERE BookID = ?', (book_id,))
    conn.commit()
    conn.close()
    return render_template('user_page.html')



@app.route('/register', methods = ['POST'])
def register_users():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    name = request.form.get("name")
    id = request.form.get("university_id")
    email = request.form.get("email")
    department = request.form.get("department")
    role = request.form.get("role")
    if role == "Student":
        cur.execute("INSERT INTO Users (Name, Role, User_ID )  VALUES(?,?, ?)", (name, role, id))
        cur.execute("INSERT INTO Students (Name, Email, Department, Student_ID) VALUES(?,?, ?, ?)", (name, email, department, id))
    elif role == "Faculty":
        cur.execute("INSERT INTO Users (Name, Role, User_ID) VALUES(?,?,?)", (name, role, id))
        cur.execute("INSERT INTO Faculty (Name, Email, Department,Faculty_ID ) VALUES(?,?, ?, ?)", (name, email, department, id))
    elif role == "Librarian":
        cur.execute("INSERT INTO Librarians (Name, Email, Librarian_ID) VALUES(?,?,?)", (name, email, id))
    elif role == "Manager":
        cur.execute("INSERT INTO Managers (Name, Email, Manager_ID) VALUES(?,?, ?)", (name, email, id))
    else:
        print("Not a valid role!")
        return render_template('manager_page.html',  error="Invalid Role! Must be Faculty, Librarian, Manager or Student ")
    conn.commit()
    conn.close()
    return manager_page()


@app.route('/decision', methods = ['POST'])
def approve_requests():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    librarian_id = session.get('id')
    result_json = request.form.get('result')
    results = json.loads(result_json)
    approved = results[0]
    denied = results[1]

    for req in denied:
        request_id, user_id, title, book_id = req
        cur.execute('DELETE FROM Requests WHERE Request_ID = ? AND Book_Title = ? AND User_ID = ? AND Book_ID = ?', (request_id, title, user_id, book_id))
    
    for req in approved:
        request_id, user_id, title, book_id = req
        cur.execute('INSERT INTO Transactions (Book_ID, Title, User_ID, Librarian_ID, Borrowed_Date) VALUES(?, ?, ?, ?, ?)', (book_id, title, user_id, librarian_id, datetime.now().date()) )
        cur.execute('DELETE FROM Requests WHERE Request_ID = ? AND Book_Title = ? AND User_ID = ? AND Book_ID = ?', (request_id, title, user_id, book_id))

    
    conn.commit()
    conn.close()
    return requests()
        

@app.route('/previous', methods=['GET'])
def redirect_to_previous():
    user_id = session.get('id')
    user_name = session.get('name')
    ret = get_user_role(user_name,user_id)
    role = ret[0]
    if role == 'user':
       return redirect(url_for('user_page'))
    elif role == 'librarian':
       return redirect(url_for('librarian_page'))
    elif role == 'manager':
        return redirect(url_for('manager_page'))

@app.route('/download_database')
def download_database():
    current_date = datetime.now().strftime('%Y%m%d') 
    directory = os.path.dirname(os.path.abspath(DATABASE)) 
    filename = os.path.basename(DATABASE)
    return send_from_directory(directory, filename, as_attachment=True, download_name=f"library_backup_{current_date}.db")

if __name__ == '__main__':
    app.run(debug=True)
