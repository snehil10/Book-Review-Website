import os
import requests

from flask import Flask, render_template, request, session, redirect, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)
key = "tiTGj08PsB3Vv8iw1yTUDQ"

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():
    if "email" in session:
        return redirect(url_for("search"))
    return render_template("index.html")

@app.route("/register")
def register():
    if "email" in session:
        return redirect(url_for("search"))
    return render_template("register.html")

@app.route("/login")
def login():
    if "email" in session:
        return redirect(url_for("search"))
    return render_template("login.html")

@app.route("/search")
def search():
    if "email" not in session:
        return redirect(url_for("index"))
    return render_template("search.html", fname = session["fname"])

@app.route("/bookDetails")
def bookDetails():
    if "email" not in session:
        return redirect(url_for("index"))
    return render_template("bookDetails.html", fname = session["fname"])

@app.route("/error")
def error():
    return render_template("error.html", error = request.args.get("someError"))


# function to search for books
@app.route("/searchBooks", methods=["POST"])
def searchBooks():
    if "email" not in session:
        return redirect(url_for("index"))
    searchText = "%" + request.form.get("searchText") + "%"
    radio = request.form.get("selector")
    books = []
    num = []
    if radio == "isbn":
        books = db.execute("SELECT * FROM books WHERE LOWER(books.isbn) LIKE :searchText",
        {"searchText": searchText})
    elif radio == "title":
        books = db.execute("SELECT * FROM books WHERE LOWER(books.title) LIKE :searchText",
        {"searchText": searchText})
    else:
        books = db.execute("SELECT * FROM books WHERE LOWER(books.author) LIKE :searchText",
        {"searchText": searchText})
    num = list(range(1, books.rowcount+1))
    lenArr = len(num)
    return render_template("/search.html", fname = session["fname"], books = zip(books, num),
    lenArr = lenArr, searchText = searchText[1:-1], radio = radio)


# function to register new user in our website
@app.route("/registerUser", methods=["POST"])
def registerUser():
    if "email" in session:
        return redirect(url_for(search))

    fname = request.form.get("fname")
    lname = request.form.get("lname")
    email = request.form.get("email")
    pwd = request.form.get("pwd")
    cnfpwd = request.form.get("cnfpwd")

    if pwd == cnfpwd and db.execute("SELECT * FROM users WHERE email = :email", {"email": email}).rowcount == 0:
        db.execute("INSERT INTO users (fname, lname, email, password) VALUES (:fname, :lname, :email, :pwd)",
        {"fname": fname, "lname": lname, "email": email, "pwd": pwd});
    elif pwd != cnfpwd:
        return redirect(url_for("error", someError="Passwords do not match"))
    else:
        return redirect(url_for("error", someError="Email Id already registered"))
    db.commit()

    user = db.execute("SELECT * FROM users WHERE email = :email", {"email": email}).fetchone()
    if user != None:
        session["id"] = user.id
        session["email"] = email
        session["fname"] = fname
        return render_template("search.html", fname = session["fname"])
    else:
        redirect(url_for("error", someError="Something wrong in db"))



@app.route("/validateUser", methods=["POST"])
def validateUser():
    email = request.form.get("email")
    pwd = request.form.get("pwd")

    user = db.execute("SELECT id, fname, password FROM users WHERE email = :email", {"email": email}).fetchone();
    if user != None and user.password == pwd:
        session["id"] = user.id
        session["email"] = email
        session["fname"] = user.fname
        return redirect(url_for("search"))
    else:
        return render_template("index.html", loginError="Incorrect Email/Password")

def getReview(isbn):
    user_id = session["id"]

    reviews = db.execute("SELECT review, rating from reviews WHERE user_id = :user_id and isbn = :isbn",
    {"user_id": session["id"], "isbn": isbn}).fetchone()

    return reviews

def getGoodreadsData(isbns):
    goodreads = requests.get("https://www.goodreads.com/book/review_counts.json",
    params = {"key": key, "isbns": isbns})
    if goodreads.status_code == 200:
        goodreads = goodreads.json()

    return goodreads

# function used to render book on bookDetails page after the user click view book in search page
@app.route("/renderBook/<string:isbn>/<int:editable>", methods=["GET"])
def renderBook(isbn, editable):
    reviews = getReview(isbn)
    isbns = convertToISBNS(isbn)
    goodreads = getGoodreadsData(isbns)

    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    return render_template("bookDetails.html", book = book, goodreads = goodreads, reviews = reviews, fname = session["fname"], editable = editable)

@app.route("/writeReview", methods=["POST"])
def writeReview():
    if "email" not in session:
        return redirect(url_for("index"))

    review = request.form.get("review")
    rating = request.form.get("rating")
    isbn = request.args.get("isbn")

    if db.execute("SELECT id from reviews WHERE user_id = :user_id and isbn = :isbn", {"user_id": session["id"], "isbn": isbn}).rowcount == 0:
        db.execute("INSERT INTO reviews (user_id, isbn, review, rating) VALUES(:user_id, :isbn, :review, :rating)",
        {"user_id": session["id"], "isbn": isbn, "review": review, "rating": rating})
    else:
        db.execute("UPDATE reviews SET review = :review, rating = :rating WHERE user_id = :user_id and isbn = :isbn",
        {"user_id": session["id"], "isbn": isbn, "review": review, "rating": rating})
    db.commit()

    return redirect(url_for("renderBook", isbn=isbn, editable = 0))

@app.route("/deleteReview", methods=["POST"])
def deleteReview():
    isbn = request.args.get("isbn")
    user_id = session["id"]

    if db.execute("SELECT id from reviews WHERE user_id = :user_id and isbn = :isbn", {"user_id": session["id"], "isbn": isbn}).rowcount == 1:
        db.execute("DELETE FROM reviews WHERE user_id = :user_id and isbn = :isbn", {"user_id": user_id, "isbn": isbn})
    db.commit()
    return redirect(url_for("renderBook", isbn = isbn, editable = 0))

@app.route("/editReview", methods=["POST"])
def editReview():
    isbn = request.args.get("isbn")
    return redirect(url_for("renderBook", isbn = isbn, editable = 1))


# route for when logout is clicked
@app.route("/logout", methods=["GET"])
def logout():
    if "email" in session:
        session.pop("id", None)
        session.pop("fname", None)
        session.pop("email", None)
    return redirect(url_for("index"))


# function to convert isbn10 to isbn13
def convertToISBNS(isbn):
     sum = 0
     isbns = "978" + isbn[0:-1]
     for i in range(0, len(isbns)):
         dig = int(isbns[i])
         if i%2 == 1:
             sum += dig * 3
         else:
             sum += dig
     sum = (10 - (sum % 10)) % 10
     isbns += str(sum)
     return isbns
