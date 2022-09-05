import os
import requests
import urllib.parse
import math


from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = os.environ.get("API_KEY")
        url = f"https://cloud.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}"
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


def creditCardChecker(creditCardNum):
    bucket1=0
    bucket2=0
    for i in range(1,17,2):
        a=int(creditCardNum)/(10**i)
        b=a%10
        c=math.floor(b)*2
        if c > 9:
            d=c%10
            e=math.floor(c/10)
            bucket2=bucket2+d+e
            c=0
        bucket1=bucket1+c

    bigBucket1=bucket1+bucket2

    return bigBucket1
# this function checks every other digit from the last number, and just adds them together
# to put them in a bucket

def creditCardCheckerRM(creditCardNum):
    bucket3=0
    for i in range(0,17,2):
        f=int(creditCardNum)/(10**(i))
        g=f%10
        h=math.floor(g)
        bucket3=bucket3+h
    return bucket3



