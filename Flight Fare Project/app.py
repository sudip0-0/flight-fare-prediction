import os
from pyexpat import features, model
from turtle import pd
import pandas as pd
from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask import Flask, render_template, request
import stripe
from wtforms.validators import InputRequired, Length, Email
from flask_bootstrap import Bootstrap
from flask_cors import cross_origin
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from datetime import datetime
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import joblib  # Use joblib for loading the model
from dotenv import load_dotenv
import numpy as np



app = Flask(__name__)

stripe_keys = {
        "secret_key": os.environ["STRIPE_SECRET_KEY"],
        "publishable_key": os.environ["STRIPE_PUBLISHABLE_KEY"],
    }
stripe.api_key = stripe_keys["secret_key"]
stripe.api_key = stripe_keys["publishable_key"]

app.config['SECRET_KEY'] = 'hello1234'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/Project'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
Bootstrap(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    contact =db.Column(db.String(120),unique=True, nullable=False)  

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=80)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=6, max=80)])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=80)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=6, max=80)])
    email = StringField('Email', validators=[InputRequired(), Email()])
    contact = StringField('Contact', validators=[InputRequired(), Length(min=10, max=15)])
    submit = SubmitField('Register')
load_dotenv() 

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

model = joblib.load('flight_rf_dollar.pkl')
@app.route('/')
def home():
    username = None
    if current_user.is_authenticated:
        username = current_user.username
    return render_template('home.html',username=username)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.password == password:
            login_user(user)
            flash('Login successful', 'success')
            return redirect(url_for('home'))
        else:
            flash('User is not registered or invalid password', 'error')
            return render_template('login.html', form=form)
    
    return render_template('login.html', form=form)
# def login():
#     form = LoginForm()
#     if form.validate_on_submit():
#         username = form.username.data
#         password = form.password.data
#         user = User.query.filter_by(username=username).first()
#         if user.username == username and user.password == password:
#             login_user(user)
#             flash('Login successful', 'success')
#             return redirect(url_for('home'))
#         else:
#             print("User Is not Registered ")
#         flash('Invalid username or password', 'error')
#     return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
       username = form.username.data
       password = form.password.data
       email = form.email.data
       contact = form.contact.data
       user = User(username=username, password=password,email=email,contact=contact)
       db.session.add(user)
       db.session.commit()

       session['user_email']=email
       flash('Registration successful. Please log in.', 'success')
       return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/checkout',methods=['POST'])
@login_required
def checkout():
    publishable_key = os.environ.get("STRIPE_PUBLISHABLE_KEY")
   
    predicted_price = session.get("predicted_price")
 
    predicted_price_in_cent = int(predicted_price*100)
    return render_template('checkout.html', key=publishable_key,predicted_price=predicted_price_in_cent)

@app.route('/charge', methods=['POST'])
def charge():
     

    stripe.api_key =os.environ["STRIPE_SECRET_KEY"]
    predicted_price = session.get("predicted_price")
    
    predicted_price_float = float(predicted_price)

    amount = int(predicted_price_float*100)

    user_email = session.get("user_email")
    if not user_email:
        flash('User email not found. Please register again.', 'error')
        return redirect(url_for('register'))
    
    customer = stripe.Customer.create(
        email=user_email,  
        source=request.form['stripeToken']
    )

    charge = stripe.Charge.create(
            customer=customer.id,
            amount=amount,
            currency='usd',
            description='Flight Fare'
        )

    return render_template('charge.html', amount=amount)

##for getting current time
def get_current_datetime():
    now = datetime.now()
    current_datetime = now.strftime("%Y-%m-%d %H:%M:%S")
    return current_datetime

