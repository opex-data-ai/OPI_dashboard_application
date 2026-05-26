"""
AI Chat Assistant — V3 (Metric-Aware with Self-Correction & Polite Fallbacks)
Converts natural-language questions into SQL, queries DuckDB, and returns answers.
Uses predefined SQL templates for common queries, validates SQL execution,
self-corrects syntax/binder errors using LLM, and provides premium executive fallbacks.
"""
from google import genai
import os
import re
import logging
import json
from typing import Dict, Any, Optional, List
from utils.anonymizer import anonymize_data, restore_pii
from data_engine.sheets_handler import get_sheets_handler
from data_engine.chart_descriptions import METRIC_INFO

logger = logging.getLogger(__name__)

# Initialize GenAI Client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# ─── PII Configuration ───────────────────────────────────────────
PII_COLUMNS = ['organizationName', 'user_id', 'email', 'user_pseudo_id', 'organization_id']

# ─── Standard Reference SQL Templates ────────────────────────────
STANDARD_TEMPLATES = """
Below are mathematically correct reference SQL queries for common dashboard questions.
Always use these exact patterns and tables when answering relevant questions:

1. User count / user base by platform:
SELECT platform, COUNT(DISTINCT user_id) AS total_users FROM all_users GROUP BY platform;

2. Organisation count / tracking count by platform:
SELECT platform, COUNT(DISTINCT email_domain) AS total_orgs FROM all_organizations GROUP BY platform;

3. Ecosystem / Multi-platform adoption (organisations using > 1 platform):
WITH org_platforms AS (
  SELECT email_domain, COUNT(DISTINCT platform) AS platform_count FROM all_organizations GROUP BY email_domain
)
SELECT 
  COUNTIF(platform_count > 1) AS multi_platform_orgs_count, 
  COUNT(*) AS total_orgs, 
  COUNTIF(platform_count > 1) / COUNT(*) AS multi_platform_adoption_rate 
FROM org_platforms;

4. Monthly active users/growth trend (Uses safe strftime date casting):
SELECT 
  platform, 
  strftime(CAST(date AS DATE), '%Y-%m') AS month, 
  COUNT(DISTINCT user_id) AS active_users 
FROM daily_user_metrics 
GROUP BY platform, month 
ORDER BY platform, month;

5. Active organizations by platform:
SELECT platform, COUNT(DISTINCT organization_id) AS active_orgs FROM daily_organization_metrics GROUP BY platform;

6. Top active organizations by user count:
SELECT platform, organization_id, COUNT(DISTINCT user_id) AS user_count FROM daily_user_metrics GROUP BY platform, organization_id ORDER BY user_count DESC LIMIT 10;
""".strip()

# ─── Schema Cache ────────────────────────────────────────────────
_schema_cache: Optional[str] = None


def get_schema_context() -> str:
    """Query DuckDB for all table names and their column schemas. Cached."""
    global _schema_cache
    if _schema_cache:
        return _schema_cache

    from data_engine.data_loader import get_data_loader
    loader = get_data_loader()

    try:
        tables = loader.con.execute("SHOW TABLES").fetchall()
        schema_parts = []
        for (table_name,) in tables:
            if table_name.startswith('_'):
                continue
            cols = loader.con.execute(f"DESCRIBE {table_name}").fetchall()
            col_descs = ", ".join([f"{c[0]} ({c[1]})" for c in cols])
            schema_parts.append(f"  • {table_name}: {col_descs}")

        _schema_cache = "\n".join(schema_parts)
        logger.info(f"Schema context built: {len(schema_parts)} tables discovered.")
        return _schema_cache
    except Exception as e:
        logger.error(f"Failed to build schema context: {e}")
        return "(schema unavailable)"


def get_standard_metrics_context() -> str:
    """Build a compact list of official dashboard metrics and calculation rules for the LLM."""
    try:
        lines = []
        for key, info in METRIC_INFO.items():
            title = info.get('title', key)
            desc = info.get('description', '')
            schema_exp = info.get('schema_explanation', '')
            chart_data = info.get('chart_data')
            lines.append(f"  • {key}: {title} — {desc} (Calculation Guide: {schema_exp}, Query Key: {chart_data})")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to build standard metrics context: {e}")
        return "(no standard metrics metadata)"


