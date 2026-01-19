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

def save_data_to_json(data, filename_prefix="reviews_data"):
    """Save data to JSON file with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.json"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Data saved to {filename}")
        return filename
    except Exception as e:
        print(f"Error saving to file {filename}: {e}")
        return None

def extract_reviews():
    params = {
        "api_key": "your_serp_api_key",
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
                results = search.get_dict()
                print(f"Extracting reviews from page {page_num}.")

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