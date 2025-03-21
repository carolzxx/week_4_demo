from flask import Flask, render_template, request, flash
from duckduckgo_search import DDGS
import time
from duckduckgo_search.exceptions import DuckDuckGoSearchException

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for flash messages

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    error_message = None
    
    if request.method == 'POST':
        query = request.form.get('query', '')
        if query:
            try:
                with DDGS() as ddgs:
                    # Add a small delay before making the request
                    time.sleep(1)
                    results = list(ddgs.text(query, max_results=3))
            except DuckDuckGoSearchException as e:
                if "Ratelimit" in str(e):
                    error_message = "We're experiencing high search volume. Please try again in a few moments."
                else:
                    error_message = "An error occurred while searching. Please try again."
                results = []
    
    return render_template('index.html', results=results, error_message=error_message)

if __name__ == '__main__':
    app.run(port=5008)
