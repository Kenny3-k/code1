from flask import Flask, url_for, redirect, request, render_template, session, jsonify, flash
#from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

import sqlite3
import stripe
import os

from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from flask_mail import Mail, Message


HOTEL_PRICES ={
    "Standard":100,
    "Family":300,
    "Couple":150,
    "VIP":200,
}

ZOO_TICKET=25

app=Flask(__name__)
app.secret_key= '97z6noG71M658mOE0okhh8uG4a5L5krxHPZQckfIE-8'
stripe.api_key=os.getenv("STRIPE_SECRET_KEY")
YOUR_DOMAIN ="http://127.0.0.1:5000"

def get_db():
    return sqlite3.connect("rza2.db")

#create payment db+tables

def get_dbp():
    conn=sqlite3.connect("payments1.db")

    conn.row_factory=sqlite3.Row
    return conn

def init_db():
    db=get_dbp()
    db.execute(
        """CREATE TABLE IF NOT EXISTS payments1(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount INTEGER,
        status TEXT,
        stripe_id TEXT)"""
    )
    db.commit()
init_db()

@app.route("/")
def index():
    return render_template("index.html")

""" @app.route("/registration", methods=["GET", "POST"])
def registration():
    if request.method=="POST":
        hashed_pw= generate_password_hash(request.form["password"])
        db=get_db()
        db.execute(
            "INSERT INTO users (name, email, password) VALUES(?, ?, ?)", 
            (request.form["name"], request.form["email"], hashed_pw)
        )
        db.commit
        return redirect("/login")
    return render_template("registration.html") """

@app.route("/registration", methods=["GET","POST"])
def registration():
    if request.method=="POST":
        hashed_pw=generate_password_hash(request.form["password"])
        db=get_db()
        db.execute(
            "INSERT INTO users (name, email, password) VALUES(?,?,?)",
            (request.form["name"],request.form["email"],hashed_pw)
        )
        db.commit()
        return redirect("/login")
    return render_template("registration.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method=="POST":
        db=get_db()
        user=db.execute(
            "SELECT * FROM users WHERE email=?",
            (request.form["email"],)
        ).fetchone()
        if user and check_password_hash(user[3],request.form["password"]):
            session["user_id"]=user[0]
            return redirect("/")
    return render_template("login.html")

@app.route("/hotel_booking", methods=["GET", "POST"])
def hotel_booking():
    if"user_id" not in session:
        return redirect("/login")
    total_price= None

    if request.method== "POST":
        check_in= request.form["check_in"]
        check_out= request.form["check_out"]
        room_type= request.form["room"]

        d1= datetime.strptime(check_in, "%Y-%m-%d")
        d2= datetime.strptime(check_out, "%Y-%m-%d")
        nights= (d2-d1).days 

        if nights<=0:
            return render_template("hotel_booking.html", error="Invalid dates")
        
        price_per_night=HOTEL_PRICES.get(room_type, 0)
        total_price= nights*price_per_night

        db=get_db()
        db.execute(
            "INSERT INTO hotel_bookings (user_id, check_in, check_out, room_type) VALUES(?,?,?,?)",
            (session ["user_id"],request.form["check_in"],request.form["check_out"],request.form["room"])
        )
        db.execute(
            "UPDATE users SET loyalty_points=loyalty_points+10 WHERE id=?", (session["user_id"],)
        )
        db.commit() 

        return render_template(
            "hotel_booking.html", total_price=total_price, nights=nights, room_type=room_type, check_in=check_in,
            check_out=check_out, stripe_amount=total_price, description=f"Hotel Booking ({room_type} room for {nights} nights)"
        )
    return render_template("hotel_booking.html")

@app.route("/zoo_booking", methods=["GET", "POST"])
def zoo_booking():
    total_price=None

    if request.method== "POST":
        tickets= int(request.form["tickets"])
        visit_date= int(request.form["date"])
        total_price=tickets* ZOO_TICKET

        db=get_db()
        db.execute(
            "INSERT INTO zoo_bookings (user_id, visit_date, tickets, total_price) VALUES(?,?,?,?)",
            (session ["user_id"], visit_date,tickets, total_price)
        )
        db.execute(
            "UPDATE users SET loyalty_points=loyalty_points+10 WHERE id=?", (session["user_id"],)
        )
        db.commit() 
        return render_template(
            "zoo_booking.html", total_price=total_price,stripe_amount=total_price,
            description=f"Zoo Tickets ({tickets} tickets)"
        )
    return render_template("/zoo_booking.html", total_price=total_price)

@app.route("/create_checkout_session", methods=["POST"])
def create_checkout_session():
    data=request.get_json()

    if not data:
        return jsonify({"error": "No data received"}), 400
    
    amount=int(data["amount"])
    description=data["description"]

    try:
        checkout_session= stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data":{
                    "currency":"gbp",
                    "product_data":{
                        "name": description,
                    },
                    "unit_amount":amount * 100,
                },
                "quantity":1,
            }],
            mode="payment",
            success_url=YOUR_DOMAIN + "/payment_success",
            cancel_url=YOUR_DOMAIN +"/payment_cancel",
        )

        db=get_dbp()
        db.execute(
            "INSERT INTO payments1 (amount, status, stripe_id) VALUES (?, ?, ?)",
            (amount, "created", checkout_session.id)
        )
        db.commit()

        return jsonify({"id": checkout_session.id})
    except Exception as e:
        print("Stripe error:", e)
        return jsonify({"error": str(e)}), 403
    
@app.route("/payment_success")
def payment_success():
    return render_template("payment_success.html")

@app.route("/payment_cancel")
def payment_cancel():
    return render_template("payment_cancel.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect ("/login")
    db=get_db()
    user=db.execute(
        "SELECT * FROM  users WHERE id=?", (session["user_id"],)
    ).fetchone()
    return render_template("dashboard.html", user=user)

@app.route("/educational_visit", methods=["GET", "POST"])
def educational_visit():
    if request.method == "POST":
        school_name=request.form["school_name"]
        contact_name=request.form["contact_name"]
        email=request.form["email"]
        visit_date=request.form["visit_date"]
        students=request.form["students"]
        level=request.form["level"]
        message=request.form["message"]

        try:
            msg=Message(
                subject="Your Educational Visit to RZA",
                recipients=[email]
            )
            msg.body=f"""Hello {contact_name}, thank you for you booking for an educational visit to RZA. Here are your details: 
            School/Organisation: {school_name}
            Visit date: {visit_date}
            Number of students: {students}
            Eductaional Level: {level}
            
            Additional notes:{message if message else None}

            We look forward to seeing you.
            
            Best regards,
            RZA"""

            mail.send(msg)
            flash("your visit request is accepted, an email will be sent to you", "success")
        except Exception as e:
            print("error send email", e)
            flash("visit accepted but email not sent", "warning")

        print(school_name, contact_name, email, visit_date, students, level, message)

        flash("Educational visit request submitted successfully!", "success")
        return redirect(url_for("educational_visit"))
    return render_template("educational_visit.html")

@app.route("/view_rrsources")
def view_resources():
    return render_template("view_resources.html")

app.config.update(
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT=587,
    MAIL_USER_TLS=True,
    #MAIL_USER_SSL=False,
    MAIL_USERNAME="kehindeomisakin3@gmail.com",
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_DEFAULT_SENDER=('RZA', 'info@rza.com')
)
mail=Mail(app)

app.run(debug=True)