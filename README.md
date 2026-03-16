# RegTech365 Enterprise Dashboard

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

---
*Developed by the Data & AI Team*