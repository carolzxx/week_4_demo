import os
import time
import requests
import logging
import shutil
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import DuckDuckGoSearchException
from agents import SummarizerAgent

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Directory to save results
RESULTS_DIR = "results"

# Delete old results and create a fresh folder
if os.path.exists(RESULTS_DIR):
    logging.info("🗑️ Deleting old results folder...")
    shutil.rmtree(RESULTS_DIR)

os.makedirs(RESULTS_DIR)
logging.info("📂 Fresh results folder created.")

# Instantiate summarizer agent once
summarizer = SummarizerAgent()


def fetch_and_save_webpage(url, filename):
    """
    Fetches the content of a webpage, removes short paragraphs (<10 words), and saves it.
    Also generates a summary using SummarizerAgent and saves it with a 'summarized_' prefix.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Parse text content
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.get_text().split("\n")
        filtered_paragraphs = [p.strip() for p in paragraphs if len(p.split()) >= 10]
        page_text = "\n\n".join(filtered_paragraphs)

        if not page_text.strip():
            logging.warning(f"⚠️ No relevant content found for {url}")
            return None

        # Save raw content
        file_path = os.path.join(RESULTS_DIR, filename)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(page_text)
        logging.info(f"✅ Saved: {file_path}")

        # ✂️ Truncate to 500 words for summarizer
        words = page_text.split()
        truncated_text = " ".join(words[:500])

        # 🧠 Summarize
        summary = summarizer.process(truncated_text)

        # 💾 Save summary
        summary_filename = f"summarized_{filename}"
        summary_path = os.path.join(RESULTS_DIR, summary_filename)
        with open(summary_path, "w", encoding="utf-8") as summary_file:
            summary_file.write(summary)
        logging.info(f"📝 Summary saved: {summary_path}")

        return file_path

    except requests.RequestException as e:
        logging.error(f"❌ Error fetching {url}: {e}")
        return None


def search_and_save(query):
    """
    Searches DuckDuckGo for 3 URLs based on a query and saves their content and summaries.
    Implements exponential backoff for rate limits.
    """
    if not query.strip():
        logging.warning("⚠️ Empty query provided. Please enter a valid search term.")
        return []

    logging.info(f"🔍 Searching DuckDuckGo for: {query}")
    results = []
    attempts = 0
    max_attempts = 5
    delay = 2

    while attempts < max_attempts:
        try:
            with DDGS() as ddgs:
                search_results = list(ddgs.text(query, max_results=3))

                if not search_results:
                    logging.warning("⚠️ No results found.")
                    return []

                for idx, result in enumerate(search_results):
                    url = result.get("href", "").strip()
                    if not url.startswith("http"):
                        continue

                    filename = f"{query.replace(' ', '_')}_{idx + 1}.txt"
                    saved_path = fetch_and_save_webpage(url, filename)

                    if saved_path:
                        results.append({
                            "title": result.get("title", "No Title"),
                            "link": url,
                            "file": saved_path
                        })

                return results

        except DuckDuckGoSearchException as e:
            if "Ratelimit" in str(e):
                logging.warning(f"⏳ Rate limit hit! Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2
            else:
                logging.error(f"❌ Search error: {e}")
                break

        attempts += 1

    logging.error("🚨 Max retry attempts reached. No results available.")
    return []


if __name__ == "__main__":
    query = input("Enter your search query: ").strip()
    search_and_save(query)

