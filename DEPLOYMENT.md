# 🚀 Deployment Guide - Hybrid Approach

This guide will help you deploy your Amazon Keyword Performance AI Chatbot using the **Hybrid Approach**:
- **Backend**: Deployed on Railway/Render/Heroku
- **Frontend**: Deployed on Streamlit Cloud
- **Database**: Snowflake (cloud-based)

## 📋 Prerequisites

- GitHub account
- Snowflake account with Amazon keyword data
- Anthropic API key
- Railway/Render/Heroku account (for backend)
- Streamlit Cloud account (for frontend)

## 🔧 Step 1: Prepare Your Repository

### 1.1 Push to GitHub
```bash
git add .
git commit -m "Prepare for deployment"
git push origin main
```

### 1.2 Verify Files Structure
```
Snowflake/
├── api/
│   └── main.py                 # FastAPI backend
├── frontend/
│   └── streamlit_app.py        # Streamlit frontend
├── database/
│   └── snowflake_client.py     # Snowflake client
├── ai/
│   └── claude_client.py        # Claude AI client
├── config.py                   # Configuration
├── requirements.txt            # Dependencies
├── Dockerfile                  # Backend container
├── Procfile                    # Heroku compatibility
├── runtime.txt                 # Python version
├── .gitignore                  # Git ignore rules
└── DEPLOYMENT.md               # This file
```

## 🌐 Step 2: Deploy Backend

### Option A: Railway (Recommended)

1. **Go to [Railway](https://railway.app)**
2. **Connect your GitHub repository**
3. **Create new project from GitHub repo**
4. **Set Environment Variables:**
   ```
   SNOWFLAKE_ACCOUNT=your_account.region
   SNOWFLAKE_USER=your_username
   SNOWFLAKE_PASSWORD=your_password
   SNOWFLAKE_DATABASE=your_database
   ANTHROPIC_API_KEY=your_api_key
   ENV=production
   ```
5. **Deploy** - Railway will automatically build and deploy
6. **Copy the deployment URL** (e.g., `https://your-app.railway.app`)

### Option B: Render

1. **Go to [Render](https://render.com)**
2. **Create new Web Service**
3. **Connect GitHub repository**
4. **Configure:**
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
5. **Set Environment Variables** (same as Railway)
6. **Deploy**

### Option C: Heroku

1. **Install Heroku CLI**
2. **Login and create app:**
   ```bash
   heroku login
   heroku create your-app-name
   ```
3. **Set environment variables:**
   ```bash
   heroku config:set SNOWFLAKE_ACCOUNT=your_account.region
   heroku config:set SNOWFLAKE_USER=your_username
   heroku config:set SNOWFLAKE_PASSWORD=your_password
   heroku config:set SNOWFLAKE_DATABASE=your_database
   heroku config:set ANTHROPIC_API_KEY=your_api_key
   heroku config:set ENV=production
   ```
4. **Deploy:**
   ```bash
   git push heroku main
   ```

## 🎨 Step 3: Deploy Frontend (Streamlit Cloud)

### 3.1 Prepare Streamlit Secrets

1. **Go to [Streamlit Cloud](https://share.streamlit.io)**
2. **Sign in with GitHub**
3. **Create new app**
4. **Configure app:**
   - **Repository**: Your GitHub repo
   - **Branch**: `main`
   - **Main file path**: `frontend/streamlit_app.py`

### 3.2 Set Streamlit Secrets

In the Streamlit Cloud dashboard, add these secrets:

```toml
# API Configuration
API_BASE_URL = "https://your-backend-url.railway.app"  # Your backend URL

# Authentication (set to true for public access)
ENABLE_AUTH = false  # Change to true for public deployment
ADMIN_USERNAME = "Jung"
ADMIN_PASSWORD = "Daddycarry12"

# Optional settings
MAX_REQUESTS_PER_MINUTE = 60
SESSION_TIMEOUT_MINUTES = 30
```

### 3.3 Deploy

Click **Deploy** and wait for the build to complete.

## 🔐 Step 4: Security Configuration

### 4.1 For Public Deployment

If you want public access, enable authentication:

1. **In Streamlit secrets, set:**
   ```toml
   ENABLE_AUTH = true
   ADMIN_USERNAME = "your-username"
   ADMIN_PASSWORD = "your-strong-password"
   ```

2. **Update your backend environment variables:**
   ```
   SECRET_KEY=your-very-secure-secret-key
   ```

### 4.2 Rate Limiting

Configure rate limiting in your backend environment:
```
MAX_REQUESTS_PER_MINUTE=60
```

## 🧪 Step 5: Testing

### 5.1 Test Backend
```bash
# Test health endpoint
curl https://your-backend-url.railway.app/health

# Test chat endpoint
curl -X POST https://your-backend-url.railway.app/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me top 5 keywords by purchases"}'
```

### 5.2 Test Frontend
1. **Visit your Streamlit app URL**
2. **Test the chat functionality**
3. **Verify API connection**

## 🔍 Step 6: Monitoring

### 6.1 Health Checks
- Backend: `https://your-backend-url/health`
- Frontend: Check Streamlit Cloud logs

### 6.2 Logs
- **Railway**: View logs in dashboard
- **Render**: View logs in dashboard
- **Streamlit Cloud**: View logs in dashboard

## 🚨 Troubleshooting

### Common Issues

1. **Backend Connection Error**
   - Check environment variables
   - Verify Snowflake credentials
   - Check API key validity

2. **Frontend Can't Connect to Backend**
   - Verify API_BASE_URL in Streamlit secrets
   - Check CORS settings
   - Ensure backend is running

3. **Authentication Issues**
   - Verify username/password in Streamlit secrets
   - Check ENABLE_AUTH setting

4. **Performance Issues**
   - Monitor API usage
   - Check rate limiting
   - Optimize database queries

### Debug Commands

```bash
# Check backend logs
railway logs  # or heroku logs --tail

# Test database connection
python test_snowflake.py

# Test API endpoints
python test_chat_api.py
```

## 📈 Step 7: Production Considerations

### 7.1 Scaling
- **Railway**: Auto-scales based on usage
- **Render**: Manual scaling options
- **Streamlit Cloud**: Handles scaling automatically

### 7.2 Cost Management
- **Monitor API usage** (Claude API costs)
- **Track Snowflake compute** usage
- **Set up billing alerts**

### 7.3 Security
- **Rotate credentials** regularly
- **Monitor access logs**
- **Implement proper authentication**
- **Use HTTPS everywhere**

## 🎉 Success!

Your Amazon Keyword Performance AI Chatbot is now deployed with:
- ✅ **Public frontend** on Streamlit Cloud
- ✅ **Secure backend** on Railway/Render/Heroku
- ✅ **Private data access** via Snowflake
- ✅ **AI-powered insights** via Claude

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section
2. Review platform-specific documentation
3. Check logs for error messages
4. Verify all environment variables are set correctly 