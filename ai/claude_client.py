import anthropic
import json
import logging
import time
from typing import Dict, Any, List, Optional
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClaudeClient:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.model = Config.CLAUDE_MODEL
        
    def _make_api_call(self, messages, system_prompt=None, max_tokens=1000, temperature=0.1, retries=3):
        """Make API call with retry logic"""
        for attempt in range(retries):
            try:
                kwargs = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": messages
                }
                
                if system_prompt:
                    kwargs["system"] = system_prompt
                
                response = self.client.messages.create(**kwargs)
                return response
                
            except Exception as e:
                logger.error(f"API call failed (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
        
    def generate_sql_query(self, user_query: str, table_schema: List[Dict[str, Any]]) -> str:
        """Generate SQL query from natural language using Claude with simplified columns"""
        
        try:
            # Define the simplified schema for the AI
            simplified_schema = [
                {"column": "DATE", "type": "DATE", "description": "Date of the data"},
                {"column": "SEARCH_QUERY", "type": "VARCHAR", "description": "The search keyword"},
                {"column": "SEARCH_QUERY_SCORE", "type": "NUMBER", "description": "Search volume score"},
                {"column": "SEARCH_QUERY_VOLUME", "type": "NUMBER", "description": "Number of times keyword was searched"},
                {"column": "Impressions: Total Count", "type": "NUMBER", "description": "Total impressions for the keyword"},
                {"column": "Clicks: Total Count", "type": "NUMBER", "description": "Total clicks for the keyword"},
                {"column": "Cart Adds: Total Count", "type": "NUMBER", "description": "Total cart additions for the keyword"},
                {"column": "Purchases: Total Count", "type": "NUMBER", "description": "Total purchases for the keyword"}
            ]
            
            schema_info = "\n".join([f"- {col['column']} ({col['type']}) - {col['description']}" for col in simplified_schema])
            
            system_prompt = f"""You are an expert SQL analyst specializing in Amazon keyword performance data. 
            
            Table Schema for {Config.KEYWORD_TABLE}:
            {schema_info}
            
            Your task is to convert natural language queries into accurate SQL queries. 
            
            Rules:
            1. Always use proper SQL syntax for Snowflake
            2. Include appropriate WHERE clauses for filtering
            3. Use ORDER BY for sorting when relevant
            4. Calculate derived metrics like CTR (clicks/impressions) and conversion rate (purchases/clicks)
            5. Handle division by zero with CASE statements
            6. Return only the SQL query, no explanations
            7. Use the exact column names from the schema (with quotes for columns with spaces)
            8. For CTR: CASE WHEN "Impressions: Total Count" > 0 THEN "Clicks: Total Count" / "Impressions: Total Count" ELSE 0 END
            9. For conversion rate: CASE WHEN "Clicks: Total Count" > 0 THEN "Purchases: Total Count" / "Clicks: Total Count" ELSE 0 END
            10. For cart add rate: CASE WHEN "Clicks: Total Count" > 0 THEN "Cart Adds: Total Count" / "Clicks: Total Count" ELSE 0 END
            11. LIMIT rules:
                - If user specifies a number (e.g., "top 20", "show 5"), use that number
                - If user says "top" without a number, use LIMIT 10
                - If no limit mentioned, use LIMIT 10 as default
                - Maximum limit is 100
            
            Example queries:
            - "top 10 keywords by purchases" → "SELECT SEARCH_QUERY, \"Purchases: Total Count\" FROM {Config.KEYWORD_TABLE} ORDER BY \"Purchases: Total Count\" DESC LIMIT 10"
            - "top 20 keywords by clicks" → "SELECT SEARCH_QUERY, \"Clicks: Total Count\" FROM {Config.KEYWORD_TABLE} ORDER BY \"Clicks: Total Count\" DESC LIMIT 20"
            - "show top 5 keywords" → "SELECT SEARCH_QUERY, \"Purchases: Total Count\" FROM {Config.KEYWORD_TABLE} ORDER BY \"Purchases: Total Count\" DESC LIMIT 5"
            - "keywords with high conversion rate" → "SELECT SEARCH_QUERY, CASE WHEN \"Clicks: Total Count\" > 0 THEN \"Purchases: Total Count\" / \"Clicks: Total Count\" ELSE 0 END as conversion_rate FROM {Config.KEYWORD_TABLE} WHERE \"Clicks: Total Count\" > 0 ORDER BY conversion_rate DESC LIMIT 10"
            - "keywords with low CTR" → "SELECT SEARCH_QUERY, CASE WHEN \"Impressions: Total Count\" > 0 THEN \"Clicks: Total Count\" / \"Impressions: Total Count\" ELSE 0 END as ctr FROM {Config.KEYWORD_TABLE} WHERE \"Impressions: Total Count\" > 100 ORDER BY ctr ASC LIMIT 10"
            """
            
            response = self._make_api_call(
                messages=[{"role": "user", "content": f"Convert this query to SQL: {user_query}"}],
                system_prompt=system_prompt,
                max_tokens=1000,
                temperature=0.1
            )
            
            # Defensive: Check response structure
            sql_query = ""
            if response and hasattr(response, 'content') and response.content:
                sql_query = response.content[0].text.strip()
            else:
                logger.error(f"Claude API returned unexpected response: {response}")
                return ""
            
            # Clean up the response to extract just the SQL
            if sql_query.startswith("```sql"):
                sql_query = sql_query[6:]
            if sql_query.endswith("```"):
                sql_query = sql_query[:-3]
            
            return sql_query.strip()
            
        except Exception as e:
            logger.error(f"Error generating SQL query: {e}")
            return ""
    
    def analyze_data(self, user_query: str, data: Dict[str, Any]) -> str:
        """Analyze data and provide insights using Claude"""
        
        try:
            # Convert data to readable format
            if isinstance(data, dict) and 'data' in data:
                df_data = data['data']
                if hasattr(df_data, 'to_dict'):
                    data_str = df_data.to_dict('records')
                else:
                    data_str = str(df_data)
            else:
                data_str = str(data)
            
            system_prompt = """You are an expert Amazon PPC analyst. Analyze the provided keyword performance data and provide actionable insights.

            Focus on:
            1. Performance trends and patterns
            2. Opportunities for optimization
            3. Underperforming keywords that need attention
            4. Recommendations for budget allocation
            5. Seasonal or temporal patterns
            
            Provide clear, actionable insights in a business-friendly format.
            """
            
            response = self._make_api_call(
                messages=[{
                    "role": "user",
                    "content": f"User Question: {user_query}\n\nData: {data_str}\n\nPlease analyze this data and provide insights."
                }],
                system_prompt=system_prompt,
                max_tokens=2000,
                temperature=0.3
            )
            
            if response and hasattr(response, 'content') and response.content:
                return response.content[0].text
            else:
                logger.error(f"Claude API returned unexpected response: {response}")
                return "Sorry, I encountered an error while analyzing the data: Unexpected Claude API response."
            
        except Exception as e:
            logger.error(f"Error analyzing data: {e}")
            return f"Sorry, I encountered an error while analyzing the data: {str(e)}"
    
    def generate_insights(self, query_results: Dict[str, Any]) -> str:
        """Generate insights from query results"""
        
        try:
            system_prompt = """You are a data analyst specializing in Amazon keyword performance. 
            Analyze the provided data and generate actionable business insights.
            
            Focus on:
            - Key performance indicators
            - Trends and patterns
            - Optimization opportunities
            - Recommendations for improvement
            
            Provide insights in a clear, structured format.
            """
            
            data_summary = str(query_results)
            
            response = self._make_api_call(
                messages=[{
                    "role": "user",
                    "content": f"Please analyze this keyword performance data and provide insights:\n\n{data_summary}"
                }],
                system_prompt=system_prompt,
                max_tokens=1500,
                temperature=0.2
            )
            
            if response and hasattr(response, 'content') and response.content:
                return response.content[0].text
            else:
                logger.error(f"Claude API returned unexpected response: {response}")
                return "Unable to generate insights at this time. Claude API response was unexpected."
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return "Unable to generate insights at this time."
    
    def understand_query_intent(self, user_query: str) -> Dict[str, Any]:
        """Understand the intent and type of query"""
        
        try:
            system_prompt = """Analyze the user's query about Amazon keyword performance data and classify its intent.

            Query Types:
            1. PERFORMANCE_ANALYSIS - Questions about performance metrics, trends, comparisons
            2. KEYWORD_SEARCH - Looking for specific keywords or keyword patterns
            3. OPTIMIZATION - Questions about improving performance, recommendations
            4. SUMMARY - General overview, top performers, statistics
            5. TREND_ANALYSIS - Time-based analysis, seasonal patterns
            
            Return a JSON object with:
            {
                "intent": "query_type",
                "confidence": 0.0-1.0,
                "entities": ["keyword", "metric", "time_period"],
                "requires_sql": true/false
            }
            """
            
            response = self._make_api_call(
                messages=[{"role": "user", "content": f"Classify this query: {user_query}"}],
                system_prompt=system_prompt,
                max_tokens=500,
                temperature=0.1
            )
            
            result_text = ""
            if response and hasattr(response, 'content') and response.content:
                result_text = response.content[0].text.strip()
            else:
                logger.error(f"Claude API returned unexpected response: {response}")
                return {
                    "intent": "PERFORMANCE_ANALYSIS",
                    "confidence": 0.5,
                    "entities": [],
                    "requires_sql": True
                }
                
            # Try to parse JSON response
            try:
                return json.loads(result_text)
            except json.JSONDecodeError:
                # Fallback to simple classification
                return {
                    "intent": "PERFORMANCE_ANALYSIS",
                    "confidence": 0.8,
                    "entities": [],
                    "requires_sql": True
                }
                
        except Exception as e:
            logger.error(f"Error understanding query intent: {e}")
            return {
                "intent": "PERFORMANCE_ANALYSIS",
                "confidence": 0.5,
                "entities": [],
                "requires_sql": True
            }
    
    def generate_simple_response(self, user_query: str, data: Dict[str, Any]) -> str:
        """Generate a simple, concise response for simple mode"""
        
        try:
            # Convert data to readable format
            if isinstance(data, dict) and 'data' in data:
                df_data = data['data']
                if hasattr(df_data, 'to_dict'):
                    data_str = df_data.to_dict('records')
                else:
                    data_str = str(df_data)
            else:
                data_str = str(data)
            
            system_prompt = """You are an expert Amazon PPC analyst. Provide simple, direct answers to questions about keyword performance data.

            Guidelines for simple mode:
            1. Keep responses concise (1-3 sentences maximum)
            2. Focus on the most important information
            3. Use simple language
            4. Provide yes/no answers when possible
            5. Include key numbers/percentages if relevant
            6. Avoid lengthy explanations or recommendations
            
            Format: Direct answer with key data points if available.
            """
            
            response = self._make_api_call(
                messages=[{
                    "role": "user",
                    "content": f"Question: {user_query}\n\nData: {data_str}\n\nProvide a simple, direct answer."
                }],
                system_prompt=system_prompt,
                max_tokens=300,  # Shorter for simple mode
                temperature=0.1
            )
            
            if response and hasattr(response, 'content') and response.content:
                return response.content[0].text.strip()
            else:
                logger.error(f"Claude API returned unexpected response: {response}")
                return "I found some data but couldn't provide a simple answer."
            
        except Exception as e:
            logger.error(f"Error generating simple response: {e}")
            return "I found some data but couldn't provide a simple answer."
    
    def translate_text(self, text: str, target_language: str) -> str:
        """Translate text to the target language using Claude AI"""
        
        try:
            system_prompt = f"""You are a professional translator. Translate the given text to {target_language}.

            Guidelines:
            1. Maintain the original meaning and tone
            2. Preserve any technical terms appropriately
            3. Keep the same formatting and structure
            4. If the text contains data or numbers, keep them as is
            5. Translate business and technical terms accurately
            6. Return only the translated text, no explanations
            
            Target language: {target_language}
            """
            
            response = self._make_api_call(
                messages=[{
                    "role": "user",
                    "content": f"Translate this text to {target_language}:\n\n{text}"
                }],
                system_prompt=system_prompt,
                max_tokens=1000,
                temperature=0.1
            )
            
            if response and hasattr(response, 'content') and response.content:
                return response.content[0].text.strip()
            else:
                logger.error(f"Claude API returned unexpected response for translation: {response}")
                return text  # Return original text if translation fails
            
        except Exception as e:
            logger.error(f"Error translating text: {e}")
            return text  # Return original text if translation fails 