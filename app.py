
from auth import auth_bp
# from credits import credits_bp
import os
import logging
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import cohere

# Logging setup
logging.basicConfig(level=logging.DEBUG)

# Flask app init
app = Flask(__name__)
app.register_blueprint(auth_bp, url_prefix='/auth')
#app.register_blueprint(credits_bp, url_prefix='/credits')  # se usi anche questo

# API Key load (env or fallback)
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "py3vt04R5KgSaaAj1rD39qMkbmL2uAb2tUPuPwbg")
if not COHERE_API_KEY:
    raise ValueError("COHERE_API_KEY not found!")

# Init Cohere client
co = cohere.Client(COHERE_API_KEY)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/evaluate', methods=["POST"])
def evaluate():
    try:
        data = request.get_json()
        user_input = data.get("input_text", "").strip()
        logging.debug(f"User input: {user_input}")

        if not user_input:
            return jsonify({"error": "Text not provided!"}), 400

        # Prompt dinamico con l'idea dell'utente inclusa
        prompt = f"""
You are an expert startup evaluator. Analyze the following startup idea:

STARTUP IDEA:
{user_input}

Please follow this structure in your response, using clear paragraphs and section titles (without asterisks or markdown):

	1.	BUSINESS PLAN

Begin with a detailed and data-driven business plan based on a close and accurate reading of the submitted startup idea. Carefully analyze the content, objectives, and assumptions in the user’s input before proceeding. Use this analysis to shape precise financial projections and operational strategies.

Include the following elements:
	•	Estimated startup costs with detailed breakdowns (e.g., technology development, legal setup, branding and marketing, staffing, licenses).
	•	Ongoing sustainability and operational costs (e.g., server hosting, maintenance, personnel, customer support).
	•	Evaluation of possible revenue models (e.g., subscriptions, advertising, licensing, freemium, SaaS) with pros and cons for each in this specific context.
	•	A robust financial forecast including estimated revenue, expenses, and profit/loss margins for years 1, 3, and 5. Ensure these numbers are internally consistent and realistic, based on the project’s scope and industry standards.

Then outline a step-by-step roadmap:
	•	Define clear strategic goals and deliverables (e.g., MVP release, beta testing, monetization).
	•	Estimate timelines in months or quarters for each key phase.
	•	Assign projected milestone dates and include cost or revenue impact when relevant.

Conclude this section by identifying and analyzing potential risks:
	•	Consider legal, regulatory, financial, technical, and organizational risks.
	•	For each risk, describe a specific mitigation strategy.
	•	Address scalability and investor concerns if applicable.

All insights should be informed directly by the original idea. Avoid assumptions that are not grounded in the source text.
	2.	MARKET ANALYSIS

Perform a comprehensive market analysis tailored to the submitted project idea. Do not generalize — instead, read and interpret the text thoroughly to extract relevant market implications.

Include the following:
	•	Define Total Addressable Market (TAM), Serviceable Available Market (SAM), and the most realistic initial target segment based on the idea.
	•	Identify demographic, geographic, and behavioral characteristics of the potential user base.
	•	Provide a competitive landscape analysis featuring 2 to 4 relevant competitors. Include a table comparing key aspects such as product features, pricing, UX, branding, and market positioning.
	•	Highlight industry trends, adoption barriers, and current market opportunities.
	•	Include structured tables and hypothetical data points. When useful, suggest specific visual formats (such as pie charts, bar graphs, or timelines) to illustrate findings, and clearly describe what each graph should show. Creation of at least one visual representation (e.g., a projected revenue line chart or competitor positioning matrix) is mandatory.

	3.	IDEA JUDGMENT

Conclude with a strategic evaluation of the startup idea, based on the detailed readings and analysis conducted above.
	•	Provide a summary of the concept’s key strengths and potential limitations.
	•	Assess viability using clear criteria: is it realistic, scalable, fundable, competitive, and sustainable?
	•	Issue a final recommendation: whether to proceed as is, pivot, or pause for refinement.
	•	If necessary, suggest strategic improvements, alternate monetization approaches, stronger niche targeting, or a change in core positioning to increase its chances of success.

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

from flask import redirect, url_for

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')

    app.logger.debug(f"Register attempt with Name: {name}, Email: {email}")

    # Qui potresti aggiungere la logica per salvare l'utente nel DB
    # Per ora simuliamo solo successo

    return redirect(url_for('index'))

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
