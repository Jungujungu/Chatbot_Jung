import snowflake.connector
import pandas as pd
from typing import Optional, List, Dict, Any
import logging
import time
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SnowflakeClient:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Establish connection to Snowflake with retry logic"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect to Snowflake (attempt {attempt + 1}/{max_retries})")
                
                self.connection = snowflake.connector.connect(
                    account=Config.SNOWFLAKE_ACCOUNT,
                    user=Config.SNOWFLAKE_USER,
                    password=Config.SNOWFLAKE_PASSWORD,
                    warehouse=Config.SNOWFLAKE_WAREHOUSE,
                    database=Config.SNOWFLAKE_DATABASE,
                    schema=Config.SNOWFLAKE_SCHEMA,
                    # Add connection parameters for better stability
                    client_session_keep_alive=True,
                    login_timeout=60,
                    network_timeout=60
                )
                logger.info("Successfully connected to Snowflake")
                return
                
            except Exception as e:
                logger.error(f"Failed to connect to Snowflake (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise ConnectionError(f"Failed to connect to Snowflake after {max_retries} attempts: {e}")
    
    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute a SQL query and return results as DataFrame"""
        try:
            if not self.connection:
                logger.info("Connection lost, reconnecting...")
                self.connect()
            
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            # Fetch results
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            df = pd.DataFrame(results, columns=columns)
            cursor.close()
            
            return df
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            logger.error(f"Query: {query}")
            raise
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get schema information for a table"""
        query = f"""
        DESCRIBE TABLE {table_name}
        """
        try:
            df = self.execute_query(query)
            schema = []
            for _, row in df.iterrows():
                schema.append({
                    'column': row['name'],
                    'type': row['type'],
                    'nullable': row['null?'] == 'Y'
                })
            return schema
        except Exception as e:
            logger.error(f"Error getting schema for {table_name}: {e}")
            return []
    
    def get_sample_data(self, table_name: str, limit: int = 10) -> pd.DataFrame:
        """Get sample data from a table"""
        query = f"""
        SELECT * FROM {table_name}
        LIMIT {limit}
        """
        return self.execute_query(query)
    
    def get_keyword_performance_summary(self) -> Dict[str, Any]:
        """Get summary statistics for keyword performance using simplified columns"""
        try:
            query = f"""
            SELECT 
                COUNT(*) as total_keywords,
                SUM("Impressions: Total Count") as total_impressions,
                SUM("Clicks: Total Count") as total_clicks,
                SUM("Cart Adds: Total Count") as total_cart_adds,
                SUM("Purchases: Total Count") as total_purchases,
                AVG("Impressions: Total Count") as avg_impressions,
                AVG("Clicks: Total Count") as avg_clicks,
                AVG("Cart Adds: Total Count") as avg_cart_adds,
                AVG("Purchases: Total Count") as avg_purchases,
                AVG(CASE WHEN "Impressions: Total Count" > 0 
                    THEN "Clicks: Total Count" / "Impressions: Total Count" 
                    ELSE 0 END) as avg_ctr,
                AVG(CASE WHEN "Clicks: Total Count" > 0 
                    THEN "Purchases: Total Count" / "Clicks: Total Count" 
                    ELSE 0 END) as avg_conversion_rate,
                AVG(CASE WHEN "Clicks: Total Count" > 0 
                    THEN "Cart Adds: Total Count" / "Clicks: Total Count" 
                    ELSE 0 END) as avg_cart_add_rate
            FROM {Config.KEYWORD_TABLE}
            """
            
            df = self.execute_query(query)
            return df.to_dict('records')[0] if not df.empty else {}
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {}
    
    def get_top_performing_keywords(self, limit: int = 10, metric: str = 'purchases') -> pd.DataFrame:
        """Get top performing keywords by specified metric using simplified columns"""
        try:
            # Map metric names to actual column names
            metric_mapping = {
                'impressions': '"Impressions: Total Count"',
                'clicks': '"Clicks: Total Count"',
                'cart_adds': '"Cart Adds: Total Count"',
                'purchases': '"Purchases: Total Count"',
                'ctr': 'CASE WHEN "Impressions: Total Count" > 0 THEN "Clicks: Total Count" / "Impressions: Total Count" ELSE 0 END',
                'conversion_rate': 'CASE WHEN "Clicks: Total Count" > 0 THEN "Purchases: Total Count" / "Clicks: Total Count" ELSE 0 END',
                'cart_add_rate': 'CASE WHEN "Clicks: Total Count" > 0 THEN "Cart Adds: Total Count" / "Clicks: Total Count" ELSE 0 END'
            }
            
            # Default to purchases if metric not found
            order_by_metric = metric_mapping.get(metric, '"Purchases: Total Count"')
            
            query = f"""
            SELECT 
                SEARCH_QUERY as keyword,
                DATE,
                "Impressions: Total Count" as impressions,
                "Clicks: Total Count" as clicks,
                "Cart Adds: Total Count" as cart_adds,
                "Purchases: Total Count" as purchases,
                CASE WHEN "Impressions: Total Count" > 0 
                    THEN "Clicks: Total Count" / "Impressions: Total Count" 
                    ELSE 0 END as ctr,
                CASE WHEN "Clicks: Total Count" > 0 
                    THEN "Purchases: Total Count" / "Clicks: Total Count" 
                    ELSE 0 END as conversion_rate,
                CASE WHEN "Clicks: Total Count" > 0 
                    THEN "Cart Adds: Total Count" / "Clicks: Total Count" 
                    ELSE 0 END as cart_add_rate
            FROM {Config.KEYWORD_TABLE}
            ORDER BY {order_by_metric} DESC
            LIMIT {limit}
            """
            
            return self.execute_query(query)
            
        except Exception as e:
            logger.error(f"Error getting top keywords: {e}")
            return pd.DataFrame()
    
    def search_keywords(self, search_term: str) -> pd.DataFrame:
        """Search for keywords containing the search term using simplified columns"""
        try:
            query = f"""
            SELECT 
                SEARCH_QUERY as keyword,
                DATE,
                "Impressions: Total Count" as impressions,
                "Clicks: Total Count" as clicks,
                "Cart Adds: Total Count" as cart_adds,
                "Purchases: Total Count" as purchases,
                CASE WHEN "Impressions: Total Count" > 0 
                    THEN "Clicks: Total Count" / "Impressions: Total Count" 
                    ELSE 0 END as ctr,
                CASE WHEN "Clicks: Total Count" > 0 
                    THEN "Purchases: Total Count" / "Clicks: Total Count" 
                    ELSE 0 END as conversion_rate,
                CASE WHEN "Clicks: Total Count" > 0 
                    THEN "Cart Adds: Total Count" / "Clicks: Total Count" 
                    ELSE 0 END as cart_add_rate
            FROM {Config.KEYWORD_TABLE}
            WHERE LOWER(SEARCH_QUERY) LIKE LOWER('%{search_term}%')
            ORDER BY "Impressions: Total Count" DESC
            """
            
            return self.execute_query(query)
            
        except Exception as e:
            logger.error(f"Error searching keywords: {e}")
            return pd.DataFrame()
    
    def close(self):
        """Close the Snowflake connection"""
        if self.connection:
            try:
                self.connection.close()
                logger.info("Snowflake connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {e}") 