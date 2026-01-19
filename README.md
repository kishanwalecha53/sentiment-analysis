# Sentiment Analysis Dashboard

A comprehensive tool for scraping Google Maps reviews, analyzing them using OpenAI's GPT models for sentiment and thematic insights, and visualizing the results in an interactive web dashboard.

## 📋 Prerequisites

Before getting started, ensure you have the following installed:
- [Python 3.8+](https://www.python.org/downloads/)
- [pip](https://pip.pypa.io/en/stable/installation/)

You will also need API keys for:
- **OpenAI API**: For sentiment analysis.
- **SerpApi**: For scraping Google Maps reviews (if you plan to scrape new data).

## 🚀 Installation

1.  **Clone the repository** (if you haven't already):
    ```bash
    git clone <repository-url>
    cd sentiment-analysis-website-main/sentiment-analysis
    ```

2.  **Install Python dependencies**:
    It is recommended to use a virtual environment.
    ```bash
    # Create virtual environment
    python -m venv venv
    
    # Activate virtual environment
    # On Windows:
    venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate

    # Install requirements
    pip install -r requirements.txt
    ```

## 🛠️ Usage Workflow

### Step 1: Scrape Reviews (Optional)
If you need fresh data from Google Maps, use the `scripts/serp.py` script.

1.  Open `scripts/serp.py`.
2.  Locate the `params` dictionary and update the `api_key` with your **SerpApi key**.
3.  Update the `data_id` with the specific Google Maps location ID you want to scrape.
4.  Run the scraper:
    ```bash
    python scripts/serp.py
    ```
    *This will generate a JSON file (e.g., `reviews_data_YYYYMMDD_HHMMSS.json`) containing the raw reviews.*

### Step 2: Analyze Sentiment
Run the main analysis script to process the raw reviews using OpenAI.

**Command Syntax:**
```bash
python scripts/main.py <input_file> -k <your_openai_api_key> [options]
```

**Arguments:**
- `input_file`: Path to the raw JSON file (e.g., the output from Step 1 or a custom JSON file).
- `-k, --api-key`: Your OpenAI API key.
- `-o, --output`: (Optional) Output file path (default: `analysis_results.json`).
- `-d, --delay`: (Optional) Delay between API calls in seconds (default: 1.0).

**Example:**
```bash
# Analyze 'reviews.json' and save to 'analysis_results.json'
python scripts/main.py reviews.json -k sk-your-api-key-here

# Analyze with a custom output filename
python scripts/main.py scripts/reviews_data_example.json -k sk-... -o my_analysis.json
```

### Step 3: View Dashboard
The dashboard runs in the browser and visualizes the generated `analysis_results.json`.

1.  Ensure `analysis_results.json` is in the root directory (same level as `index.html`).
2.  **Start a local server**:
    Browsers restrict fetching local files (CORS policy), so you cannot just double-click `index.html`. Using Python's built-in server is the easiest way.
    ```bash
    # Run this in the 'sentiment-analysis' directory
    python -m http.server 8000
    ```
3.  **Open in Browser**:
    Go to [http://localhost:8000](http://localhost:8000)

## 📂 Project Structure

- `scripts/main.py`: Core logic for calling OpenAI API and generating sentiment analysis.
- `scripts/serp.py`: Script for scraping Google Maps reviews using SerpApi.
- `index.html`: Main dashboard interface.
- `script.js`: Frontend logic for parsing the JSON data and rendering charts/tables.
- `styles.css`: Dashboard styling.
- `requirements.txt`: Python package dependencies.