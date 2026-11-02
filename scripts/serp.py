from serpapi import GoogleSearch
from urllib.parse import urlsplit, parse_qsl
import json
import traceback
from datetime import datetime

def safe_get_nested(data, *keys, default=None):
    """Safely get nested dictionary values"""
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current

# Tomosu AI Recommendation: Switched extraction artifact timestamps to UTC for consistent support timelines
def save_data_to_json(data, filename_prefix="reviews_data"):
    """Save data to JSON file with timestamp"""
    from datetime import timezone

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.json"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Data saved to {filename}")
        return filename
    except Exception as e:
        print(f"Error saving to file {filename}: {e}")
        return None

# Tomosu AI Recommendation: Externalized SerpAPI key to prevent credential leaks and fail fast on missing config
def extract_reviews():
    import os

    serpapi_api_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_api_key:
        raise RuntimeError("SerpAPI extraction configuration failed: SERPAPI_API_KEY is not set. Action: configure the secret before running review extraction.")

    params = {
        "api_key": serpapi_api_key,
        "engine": "google_maps_reviews",
        "hl": "ar",
        "data_id": "0x3e2f039b4cec3f29:0x28429402fbebe3"
        
    }

    search = GoogleSearch(params)
    reviews = []
    errors = []
    page_num = 0
    
    try:
        while True:
            page_num += 1
            
            try:
                # Tomosu AI Recommendation: Added bounded jittered SerpAPI page fetch retries to reduce incomplete extraction from transient failures
                import random
                import time

                for fetch_attempt in range(3):
                    try:
                        results = search.get_dict()
                        break
                    except Exception as fetch_error:
                        if fetch_attempt == 2:
                            raise
                        wait_time = min(10.0, (2 ** fetch_attempt) + random.uniform(0.1, 1.0))
                        print(f"[tomo-id-067] SerpAPI page fetch retry scheduled; page={page_num}; attempt={fetch_attempt + 1}; wait_seconds={wait_time:.2f}; error_type={type(fetch_error).__name__}; action=retry_with_backoff")
                        time.sleep(wait_time)
                print(f"[tomo-id-068] Extracting reviews from page {page_num}.")

                if "error" not in results:
                    # Process reviews for current page
                    page_reviews = results.get("reviews", [])
                    
                    for result in page_reviews:
                        try:
                            # Safely extract all fields with proper error handling
                            review_data = {
                                "page": page_num,
                                "name": safe_get_nested(result, "user", "name", default=""),
                                "link": safe_get_nested(result, "user", "link", default=""),
                                "thumbnail": safe_get_nested(result, "user", "thumbnail", default=""),
                                "rating": result.get("rating", None),
                                "date": result.get("date", ""),
                                "snippet": result.get("snippet", ""),
                                "images": result.get("images", []),
                                "local_guide": safe_get_nested(result, "user", "local_guide", default=False),
                                "text": safe_get_nested(result, "extracted_snippet", "original", default=""),
                            }
                            reviews.append(review_data)
                            
                        except Exception as e:
                            error_msg = f"Error processing review on page {page_num}: {e}"
                            print(error_msg)
                            errors.append({
                                "page": page_num,
                                "error": error_msg,
                                "traceback": traceback.format_exc()
                            })
                            
                            # Add partial review data even if there's an error
                            partial_review = {
                                "page": page_num,
                                "name": "",
                                "link": "",
                                "thumbnail": "",
                                "rating": None,
                                "date": "",
                                "snippet": "",
                                "images": [],
                                "local_guide": False,
                                "text": "",
                                "error": str(e)
                            }
                            reviews.append(partial_review)
                            continue
                
                else:
                    error_msg = f"API Error on page {page_num}: {results['error']}"
                    print(error_msg)
                    errors.append({
                        "page": page_num,
                        "error": error_msg,
                        "api_error": results["error"]
                    })
                    break

                # Check for next page
                try:
                    pagination = results.get("serpapi_pagination", {})
                    if pagination.get("next") and pagination.get("next_page_token"):
                        # Update search params for next page
                        next_url = pagination["next"]
                        search.params_dict.update(dict(parse_qsl(urlsplit(next_url).query)))
                    else:
                        print("No more pages to process.")
                        break
                        
                except Exception as e:
                    error_msg = f"Error processing pagination on page {page_num}: {e}"
                    print(error_msg)
                    errors.append({
                        "page": page_num,
                        "error": error_msg,
                        "traceback": traceback.format_exc()
                    })
                    break
                    
            except Exception as e:
                error_msg = f"Error fetching page {page_num}: {e}"
                print(error_msg)
                errors.append({
                    "page": page_num,
                    "error": error_msg,
                    "traceback": traceback.format_exc()
                })
                break
                
    except KeyboardInterrupt:
        print("Process interrupted by user.")
        errors.append({
            "page": page_num,
            "error": "Process interrupted by user",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(error_msg)
        errors.append({
            "error": error_msg,
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        })

    # Prepare final data structure
    final_data = {
        "metadata": {
            "total_reviews": len(reviews),
            "total_pages_processed": page_num,
            "extraction_date": datetime.now().isoformat(),
            "has_errors": len(errors) > 0,
            "error_count": len(errors)
        },
        "reviews": reviews,
        "errors": errors
    }

    # Save data to JSON file
    saved_file = save_data_to_json(final_data)
    
    # Print summary
    print(f"\n=== EXTRACTION SUMMARY ===")
    print(f"Total reviews extracted: {len(reviews)}")
    print(f"Total pages processed: {page_num}")
    print(f"Errors encountered: {len(errors)}")
    if saved_file:
        print(f"Data saved to: {saved_file}")
    
    # Also print the JSON to console (optional, you can remove this if files get too large)
    print(f"\n=== JSON OUTPUT ===")
    # print(json.dumps(final_data, indent=2, ensure_ascii=False))
    
    return final_data

if __name__ == "__main__":
    try:
        data = extract_reviews()
    except Exception as e:
        print(f"Critical error: {e}")
        traceback.print_exc()
        # Save whatever we can in case of critical failure
        emergency_data = {
            "critical_error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }
        save_data_to_json(emergency_data, "emergency_backup")