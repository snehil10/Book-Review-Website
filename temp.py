from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
	return render_template("index.html")

@app.route("/register")
def register():
	return render_template("register.html")

@app.route("/login")
def login():
	return render_template("login.html")

@app.route("/search")
def search():
	return render_template("search.html")

@app.route("/bookDetails")
def bookDetails():
	return render_template("bookDetails.html")
