from flask import Flask, render_template, request, jsonify, flash
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import DuckDuckGoSearchException
from bs4 import BeautifulSoup
import requests
import logging
import time

from agents import SummarizerAgent, InsightAgent, RecommenderAgent

# Initialize Flask App
app = Flask(__name__)
app.secret_key = "your-secret-key-here"
logging.basicConfig(level=logging.INFO)

# Initialize agents
summarizer = SummarizerAgent()
insight_agent = InsightAgent()
recommender_agent = RecommenderAgent()


def get_url_content(url):
    """Fetch text content from a webpage, removing short/irrelevant text."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style"]):
            tag.extract()

        text = soup.get_text(separator="\n")
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        filtered = [chunk for chunk in chunks if chunk and len(chunk.split()) >= 10]

        return "\n".join(filtered)

    except Exception as e:
        logging.error(f"Error fetching content from {url}: {e}")
        return None


def summarize_content(content):
    """Trim to 500 words and summarize."""
    words = content.split()
    truncated = " ".join(words[:500])
    return summarizer.process(truncated)


def search_duckduckgo(query):
    """DuckDuckGo search with exponential backoff and summarization."""
    attempts = 0
    delay = 2
    max_attempts = 5
    results = []

    while attempts < max_attempts:
        try:
            with DDGS() as ddgs:
                logging.info(f"🔍 Searching: {query}")
                raw_results = list(ddgs.text(query, max_results=3))

                for result in raw_results:
                    url = result.get("href", "").strip()
                    if url.startswith("http"):
                        content = get_url_content(url)
                        summary = summarize_content(content) if content else "No summary available"
                        result["summary"] = summary
                        results.append(result)

                return results

        except DuckDuckGoSearchException as e:
            if "Ratelimit" in str(e):
                logging.warning(f"⏳ Rate limit hit. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                logging.error(f"❌ Search error: {e}")
                break

        attempts += 1

    return []


@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    error_message = None

    if request.method == "POST":
        query = request.form.get("query", "")
        if query:
            results = search_duckduckgo(query)
            if not results:
                error_message = "We're experiencing high search volume. Try again shortly."

    return render_template("index.html", results=results, error_message=error_message)


@app.route("/summarize_all", methods=["POST"])
def summarize_all():
    urls = request.json.get("urls", [])
    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    summaries = {}
    try:
        for url in urls:
            content = get_url_content(url)
            summary = summarize_content(content) if content else "Error retrieving content"
            summaries[url] = summary

        insights = insight_agent.process_text(list(summaries.values()))
        return jsonify({"summaries": summaries, "insights": insights})

    except Exception as e:
        return jsonify({"error": f"Failed to summarize and analyze: {str(e)}"}), 500


@app.route("/generate_recommendations", methods=["POST"])
def generate_recommendations():
    data = request.json
    insights = data.get("insights", "")
    summaries = data.get("summaries", [])
    goal = data.get("goal", "")
    persona = data.get("persona", "")

    if not insights or not summaries or not goal:
        return jsonify({"error": "Missing required data"}), 400

    try:
        recommendations = recommender_agent.process(insights, summaries, goal, persona)
        next_query = recommender_agent.suggest_next_query(insights, summaries, goal, persona)
        return jsonify({"recommendations": recommendations, "next_query": next_query})
    except Exception as e:
        return jsonify({"error": f"Failed to generate recommendations: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(port=5008, host="0.0.0.0", debug=True)

