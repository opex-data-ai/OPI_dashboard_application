# Opex Product Intelligence Hub

A modern, high-performance enterprise dashboard built with [NiceGUI](https://nicegui.io/), Python, and MongoDB. This platform integrates with Google Cloud services to provide comprehensive analytics, project tracking, and AI-driven insights.

## 🚀 Features

- **Authentication**: Secure multi-factor authentication (Password & Google OAuth 2.0).
- **Interactive Analytics**: Dynamic charts and metrics powered by ECharts.
- **Data Engine**: Optimized caching with DuckDB for ultra-fast metric rendering.
- **Integrations**: 
  - **Google BigQuery**: Real-time data warehouse querying.
  - **Google Drive**: Automated report and document fetching.
  - **Gmail API**: Integrated communication and alerting.
- **Project Management**: Built-in tools for tracking projects, tasks, and resource utilization.

## 🛠️ Technical Stack

- **Frontend**: NiceGUI (FastAPI + Vue.js + Tailwind CSS)
- **Database**: 
  - **MongoDB**: User profiles, notifications, and application settings.
  - **DuckDB**: High-performance local analytical database.
- **Infrastructure**: Google Cloud Platform (BQ, Drive, Gmail)

## 📋 Prerequisites

- Python 3.9+
- MongoDB instance (Local or Atlas)
- Google Cloud Platform Project with enabled BigQuery, Drive, and Gmail APIs.

## ⚙️ Configuration

1. **Environment Variables**: Create a `.env` file in the root directory (refer to `.env.example` if available) with the following:
   ```env
   MONGO_URI=your_mongodb_uri
   STORAGE_SECRET=your_nicegui_storage_secret
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   ```

2. **Google Service Accounts**:
   - Place `_service_account.json` (Main service account) and `gmail_credentials.json` in the root directory.

## 🏃 Getting Started

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   python main.py
   ```
   The dashboard will be available at `http://localhost:8080`.

## 📂 Project Structure

- `/pages`: Individual UI modules (Login, Overview, Products, Projects).
- `/services`: Core logic for auth, database initialization, and cloud integrations.
- `/data_engine`: Data fetching, transformation, and query management logic.
- `/assets`: Static resources and global styles.

## 🚀 Deploying to Render

Deployed at: **https://regtech365-product-intelligence-dashboard.onrender.com**

The app supports both local (file-based) and Render (env-var-based) credential modes automatically.

### Required Render Environment Variables

| Variable | Description |
|---|---|
| `MONGO_URI` | MongoDB Atlas connection string |
| `STORAGE_SECRET` | NiceGUI session secret key |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret |
| `GOOGLE_REDIRECT_URI` | `https://regtech365-product-intelligence-dashboard.onrender.com/auth/google/callback` |
| `BQ_SERVICE_ACCOUNT_JSON` | Full JSON content of `epi_service_account.json` |
| `GMAIL_TOKEN_BASE64` | Base64-encoded `token.pickle` (see below) |
| `BQ_PROJECT_ID` | BigQuery project ID |
| `BQ_DATASET_ID` | BigQuery dataset ID |
| `DRIVE_FOLDER_ID` | Google Drive folder ID |

### Generating `GMAIL_TOKEN_BASE64` (run once locally):
```bash
python -c "import base64,pickle; print(base64.b64encode(open('token.pickle','rb').read()).decode())"
```

### Important: Google Cloud Console
Add **both** of the following to your OAuth app's Authorized Redirect URIs:
- `http://localhost:8080/auth/google/callback`
- `https://regtech365-product-intelligence-dashboard.onrender.com/auth/google/callback`

---
*Developed by the Data & AI Team*