def _extract_sql(text: str) -> Optional[str]:
    """Extract SQL from a code-fenced response."""
    match = re.search(r"```sql\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    stripped = text.strip()
    if stripped.upper().startswith("SELECT"):
        return stripped
    return None


def _is_safe_sql(sql: str) -> bool:
    """Reject any SQL that is not a SELECT."""
    dangerous = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE', 'REPLACE']
    upper = sql.upper().strip()
    for keyword in dangerous:
        if re.search(rf'\b{keyword}\b', upper):
            logger.warning(f"Blocked dangerous SQL keyword: {keyword}")
            return False
    return True


def ask(question: str, conversation_context: str = "") -> Dict[str, Any]:
    """
    Main entry point: NLP question → SQL (with reference templates + self-correction) 
    → DuckDB query → natural-language answer.
    """
    logger.info(f"Chat assistant V3 received question: '{question[:80]}...'")

    schema = get_schema_context()
    metrics_context = get_standard_metrics_context()

    # Build conversation history block
    history_block = ""
    if conversation_context and conversation_context.strip():
        history_block = (
            "Prior conversation (resolve pronouns / references like "
            "\"it\", \"that platform\", \"its trend\" against this history):\n"
            + conversation_context
        )

    # ── Step 1: Generate SQL ──────────────────────────────────────
    sql_prompt = f"""
You are a senior data analyst for a RegTech SaaS platform dashboard called "AI Analyst".
You have access to a DuckDB database with these tables and columns:

{schema}

Official Dashboard Metrics and Calculation Rules:
{metrics_context}

{STANDARD_TEMPLATES}

{history_block}

Current question: {question}

Instructions:
1. Using the conversation history (if any), resolve references to previous answers.
2. Write a single SQL SELECT query that answers the current question. Use standard reference templates and calculations when applicable.
3. Wrap the SQL in a ```sql``` code fence.
4. If the question matches one of the standard dashboard metrics listed above, include a line at the very end of your response:
   METRIC_KEY: [insert_matching_key_here]
   (e.g., METRIC_KEY: user_breakdown)
5. After the SQL, write one sentence explaining what the query does.

Rules:
- Only SELECT statements — never INSERT, UPDATE, DELETE, DROP, etc.
- Only reference tables and columns listed above.
- Use DuckDB SQL dialect.
- For any monthly or date groupings, format date types safely. E.g. use strftime(CAST(col AS DATE), '%Y-%m') instead of strftime('%Y-%m', col).
- If the question cannot be answered with the available data, say so clearly without generating SQL.
""".strip()

    try:
        logger.debug("Generating SQL query using LLM...")
        sql_response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=sql_prompt
        )
        raw_response = sql_response.text.strip()
        sql = _extract_sql(raw_response)

        # Parse matching METRIC_KEY from the generated response
        metric_key = None
        metric_match = re.search(r"METRIC_KEY:\s*([a-zA-Z0-9_]+)", raw_response, re.IGNORECASE)
        if metric_match:
            metric_key = metric_match.group(1).strip()
            logger.info(f"Standard dashboard metric key identified: {metric_key}")

        if not sql:
            # If LLM didn't formulate SQL, return its raw conversational answer
            return {
                "answer": raw_response.replace("```", "").strip(),
                "sql": None,
                "data": None,
                "error": None
            }

        if not _is_safe_sql(sql):
            return {
                "answer": "I can only run read-only queries. Your request appears to modify data, which I cannot do.",
                "sql": sql,
                "data": None,
                "error": "Blocked: non-SELECT SQL detected."
            }

        # ── Step 2: Safe SQL Execution & Validation Layer ─────────
        from data_engine.data_loader import get_data_loader
        loader = get_data_loader()

        df = None
        execution_error = None

        try:
            df = loader.execute_query(sql, raise_errors=True)
        except Exception as query_err:
            execution_error = str(query_err)
            logger.warning(f"Initial SQL query failed: {execution_error}. Attempting Self-Correction...")

            # ── Step 2.5: SQL Self-Correction Pass ─────────────────
            correction_prompt = f"""
You are a senior DuckDB SQL expert.
You wrote this SQL query for the user's question, but it threw a database execution error:

Question: {question}
SQL Generated:
```sql
{sql}
```

Database Error:
{execution_error}

Table schemas available:
{schema}

Instructions:
1. Fix the error in the SQL query. 
2. Ensure you cast string dates properly, e.g. strftime(CAST(date_column AS DATE), '%Y-%m') or cast(date_column as DATE).
3. Output ONLY a corrected SQL statement inside a single ```sql ``` block. No explanation.
""".strip()

            try:
                correction_response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=correction_prompt
                )
                corrected_sql = _extract_sql(correction_response.text.strip())

                if corrected_sql and corrected_sql != sql:
                    logger.info(f"Executing corrected SQL query: {corrected_sql[:120]}...")
                    df = loader.execute_query(corrected_sql, raise_errors=True)
                    sql = corrected_sql  # Update with successfully corrected SQL
                    execution_error = None  # Clear error
                else:
                    raise Exception("Correction produced identical SQL or failed to parse.")
            except Exception as correction_err:
                logger.error(f"SQL Self-Correction failed: {correction_err}")
                execution_error = f"Original error: {execution_error}. Correction error: {correction_err}"

        # ── Step 2.6: Polite Executive Fallback ───────────────────
        if execution_error or df is None or df.empty:
            logger.warning("No data retrieved or SQL is invalid. Generating polite executive response...")
            
            polite_prompt = f"""
You are "AI Analyst", a professional product and sales intelligence assistant.
The user asked: "{question}"
We were unable to successfully fetch dynamic metrics from the backend database for this query.

Table schemas available:
{schema}

Instructions:
1. Write a polite, premium, executive-level response explaining that we couldn't compile the exact figures for their specific query layout (avoid technical jargon like "SQL", "database", "DuckDB", "syntax error").
2. Describe what relevant data we DO track (e.g. users, organisations, engagement metrics by platform) in a reassuring way.
3. Suggest 2-3 clean, alternative questions they can ask instead, like:
   - "How many platforms are we tracking?"
   - "Show me the user base size by platform."
   - "Which platform has the highest active organisation count?"
4. Keep the tone extremely professional, helpful, and concise. No headers or bullet points.
""".strip()

            fallback_response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=polite_prompt
            )
            return {
                "answer": fallback_response.text.strip(),
                "sql": sql if sql else None,
                "data": None,
                "error": execution_error or "Query returned no results."
            }

        # ── Step 3: Summarise Working Results ────────────────────
        row_count = len(df)
        display_df = df.head(20)
        data_for_display = display_df.to_dict(orient='records')

        # PII Protection
        found_pii = [col for col in display_df.columns if col in PII_COLUMNS]
        pii_mapping = {}

        if found_pii:
            logger.info(f"PII columns detected: {found_pii}. Anonymizing.")
            anonymized_records, pii_mapping = anonymize_data(data_for_display, found_pii)
            summary_data_text = json.dumps(anonymized_records, indent=1)
        else:
            summary_data_text = display_df.to_string(index=False)

        # Fetch matching metric info from chart_descriptions.py if matched
        metric_info_block = ""
        if metric_key and metric_key in METRIC_INFO:
            info = METRIC_INFO[metric_key]
            metric_info_block = f"""
Official Dashboard Metric Definition:
- Title: {info.get('title')}
- Description: {info.get('description')}
- Calculation Detail: {info.get('schema_explanation')}
Use this official metric description and calculation rationale to ensure your analysis perfectly matches the dashboard's design.
"""

        logger.info(f"Query succeeded. Row count: {row_count}. Generating analyst summary...")

        summary_prompt = f"""
You are "AI Analyst", a strategic product and business intelligence assistant for a RegTech SaaS platform.
Your audience is product managers, sales reps, business development leaders, and senior executives.

{metric_info_block}

{history_block}

Current question: "{question}"

Data returned ({row_count} total rows, top {len(display_df)} shown):
{summary_data_text}

Instructions:
1. Write a concise, plain-English response (2–4 sentences) that directly answers the current question using conversation history for context.
2. Focus on strategic business insights — growth signals, adoption patterns, engagement trends, commercial opportunities, action items.
3. Avoid commenting on data structure or completeness. If a genuine data quality issue would distort the insight, mention it briefly in passing.
4. Be specific with numbers. No markdown, headers, or bullet points. Never mention SQL or databases.
5. If you see values starting with "HIDDEN_", they are anonymised identifiers — refer to them as "Organisation [ID]" or similar.
""".strip()

        summary_response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=summary_prompt
        )
        answer = summary_response.text.strip()

        # Restore PII hashes in response
        if pii_mapping:
            logger.info("Restoring PII hashes in AI answer.")
            answer = restore_pii(answer, pii_mapping)

        # Log Interaction
        tokens_used = 0
        try:
            tokens_used = summary_response.usage_metadata.total_token_count
        except Exception:
            pass

        try:
            sheets = get_sheets_handler()
            sheets.log_interaction(
                user_input=question,
                sql=sql,
                data=data_for_display,
                output=answer,
                tokens=tokens_used
            )
        except Exception as sheet_err:
            logger.error(f"Failed to log to Google Sheets: {sheet_err}")

        return {
            "answer": answer,
            "sql": sql,
            "data": data_for_display,
            "error": None
        }

    except Exception as e:
        logger.error(f"Chat assistant critical exception: {e}")
        return {
            "answer": "I encountered an error processing your question. Please try again.",
            "sql": None,
            "data": None,
            "error": str(e)
        }
