# backend/main.py
print("Using updated main.py without dotenv")

import os
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS # Handles browser security (CORS)
# from dotenv import load_dotenv # Import for loading .env file

# Libraries for scraping web pages
import requests
from bs4 import BeautifulSoup

# --- 1. Load Environment Variables ---
# load_dotenv() # Load variables from .env file

# --- 2. Configure the Server ---
app = Flask(__name__)
# IMPORTANT: Allow requests from any origin ('*').
CORS(app)

# --- 3. Configure the AI ---
# Get your Gemini API key from an environment variable
gemini_api_key = os.environ.get("GEMINI_API_KEY")
if not gemini_api_key:
    print("Warning: GEMINI_API_KEY environment variable not set.")
else:
    try:
        genai.configure(api_key=gemini_api_key)
    except Exception as e:
        print(f"Error configuring Gemini: {e}")

# --- ADD THIS BLOCK TO LIST AVAILABLE MODELS ---
print("Listing available Gemini models...")
try:
    if gemini_api_key: # Only try if key exists
        # Iterate through the list of models and print their names
        for m in genai.list_models():
            # Check if the model supports the 'generateContent' method
            if 'generateContent' in m.supported_generation_methods:
                print(f" - {m.name}")
    else:
        print("Skipping model listing as API key is not set.")
except Exception as e:
    print(f"Could not list models: {e}")
# --- END OF BLOCK TO LIST MODELS ---

# --- 4. Web Scraping Function ---
def scrape_article_text(url: str) -> str:
    """Very basic scraper. Downloads HTML and extracts text from <p> tags."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10) # Added timeout
        response.raise_for_status() # Raise error for bad responses (4xx or 5xx)

        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all paragraph tags <p> - a simple approach
        paragraphs = soup.find_all('p')
        text = ' '.join([p.get_text(strip=True) for p in paragraphs]) # strip=True removes extra whitespace

        # Limit text length (~1500 words) to avoid huge API requests
        max_words = 1500
        return ' '.join(text.split()[:max_words])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return "" # Return empty string on fetch error
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return "" # Return empty string on other errors

# --- 5. The API Endpoint ---
@app.route("/summarize", methods=["POST"])
def summarize():
    """Receives a URL, scrapes it, gets summary from AI, returns summary."""
    try:
        data = request.get_json()
        if not data or "url" not in data:
            print("Error: No URL provided in request.")
            return jsonify({"error": "No URL provided"}), 400

        url_to_scrape = data["url"]
        print(f"Received request to summarize: {url_to_scrape}") # Log the request

        # Step A: Scrape the article text
        article_text = scrape_article_text(url_to_scrape)
        if not article_text:
            print(f"Failed to scrape text from {url_to_scrape}")
            return jsonify({"error": "Could not scrape text from URL"}), 400
        print(f"Scraped {len(article_text.split())} words. Sending to Gemini...")

        # Step B: Send the text to the Gemini API
        if not gemini_api_key:
             print("Error: AI API key not configured on server.")
             return jsonify({"error": "AI API key not configured on server"}), 500

        # !! IMPORTANT: Update this model name based on the output of list_models() !!
        model_name_to_use = "models/gemini-pro-latest" # Use the specific alias from the list
        print(f"Using model: {model_name_to_use}")
        model = genai.GenerativeModel(model_name_to_use)

        prompt = f"Summarize the following article text in 3 concise bullet points:\n\n{article_text}"

        # Make the API call
        response = model.generate_content(prompt)

        print("Received summary from Gemini.")

        # Step C: Return the summary
        return jsonify({"summary": response.text})

    except Exception as e:
        # Catch any unexpected errors during the process
        print(f"Error in /summarize endpoint: {e}")
        # Return a generic server error message
        return jsonify({"error": "An internal server error occurred"}), 500

# --- 6. Run Locally (Only if run directly with `python main.py`) ---
if __name__ == "__main__":
    # Use port from environment variable, default to 8081 if not set or if 8080 is busy
    port = int(os.environ.get("PORT", 8082))
    app.run(debug=True, host="0.0.0.0", port=port)