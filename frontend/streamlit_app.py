import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os
import time
import threading
from queue import Queue

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

def translate_to_korean(text):
    """Translate text to Korean using Claude AI"""
    try:
        # Use Claude AI for translation
        response = requests.post(
            f"{API_BASE_URL}/translate",
            json={"text": text, "target_language": "Korean"},
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get("translation", text)
        else:
            return text  # Return original text if translation fails
    except Exception as e:
        st.warning(f"Translation failed: {str(e)}")
        return text

def send_chat_message_with_mode(message, mode="research"):
    """Send a message to the chat API with specified mode"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json={"message": message, "mode": mode},
            timeout=60 if mode == "research" else 30
        )
        return response.status_code == 200, response.json()
    except requests.exceptions.Timeout:
        return False, {"error": "Request timed out. Please try again."}
    except requests.exceptions.ConnectionError:
        return False, {"error": f"Cannot connect to API server at {API_BASE_URL}"}
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
        
        # Response Mode Selection
        st.subheader("🎯 Response Mode")
        response_mode = st.radio(
            "Choose your response style:",
            ["Simple Mode", "Research Mode"],
            help="Simple Mode: Quick, concise answers. Research Mode: Detailed analysis with insights."
        )
        
        # Mode descriptions
        if response_mode == "Simple Mode":
            st.info("💡 **Simple Mode**: Get quick, direct answers with minimal explanation.")
        else:
            st.info("🔬 **Research Mode**: Receive comprehensive analysis with detailed insights and recommendations.")
        
        # API Status
        st.subheader("🔍 API Status")
        if api_healthy:
            st.success("✅ Connected")
        
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
        
        if st.button(f"🏆 Get Top Keywords"):
            success, data = get_top_keywords(metric, 10)  # Fixed to 10 results
            if success:
                st.success(f"✅ Top keywords loaded!")
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
    
    # Initialize chat history and translation state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show Korean translation for assistant messages if available
            if message["role"] == "assistant" and message.get("korean_translation"):
                with st.expander("🇰🇷 한국어 번역"):
                    st.markdown(message["korean_translation"])

    # Chat input
    if prompt := st.chat_input("Ask about your keyword performance..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response with progress indicator
        with st.chat_message("assistant"):
            mode = "simple" if response_mode == "Simple Mode" else "research"
            
            if mode == "research":
                # Research mode with progress indicators
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Progress stages for research mode
                stages = [
                    "🔍 Analyzing your question...",
                    "📊 Querying the database...",
                    "🤖 Generating AI insights...",
                    "📈 Creating visualizations...",
                    "✅ Finalizing response..."
                ]
                
                for i, stage in enumerate(stages):
                    progress_bar.progress((i + 1) / len(stages))
                    status_text.text(stage)
                    time.sleep(0.5)  # Simulate processing time
                
                status_text.text("✅ Analysis complete!")
                time.sleep(0.5)
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
            
            # Get response from API with streaming
            success, response = send_chat_message_with_mode(prompt, mode)
            
            if success:
                # Display response with real-time streaming effect
                response_text = response.get("response", "No response received")
                
                # Create a placeholder for streaming effect
                response_placeholder = st.empty()
                
                # Simulate streaming effect by showing text character by character
                displayed_text = ""
                for char in response_text:
                    displayed_text += char
                    response_placeholder.markdown(displayed_text + "▌")  # Add cursor effect
                    time.sleep(0.01)  # Adjust speed as needed
                
                # Final display without cursor
                response_placeholder.markdown(response_text)
                
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
                
                # Add assistant response to chat history with translation button
                message_key = f"msg_{len(st.session_state.messages)}"
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response_text,
                    "message_key": message_key
                })
                
                # Add translation button for this specific message
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button(f"🇰🇷 Translate", key=f"translate_{message_key}"):
                        with st.spinner("Translating to Korean..."):
                            korean_text = translate_to_korean(response_text)
                            # Update the specific message with translation
                            for msg in st.session_state.messages:
                                if msg.get("message_key") == message_key:
                                    msg["korean_translation"] = korean_text
                                    break
                            st.rerun()
                
                # Display Korean translation if available for this message
                for msg in st.session_state.messages:
                    if msg.get("message_key") == message_key and msg.get("korean_translation"):
                        with st.expander("🇰🇷 한국어 번역", expanded=True):
                            st.markdown(msg["korean_translation"])
                        break
                
            else:
                error_msg = response.get("error", "Unknown error occurred")
                st.error(f"❌ Error: {error_msg}")
                st.session_state.messages.append({"role": "assistant", "content": f"Sorry, I encountered an error: {error_msg}"})

    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

def send_chat_message(message):
    """Send a message to the chat API (legacy function for compatibility)"""
    return send_chat_message_with_mode(message, "research")

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