import psycopg2

import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, creditCardChecker, creditCardCheckerRM

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL(os.environ.get("DATABASE_URL") or "sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    rows = db.execute("SELECT * FROM users")
    if len(rows) == 0:

        return redirect("/login")
    else:
        owned = db.execute("SELECT * FROM purchases WHERE user_id= ?", session["user_id"])

        totalCash=0

        for owns in owned:
            symbol = owns["symbol"]
            name = owns["name"]
            shares = owns["shares"]
            priceGet = lookup(symbol)
            price1 = priceGet["price"]
            owns["price"] = price1
            price = round(owns["price"],2)
            totalCash+=shares * price

        cash = db.execute("SELECT cash FROM users WHERE id=?", session["user_id"])

        cash1 = round(cash[0]["cash"],2)

        total1 = round(cash[0]["cash"] + totalCash,2)

        return render_template("index.html", owned=owned, cash1=cash1, total1=total1)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method =="POST":

        if not request.form.get("symbol"):
            return apology("please fill out symbol field")

        if not request.form.get("shares"):
            return apology("please fill out share field")

        Bsymbol = lookup(request.form.get("symbol"))

        if not Bsymbol:
            return apology("Stock does not exist")

        if int(request.form.get("shares")) < 1:
            return apology("share is no valid")


        stockPrice = float(Bsymbol["price"])

        symbol = Bsymbol["symbol"]

        name = Bsymbol["name"]

        share = int(request.form.get("shares"))

        balance = db.execute("SELECT cash FROM users WHERE id = ?",session["user_id"])

        cash = balance[0]["cash"]

        if isinstance(share,float) == True:
            return apology("float number")

        if (cash - (stockPrice * share)) < 1.00:
            return apology("balance not sufficient")

        pCheck = db.execute("SELECT symbol, shares FROM purchases WHERE user_id = ?", session["user_id"])

        for row in pCheck:
            if row["symbol"] == symbol:
                newShare = (row["shares"]) + share
                db.execute("UPDATE purchases SET shares = ? WHERE user_id = ? AND symbol = ?", newShare, session["user_id"], symbol )

                newBalance1 = cash - (share * stockPrice)

                db.execute("UPDATE users SET cash = ? WHERE id = ?", round(newBalance1,2), session["user_id"])

                db.execute("INSERT INTO history (user_id, symbol, shares, price) VALUES(?, ?, ?, ?)", session["user_id"] , symbol, share, stockPrice)
                return redirect("/")

        total = stockPrice * share

        db.execute("INSERT INTO purchases (user_id, symbol, shares, price, name) VALUES(?, ?, ?, ?, ?)", session["user_id"] , symbol, share, stockPrice, name)

        db.execute("INSERT INTO history (user_id, symbol, shares, price) VALUES(?, ?, ?, ?)", session["user_id"] , symbol, share, stockPrice)

        newBalance = cash - (stockPrice * share)

        db.execute("UPDATE users SET cash = ? WHERE id = ?", round(newBalance,2), session["user_id"])

        return redirect("/")


    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():

    rows = db.execute("SELECT * FROM users")
    if len(rows) == 0:

        return redirect("/login")

    else:

        Thistory = db.execute("SELECT * FROM history WHERE user_id = ? ORDER BY timestamp DESC", session["user_id"])

        for logs in Thistory:
            symbol = logs["symbol"]
            shares = logs["shares"]
            price = logs["price"]
            timestamp = logs["timestamp"]

        return render_template("history.html",Thistory=Thistory)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method =="POST":

        if not request.form.get("symbol"):
            return apology("Please fill out Symbol field")

        Qsymbol = lookup(request.form.get("symbol"))

        if not Qsymbol:
            return apology("Stock does not exist")

        return render_template("quoted.html", name=Qsymbol["name"] , symbol=Qsymbol["symbol"], price=Qsymbol["price"])

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        if not request.form.get("username"):
            return apology("must input a username", 400)

        # Ensure password was submitted
        elif not request.form.get("confirmation") or not request.form.get("password"):
            return apology("must input a password", 400)

        if request.form.get("confirmation") != request.form.get("password"):
            return apology("passwords do not match", 400)

        users = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        if len(users) >= 1:
            return apology("User already exists")

        username = request.form.get("username")

        passHash = generate_password_hash(request.form.get("confirmation"))

        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, passHash)

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        session["user_id"] = rows[0]["id"]

        return redirect("/")



    else:
        return render_template("registration.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method =="POST":

        if not request.form.get("symbol"):
            return apology("please fill out symbol field")

        if not request.form.get("shares"):
            return apology("please fill out share field")

        if request.form.get("symbol") == "disabled":
            return apology("Please select valid stock")

        owned = db.execute("SELECT * FROM purchases WHERE user_id= ? AND symbol = ?", session["user_id"], request.form.get("symbol") )

        shares = int(request.form.get("shares"))

        newShares = (int(owned[0]["shares"]) - shares)

        symbol = request.form.get("symbol")

        Ssymbol = lookup(request.form.get("symbol"))

        stockPrice = Ssymbol["price"]

        balance = db.execute("SELECT cash FROM users WHERE id = ?",session["user_id"])

        newBalance = balance[0]["cash"] + (shares * stockPrice)

        if newShares < 0:
            return apology("not enough shares to sell")

        elif newShares == 0:
            db.execute("DELETE FROM purchases WHERE symbol = ? AND user_id = ?", request.form.get("symbol"), session["user_id"])
        else:
            db.execute("UPDATE purchases SET shares = ? WHERE user_id = ? AND symbol = ?", newShares, session["user_id"],request.form.get("symbol") )

        db.execute("INSERT INTO history (user_id, symbol, shares, price) VALUES(?, ?, ?, ?)", session["user_id"] , symbol, (-shares), stockPrice)

        db.execute("UPDATE users SET cash = ? WHERE id = ?", newBalance, session["user_id"])

        return redirect("/")
    else:

        owned = db.execute("SELECT * FROM purchases WHERE user_id= ?", session["user_id"])

        for owns in owned:
            symbol = owns["symbol"]
            name = owns["name"]


        return render_template("sell.html", owned=owned)

@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    if request.method =="POST":

        if not request.form.get("creditNumber"):
            return apology("Please fill out all fields")
        if not request.form.get("month"):
            return apology("Please fill out all fields")
        if not request.form.get("year"):
            return apology("Please fill out all fields")
        if not request.form.get("amount"):
            return apology("Please fill out all fields")

        if not request.form.get("creditNumber").isnumeric():
            return apology("Invalid Keys")

        creditCardNum = int(request.form.get("creditNumber"))

        month = int(request.form.get("month"))

        year = int(request.form.get("year"))

        amount = float(request.form.get("amount"))

        if month < 1 & month > 12 or year < 23 & year > 99:
            return apoloy("Invalid Expiry Date")

        if amount < 1:
            return apology("Invalid Amount of Funds Requested")


        checkSum=creditCardChecker(creditCardNum)+creditCardCheckerRM(creditCardNum)

        if (creditCardNum > 3999999999999999 and creditCardNum < 4999999999999999) or (creditCardNum > 3999999999999 and creditCardNum < 4999999999999):
            if checkSum % 10 == 0:
                updateBalance(amount)
        elif creditCardNum > 5099999999999999 and creditCardNum < 5600000000000000:
            if checkSum % 10 == 0:
                updateBalance(amount)
        elif (creditCardNum > 339999999999999 and creditCardNum < 350000000000000) or (creditCardNum > 369999999999999 and creditCardNum <380000000000000):
            if checkSum % 10 == 0:
                updateBalance(amount)
        else:
            return apology("Invalid Card")

        return redirect("/")
    else:

        return render_template("deposit.html")

def updateBalance(amount):
    balance = db.execute("SELECT cash FROM users WHERE id = ?",session["user_id"])
    cash = balance[0]["cash"]
    newBalance = cash + amount
    db.execute("UPDATE users SET cash = ? WHERE id = ?", newBalance, session["user_id"])


if __name__=="__main__":
    port = int(os.environ.get("PORT",8080))
    app.run(hots="0.0.0.0", port=port)
