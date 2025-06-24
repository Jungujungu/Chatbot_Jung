from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
import traceback
import time
import os
from contextlib import asynccontextmanager

from database.snowflake_client import SnowflakeClient
from ai.claude_client import ClaudeClient
from config import Config

# Configure logging based on environment
if Config.is_production():
    logging.basicConfig(level=logging.WARNING)
else:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    try:
        Config.validate_config()
        logger.info("Configuration validated successfully")
        logger.info(f"Environment: {Config.ENV}")
        logger.info(f"Database: {Config.get_database_url()}")
        
        # Test connections on startup
        try:
            sf_client = get_snowflake_client()
            logger.info("Snowflake connection test successful")
        except Exception as e:
            logger.warning(f"Snowflake connection test failed: {e}")
        
        try:
            claude = get_claude_client()
            logger.info("Claude API connection test successful")
        except Exception as e:
            logger.warning(f"Claude API connection test failed: {e}")
            
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise
    
    yield
    
    # Shutdown
    global snowflake_client
    if snowflake_client:
        try:
            snowflake_client.close()
            logger.info("Snowflake connection closed")
        except Exception as e:
            logger.error(f"Error closing Snowflake connection: {e}")

# Initialize FastAPI app
app = FastAPI(
    title="Amazon Keyword Performance AI Chatbot",
    description="AI-powered chatbot for analyzing Amazon keyword performance data from Snowflake",
    version="1.0.0",
    docs_url="/docs" if not Config.is_production() else None,
    redoc_url="/redoc" if not Config.is_production() else None,
    lifespan=lifespan
)