@app.route("/predict", methods = ["GET", "POST"])
@cross_origin()
def predict():
    if request.method == "POST":
         
        form = LoginForm()
        username = form.username.data

        country = request.form.get("country")
        # Date_of_Journey
        date_dep = request.form["Dep_Time"]
        Journey_day = int(pd.to_datetime(date_dep, format="%Y-%m-%dT%H:%M").day)
        Journey_month = int(pd.to_datetime(date_dep, format ="%Y-%m-%dT%H:%M").month)
        # print("Journey Date : ",Journey_day, Journey_month)

        # Departure
        Dep_hour = int(pd.to_datetime(date_dep, format ="%Y-%m-%dT%H:%M").hour)
        Dep_min = int(pd.to_datetime(date_dep, format ="%Y-%m-%dT%H:%M").minute)
        # print("Departure : ",Dep_hour, Dep_min)

        # Arrival
        date_arr = request.form["Arrival_Time"]
        Arrival_hour = int(pd.to_datetime(date_arr, format ="%Y-%m-%dT%H:%M").hour)
        Arrival_min = int(pd.to_datetime(date_arr, format ="%Y-%m-%dT%H:%M").minute)
        # print("Arrival : ", Arrival_hour, Arrival_min)

        # Duration
        dur_hour = abs(Arrival_hour - Dep_hour)
        dur_min = abs(Arrival_min - Dep_min)
        # print("Duration : ", dur_hour, dur_min)

        # Total Stops
        Total_stops = int(request.form["stops"])
        # print(Total_stops)

        # Airline
        # AIR ASIA = 0 (not in column)
        airline=request.form['airline']
        if(airline=='Jet Airways'):
            Jet_Airways = 1
            IndiGo = 0
            Air_India = 0
            Multiple_carriers = 0
            Buddha_Air = 0
            Yeti_Airlines = 0
            Shree_Airlines = 0
            SpiceJet = 0
            Vistara = 0
            GoAir = 0
            


        elif (airline=='IndiGo'):
            Jet_Airways = 0
            IndiGo = 1
            Air_India = 0
            Multiple_carriers = 0
            Buddha_Air = 0
            Yeti_Airlines = 0
            Shree_Airlines = 0
            SpiceJet = 0
            Vistara = 0
            GoAir = 0
        elif (airline=='Air India'):
            Jet_Airways = 0
            IndiGo = 0
            Air_India = 1
            Multiple_carriers = 0
            Buddha_Air = 0
            Yeti_Airlines = 0
            Shree_Airlines = 0
            SpiceJet = 0
            Vistara = 0
            GoAir = 0
            
        elif (airline=='Multiple carriers'):
            Jet_Airways = 0
            IndiGo = 0
            Air_India = 0
            Multiple_carriers = 1
            Buddha_Air = 0
            Yeti_Airlines = 0
            Shree_Airlines = 0
            SpiceJet = 0
            Vistara = 0
            GoAir = 0 
            
        elif (airline=='SpiceJet'):
            Jet_Airways = 0
            IndiGo = 0
            Air_India = 0
            Multiple_carriers = 0
            Buddha_Air = 0
            Yeti_Airlines = 0
            Shree_Airlines = 0
            SpiceJet = 1
            Vistara = 0
            GoAir = 0
            
        elif (airline=='Vistara'):
            Jet_Airways = 0
            IndiGo = 0
            Air_India = 0
            Multiple_carriers = 0
            Buddha_Air = 0
            Yeti_Airlines = 0
            Shree_Airlines = 0
            SpiceJet = 0
            Vistara = 1
            GoAir = 0

        elif (airline=='GoAir'):
            Jet_Airways = 0
            IndiGo = 0
            Air_India = 0
            Multiple_carriers = 0
            Buddha_Air = 0
            Yeti_Airlines = 0
            Shree_Airlines = 0
            SpiceJet = 0
            Vistara = 0
            GoAir = 1

        elif (airline=='Buddha Air'):
            Jet_Airways = 0
            IndiGo = 0
            Air_India = 0
            Multiple_carriers = 0
            Buddha_Air = 1
            Yeti_Airlines = 0
            Shree_Airlines = 0
            SpiceJet = 0
            Vistara = 0
            GoAir = 0

        elif (airline=='Yeti Airlines'):
            Jet_Airways = 0
            IndiGo = 0
            Air_India = 0
            Multiple_carriers = 0
            Buddha_Air = 0
            Yeti_Airlines = 1
            Shree_Airlines = 0
            SpiceJet = 0
            Vistara = 0
            GoAir = 0

        elif (airline=='Shree Airlines'):
            Jet_Airways = 0
            IndiGo = 0
            Air_India = 0
            Multiple_carriers = 0
            Buddha_Air = 0
            Yeti_Airlines = 0
            Shree_Airlines = 1
            SpiceJet = 0
            Vistara = 0
            GoAir = 0
            
        

        else:
            Jet_Airways = 0
            IndiGo = 0
            Air_India = 0
            Multiple_carriers = 0
            Buddha_Air = 0
            Yeti_Airlines = 0
            Shree_Airlines = 0
            SpiceJet = 0
            Vistara = 0
            GoAir = 0

        # print(Jet_Airways,
        #     IndiGo,
        #     Air_India,
        #     Multiple_carriers,
        #     SpiceJet,
        #     Vistara,
        #     GoAir,
        #     Multiple_carriers_Premium_economy,
        #     Jet_Airways_Business,
        #     Vistara_Premium_economy,
        #     Trujet)

        # Source
        # Banglore = 0 (not in column)
        Source = request.form["Source"]
        if (Source == 'Delhi'):
            s_Delhi = 1
            s_Kolkata = 0
            s_Kathmandu = 0
            s_Banglore = 0
            s_Mumbai = 0
            s_Biratnagar = 0
            s_Janakpur = 0
            s_Pokhara = 0
            s_Chennai = 0
            s_Nepalgunj = 0
            s_Simara = 0
            s_Bhairahawa = 0
            s_Bharatpur = 0
            s_Dhangadi = 0
            s_Bhadrapur = 0
            s_Rajbiraj = 0

        elif (Source == 'Kolkata'):
            s_Delhi = 0
            s_Kolkata = 1
            s_Kathmandu = 0
            s_Banglore = 0
            s_Mumbai = 0
            s_Biratnagar = 0
            s_Janakpur = 0
            s_Pokhara = 0
            s_Chennai = 0
            s_Nepalgunj = 0
            s_Simara = 0
            s_Bhairahawa = 0
            s_Bharatpur = 0
            s_Dhangadi = 0
            s_Bhadrapur = 0
            s_Rajbiraj = 0

        elif (Source == 'Kathmandu'):
            s_Delhi = 0
            s_Kolkata = 0
            s_Kathmandu = 1
            s_Banglore = 0
            s_Mumbai = 0
            s_Biratnagar = 0
            s_Janakpur = 0
            s_Pokhara = 0
            s_Chennai = 0
            s_Nepalgunj = 0
            s_Simara = 0
            s_Bhairahawa = 0
            s_Bharatpur = 0
            s_Dhangadi = 0
            s_Bhadrapur = 0
            s_Rajbiraj = 0

        elif (Source == 'Banglore'):
            s_Delhi = 0
            s_Kolkata = 0
            s_Kathmandu = 0
            s_Banglore = 1
            s_Mumbai = 0
            s_Biratnagar = 0
            s_Janakpur = 0
            s_Pokhara = 0
            s_Chennai = 0
            s_Nepalgunj = 0
            s_Simara = 0
            s_Bhairahawa = 0
            s_Bharatpur = 0
            s_Dhangadi = 0
            s_Bhadrapur = 0
            s_Rajbiraj = 0

        elif (Source == 'Mumbai'):
            s_Delhi = 0
            s_Kolkata = 0
            s_Kathmandu = 0
            s_Banglore = 0
            s_Mumbai = 1
            s_Biratnagar = 0
            s_Janakpur = 0
            s_Pokhara = 0
            s_Chennai = 0
            s_Nepalgunj = 0
            s_Simara = 0
            s_Bhairahawa = 0
            s_Bharatpur = 0
            s_Dhangadi = 0
            s_Bhadrapur = 0
            s_Rajbiraj = 0
        
        elif (Source == 'Biratnagar'):
            s_Delhi = 0
            s_Kolkata = 0
            s_Kathmandu = 0
            s_Banglore = 0
            s_Mumbai = 0
            s_Biratnagar = 1
            s_Janakpur = 0
            s_Pokhara = 0
            s_Chennai = 0
            s_Nepalgunj = 0
            s_Simara = 0
            s_Bhairahawa = 0
            s_Bharatpur = 0
            s_Dhangadi = 0
            s_Bhadrapur = 0
            s_Rajbiraj = 0
        
        elif (Source == 'Janakpur'):
            s_Delhi = 0
            s_Kolkata = 0
            s_Kathmandu = 0
            s_Banglore = 0
            s_Mumbai = 0
            s_Biratnagar = 0
            s_Janakpur = 1
            s_Pokhara = 0
            s_Chennai = 0
            s_Nepalgunj = 0
            s_Simara = 0
            s_Bhairahawa = 0
            s_Bharatpur = 0
            s_Dhangadi = 0
            s_Bhadrapur = 0
            s_Rajbiraj = 0
        
        elif (Source == 'Pokhara'):
            s_Delhi = 0
            s_Kolkata = 0
            s_Kathmandu = 0
            s_Banglore = 0
            s_Mumbai = 0
            s_Biratnagar = 0
            s_Janakpur = 0
            s_Pokhara = 1
            s_Chennai = 0
            s_Nepalgunj = 0
            s_Simara = 0
            s_Bhairahawa = 0
            s_Bharatpur = 0
            s_Dhangadi = 0
            s_Bhadrapur = 0
            s_Rajbiraj = 0
        
        elif (Source == 'Chennai'):
            s_Delhi = 0
            s_Kolkata = 0
            s_Kathmandu = 0
            s_Banglore = 0
            s_Mumbai = 0
            s_Biratnagar = 0
            s_Janakpur = 0
            s_Pokhara = 0
            s_Chennai = 1
            s_Nepalgunj = 0
            s_Simara = 0
            s_Bhairahawa = 0
            s_Bharatpur = 0
            s_Dhangadi = 0
            s_Bhadrapur = 0
            s_Rajbiraj = 0
        
        elif (Source == 'Nepalgunj'):
            s_Delhi = 0
            s_Kolkata = 0
            s_Kathmandu = 0
            s_Banglore = 0
            s_Mumbai = 0
            s_Biratnagar = 0
            s_Janakpur = 0
            s_Pokhara = 0
            s_Chennai = 0
            s_Nepalgunj = 1
            s_Simara = 0
            s_Bhairahawa = 0
            s_Bharatpur = 0
            s_Dhangadi = 0
            s_Bhadrapur = 0
            s_Rajbiraj = 0
        
        elif (Source == 'Simara'):
            s_Delhi = 0
            s_Kolkata = 0
            s_Kathmandu = 0
            s_Banglore = 0
            s_Mumbai = 0
            s_Biratnagar = 0
            s_Janakpur = 0
            s_Pokhara = 0
            s_Chennai = 0
            s_Nepalgunj = 0
            s_Simara = 1
            s_Bhairahawa = 0
            s_Bharatpur = 0
            s_Dhangadi = 0
            s_Bhadrapur = 0
            s_Rajbiraj = 0
        
        elif (Source == 'Bhairahawa'):
            s_Delhi = 0
            s_Kolkata = 0
            s_Kathmandu = 0
            s_Banglore = 0
            s_Mumbai = 0
            s_Biratnagar = 0
            s_Janakpur = 0
            s_Pokhara = 0
            s_Chennai = 0
            s_Nepalgunj = 0
            s_Simara = 0
            s_Bhairahawa = 1
            s_Bharatpur = 0
            s_Dhangadi = 0
            s_Bhadrapur = 0
            s_Rajbiraj = 0
        
        elif (Source == 'Bharatpur'):
            s_Delhi = 0
            s_Kolkata = 0
            s_Kathmandu = 0
            s_Banglore = 0
            s_Mumbai = 0
            s_Biratnagar = 0
            s_Janakpur = 0
            s_Pokhara = 0
            s_Chennai = 0
            s_Nepalgunj = 0
            s_Simara = 0
            s_Bhairahawa = 0
            s_Bharatpur = 1
            s_Dhangadi = 0
            s_Bhadrapur = 0
            s_Rajbiraj = 0

        elif (Source == 'Dhangadi'):
            s_Delhi = 0
            s_Kolkata = 0
            s_Kathmandu = 0
            s_Banglore = 0
            s_Mumbai = 0
            s_Biratnagar = 0
            s_Janakpur = 0
            s_Pokhara = 0
            s_Chennai = 0
            s_Nepalgunj = 0
            s_Simara = 0
            s_Bhairahawa = 0
            s_Bharatpur = 0
            s_Dhangadi = 1
            s_Bhadrapur = 0
            s_Rajbiraj = 0
        
        elif (Source == 'Bhadrapur'):
            s_Delhi = 0
            s_Kolkata = 0
            s_Kathmandu = 0
            s_Banglore = 0
            s_Mumbai = 0
            s_Biratnagar = 0
            s_Janakpur = 1
            s_Pokhara = 0
            s_Chennai = 0
            s_Nepalgunj = 0
            s_Simara = 0
            s_Bhairahawa = 0
            s_Bharatpur = 0
            s_Dhangadi = 0
            s_Bhadrapur = 1
            s_Rajbiraj = 0
        
        elif (Source == 'Rajbiraj'):
            s_Delhi = 0
            s_Kolkata = 0
            s_Kathmandu = 0
            s_Banglore = 0
            s_Mumbai = 0
            s_Biratnagar = 0
            s_Janakpur = 0
            s_Pokhara = 0
            s_Chennai = 0
            s_Nepalgunj = 0
            s_Simara = 0
            s_Bhairahawa = 0
            s_Bharatpur = 0
            s_Dhangadi = 0
            s_Bhadrapur = 0
            s_Rajbiraj = 1




        # print(s_Delhi,
        #     s_Kolkata,
        #     s_Mumbai,
        #     s_Chennai)

        # Destination
        # Banglore = 0 (not in column)
        Destination = request.form["Destination"]
        if (Destination == 'Cochin'):
            d_Delhi = 0
            d_Hyderabad = 0
            d_Kolkata = 0
            d_Cochin = 1
            d_Kathmandu = 0
            d_Banglore = 0
            d_Mumbai = 0
            d_Biratnagar = 0
            d_Janakpur = 0
            d_Pokhara = 0
            d_Chennai = 0
            d_Nepalgunj = 0
            d_Simara = 0
            d_Bhairahawa = 0
            d_Bharatpur = 0
            d_Dhangadi = 0
            d_Bhadrapur = 0
            d_Rajbiraj = 0
        
        elif (Destination == 'Delhi'):
            d_Delhi = 1
            d_Hyderabad = 0
            d_Kolkata = 0
            d_Cochin = 0
            d_Kathmandu = 0
            d_Banglore = 0
            d_Mumbai = 0
            d_Biratnagar = 0
            d_Janakpur = 0
            d_Pokhara = 0
            d_Chennai = 0
            d_Nepalgunj = 0
            d_Simara = 0
            d_Bhairahawa = 0
            d_Bharatpur = 0
            d_Dhangadi = 0
            d_Bhadrapur = 0
            d_Rajbiraj = 0

        

        elif (Destination == 'Hyderabad'):
            d_Delhi = 0
            d_Kolkata = 0
            d_Cochin = 0
            d_Hyderabad = 1
            d_Kathmandu = 0
            d_Banglore = 0
            d_Mumbai = 0
            d_Biratnagar = 0
            d_Janakpur = 0
            d_Pokhara = 0
            d_Chennai = 0
            d_Nepalgunj = 0
            d_Simara = 0
            d_Bhairahawa = 0
            d_Bharatpur = 0
            d_Dhangadi = 0
            d_Bhadrapur = 0
            d_Rajbiraj = 0

        elif (Destination == 'Kolkata'):
            d_Delhi = 0
            d_Kolkata = 1
            d_Cochin = 0
            d_Hyderabad = 0
            d_Kathmandu = 0
            d_Banglore = 0
            d_Mumbai = 0
            d_Biratnagar = 0
            d_Janakpur = 0
            d_Pokhara = 0
            d_Chennai = 0
            d_Nepalgunj = 0
            d_Simara = 0
            d_Bhairahawa = 0
            d_Bharatpur = 0
            d_Dhangadi = 0
            d_Bhadrapur = 0
            d_Rajbiraj = 0
        
        elif (Destination == 'Kathmandu'):
            d_Delhi = 0
            d_Kolkata = 0
            d_Cochin = 0
            d_Hyderabad = 0
            d_Kathmandu = 1
            d_Banglore = 0
            d_Mumbai = 0
            d_Biratnagar = 0
            d_Janakpur = 0
            d_Pokhara = 0
            d_Chennai = 0
            d_Nepalgunj = 0
            d_Simara = 0
            d_Bhairahawa = 0
            d_Bharatpur = 0
            d_Dhangadi = 0
            d_Bhadrapur = 0
            d_Rajbiraj = 0
        
        elif (Destination == 'Banglore'):
            d_Delhi = 0
            d_Kolkata = 0
            d_Cochin = 0
            d_Hyderabad = 0
            d_Kathmandu = 0
            d_Banglore = 1
            d_Mumbai = 0
            d_Biratnagar = 0
            d_Janakpur = 0
            d_Pokhara = 0
            d_Chennai = 0
            d_Nepalgunj = 0
            d_Simara = 0
            d_Bhairahawa = 0
            d_Bharatpur = 0
            d_Dhangadi = 0
            d_Bhadrapur = 0
            d_Rajbiraj = 0
        
        elif (Destination == 'Mumbai'):
            d_Delhi = 0
            d_Kolkata = 0
            d_Cochin = 0
            d_Hyderabad = 0
            d_Kathmandu = 0
            d_Banglore = 0
            d_Mumbai = 1
            d_Biratnagar = 0
            d_Janakpur = 0
            d_Pokhara = 0
            d_Chennai = 0
            d_Nepalgunj = 1
            d_Simara = 0
            d_Bhairahawa = 0
            d_Bharatpur = 0
            d_Dhangadi = 0
            d_Bhadrapur = 0
            d_Rajbiraj = 0
        
        elif (Destination == 'Biratnagar'):
            d_Delhi = 0
            d_Kolkata = 0
            d_Cochin = 0
            d_Hyderabad = 0
            d_Kathmandu = 0
            d_Banglore = 0
            d_Mumbai = 0
            d_Biratnagar = 1
            d_Janakpur = 0
            d_Pokhara = 0
            d_Chennai = 0
            d_Nepalgunj = 0
            d_Simara = 0
            d_Bhairahawa = 0
            d_Bharatpur = 0
            d_Dhangadi = 0
            d_Bhadrapur = 0
            d_Rajbiraj = 0
        
        elif (Destination == 'Janakpur'):
            d_Delhi = 0
            d_Kolkata = 0
            d_Cochin = 0
            d_Hyderabad = 0
            d_Kathmandu = 0
            d_Banglore = 0
            d_Mumbai = 0
            d_Biratnagar = 0
            d_Janakpur = 1
            d_Pokhara = 0
            d_Chennai = 0
            d_Nepalgunj = 0
            d_Simara = 0
            d_Bhairahawa = 0
            d_Bharatpur = 0
            d_Dhangadi = 0
            d_Bhadrapur = 0
            d_Rajbiraj = 0
        
        elif (Destination == 'Pokhara'):
            d_Delhi = 0
            d_Kolkata = 0
            d_Cochin = 0
            d_Hyderabad = 0
            d_Kathmandu = 0
            d_Banglore = 0
            d_Mumbai = 0
            d_Biratnagar = 0
            d_Janakpur = 0
            d_Pokhara = 1
            d_Chennai = 0
            d_Nepalgunj = 0
            d_Simara = 0
            d_Bhairahawa = 0
            d_Bharatpur = 0
            d_Dhangadi = 0
            d_Bhadrapur = 0
            d_Rajbiraj = 0
        
        elif (Destination == 'Chennai'):
            d_Delhi = 0
            d_Kolkata = 0
            d_Cochin = 0
            d_Hyderabad = 0
            d_Kathmandu = 0
            d_Banglore = 0
            d_Mumbai = 0
            d_Biratnagar = 0
            d_Janakpur = 0
            d_Pokhara = 0
            d_Chennai = 1
            d_Nepalgunj = 0
            d_Simara = 0
            d_Bhairahawa = 0
            d_Bharatpur = 0
            d_Dhangadi = 0
            d_Bhadrapur = 0
            d_Rajbiraj = 0
        
        elif (Destination == 'Nepalgunj'):
            d_Delhi = 0
            d_Kolkata = 0
            d_Cochin = 0
            d_Hyderabad = 0
            d_Kathmandu = 0
            d_Banglore = 0
            d_Mumbai = 0
            d_Biratnagar = 0
            d_Janakpur = 0
            d_Pokhara = 0
            d_Chennai = 0
            d_Nepalgunj = 1
            d_Simara = 0
            d_Bhairahawa = 0
            d_Bharatpur = 0
            d_Dhangadi = 0
            d_Bhadrapur = 0
            d_Rajbiraj = 0
        
        elif (Destination == 'Simara'):
            d_Delhi = 0
            d_Kolkata = 0
            d_Cochin = 0
            d_Hyderabad = 0
            d_Kathmandu = 0
            d_Banglore = 0
            d_Mumbai = 0
            d_Biratnagar = 0
            d_Janakpur = 0
            d_Pokhara = 0
            d_Chennai = 0
            d_Nepalgunj = 0
            d_Simara = 1
            d_Bhairahawa = 0
            d_Bharatpur = 0
            d_Dhangadi = 0
            d_Bhadrapur = 0
            d_Rajbiraj = 0
        
        elif (Destination == 'Bhairahawa'):
            d_Delhi = 0
            d_Kolkata = 0
            d_Cochin = 0
            d_Hyderabad = 0
            d_Kathmandu = 0
            d_Banglore = 0
            d_Mumbai = 0
            d_Biratnagar = 0
            d_Janakpur = 0
            d_Pokhara = 0
            d_Chennai = 0
            d_Nepalgunj = 0
            d_Simara = 0
            d_Bhairahawa = 1
            d_Bharatpur = 0
            d_Dhangadi = 0
            d_Bhadrapur = 0
            d_Rajbiraj = 0

        elif (Destination == 'Bharatpur'):
            d_Delhi = 0
            d_Kolkata = 0
            d_Cochin = 0
            d_Hyderabad = 0
            d_Kathmandu = 0
            d_Banglore = 0
            d_Mumbai = 0
            d_Biratnagar = 0
            d_Janakpur = 0
            d_Pokhara = 0
            d_Chennai = 0
            d_Nepalgunj = 0
            d_Simara = 0
            d_Bhairahawa = 0
            d_Bharatpur = 1
            d_Dhangadi = 0
            d_Bhadrapur = 0
            d_Rajbiraj = 0
        
        elif (Destination == 'Dhangadi'):
            d_Delhi = 0
            d_Kolkata = 0
            d_Cochin = 0
            d_Hyderabad = 0
            d_Kathmandu = 0
            d_Banglore = 0
            d_Mumbai = 0
            d_Biratnagar = 0
            d_Janakpur = 0
            d_Pokhara = 0
            d_Chennai = 0
            d_Nepalgunj = 0
            d_Simara = 0
            d_Bhairahawa = 0
            d_Bharatpur = 0
            d_Dhangadi = 1
            d_Bhadrapur = 0
            d_Rajbiraj = 0
        
        elif (Destination == 'Bhadrapur'):
            d_Delhi = 0
            d_Kolkata = 0
            d_Cochin = 0
            d_Hyderabad = 0
            d_Kathmandu = 0
            d_Banglore = 0
            d_Mumbai = 0
            d_Biratnagar = 0
            d_Janakpur = 0
            d_Pokhara = 0
            d_Chennai = 0
            d_Nepalgunj = 0
            d_Simara = 0
            d_Bhairahawa = 0
            d_Bharatpur = 0
            d_Dhangadi = 0
            d_Bhadrapur = 1
            d_Rajbiraj = 0
        
        elif (Destination == 'Rajbiraj'):
            d_Delhi = 0
            d_Kolkata = 0
            d_Cochin = 0
            d_Hyderabad = 0
            d_Kathmandu = 0
            d_Banglore = 0
            d_Mumbai = 0
            d_Biratnagar = 0
            d_Janakpur = 0
            d_Pokhara = 0
            d_Chennai = 0
            d_Nepalgunj = 0
            d_Simara = 0
            d_Bhairahawa = 0
            d_Bharatpur = 0
            d_Dhangadi = 0
            d_Bhadrapur = 0
            d_Rajbiraj = 1
        


        else:
            d_Delhi = 0
            d_Kolkata = 0
            d_Cochin = 0
            d_Hyderabad = 0
            d_Kathmandu = 0
            d_Banglore = 0
            d_Mumbai = 0
            d_Biratnagar = 0
            d_Janakpur = 0
            d_Pokhara = 0
            d_Chennai = 0
            d_Nepalgunj = 0
            d_Simara = 0
            d_Bhairahawa = 0
            d_Bharatpur = 0
            d_Dhangadi = 0
            d_Bhadrapur = 0
            d_Rajbiraj = 0

        # print(
        #     d_Cochin,
        #     d_Delhi,
        #     d_New_Delhi,
        #     d_Hyderabad,
        #     d_Kolkata
        # )
        

    #     ['Total_Stops', 'Journey_day', 'Journey_month', 'Dep_hour',
    #    'Dep_min', 'Arrival_hour', 'Arrival_min', 'Duration_hours',
    #    'Duration_mins', 'Airline_Air India', 'Airline_GoAir', 'Airline_IndiGo',
    #    'Airline_Jet Airways', 'Airline_Jet Airways Business',
    #    'Airline_Multiple carriers',
    #    'Airline_Multiple carriers Premium economy', 'Airline_SpiceJet',
    #    'Airline_Trujet', 'Airline_Vistara', 'Airline_Vistara Premium economy',
    #    'Source_Chennai', 'Source_Delhi', 'Source_Kolkata', 'Source_Mumbai',
    #    'Destination_Cochin', 'Destination_Delhi', 'Destination_Hyderabad',
    #    'Destination_Kolkata', 'Destination_New Delhi']
        
    features = np.array([
            Total_stops,
            Journey_day,
            Journey_month,
            Dep_hour,
            Dep_min,
            Arrival_hour,
            Arrival_min,
            dur_hour,
            dur_min,
            Air_India,
            Buddha_Air,
            GoAir,
            IndiGo,
            Jet_Airways,
            Air_India,
            Multiple_carriers,
            Shree_Airlines,
            SpiceJet,
            Vistara,
            Yeti_Airlines,
            s_Delhi,
            s_Kolkata,
            s_Kathmandu,
            s_Banglore,
            s_Mumbai,
            s_Biratnagar,
            s_Janakpur,
            s_Pokhara,
            s_Chennai,
            s_Nepalgunj,
            s_Simara,
            s_Bhairahawa,
            s_Bharatpur,
            s_Dhangadi,
            s_Bhadrapur, 
            s_Rajbiraj,
            d_Delhi,
            d_Kolkata,
            d_Hyderabad,
            d_Kathmandu,
            d_Banglore,
            d_Biratnagar,
            d_Janakpur,
            d_Pokhara,
            d_Nepalgunj,
            d_Simara,
            d_Bhairahawa,
            d_Bharatpur,
            d_Dhangadi,
            d_Bhadrapur,
            d_Rajbiraj 
        ])

    prediction = model.predict([features])
    output = round(prediction[0], 2)
    # Store input data in the session
    session["input_data"] = {
        "dep_time": date_dep,
        "username":username,
        "arrival_time": date_arr,
        "source": Source,
        "destination": Destination,
        "stops": Total_stops,
        "airline": airline,
        "price":output,
        "current_datetime": get_current_datetime(),
        "country":country
        }
    session["predicted_price"] =output

    return render_template('home.html',prediction_text="Your Flight price is $. {}".format(output))

@app.route('/show', methods=['POST', 'GET'])
@login_required
def show():
    input_data = session.get("input_data", None)

    if input_data:
        username = current_user.username if current_user.is_authenticated else "Guest"
        email = current_user.email
        contact = current_user.contact
        return render_template('show.html', dep_time=input_data["dep_time"], arrival_time=input_data["arrival_time"],
                               source=input_data["source"], destination=input_data["destination"],
                               stops=input_data["stops"], airline=input_data["airline"], price=input_data["price"],show=username,email=email, contact=contact, current_datetime=input_data["current_datetime"],country = input_data["country"])
    else:
        flash("Please provide data for prediction before showing details.", 'error')
        return redirect(url_for('show'))
    
@app.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    if request.method == 'POST':
        # Process the payment here, you can use a payment gateway or process the payment as needed.

        # After processing payment, you can show a success message or redirect to a thank you page.
        flash("Payment processed successfully!", 'success')
        return redirect(url_for('thank_you'))



if __name__ == "__main__":
    app.run(debug=True)
