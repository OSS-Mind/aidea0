import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
import cohere

# Logging setup
logging.basicConfig(level=logging.DEBUG)

# Flask app init
app = Flask(__name__)

# Load environment variables
load_dotenv()

# --- Configuration ---
# IMPORTANT: Replace 'your_super_secret_key' with a strong, random key in production!
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_super_secret_key')
# Database configuration for SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # To suppress a warning

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # The route name for the login page

# API Key load (env or fallback)
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "YOUR_DEFAULT_COHERE_API_KEY_HERE") # Replace with your actual key or ensure it's in .env
if not COHERE_API_KEY or COHERE_API_KEY == "YOUR_DEFAULT_COHERE_API_KEY_HERE":
    logging.warning("COHERE_API_KEY not found or is default. Please set it in your .env file.")
co = cohere.Client(COHERE_API_KEY)

# --- User Model ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# --- Flask-Login User Loader ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('evaluate_page')) # Redirect logged-in users

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        app.logger.debug(f"Signup attempt with Username: {username}, Email: {email}")

        # Basic validation
        if not username or not email or not password:
            flash('All fields are required!', 'danger')
            return render_template('signup.html')

        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different one.', 'warning')
            return render_template('signup.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please use a different one or login.', 'warning')
            return render_template('signup.html')

        new_user = User(username=username, email=email)
        new_user.set_password(password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Your account has been created! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error during user signup: {e}")
            flash('An error occurred during registration. Please try again.', 'danger')

    return render_template('signup.html') # Render the signup form on GET

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('evaluate_page')) # Redirect logged-in users

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        app.logger.debug(f"Login attempt with Email: {email}")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('evaluate_page'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')

    return render_template('login.html') # Render the login form on GET

@app.route('/logout')
@login_required # Requires user to be logged in to access this route
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/evaluate_page') # A new route for the evaluation page that requires login
@login_required
def evaluate_page():
    # You might want to pass user-specific data to this template
    return render_template('evaluate.html', username=current_user.username)

@app.route('/evaluate', methods=["POST"])
@login_required # Ensure only logged-in users can evaluate
def evaluate_idea(): # Renamed the function to avoid conflict with route name
    try:
        data = request.get_json()
        user_input = data.get("input_text", "").strip()
        logging.debug(f"User '{current_user.username}' input: {user_input}") # Log current user

        if not user_input:
            return jsonify({"error": "Text not provided!"}), 400

        # Prompt dinamico con l'idea dell'utente inclusa
        prompt = f"""
You are an expert startup evaluator. Analyze the following startup idea:

STARTUP IDEA:
{user_input}

Please follow this structure in your response, using clear paragraphs and section titles (without asterisks or markdown):

    1.  BUSINESS PLAN

Begin with a detailed and data-driven business plan based on a close and accurate reading of the submitted startup idea. Carefully analyze the content, objectives, and assumptions in the user’s input before proceeding. Use this analysis to shape precise financial projections and operational strategies.

Include the following elements:
    •   Estimated startup costs with detailed breakdowns (e.g., technology development, legal setup, branding and marketing, staffing, licenses).
    •   Ongoing sustainability and operational costs (e.g., server hosting, maintenance, personnel, customer support).
    •   Evaluation of possible revenue models (e.g., subscriptions, advertising, licensing, freemium, SaaS) with pros and cons for each in this specific context.
    •   A robust financial forecast including estimated revenue, expenses, and profit/loss margins for years 1, 3, and 5. Ensure these numbers are internally consistent and realistic, based on the project’s scope and industry standards.

Then outline a step-by-step roadmap:
    •   Define clear strategic goals and deliverables (e.g., MVP release, beta testing, monetization).
    •   Estimate timelines in months or quarters for each key phase.
    •   Assign projected milestone dates and include cost or revenue impact when relevant.

Conclude this section by identifying and analyzing potential risks:
    •   Consider legal, regulatory, financial, technical, and organizational risks.
    •   For each risk, describe a specific mitigation strategy.
    •   Address scalability and investor concerns if applicable.

All insights should be informed directly by the original idea. Avoid assumptions that are not grounded in the source text.
    2.  MARKET ANALYSIS

Perform a comprehensive market analysis tailored to the submitted project idea. Do not generalize — instead, read and interpret the text thoroughly to extract relevant market implications.

Include the following:
    •   Define Total Addressable Market (TAM), Serviceable Available Market (SAM), and the most realistic initial target segment based on the idea.
    •   Identify demographic, geographic, and behavioral characteristics of the potential user base.
    •   Provide a competitive landscape analysis featuring 2 to 4 relevant competitors. Include a table comparing key aspects such as product features, pricing, UX, branding, and market positioning.
    •   Highlight industry trends, adoption barriers, and current market opportunities.
    •   Include structured tables and hypothetical data points. When useful, suggest specific visual formats (such as pie charts, bar graphs, or timelines) to illustrate findings, and clearly describe what each graph should show. Creation of at least one visual representation (e.g., a projected revenue line chart or competitor positioning matrix) is mandatory.

    3.  IDEA JUDGMENT

Conclude with a strategic evaluation of the startup idea, based on the detailed readings and analysis conducted above.
    •   Provide a summary of the concept’s key strengths and potential limitations.
    •   Assess viability using clear criteria: is it realistic, scalable, fundable, competitive, and sustainable?
    •   Issue a final recommendation: whether to proceed as is, pivot, or pause for refinement.
    •   If necessary, suggest strategic improvements, alternate monetization approaches, stronger niche targeting, or a change in core positioning to increase its chances of success.

Ensure that every part of your analysis remains consistent with the original project description. Do not make speculative leaps. Stay grounded in the actual content and intent of the user’s idea.
Write clearly and professionally. Avoid asterisks, hashtags, bold characters and markdown formatting. Instead, use paragraph spacing and capitalized section headings to organize the output.
"""

        logging.debug("Sending request to Cohere...")

        response = co.generate(
            model="command-r-plus",
            prompt=prompt,
            max_tokens=5000,
            temperature=0.7,
            k=0,
            p=0.75,
            return_likelihoods="NONE"
        )

        if not response or not response.generations:
            raise ValueError("Empty response from Cohere")

        result_text = response.generations[0].text.strip()
        logging.debug(f"Cohere response: {result_text}")

        return jsonify({"result": result_text})

    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({"error": "Error communicating with Cohere API"}), 502

# This part ensures the database tables are created before the first request.
# ... (all your other code, including imports, app config, User model, routes) ...

if __name__ == "__main__":
    # Ensure database tables are created when the application starts
    with app.app_context(): # <--- Use app_context to perform db operations
        db.create_all()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True) # Set debug=True for development
