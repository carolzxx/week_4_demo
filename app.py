from flask import Flask, render_template, request, flash
from duckduckgo_search import DDGS
import time
import logging
from duckduckgo_search.exceptions import DuckDuckGoSearchException

# Initialize Flask App
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for flash messages

# Setup Logging for Rate Limits
logging.basicConfig(level=logging.INFO)

def search_duckduckgo(query):
    """Perform DuckDuckGo search with rate-limit handling and exponential backoff."""
    attempts = 0
    max_attempts = 5  # Maximum retry attempts
    delay = 2  # Initial delay in seconds

    while attempts < max_attempts:
        try:
            with DDGS() as ddgs:
                logging.info(f"Searching DuckDuckGo: {query} (Attempt {attempts+1})")
                results = list(ddgs.text(query, max_results=3))
                return results  # Success, return results

        except DuckDuckGoSearchException as e:
            if "Ratelimit" in str(e):
                logging.warning(f"Rate limit hit! Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff (2s → 4s → 8s)
            else:
                logging.error(f"Error during search: {e}")
                break  # Stop retrying if it's a different error

        attempts += 1

    logging.error("Max retry attempts reached. Returning empty results.")
    return []  # Return empty results after max retries

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    error_message = None

    if request.method == 'POST':
        query = request.form.get('query', '')
        if query:
            results = search_duckduckgo(query)

            if not results:
                error_message = "We're experiencing high search volume. Please try again in a few moments."

    return render_template('index.html', results=results, error_message=error_message)

if __name__ == '__main__':
    app.run(port=5008, host="0.0.0.0")

