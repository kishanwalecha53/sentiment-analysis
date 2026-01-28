# openai_sentiment_analysis_pipeline - sentiment-analysis

# openai_sentiment_analysis_pipeline

**Quick Summary:** This article helps you run the OpenAI-based sentiment analysis step (`scripts/main.py`) successfully by ensuring your input file and OpenAI API key are provided in the expected format.

**Type:** Troubleshooting Guide | **Difficulty:** Intermediate | **Estimated Time:** 10-15 minutes

## Applies To

- **Product/Repository:** sentiment-analysis
- **Language/Framework:** Python
- **Versions:** `openai==1.109.1`
- **Environment:** Development

## Symptoms

Users experiencing this issue may observe:

- **Error Messages (examples; exact text may vary by environment):**
  - CLI argument errors when required args are missing (e.g., missing `input_file` or `-k/--api-key`)
  - OpenAI authentication/authorization errors if the API key is missing/invalid
  - File-not-found errors if the provided input JSON path does not exist

- **Behavior:**
  - Running the sentiment analysis step requires a JSON input file path and an OpenAI API key.
  - If those required inputs aren’t provided as documented, the analysis step won’t run as intended.

- **Impact:**
  - You can’t generate analysis output for the dashboard (the frontend expects a dataset such as `analysis_results.json`).

## Root Cause

### Technical Explanation

The sentiment analysis workflow in this repository is command-line driven. The README documents that `scripts/main.py` expects:
- An `input_file` argument pointing to a raw reviews JSON file (for example, the output of `scripts/serp.py`)
- An OpenAI API key provided via `-k/--api-key`

If either the input file path or the OpenAI API key is missing or not provided in the documented way, the pipeline cannot perform OpenAI-based sentiment analysis.

**Key factors:**
- The README specifies a required CLI syntax: `python scripts/main.py <input_file> -k <your_openai_api_key> [options]`
- The analysis step is implemented as a dedicated script (`scripts/main.py`) and is the “main analysis script” in the workflow
- The analyzer logic is described as being centered around a `ReviewSentimentAnalyzer` class that initializes with an OpenAI API key and analyzes reviews one-by-one

## Resolution

### Step-by-Step Fix

**Method 1: Run sentiment analysis using the documented CLI arguments**

Follow these steps to resolve the issue:

1. **Confirm your environment meets prerequisites**
  - Python **3.8+**
  - `pip`
  - An **OpenAI API key**
  - (Optional for scraping) A **SerpApi key**

2. **Install dependencies in a virtual environment (recommended by the README)**
   ```bash
   python -m venv venv

   # Windows

   venv\Scripts\activate

   # macOS/Linux

   source venv/bin/activate

   pip install -r requirements.txt
   ```

3. **(Optional) Generate a raw reviews JSON file using the Google Maps scraper**
  - Open `scripts/serp.py`
  - Update the `params` dictionary:
    - Set `api_key` to your **SerpApi key**
    - Set `data_id` to the Google Maps location ID you want to scrape
  - Run:
     ```bash
     python scripts/serp.py
     ```
  - Expected output: a timestamped JSON file such as:
    - `reviews_data_YYYYMMDD_HHMMSS.json`

4. **Run sentiment analysis with the required arguments**
   Use the exact command structure documented in the README:
   ```bash
   python scripts/main.py <input_file> -k <your_openai_api_key>
   ```

   Example (replace with your actual filename):
   ```bash
   python scripts/main.py reviews_data_YYYYMMDD_HHMMSS.json -k YOUR_OPENAI_API_KEY
   ```

   Optional: write to a custom output file (README-documented):
   ```bash
   python scripts/main.py reviews_data_YYYYMMDD_HHMMSS.json -k YOUR_OPENAI_API_KEY -o my_analysis.json
   ```

**Expected Result:**
- The analysis script processes the reviews file and produces sentiment/thematic insights.
- By default, the output file is `analysis_results.json` (unless overridden with `-o/--output`).

**Verification:**
- Re-run the analysis command and confirm it completes successfully:
  ```bash
  python scripts/main.py <input_file> -k <your_openai_api_key>
  ```
- Confirm your analysis output file exists:
  - If you used defaults: `analysis_results.json`
  - If you used `-o`: the custom filename you provided
- If you are using the dashboard, ensure `analysis_results.json` is in the **root directory** (same level as `index.html`), because the frontend loads it via a relative fetch.

### Migration Guide (For Code-Level Changes)

Not applicable.

## Workarounds

If the above fix cannot be applied immediately:

**Temporary Solution:**
- Use an existing raw reviews JSON file (for example, a previously generated `reviews_data_YYYYMMDD_HHMMSS.json`) and rerun only the analysis step:
  ```bash
  python scripts/main.py <existing_input_file> -k <your_openai_api_key>
  ```

**Note:** This is a temporary measure. Apply the full resolution when possible (especially if you need fresh data from Google Maps).

## Prevention & Best Practices

To avoid this issue in the future:

1. **Follow the documented workflow order**
  - Scrape reviews (optional) with `scripts/serp.py`
  - Analyze sentiment with `scripts/main.py` using the documented CLI syntax
  - Use the dashboard to visualize results (frontend files include `index.html`, `script.js`, and `styles.css`)

2. **Keep your API keys available for the steps that require them**
  - OpenAI API key is required for sentiment analysis (`scripts/main.py`)
  - SerpApi key is required only if you scrape new Google Maps reviews (`scripts/serp.py`)

3. **Use the repository’s recommended virtual environment setup**
  - The README recommends using a virtual environment and installing dependencies via:
     ```bash
     pip install -r requirements.txt
     ```

4. **Keep the dashboard data file in the expected location**
  - The README and frontend expect `analysis_results.json` to be in the repo root (same level as `index.html`) for the dashboard to load it correctly.

## References

| Resource Type | Reference |
|---|---|
| Related GitHub Issues | Not available in provided repository evidence. |
| Pull Requests | Not available in provided repository evidence. |
| Documentation | Repository README (Sentiment Analysis Dashboard; workflow for `scripts/serp.py` and `scripts/main.py`) |
| Related Files | `scripts/main.py`, `scripts/serp.py`, `requirements.txt`, `index.html`, `script.js`, `styles.css` |

## Related Articles

- Sentiment Analysis Dashboard: Installation and setup (README-based)
- Scraping Google Maps reviews with `scripts/serp.py` (README-based)
- Viewing results in the dashboard (frontend reads from `analysis_results.json`, as described in the documentation)

## Support Escalation

If this article does not resolve your issue:

1. **Gather the following information:**
  - The exact command you ran (including arguments)
  - The path and name of the input JSON file you supplied to `scripts/main.py`
  - The full console output (including any stack trace)
  - Your environment details (OS, Python version, whether you used a virtual environment)
  - Confirmation that dependencies were installed from `requirements.txt`

2. **Contact Support:**
  - Submit via: Not specified in provided repository evidence.
  - Include: All information from step 1
  - Reference: This KB article

*Last Updated: 2026-01-28*  
*Article ID: KB-OASAP-20260128*