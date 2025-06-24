import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os

# Configuration - supports both local and deployed environments
def get_api_base_url():
    """Get API base URL from environment or Streamlit secrets"""
    # Check Streamlit secrets first (for deployed environment)
    if hasattr(st, 'secrets') and st.secrets.get("API_BASE_URL"):
        return st.secrets.get("API_BASE_URL")
    
    # Check environment variable
    env_url = os.getenv("API_BASE_URL")
    if env_url:
        return env_url
    
    # Default to localhost for development
    return "http://localhost:8000"

API_BASE_URL = get_api_base_url()

# Security configuration
def get_secret(key, default_value):
    """Safely get secret from Streamlit secrets or return default"""
    try:
        if hasattr(st, 'secrets') and st.secrets is not None:
            return st.secrets.get(key, default_value)
        return default_value
    except:
        return default_value

ENABLE_AUTH = get_secret("ENABLE_AUTH", False)
ADMIN_USERNAME = get_secret("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = get_secret("ADMIN_PASSWORD", "password")

def check_authentication():
    """Check if user is authenticated"""
    if not ENABLE_AUTH:
        return True
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        return False
    return True

def login_form():
    """Display login form"""
    st.title("🔐 Amazon Keyword Performance AI Chatbot - Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                st.session_state.authenticated = True
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials")

def check_api_health():
    """Check if the API is running and healthy"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, {"error": str(e)}

def main_app():
    """Main application after authentication"""
    # Page configuration
    st.set_page_config(
        page_title="Amazon Keyword Performance AI Chatbot",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Header
    st.title("🤖 Amazon Keyword Performance AI Chatbot")
    st.markdown("Ask questions about your Amazon keyword performance data in natural language!")

    # Check API health
    api_healthy, health_data = check_api_health()
    if not api_healthy:
        st.error(f"⚠️ Cannot connect to API server at {API_BASE_URL}")
        st.info("Please ensure the backend server is running and accessible.")
        return

    # Sidebar
    with st.sidebar:
        st.header("📊 Quick Actions")
        
        # API Status
        st.subheader("🔍 API Status")
        if api_healthy:
            st.success("✅ Connected")
            if health_data and isinstance(health_data, dict) and 'data_summary' in health_data:
                summary = health_data['data_summary']
                if isinstance(summary, dict):
                    st.write(f"**Total Keywords:** {summary.get('TOTAL_KEYWORDS', 'N/A'):,}")
                    st.write(f"**Total Impressions:** {summary.get('TOTAL_IMPRESSIONS', 'N/A'):,}")
        
        # Performance Summary
        if st.button("📈 Get Performance Summary"):
            success, data = get_performance_summary()
            if success:
                st.success("✅ Performance data loaded!")
                st.json(data)
            else:
                st.error("❌ Failed to load performance data")
        
        # Top Keywords
        metric = st.selectbox("Top Keywords by:", ["purchases", "clicks", "impressions", "cart_adds"])
        limit = st.slider("Number of results:", 5, 50, 10)
        
        if st.button(f"🏆 Get Top {limit} Keywords"):
            success, data = get_top_keywords(metric, limit)
            if success:
                st.success(f"✅ Top {limit} keywords loaded!")
                if data.get('results'):
                    df = pd.DataFrame(data['results'])
                    st.dataframe(df)
            else:
                st.error("❌ Failed to load top keywords")
        
        # Logout button
        if ENABLE_AUTH:
            if st.button("🚪 Logout"):
                st.session_state.authenticated = False
                st.rerun()

    # Main chat interface
    st.header("💬 Chat with Your Data")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about your keyword performance..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Analyzing your data..."):
                success, response = send_chat_message(prompt)
                
                if success:
                    # Display response
                    st.markdown(response.get("response", "No response received"))
                    
                    # Display SQL query if available
                    if response.get("sql_query"):
                        with st.expander("🔍 Generated SQL Query"):
                            st.code(response["sql_query"], language="sql")
                    
                    # Display data if available
                    if response.get("data"):
                        with st.expander("📊 Query Results"):
                            df = pd.DataFrame(response["data"])
                            st.dataframe(df)
                            
                            # Create visualizations
                            if not df.empty:
                                st.subheader("📈 Visualizations")
                                
                                # Time series if date column exists
                                if 'DATE' in df.columns:
                                    df['DATE'] = pd.to_datetime(df['DATE'])
                                    fig = px.line(df, x='DATE', y='Impressions: Total Count', 
                                                 title='Impressions Over Time')
                                    st.plotly_chart(fig)
                                
                                # Top performers chart
                                if 'SEARCH_QUERY' in df.columns and 'Purchases: Total Count' in df.columns:
                                    top_keywords = df.nlargest(10, 'Purchases: Total Count')
                                    fig = px.bar(top_keywords, x='SEARCH_QUERY', y='Purchases: Total Count',
                                                title='Top 10 Keywords by Purchases')
                                    st.plotly_chart(fig)
                    
                    # Display insights if available
                    if response.get("insights"):
                        with st.expander("💡 AI Insights"):
                            st.markdown(response["insights"])
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({"role": "assistant", "content": response.get("response", "")})
                    
                else:
                    error_msg = response.get("error", "Unknown error occurred")
                    st.error(f"❌ Error: {error_msg}")
                    st.session_state.messages.append({"role": "assistant", "content": f"Sorry, I encountered an error: {error_msg}"})

    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

def send_chat_message(message):
    """Send a message to the chat API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json={"message": message},
            timeout=30
        )
        return response.status_code == 200, response.json()
    except requests.exceptions.Timeout:
        return False, {"error": "Request timed out. Please try again."}
    except requests.exceptions.ConnectionError:
        return False, {"error": f"Cannot connect to API server at {API_BASE_URL}"}
    except Exception as e:
        return False, {"error": str(e)}

def get_performance_summary():
    """Get performance summary from API"""
    try:
        response = requests.get(f"{API_BASE_URL}/summary", timeout=10)
        return response.status_code == 200, response.json()
    except:
        return False, {}

def get_top_keywords(metric="purchases", limit=10):
    """Get top keywords by metric"""
    try:
        response = requests.get(f"{API_BASE_URL}/keywords/top/{metric}?limit={limit}", timeout=10)
        return response.status_code == 200, response.json()
    except:
        return False, {}

# Main application flow
if __name__ == "__main__":
    if ENABLE_AUTH and not check_authentication():
        login_form()
    else:
        main_app() 