# Add CORS middleware with production-safe defaults
allowed_origins = ["*"]  # Configure appropriately for production
if Config.is_production():
    # In production, specify exact origins
    allowed_origins = [
        "https://share.streamlit.io",
        "https://your-streamlit-app.streamlit.app"  # Replace with your actual Streamlit URL
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    data: Optional[List[Dict[str, Any]]] = None
    sql_query: Optional[str] = None
    insights: Optional[str] = None
    error: Optional[str] = None

class QueryIntent(BaseModel):
    intent: str
    confidence: float
    entities: List[str]
    requires_sql: bool

# Global clients (in production, use dependency injection)
snowflake_client = None
claude_client = None

def get_snowflake_client():
    global snowflake_client
    if snowflake_client is None:
        try:
            snowflake_client = SnowflakeClient()
        except Exception as e:
            logger.error(f"Failed to initialize Snowflake client: {e}")
            raise
    return snowflake_client

def get_claude_client():
    global claude_client
    if claude_client is None:
        try:
            claude_client = ClaudeClient()
        except Exception as e:
            logger.error(f"Failed to initialize Claude client: {e}")
            raise
    return claude_client

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Amazon Keyword Performance AI Chatbot",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        health_status = {
            "status": "healthy",
            "snowflake_connected": False,
            "claude_connected": False,
            "data_summary": None
        }
        
        # Test Snowflake connection
        try:
            sf_client = get_snowflake_client()
            summary = sf_client.get_keyword_performance_summary()
            health_status["snowflake_connected"] = True
            health_status["data_summary"] = summary
        except Exception as e:
            logger.error(f"Snowflake health check failed: {e}")
        
        # Test Claude connection
        try:
            claude = get_claude_client()
            health_status["claude_connected"] = True
        except Exception as e:
            logger.error(f"Claude health check failed: {e}")
        
        # Overall status
        if not health_status["snowflake_connected"] or not health_status["claude_connected"]:
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint for keyword performance analysis"""
    try:
        user_message = request.message.strip()
        
        if not user_message:
            return ChatResponse(
                response="Please provide a message to analyze.",
                error="Empty message"
            )
        
        # Get clients with error handling
        try:
            sf_client = get_snowflake_client()
        except Exception as e:
            return ChatResponse(
                response="I'm having trouble connecting to the database. Please check your Snowflake configuration.",
                error=f"Snowflake connection error: {str(e)}"
            )
        
        try:
            claude = get_claude_client()
        except Exception as e:
            return ChatResponse(
                response="I'm having trouble connecting to the AI service. Please check your Claude API configuration.",
                error=f"Claude connection error: {str(e)}"
            )
        
        # Step 1: Understand query intent
        try:
            intent_analysis = claude.understand_query_intent(user_message)
            logger.info(f"Query intent: {intent_analysis}")
        except Exception as e:
            logger.error(f"Error understanding query intent: {e}")
            intent_analysis = {
                "intent": "PERFORMANCE_ANALYSIS",
                "confidence": 0.5,
                "entities": [],
                "requires_sql": True
            }
        
        # Step 2: Get table schema for SQL generation
        try:
            table_schema = sf_client.get_table_schema(Config.KEYWORD_TABLE)
            if not table_schema:
                return ChatResponse(
                    response=f"I couldn't find the table schema for {Config.KEYWORD_TABLE}. Please check your table configuration.",
                    error="Table schema not found"
                )
        except Exception as e:
            return ChatResponse(
                response=f"I couldn't access the table schema: {str(e)}",
                error=f"Schema error: {str(e)}"
            )
        
        # Step 3: Generate SQL query if needed
        sql_query = None
        data = None
        data_dict = None
        
        if intent_analysis.get("requires_sql", True):
            try:
                sql_query = claude.generate_sql_query(user_message, table_schema)
                logger.info(f"Generated SQL: {sql_query}")
                
                if sql_query:
                    # Step 4: Execute SQL query
                    try:
                        data = sf_client.execute_query(sql_query)
                        data_dict = data.to_dict('records') if not data.empty else []
                        logger.info(f"Query executed successfully, returned {len(data_dict)} rows")
                    except Exception as e:
                        logger.error(f"SQL execution error: {e}")
                        return ChatResponse(
                            response=f"I generated a SQL query but encountered an error executing it: {str(e)}",
                            sql_query=sql_query,
                            error=str(e)
                        )
                else:
                    logger.warning("No SQL query generated")
                    
            except Exception as e:
                logger.error(f"Error generating SQL: {e}")
                return ChatResponse(
                    response="I had trouble converting your question to a database query. Please try rephrasing your question.",
                    error=f"SQL generation error: {str(e)}"
                )
        
        # Step 5: Generate insights and response
        try:
            if data is not None and not data.empty:
                insights = claude.analyze_data(user_message, {"data": data_dict})
                response = claude.generate_insights({"data": data_dict, "query": user_message})
            else:
                # Handle non-SQL queries (general questions, help, etc.)
                response = claude.analyze_data(user_message, {"message": user_message})
                insights = None
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            response = "I analyzed your data but had trouble generating insights. Here's what I found in the data."
            insights = None
        
        return ChatResponse(
            response=response,
            data=data_dict,
            sql_query=sql_query,
            insights=insights
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        logger.error(traceback.format_exc())
        return ChatResponse(
            response="I'm sorry, I encountered an unexpected error while processing your request. Please try again.",
            error=str(e)
        )

@app.get("/keywords/search/{search_term}")
async def search_keywords(search_term: str):
    """Search for keywords containing the search term"""
    try:
        sf_client = get_snowflake_client()
        results = sf_client.search_keywords(search_term)
        return {
            "search_term": search_term,
            "results": results.to_dict('records') if not results.empty else [],
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Keyword search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/keywords/top/{metric}")
async def get_top_keywords(metric: str = "purchases", limit: int = 10):
    """Get top performing keywords by metric"""
    try:
        sf_client = get_snowflake_client()
        results = sf_client.get_top_performing_keywords(limit=limit, metric=metric)
        return {
            "metric": metric,
            "limit": limit,
            "results": results.to_dict('records') if not results.empty else []
        }
    except Exception as e:
        logger.error(f"Top keywords error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/summary")
async def get_performance_summary():
    """Get overall performance summary"""
    try:
        sf_client = get_snowflake_client()
        summary = sf_client.get_keyword_performance_summary()
        return summary
    except Exception as e:
        logger.error(f"Summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/schema")
async def get_table_schema():
    """Get the table schema"""
    try:
        sf_client = get_snowflake_client()
        schema = sf_client.get_table_schema(Config.KEYWORD_TABLE)
        return {
            "table": Config.KEYWORD_TABLE,
            "schema": schema
        }
    except Exception as e:
        logger.error(f"Schema error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=Config.API_HOST, 
        port=Config.API_PORT,
        log_level="info" if not Config.is_production() else "warning"
    ) 