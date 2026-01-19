import json
import openai
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any
import os
from pathlib import Path
import re


def chunk_list(lst, chunk_size):
    """Yield successive chunks of size chunk_size from list"""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]


class ReviewSentimentAnalyzer:
    def __init__(self, openai_api_key: str):
        """Initialize the analyzer with OpenAI API key"""
        self.client = openai.OpenAI(api_key=openai_api_key)
        
        # Define sentiment analysis dimensions
        self.analysis_dimensions = [
            "Service Quality",
            "Facility Experience", 
            "Clinical Care",
            "Operations",
            "Trust & Safety"
        ]
    
    def _clean_openai_response(self, response_text: str) -> str:
        """Clean OpenAI response to extract valid JSON"""
        if not response_text or not response_text.strip():
            raise ValueError("Empty response from OpenAI")
        
        # Remove common prefixes that OpenAI might add
        prefixes_to_remove = [
            "Here's the analysis:",
            "Here is the analysis:",
            "Analysis:",
            "```json",
            "```"
        ]
        
        cleaned = response_text.strip()
        
        # Remove prefixes
        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):].strip()
        
        # Remove trailing ```
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
        
        # Try to find JSON boundaries
        json_start = cleaned.find('{')
        json_end = cleaned.rfind('}')
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            cleaned = cleaned[json_start:json_end+1]
        
        return cleaned
    
    def _extract_review_id(self, review: Dict[str, Any]) -> str:
        """Extract review ID from the review link or generate one"""
        link = review.get('link', '')
        if link:
            match = re.search(r'/contrib/(\d+)', link)
            if match:
                return match.group(1)
        
        # Fallback: generate ID from name and date
        name = review.get('name', 'unknown')
        date = review.get('date', 'unknown')
        return f"{name}_{date}".replace(' ', '_').replace('/', '_')

    
    def analyze_single_review(self, review: Dict[str, Any], retry_count: int = 2) -> Dict[str, Any]:
        """Analyze sentiment for a single review with retry logic"""
        
        review_text = review.get('text', '')
        rating = review.get('rating', 0)
        
        # Check if the text appears to be in Arabic
        has_arabic = bool(re.search(r'[\u0600-\u06FF]', review_text))
        
        prompt = f"""
Analyze this review using both the review text and rating to provide comprehensive sentiment analysis:

**Input:**
- Review Text: "{review_text}"
- Rating: {rating}/5
- Language: {"Arabic" if has_arabic else "English/Other"}

**Analysis Instructions:**

1. **Primary Classification:**
   - If review text exists: Analyze both text sentiment and rating
   - If review text is empty: Base classification solely on rating
   - Rating scale: 1-2 (negative), 3 (neutral), 4-5 (positive)

2. **Language Handling:**
   - If the review is in Arabic, analyze it in Arabic but respond in English
   - Preserve original Arabic text meaning in the analysis
   - Key points should reflect the original Arabic sentiment

3. **Conflict Detection:**
   - If text sentiment contradicts rating, classify as "doubtful"
   - Consider rating vs text sentiment alignment

4. **Sentiment Dimensions Analysis:**
   Identify which dimensions are mentioned:
   - **Service Quality**: Staff behavior, communication, responsiveness
   - **Facility Experience**: Cleanliness, infrastructure, amenities
   - **Clinical Care**: Treatment quality, medical outcomes
   - **Operations**: Scheduling, billing, administrative processes
   - **Trust & Safety**: Safety protocols, privacy, reliability

RESPOND WITH ONLY VALID JSON IN THIS EXACT FORMAT:
{{
  "text": Actual Text you reviewd,  
  "sentiment": "positive/negative/neutral/doubtful",
  "confidence": 0.0,
  "sentiment_score": 0.0,
  "dimensions": [
    {{
      "name": "dimension_name",
      "sentiment": "positive/negative/neutral",
      "key_points": ["point1", "point2"]
    }}
  ],
  "key_themes": ["theme1", "theme2"],
  "severity": 0,
  "summary": "Brief analysis summary"
}}

**Guidelines:**
- sentiment_score: -1.0 (very negative) to +1.0 (very positive)
- confidence: 0.0 to 1.0 (certainty in classification)
- severity: 1-5 (only for negative sentiment, 1=minor, 5=critical)
- Include only relevant dimensions that are actually mentioned
- If no text, note "Analysis based on rating only" in summary
- For Arabic text, ensure analysis captures cultural context
"""

        for attempt in range(retry_count + 1):
            try:
                # Add exponential backoff for retries
                if attempt > 0:
                    wait_time = (2 ** attempt) + 1
                    print(f"  Retrying in {wait_time} seconds... (attempt {attempt + 1})")
                    time.sleep(wait_time)
                
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system", 
                            "content": "You are an expert sentiment analyst fluent in both Arabic and English. Respond with ONLY valid JSON. No explanatory text before or after the JSON."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
                
                # Get raw response
                raw_response = response.choices[0].message.content
                if not raw_response:
                    raise ValueError("Empty response from OpenAI")
                
                # Clean and parse the JSON response
                cleaned_response = self._clean_openai_response(raw_response)
                analysis_result = json.loads(cleaned_response)
                
                # Validate required fields
                required_fields = ['sentiment', 'confidence', 'sentiment_score', 'dimensions', 'key_themes', 'severity', 'summary']
                for field in required_fields:
                    if field not in analysis_result:
                        analysis_result[field] = [] if field in ['dimensions', 'key_themes'] else 0 if field in ['confidence', 'sentiment_score', 'severity'] else 'unknown'
                
                # Extract review ID
                review_id = self._extract_review_id(review)
                
                # Add original review data to the result in the expected format
                result = {
                    "review_id": review_id,
                    "author": review.get('name', ''),
                    "rating": rating,
                    "text": review_text,  # Preserve original text (Arabic or English)
                    "date": review.get('date', ''),
                    "images": review.get('images', []),  # Include images if available
                    "analysis": analysis_result,
                    "processed_at": datetime.now().isoformat()
                }
                
                return result
                
            except json.JSONDecodeError as e:
                error_msg = f"JSON parsing error (attempt {attempt + 1}): {e}"
                if attempt < retry_count:
                    print(f"  {error_msg}, retrying...")
                    continue
                else:
                    print(f"  {error_msg}, using fallback")
                    return self._create_fallback_analysis(review, error_msg)
                    
            except Exception as e:
                error_msg = f"API error (attempt {attempt + 1}): {e}"
                if attempt < retry_count:
                    print(f"  {error_msg}, retrying...")
                    continue
                else:
                    print(f"  {error_msg}, using fallback")
                    return self._create_fallback_analysis(review, error_msg)
    
    def _create_fallback_analysis(self, review: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
        """Create a fallback analysis when API call fails"""
        rating = review.get('rating', 0)
        
        # Simple rating-based sentiment
        if rating >= 4:
            sentiment = "positive"
            sentiment_score = 0.5
        elif rating <= 2:
            sentiment = "negative"
            sentiment_score = -0.5
        else:
            sentiment = "neutral"
            sentiment_score = 0.0
        
        review_id = self._extract_review_id(review)
        
        return {
            "review_id": review_id,
            "author": review.get('name', ''),
            "rating": rating,
            "text": review.get('text', ''),
            "date": review.get('date', ''),
            "images": review.get('images', []),
            "analysis": {
                "sentiment": sentiment,
                "confidence": 0.3,
                "sentiment_score": sentiment_score,
                "dimensions": [],
                "key_themes": [],
                "severity": 0,
                "summary": f"Fallback analysis based on rating only. Error: {error_msg}"
            },
            "processed_at": datetime.now().isoformat(),
            "error": error_msg
        }
    
    def generate_sentiment_summaries(self, analyzed_reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate AI-powered summaries for positive and negative reviews"""
        
        print("Generating sentiment summaries...")
        
        summaries = {}
        
        # Process positive and negative reviews
        for sentiment_type in ['positive', 'negative']:
            filtered_reviews = [r for r in analyzed_reviews if r.get('analysis', {}).get('sentiment') == sentiment_type]
            
            if not filtered_reviews:
                summaries[sentiment_type] = {
                    "summary": f"No {sentiment_type} reviews found.",
                    "key_insights": [],
                    "recommendations": []
                }
                continue
            
            # Prepare data for summary generation
            dimensions_data = {}
            all_key_points = []
            
            for review in filtered_reviews:
                analysis = review.get('analysis', {})
                dimensions = analysis.get('dimensions', [])
                
                for dim in dimensions:
                    dim_name = dim.get('name', 'Unknown')
                    dim_sentiment = dim.get('sentiment', sentiment_type)
                    key_points = dim.get('key_points', [])
                    
                    if dim_name not in dimensions_data:
                        dimensions_data[dim_name] = {
                            'count': 0,
                            'key_points': [],
                            'sentiment': dim_sentiment
                        }
                    
                    dimensions_data[dim_name]['count'] += 1
                    dimensions_data[dim_name]['key_points'].extend(key_points)
                    all_key_points.extend(key_points)
            
            # Create summary prompt
            summary_prompt = f"""
Based on the following {sentiment_type} review analysis, generate a comprehensive summary:

**Review Count:** {len(filtered_reviews)}

**Dimension Breakdown:**
{json.dumps(dimensions_data, indent=2)}

**All Key Points:**
{all_key_points[:50]}  # Limit to avoid token limits

Generate a summary in the following JSON format:
{{
  "summary": "Brief overview of {sentiment_type} feedback",
  "key_insights": [
    "Insight 1",
    "Insight 2",
    "Insight 3",
    "Insight 4",
    "Insight 5",
    "Insight 6",
    "Insight 7",
    "Insight 8",
    "Insight 9",
    "Insight 10"
  ],
  "recommendations": [
    "Recommendation 1",
    "Recommendation 2", 
    "Recommendation 3",
    "Recommendation 4",
    "Recommendation 5",
    "Recommendation 6",
    "Recommendation 7",
    "Recommendation 8",
    "Recommendation 9",
    "Recommendation 10"
  ]
}}

**Guidelines:**
- For positive reviews: Focus on strengths to maintain and areas of excellence
- For negative reviews: Focus on improvement areas and actionable recommendations
- Keep insights concise and actionable
- Base recommendations on the most frequent issues/strengths
- Consider both Arabic and English review contexts
"""
            
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert healthcare analyst fluent in Arabic and English. Generate concise, actionable summaries in valid JSON format only."
                        },
                        {
                            "role": "user",
                            "content": summary_prompt
                        }
                    ],
                    temperature=0.3,
                    max_tokens=800
                )
                
                raw_response = response.choices[0].message.content
                cleaned_response = self._clean_openai_response(raw_response)
                summary_result = json.loads(cleaned_response)
                
                summaries[sentiment_type] = summary_result
                
            except Exception as e:
                print(f"Error generating {sentiment_type} summary: {e}")
                summaries[sentiment_type] = {
                    "summary": f"Error generating {sentiment_type} summary: {str(e)}",
                    "key_insights": [f"Analysis failed for {len(filtered_reviews)} {sentiment_type} reviews"],
                    "recommendations": ["Manual review recommended due to analysis failure"]
                }
        
        return summaries

    def generate_dimension_summaries(self, analyzed_reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate AI-powered dimension-wise summaries for positive and negative sentiments"""
        
        print("Generating dimension-wise summaries...")
        
        dimension_summaries = {}
        
        for dimension in self.analysis_dimensions:
            dimension_summaries[dimension] = {}
            
            for sentiment_type in ['positive', 'negative']:
                key_points = []
                review_count = 0
                
                for review in analyzed_reviews:
                    analysis = review.get('analysis', {})
                    dimensions = analysis.get('dimensions', [])
                    
                    for dim in dimensions:
                        if dim.get('name') == dimension and dim.get('sentiment') == sentiment_type:
                            key_points.extend(dim.get('key_points', []))
                            review_count += 1  # Count unique reviews mentioning this
                
                if review_count == 0:
                    dimension_summaries[dimension][sentiment_type] = {
                        "review_count": 0,
                        "summary": f"No {sentiment_type} mentions found for {dimension}.",
                        "key_insights": [],
                        "recommendations": []
                    }
                    continue
                
                # Create summary prompt
                summary_prompt = f"""
Based on the following {sentiment_type} mentions in the {dimension} dimension:

**Review Count:** {review_count}

**All Key Points:**
{key_points[:50]}  # Limit to avoid token limits

Generate a summary in the following JSON format:
{{
  "summary": "Brief overview of {sentiment_type} feedback in {dimension}",
  "key_insights": [
    "Insight 1",
    "Insight 2",
    "Insight 3",
    "Insight 4",
    "Insight 5",
    "Insight 6",
    "Insight 7",
    "Insight 8",
    "Insight 9",
    "Insight 10"
  ],
  "recommendations": [
    "Recommendation 1",
    "Recommendation 2", 
    "Recommendation 3",
    "Recommendation 4",
    "Recommendation 5",
    "Recommendation 6",
    "Recommendation 7",
    "Recommendation 8",
    "Recommendation 9",
    "Recommendation 10"
  ]
}}

**Guidelines:**
- For positive: Focus on strengths to maintain and areas of excellence
- For negative: Focus on improvement areas and actionable recommendations
- Keep insights concise and actionable
- Base recommendations on the most frequent issues/strengths
- Consider both Arabic and English review contexts
- Limit to 5-10 insights and recommendations
"""
                
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an expert healthcare analyst fluent in Arabic and English. Generate concise, actionable summaries in valid JSON format only."
                            },
                            {
                                "role": "user",
                                "content": summary_prompt
                            }
                        ],
                        temperature=0.3,
                        max_tokens=800
                    )
                    
                    raw_response = response.choices[0].message.content
                    cleaned_response = self._clean_openai_response(raw_response)
                    summary_result = json.loads(cleaned_response)
                    
                    summary_result["review_count"] = review_count
                    dimension_summaries[dimension][sentiment_type] = summary_result
                    
                except Exception as e:
                    print(f"Error generating {sentiment_type} summary for {dimension}: {e}")
                    dimension_summaries[dimension][sentiment_type] = {
                        "review_count": review_count,
                        "summary": f"Error generating {sentiment_type} summary for {dimension}: {str(e)}",
                        "key_insights": [f"Analysis failed for {review_count} {sentiment_type} mentions in {dimension}"],
                        "recommendations": ["Manual review recommended due to analysis failure"]
                    }
        
        return dimension_summaries
    
    def batch_analyze_reviews(self, reviews: List[Dict[str, Any]], 
                            rate_limit_delay: float = 1.0) -> Dict[str, Any]:
        """Analyze multiple reviews and generate comprehensive report"""
        
        print(f"Starting analysis of {len(reviews)} reviews...")
        
        analyzed_reviews = []
        failed_count = 0
        
        for i, review in enumerate(reviews):
            print(f"Processing review {i+1}/{len(reviews)}")
            
            result = self.analyze_single_review(review)
            analyzed_reviews.append(result)
            
            if 'error' in result:
                failed_count += 1
            
            # Rate limiting to avoid API limits
            if i < len(reviews) - 1:  # Don't sleep after last review
                time.sleep(rate_limit_delay)
        
        # Generate summary statistics
        summary_stats = self._generate_summary_stats(analyzed_reviews)
        
        # Generate AI-powered sentiment summaries
        sentiment_summaries = self.generate_sentiment_summaries(analyzed_reviews)
        
        # Generate AI-powered dimension summaries
        dimension_summaries = self.generate_dimension_summaries(analyzed_reviews)
        
        # Create final output structure
        output = {
            "metadata": {
                "total_reviews": len(reviews),
                "successfully_analyzed": len(analyzed_reviews) - failed_count,
                "failed_analyses": failed_count,
                "analysis_date": datetime.now().isoformat(),
                "processing_time_per_review": rate_limit_delay
            },
            "summary_statistics": summary_stats,
            "sentiment_summaries": sentiment_summaries,
            "dimension_summaries": dimension_summaries,
            "analyzed_reviews": analyzed_reviews
        }
        
        return output
    
    def _generate_summary_stats(self, analyzed_reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics from analyzed reviews"""
        
        total_reviews = len(analyzed_reviews)
        if total_reviews == 0:
            return {}
        
        # Count sentiment distribution
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0, "doubtful": 0}
        sentiment_scores = []
        all_themes = []
        dimension_mentions = {}
        severity_scores = []
        rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        for review in analyzed_reviews:
            analysis = review.get('analysis', {})
            
            # Sentiment distribution
            sentiment = analysis.get('sentiment', 'neutral')
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
            
            # Sentiment scores
            if 'sentiment_score' in analysis:
                sentiment_scores.append(analysis['sentiment_score'])
            
            # Themes
            themes = analysis.get('key_themes', [])
            all_themes.extend(themes)
            
            # Dimensions
            dimensions = analysis.get('dimensions', [])
            for dim in dimensions:
                dim_name = dim.get('name', '')
                if dim_name:
                    dimension_mentions[dim_name] = dimension_mentions.get(dim_name, 0) + 1
            
            # Severity (for negative reviews)
            if sentiment == 'negative' and 'severity' in analysis:
                severity_scores.append(analysis['severity'])
            
            # Rating distribution
            rating = review.get('rating', 0)
            if 1 <= rating <= 5:
                rating_distribution[rating] += 1
        
        # Calculate percentages
        sentiment_percentages = {
            k: round((v / total_reviews) * 100, 2) 
            for k, v in sentiment_counts.items()
        }
        
        # Most common themes
        theme_counts = {}
        for theme in all_themes:
            theme_counts[theme] = theme_counts.get(theme, 0) + 1
        
        top_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Most mentioned dimensions
        top_dimensions = sorted(dimension_mentions.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "sentiment_distribution": {
                "counts": sentiment_counts,
                "percentages": sentiment_percentages
            },
            "average_sentiment_score": round(sum(sentiment_scores) / len(sentiment_scores), 3) if sentiment_scores else 0,
            "rating_distribution": rating_distribution,
            "average_rating": round(sum(k * v for k, v in rating_distribution.items()) / total_reviews, 2),
            "top_themes": top_themes,
            "top_dimensions": top_dimensions,
            "average_severity": round(sum(severity_scores) / len(severity_scores), 2) if severity_scores else 0,
            "high_severity_count": len([s for s in severity_scores if s >= 4])
        }

def load_reviews_from_file(file_path: str) -> List[Dict[str, Any]]:
    """Load reviews from JSON file - handles the new input format"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle the new JSON structure
        if isinstance(data, dict) and 'reviews' in data:
            # New format: {"metadata": {...}, "reviews": [...]}
            reviews = data['reviews']
            print(f"Loaded {len(reviews)} reviews from new format")
            return reviews
        elif isinstance(data, list):
            # Old format: direct list of reviews
            return data
        elif isinstance(data, dict):
            # If it's a dict, look for other common keys that might contain reviews
            for key in ['data', 'items']:
                if key in data and isinstance(data[key], list):
                    return data[key]
            # If no common key found, treat the dict as a single review
            return [data]
        else:
            raise ValueError("Invalid JSON structure")
            
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON file: {file_path}")

def save_analysis_results(results: Dict[str, Any], output_path: str):
    """Save analysis results to JSON file"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Analysis results saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Analyze sentiment of reviews using OpenAI API')
    parser.add_argument('input_file', help='Path to input JSON file containing reviews')
    parser.add_argument('-o', '--output', help='Output file path (default: analysis_results.json)', 
                       default='analysis_results.json')
    parser.add_argument('-k', '--api-key', help='OpenAI API key (or set OPENAI_API_KEY env var)')
    parser.add_argument('-d', '--delay', type=float, default=1.0, 
                       help='Delay between API calls in seconds (default: 1.0)')
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OpenAI API key is required. Set OPENAI_API_KEY environment variable or use -k flag.")
        return
    
    try:
        # Load reviews
        print(f"Loading reviews from: {args.input_file}")
        reviews = load_reviews_from_file(args.input_file)
        print(f"Loaded {len(reviews)} reviews")
        
        # Initialize analyzer
        analyzer = ReviewSentimentAnalyzer(api_key)
        
        # Analyze reviews
        results = analyzer.batch_analyze_reviews(reviews, rate_limit_delay=args.delay)
        
        # Save results
        save_analysis_results(results, args.output)
        
        # Print summary
        stats = results['summary_statistics']
        summaries = results.get('sentiment_summaries', {})
        dimension_summaries = results.get('dimension_summaries', {})
        
        print("\n" + "="*50)
        print("ANALYSIS SUMMARY")
        print("="*50)
        print(f"Total Reviews: {results['metadata']['total_reviews']}")
        print(f"Successfully Analyzed: {results['metadata']['successfully_analyzed']}")
        print(f"Failed Analyses: {results['metadata']['failed_analyses']}")
        print(f"Average Rating: {stats.get('average_rating', 0)}/5")
        print(f"Average Sentiment Score: {stats.get('average_sentiment_score', 0)}")
        
        print("\nSentiment Distribution:")
        for sentiment, percentage in stats.get('sentiment_distribution', {}).get('percentages', {}).items():
            print(f"  {sentiment.title()}: {percentage}%")
        
        print(f"\nTop Themes:")
        for theme, count in stats.get('top_themes', [])[:5]:
            print(f"  {theme}: {count} mentions")
        
        # Print AI-generated overall summaries
        if summaries:
            print(f"\nOVERALL SENTIMENT INSIGHTS:")
            for sentiment_type, summary_data in summaries.items():
                print(f"\n{sentiment_type.upper()} REVIEWS:")
                print(f"  Summary: {summary_data.get('summary', 'N/A')}")
                print(f"  Key Insights:")
                for insight in summary_data.get('key_insights', [])[:3]:  # Show first 3 insights
                    print(f"    • {insight}")
        
        # Print dimension-wise summaries
        if dimension_summaries:
            print(f"\nDIMENSION-WISE INSIGHTS:")
            for dimension, sentiment_data in dimension_summaries.items():
                print(f"\n{dimension.upper()}:")
                for sentiment_type in ['positive', 'negative']:
                    if sentiment_type in sentiment_data:
                        data = sentiment_data[sentiment_type]
                        review_count = data.get('review_count', 0)
                        if review_count > 0:
                            print(f"  {sentiment_type.title()} ({review_count} reviews):")
                            print(f"    Summary: {data.get('summary', 'N/A')}")
                            insights = data.get('key_insights', [])
                            if insights:
                                print(f"    Top Insight: {insights[0]}")
        
        print(f"\nResults saved to: {args.output}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()