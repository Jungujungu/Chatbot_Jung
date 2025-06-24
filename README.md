# 🤖 Amazon Keyword Performance AI Chatbot

An AI-powered chatbot for analyzing Amazon keyword performance data using Snowflake and Claude AI.

## 🚀 Quick Start

### Option 1: Local Development
```bash
# Clone and setup
git clone <repository-url>
cd Snowflake
pip install -r requirements.txt

# Configure environment
cp env_example.txt .env
# Edit .env with your credentials

# Start backend
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend (in new terminal)
streamlit run frontend/streamlit_app.py
```

### Option 2: Deploy to Production (Recommended)
See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment guide.

**Hybrid Deployment:**
- **Backend**: Railway/Render/Heroku
- **Frontend**: Streamlit Cloud
- **Database**: Snowflake

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit     │    │   FastAPI       │    │   Snowflake     │
│   Frontend      │◄──►│   Backend       │◄──►│   Database      │
│   (Public)      │    │   (Private)     │    │   (Private)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Claude AI     │
                       │   (Anthropic)   │
                       └─────────────────┘
```

## 🛠️ Features

- **Natural Language Queries**: Ask questions in plain English
- **AI-Powered Analysis**: Get insights from Claude AI
- **Real-time Data**: Connect to live Snowflake data
- **Interactive Visualizations**: Charts and graphs
- **SQL Generation**: Automatic query conversion
- **Public Access**: Deploy with authentication

## 📁 Project Structure

```
Snowflake/
├── api/
│   └── main.py                 # FastAPI backend server
├── frontend/
│   └── streamlit_app.py        # Streamlit frontend
├── database/
│   └── snowflake_client.py     # Snowflake database client
├── ai/
│   └── claude_client.py        # Claude AI integration
├── config.py                   # Configuration management
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Backend container
├── Procfile                    # Heroku compatibility
├── runtime.txt                 # Python version
├── .gitignore                  # Git ignore rules
├── env_example.txt            # Environment variables template
├── DEPLOYMENT.md              # Deployment guide
├── test_deployment.py         # Deployment testing
└── README.md                  # This file
```

## 🔧 Configuration

### Environment Variables

Copy `env_example.txt` to `.env` and configure:

```env
# Snowflake Configuration
SNOWFLAKE_ACCOUNT=your_account.region
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=your_database
KEYWORD_TABLE=amazon_keywords

# Claude API Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Application Configuration
ENV=development  # Change to 'production' for deployment
SECRET_KEY=your-secret-key
```

## 🔌 API Endpoints

### Chat Endpoint
- **POST** `/chat` - Send natural language queries
- **Request**: `{"message": "Show me top keywords by purchases"}`
- **Response**: Analysis, data, SQL query, and insights

### Data Endpoints
- **GET** `/health` - Health check
- **GET** `/summary` - Performance summary
- **GET** `/keywords/top/{metric}` - Top keywords by metric
- **GET** `/keywords/search/{term}` - Search keywords
- **GET** `/schema` - Table schema

## 💡 Usage Examples

### 1. Performance Analysis
```
User: "Show me keywords with conversion rate above 5%"
AI: Analyzes data and provides insights about high-converting keywords
```

### 2. Trend Analysis
```
User: "Which keywords are declining in performance?"
AI: Identifies keywords with decreasing metrics over time
```

### 3. Optimization Recommendations
```
User: "What should I optimize for better performance?"
AI: Provides actionable recommendations based on data analysis
```

## 🚀 Deployment

### Quick Deployment

1. **Deploy Backend** (Railway/Render/Heroku):
   ```bash
   # Set environment variables in your platform
   SNOWFLAKE_ACCOUNT=your_account.region
   SNOWFLAKE_USER=your_username
   SNOWFLAKE_PASSWORD=your_password
   SNOWFLAKE_DATABASE=your_database
   ANTHROPIC_API_KEY=your_api_key
   ENV=production
   ```

2. **Deploy Frontend** (Streamlit Cloud):
   - Connect GitHub repository
   - Set main file: `frontend/streamlit_app.py`
   - Configure secrets:
     ```toml
     API_BASE_URL = "https://your-backend-url.railway.app"
     ENABLE_AUTH = true  # For public access
     ADMIN_USERNAME = "your-username"
     ADMIN_PASSWORD = "your-password"
     ```

3. **Test Deployment**:
   ```bash
   python test_deployment.py
   ```

### Detailed Deployment Guide

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete step-by-step instructions.

## 🔍 Testing

### Local Testing
```bash
# Test backend
uvicorn api.main:app --reload

# Test frontend
streamlit run frontend/streamlit_app.py

# Test deployment
python test_deployment.py
```

### Production Testing
```bash
# Test deployed backend
python test_deployment.py

# Or manually test endpoints
curl https://your-backend-url/health
curl -X POST https://your-backend-url/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me top 5 keywords by purchases"}'
```

## 🔒 Security

### For Public Deployment
- Enable authentication in Streamlit secrets
- Use strong passwords
- Set up rate limiting
- Monitor API usage
- Use HTTPS everywhere

### Best Practices
- Rotate credentials regularly
- Monitor access logs
- Implement proper authentication
- Use environment variables for secrets

## 🚨 Troubleshooting

### Common Issues

1. **Connection Error**: Check Snowflake credentials and network connectivity
2. **API Key Error**: Verify your Anthropic API key is correct
3. **Table Not Found**: Ensure your table name matches the `KEYWORD_TABLE` environment variable
4. **Import Errors**: Make sure all dependencies are installed with `pip install -r requirements.txt`

### Debug Mode

Enable debug logging by setting the log level in the code:
```python
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Performance Optimization

- Use connection pooling for Snowflake connections
- Implement caching for frequently accessed data
- Optimize SQL queries with proper indexing
- Use async/await for better concurrency

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the troubleshooting section
- Review the API documentation at `http://localhost:8000/docs`
- Check the deployment guide in [DEPLOYMENT.md](DEPLOYMENT.md)
- Open an issue in the repository

## 🔮 Future Enhancements

- [ ] Add time-series analysis capabilities
- [ ] Implement keyword clustering and categorization
- [ ] Add competitor analysis features
- [ ] Create automated reporting and alerts
- [ ] Add more visualization options
- [ ] Implement user authentication and multi-tenant support 