"""
Claims Intelligence Service

Multi-agent LLM system for analyzing MSIG's claims database to provide
data-driven insurance recommendations.

Architecture:
1. Manager Agent (o3) - Plans analytical topics
2. SQL Agents (gpt-4.1) - Generate SQL queries in parallel
3. Database Execution - Run queries on PostgreSQL
4. Manager Agent (o3) - Synthesize insights from results

Usage:
    service = await get_claims_intelligence_service()
    status, result = await service.analyze_claims(query="recommend medical coverage", sql_num=3)
"""

import json
import logging
import asyncio
import os
from typing import List, Dict, Any, Tuple, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

from backend.database.postgres_claims_client import get_postgres_claims_client
from backend.services.response_validator import ResponseValidator

# Load environment variables from .env
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class ClaimsIntelligenceService:
    """
    Multi-agent service for claims data intelligence.

    Uses LLM agents to:
    1. Plan analytical topics from user query
    2. Generate SQL queries for each topic
    3. Execute queries against claims database
    4. Synthesize actionable insights
    """

    def __init__(self):
        """Initialize service with OpenAI client and database client."""
        self.openai: Optional[AsyncOpenAI] = None
        self.db_client = None

        # Model configuration
        self.manager_model = "o3"  # Manager agent for planning and synthesis
        self.sql_model = "gpt-4.1"  # SQL generation agent

        logger.info("ClaimsIntelligenceService initialized")

    async def connect(self) -> None:
        """Initialize OpenAI and database connections."""
        if self.openai is None:
            logger.info("Initializing OpenAI client")
            self.openai = AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1/")
            )

        if self.db_client is None:
            logger.info("Initializing PostgreSQL claims client")
            self.db_client = await get_postgres_claims_client()

        logger.info("ClaimsIntelligenceService connected")

    # -------------------------------------------------------------------------
    # Phase 1: Topic Planning with Manager Agent
    # -------------------------------------------------------------------------

    async def _plan_topics(self, query: str, sql_num: int) -> Tuple[int, Optional[List[Dict[str, str]]]]:
        """
        Manager agent plans analytical topics from user query.

        Args:
            query: User's question or request
            sql_num: Number of topics/queries to plan

        Returns:
            (status_code, topics_list) where topics_list is [{"topic": "...", "focus": "..."}, ...]
            status_code: 0 for success, 1 for failure
        """
        logger.info(f"Phase 1: Planning {sql_num} analytical topics for query: {query}")

        prompt = f"""You are a data analyst specializing in travel insurance claims analysis.

Given the user's query, plan {sql_num} distinct analytical topics that could provide valuable insights from MSIG's historical claims database.

USER QUERY: {query}

## Table Schema: `claims`

### Primary Key
- **claim_number** - Unique identifier for each claim

### Complete Field Reference

#### 1. **claim_number** (VARCHAR(50))
- **Description:** Unique claim identifier serving as the primary key
- **Nullability:** NOT NULL
- **Cardinality:** High (unique per claim)
- **Usage:** 
  - Primary identifier for tracking individual claims
  - Used for joins and references
  - Key for deduplication checks

---

#### 2. **product_category** (VARCHAR(100))
- **Description:** High-level product classification
- **Nullability:** YES (nullable)
- **Cardinality:** Low (limited distinct values)
- **Distribution:** Categorical field with few unique categories
- **Usage:**
  - Segment claims by product type
  - Group policies for portfolio analysis
  - Filter claims by insurance product line
- **Analysis Tip:** Check distinct values to understand product portfolio mix

---

#### 3. **product_name** (VARCHAR(200))
- **Description:** Specific product name within a category
- **Nullability:** YES (nullable)
- **Cardinality:** Medium (multiple products per category)
- **Distribution:** More granular than product_category
- **Usage:**
  - Detailed product performance analysis
  - Identify best/worst performing products
  - Calculate product-specific loss ratios
  - Compare claims frequency across products

---

#### 4. **claim_status** (VARCHAR(100))
- **Description:** Current status of the claim
- **Nullability:** YES (nullable)
- **Cardinality:** Very low (typically 2-5 distinct values)
- **Expected Values:** Likely includes "Open", "Closed", and possibly intermediate states
- **Usage:**
  - Filter active vs. closed claims
  - Calculate closure rates
  - Monitor claims workflow
  - Identify claims requiring attention
  - Calculate pending reserves (open claims)
- **Analysis Tip:** Check distribution between open/closed for workload assessment

---

#### 5. **accident_date** (DATE)
- **Description:** Date when the incident occurred
- **Nullability:** Implied NOT NULL (critical field)
- **Range:** Depends on data collection period
- **Usage:**
  - Timeline analysis of incidents
  - Seasonality patterns (peak travel months)
  - Calculate reporting lag (accident_date to report_date)
  - Trend analysis over time
  - Identify accident clusters
- **Analysis Considerations:**
  - Should always precede report_date
  - Check for data quality issues if after report_date

---

#### 6. **report_date** (DATE)
- **Description:** Date when the claim was reported to the insurer
- **Nullability:** Implied NOT NULL (required for claim initiation)
- **Range:** Should be >= accident_date
- **Usage:**
  - Calculate reporting lag (days from accident to report)
  - Monthly claims volume analysis
  - Workflow efficiency metrics
  - Identify late reporting patterns
- **Key Metric:** `reporting_lag = report_date - accident_date`

---

#### 7. **closed_date** (DATE)
- **Description:** Date when the claim was closed
- **Nullability:** YES (NULL for open claims)
- **Range:** Should be >= report_date
- **Distribution:** NULL for all open claims, populated for closed claims
- **Usage:**
  - Calculate claim settlement duration
  - Measure claims processing efficiency
  - Identify aging claims (long settlement times)
  - Calculate closure rates by period
- **Key Metrics:**
  - `settlement_duration = closed_date - report_date`
  - `total_lifecycle = closed_date - accident_date`
- **Analysis Tip:** NULL values indicate open/active claims

---

#### 8. **destination** (VARCHAR(100))
- **Description:** Travel destination country/region
- **Nullability:** YES (nullable)
- **Cardinality:** Medium-High (many possible destinations)
- **Distribution:** Likely skewed toward popular travel destinations
- **Usage:**
  - Geographic risk analysis
  - Destination-specific loss patterns
  - Pricing by destination risk
  - Identify high-risk destinations
  - Travel trend analysis
- **Analysis Considerations:**
  - May have data quality issues (spelling variations, abbreviations)
  - Can be grouped into regions for analysis

---

#### 9. **claim_type** (VARCHAR(100))
- **Description:** Type or classification of the claim
- **Nullability:** Implied by schema
- **Cardinality:** Low-Medium (limited claim types)
- **Usage:**
  - Categorize claims by type
  - Analyze type-specific patterns
  - Calculate type-specific loss ratios

---

#### 10. **cause_of_loss** (VARCHAR(100))
- **Description:** Root cause or reason for the loss
- **Nullability:** Implied by schema
- **Cardinality:** Medium (various causes)
- **Usage:**
  - Root cause analysis
  - Identify preventable losses
  - Risk mitigation strategies
  - Claims prevention initiatives

---

#### 11. **loss_type** (VARCHAR(100))
- **Description:** Detailed category of the loss
- **Nullability:** Implied by schema
- **Cardinality:** Medium (multiple loss categories)
- **Expected Categories:** Medical, Baggage, Trip Cancellation, Trip Delay, etc.
- **Usage:**
  - Detailed loss analysis by category
  - Calculate loss-type-specific frequencies
  - Identify most expensive loss types
  - Portfolio composition analysis
  - Underwriting insights
- **Key Analysis:** Cross-tabulate with destination for risk assessment

---

### Financial Fields (All DECIMAL(10,2) in SGD)

#### 12-14. **Gross Fields** (gross_incurred, gross_paid, gross_reserve)
- **Description:** Financial amounts before reinsurance recovery
- **Nullability:** May contain NULL or 0
- **Range:** 0 to potentially millions (SGD)
- **Relationship:** `gross_incurred = gross_paid + gross_reserve`
- **Usage:**
  - Calculate total exposure
  - Measure claim costs before reinsurance
  - Assess reinsurance impact
- **Key Metrics:**
  - Total gross incurred losses
  - Average claim size (gross)

---

#### 15-17. **Net Fields** (net_incurred, net_paid, net_reserve)
- **Description:** Financial amounts after reinsurance recovery (company's actual exposure)
- **Nullability:** May contain NULL or 0
- **Range:** 0 to gross amounts (should be <= gross)
- **Relationship:** `net_incurred = net_paid + net_reserve`
- **Distribution:** 
  - net_paid: Right-skewed (few large claims, many small)
  - net_reserve: Only for open claims; 0 for closed claims
- **Usage:**
  - Calculate actual company loss exposure
  - Determine profitability
  - Reserve adequacy analysis
  - Cash flow projections
  - Loss ratio calculations

TASK: Plan {sql_num} statistical or analytical topics that:
1. Are directly relevant to the user's query
2. Can be answered with SQL analysis of the claims data
3. Provide actionable insights for insurance recommendations
4. Cover different analytical angles (e.g., frequency, severity, destination patterns, product performance)

EXAMPLES OF GOOD TOPICS:
- "Analyze medical claim severity by destination to identify high-risk locations"
- "Compare claim frequency across different product tiers for similar travel profiles"
- "Identify coverage gaps based on claim amounts vs policy limits"

OUTPUT FORMAT: Return ONLY a valid JSON object (no markdown, no explanations):
{{
  "topics": [
    {{"topic": "Brief topic description", "focus": "Specific analytical question"}},
    {{"topic": "Brief topic description", "focus": "Specific analytical question"}},
    ...
  ]
}}

Return exactly {sql_num} topics in the "topics" array."""

        try:
            response = await self.openai.chat.completions.create(
                model=self.manager_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=1,  # Some creativity for diverse topics
                max_completion_tokens=10000,  # o3 uses max_completion_tokens instead of max_tokens
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content.strip()
            logger.debug(f"Manager agent response: {content}")

            # Parse JSON response using ResponseValidator
            # Try as array first
            json_validation = ResponseValidator.extract_json_array(content)

            if json_validation["is_valid_json"]:
                # Direct array response
                topics = json_validation["parsed_json"]
            else:
                # Try as object (might have "topics" key or other key with array)
                validation = ResponseValidator.validate_json_response(content, expected_keys=[])

                if not validation["is_valid_json"]:
                    error_msg = f"JSON validation failed: {validation.get('error_type', 'Unknown error')}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                parsed = validation["parsed_json"]

                # Handle object with array key
                if isinstance(parsed, dict):
                    if "topics" in parsed:
                        topics = parsed["topics"]
                    else:
                        # Try to find any array in the response
                        for _, value in parsed.items():
                            if isinstance(value, list):
                                topics = value
                                break
                        else:
                            raise ValueError("No array found in JSON response")
                else:
                    raise ValueError("Expected JSON object or array")

            if len(topics) != sql_num:
                logger.warning(f"Expected {sql_num} topics, got {len(topics)}")

            logger.info(f"Phase 1 complete: Planned {len(topics)} topics")
            return (0, topics)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse manager agent JSON: {e}")
            return (1, None)
        except Exception as e:
            logger.error(f"Phase 1 failed: {e}", exc_info=True)
            return (1, None)

    # -------------------------------------------------------------------------
    # Phase 2: SQL Generation with Parallel Sub-Agents
    # -------------------------------------------------------------------------

    async def _generate_sql_for_topic(self, topic: Dict[str, str], topic_index: int) -> Dict[str, Any]:
        """
        Single SQL generation agent for one topic.

        Args:
            topic: Dictionary with topic description and focus
            topic_index: Index for logging

        Returns:
            {"topic": ..., "SQL_code": "..."} or {"topic": ..., "error": "..."}
        """
        logger.info(f"Phase 2.{topic_index}: Generating SQL for topic: {topic.get('topic', 'Unknown')}")

        topic_desc = topic.get("topic", "")
        focus = topic.get("focus", "")

        prompt = f"""You are an expert SQL developer specializing in PostgreSQL analytics queries.

Generate a SQL query to answer the following analytical question about travel insurance claims data.

TOPIC: {topic_desc}
FOCUS: {focus}

## Table Schema: `claims`

### Primary Key
- **claim_number** - Unique identifier for each claim

### Complete Field Reference

#### 1. **claim_number** (VARCHAR(50))
- **Description:** Unique claim identifier serving as the primary key
- **Nullability:** NOT NULL
- **Cardinality:** High (unique per claim)
- **Usage:** 
  - Primary identifier for tracking individual claims
  - Used for joins and references
  - Key for deduplication checks

---

#### 2. **product_category** (VARCHAR(100))
- **Description:** High-level product classification
- **Nullability:** YES (nullable)
- **Cardinality:** Low (limited distinct values)
- **Distribution:** Categorical field with few unique categories
- **Usage:**
  - Segment claims by product type
  - Group policies for portfolio analysis
  - Filter claims by insurance product line
- **Analysis Tip:** Check distinct values to understand product portfolio mix

---

#### 3. **product_name** (VARCHAR(200))
- **Description:** Specific product name within a category
- **Nullability:** YES (nullable)
- **Cardinality:** Medium (multiple products per category)
- **Distribution:** More granular than product_category
- **Usage:**
  - Detailed product performance analysis
  - Identify best/worst performing products
  - Calculate product-specific loss ratios
  - Compare claims frequency across products

---

#### 4. **claim_status** (VARCHAR(100))
- **Description:** Current status of the claim
- **Nullability:** YES (nullable)
- **Cardinality:** Very low (typically 2-5 distinct values)
- **Expected Values:** Likely includes "Open", "Closed", and possibly intermediate states
- **Usage:**
  - Filter active vs. closed claims
  - Calculate closure rates
  - Monitor claims workflow
  - Identify claims requiring attention
  - Calculate pending reserves (open claims)
- **Analysis Tip:** Check distribution between open/closed for workload assessment

---

#### 5. **accident_date** (DATE)
- **Description:** Date when the incident occurred
- **Nullability:** Implied NOT NULL (critical field)
- **Range:** Depends on data collection period
- **Usage:**
  - Timeline analysis of incidents
  - Seasonality patterns (peak travel months)
  - Calculate reporting lag (accident_date to report_date)
  - Trend analysis over time
  - Identify accident clusters
- **Analysis Considerations:**
  - Should always precede report_date
  - Check for data quality issues if after report_date

---

#### 6. **report_date** (DATE)
- **Description:** Date when the claim was reported to the insurer
- **Nullability:** Implied NOT NULL (required for claim initiation)
- **Range:** Should be >= accident_date
- **Usage:**
  - Calculate reporting lag (days from accident to report)
  - Monthly claims volume analysis
  - Workflow efficiency metrics
  - Identify late reporting patterns
- **Key Metric:** `reporting_lag = report_date - accident_date`

---

#### 7. **closed_date** (DATE)
- **Description:** Date when the claim was closed
- **Nullability:** YES (NULL for open claims)
- **Range:** Should be >= report_date
- **Distribution:** NULL for all open claims, populated for closed claims
- **Usage:**
  - Calculate claim settlement duration
  - Measure claims processing efficiency
  - Identify aging claims (long settlement times)
  - Calculate closure rates by period
- **Key Metrics:**
  - `settlement_duration = closed_date - report_date`
  - `total_lifecycle = closed_date - accident_date`
- **Analysis Tip:** NULL values indicate open/active claims

---

#### 8. **destination** (VARCHAR(100))
- **Description:** Travel destination country/region
- **Nullability:** YES (nullable)
- **Cardinality:** Medium-High (many possible destinations)
- **Distribution:** Likely skewed toward popular travel destinations
- **Usage:**
  - Geographic risk analysis
  - Destination-specific loss patterns
  - Pricing by destination risk
  - Identify high-risk destinations
  - Travel trend analysis
- **Analysis Considerations:**
  - May have data quality issues (spelling variations, abbreviations)
  - Can be grouped into regions for analysis

---

#### 9. **claim_type** (VARCHAR(100))
- **Description:** Type or classification of the claim
- **Nullability:** Implied by schema
- **Cardinality:** Low-Medium (limited claim types)
- **Usage:**
  - Categorize claims by type
  - Analyze type-specific patterns
  - Calculate type-specific loss ratios

---

#### 10. **cause_of_loss** (VARCHAR(100))
- **Description:** Root cause or reason for the loss
- **Nullability:** Implied by schema
- **Cardinality:** Medium (various causes)
- **Usage:**
  - Root cause analysis
  - Identify preventable losses
  - Risk mitigation strategies
  - Claims prevention initiatives

---

#### 11. **loss_type** (VARCHAR(100))
- **Description:** Detailed category of the loss
- **Nullability:** Implied by schema
- **Cardinality:** Medium (multiple loss categories)
- **Expected Categories:** Medical, Baggage, Trip Cancellation, Trip Delay, etc.
- **Usage:**
  - Detailed loss analysis by category
  - Calculate loss-type-specific frequencies
  - Identify most expensive loss types
  - Portfolio composition analysis
  - Underwriting insights
- **Key Analysis:** Cross-tabulate with destination for risk assessment

---

### Financial Fields (All DECIMAL(10,2) in SGD)

#### 12-14. **Gross Fields** (gross_incurred, gross_paid, gross_reserve)
- **Description:** Financial amounts before reinsurance recovery
- **Nullability:** May contain NULL or 0
- **Range:** 0 to potentially millions (SGD)
- **Relationship:** `gross_incurred = gross_paid + gross_reserve`
- **Usage:**
  - Calculate total exposure
  - Measure claim costs before reinsurance
  - Assess reinsurance impact
- **Key Metrics:**
  - Total gross incurred losses
  - Average claim size (gross)

---

#### 15-17. **Net Fields** (net_incurred, net_paid, net_reserve)
- **Description:** Financial amounts after reinsurance recovery (company's actual exposure)
- **Nullability:** May contain NULL or 0
- **Range:** 0 to gross amounts (should be <= gross)
- **Relationship:** `net_incurred = net_paid + net_reserve`
- **Distribution:** 
  - net_paid: Right-skewed (few large claims, many small)
  - net_reserve: Only for open claims; 0 for closed claims
- **Usage:**
  - Calculate actual company loss exposure
  - Determine profitability
  - Reserve adequacy analysis
  - Cash flow projections
  - Loss ratio calculations

REQUIREMENTS:
1. Write a PostgreSQL SELECT query (read-only)
2. Use only the hackathon.claims table
3. Include appropriate WHERE clauses, aggregations, and GROUP BY as needed
4. Add meaningful column aliases
5. Use LIMIT to return a reasonable number of rows (typically 10-20)
6. Ensure query is optimized and syntactically correct

OUTPUT FORMAT: Return ONLY a valid JSON object (no markdown, no explanations):
{{"SQL_code": "SELECT ... FROM hackathon.claims ..."}}"""

        try:
            response = await self.openai.chat.completions.create(
                model=self.sql_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,  # More deterministic for SQL generation
                max_completion_tokens=8000,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content.strip()
            logger.debug(f"SQL agent {topic_index} response: {content}")

            # Parse JSON using ResponseValidator
            validation = ResponseValidator.validate_json_response(
                content,
                expected_keys=["SQL_code"]
            )

            if not validation["is_valid_json"]:
                error_msg = f"JSON validation failed: {validation.get('error_type', 'Unknown error')}"
                logger.error(f"Phase 2.{topic_index} validation error: {error_msg}")
                raise ValueError(error_msg)

            result = validation["parsed_json"]

            logger.info(f"Phase 2.{topic_index} complete: Generated SQL")
            return {
                "topic": topic_desc,
                "focus": focus,
                "SQL_code": result["SQL_code"]
            }

        except Exception as e:
            logger.error(f"Phase 2.{topic_index} failed: {e}", exc_info=True)
            return {
                "topic": topic_desc,
                "focus": focus,
                "error": str(e)
            }

    async def _generate_all_sql(self, topics: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Generate SQL queries for all topics in parallel.

        Args:
            topics: List of topic dictionaries

        Returns:
            List of results with SQL_code or error for each topic
        """
        logger.info(f"Phase 2: Generating SQL for {len(topics)} topics in parallel")

        # Create tasks for parallel execution
        tasks = [
            self._generate_sql_for_topic(topic, i + 1)
            for i, topic in enumerate(topics)
        ]

        # Execute all SQL generation agents in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"SQL generation task {i+1} raised exception: {result}")
                processed_results.append({
                    "topic": topics[i].get("topic", f"Topic {i+1}"),
                    "error": str(result)
                })
            else:
                processed_results.append(result)

        logger.info(f"Phase 2 complete: Generated {len(processed_results)} SQL queries")
        return processed_results

    # -------------------------------------------------------------------------
    # Phase 3: Query Execution
    # -------------------------------------------------------------------------

    async def _execute_queries(self, sql_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute all SQL queries against database.

        Args:
            sql_results: List of SQL generation results

        Returns:
            List of results with query_result or execution error
        """
        logger.info(f"Phase 3: Executing {len(sql_results)} SQL queries")

        enriched_results = []

        for i, sql_result in enumerate(sql_results):
            # Skip if SQL generation failed
            if "error" in sql_result:
                logger.warning(f"Skipping query {i+1} - SQL generation failed")
                enriched_results.append({
                    **sql_result,
                    "query_result": None,
                    "execution_error": f"SQL generation failed: {sql_result['error']}"
                })
                continue

            sql_code = sql_result.get("SQL_code")
            if not sql_code:
                logger.warning(f"Skipping query {i+1} - No SQL code")
                enriched_results.append({
                    **sql_result,
                    "query_result": None,
                    "execution_error": "No SQL code provided"
                })
                continue

            # Execute query
            try:
                logger.info(f"Executing query {i+1}/{len(sql_results)}")
                query_result = await self.db_client.execute_query(sql_code)

                enriched_results.append({
                    **sql_result,
                    "query_result": query_result,
                    "execution_error": None
                })
                logger.info(f"Query {i+1} executed successfully, returned {len(query_result)} rows")

            except Exception as e:
                logger.error(f"Query {i+1} execution failed: {e}")
                enriched_results.append({
                    **sql_result,
                    "query_result": None,
                    "execution_error": str(e)
                })

        logger.info(f"Phase 3 complete: Executed {len(enriched_results)} queries")
        return enriched_results

    # -------------------------------------------------------------------------
    # Phase 4: Insight Synthesis with Manager Agent
    # -------------------------------------------------------------------------

    async def _synthesize_insights(
        self,
        query: str,
        sql_num: int,
        execution_results: List[Dict[str, Any]]
    ) -> Tuple[int, Optional[List[str]]]:
        """
        Manager agent synthesizes insights from query results.

        Args:
            query: Original user query
            sql_num: Number of insights expected
            execution_results: List of SQL + execution results

        Returns:
            (status_code, insights_list)
        """
        logger.info(f"Phase 4: Synthesizing {sql_num} insights from query results")

        # Prepare results summary for LLM
        results_summary = []
        for i, result in enumerate(execution_results):
            summary = {
                "topic": result.get("topic", f"Topic {i+1}"),
                "focus": result.get("focus", ""),
                "SQL_code": result.get("SQL_code", "N/A"),
            }

            if result.get("execution_error"):
                summary["status"] = "FAILED"
                summary["error"] = result["execution_error"]
            else:
                summary["status"] = "SUCCESS"
                query_result = result.get("query_result", [])
                summary["row_count"] = len(query_result)
                summary["data"] = query_result[:5] if query_result else []  # First 5 rows

            results_summary.append(summary)

        prompt = f"""You are a senior data analyst providing actionable insurance recommendations based on claims data analysis.

ORIGINAL USER QUERY: {query}

ANALYSIS RESULTS:
{json.dumps(results_summary, indent=2, default=str)}

TASK: Synthesize {sql_num} VERY USEFUL and ACTIONABLE insights that directly answer the user's query.

## Table Schema: `claims`

### Primary Key
- **claim_number** - Unique identifier for each claim

### Complete Field Reference

#### 1. **claim_number** (VARCHAR(50))
- **Description:** Unique claim identifier serving as the primary key
- **Nullability:** NOT NULL
- **Cardinality:** High (unique per claim)
- **Usage:** 
  - Primary identifier for tracking individual claims
  - Used for joins and references
  - Key for deduplication checks

---

#### 2. **product_category** (VARCHAR(100))
- **Description:** High-level product classification
- **Nullability:** YES (nullable)
- **Cardinality:** Low (limited distinct values)
- **Distribution:** Categorical field with few unique categories
- **Usage:**
  - Segment claims by product type
  - Group policies for portfolio analysis
  - Filter claims by insurance product line
- **Analysis Tip:** Check distinct values to understand product portfolio mix

---

#### 3. **product_name** (VARCHAR(200))
- **Description:** Specific product name within a category
- **Nullability:** YES (nullable)
- **Cardinality:** Medium (multiple products per category)
- **Distribution:** More granular than product_category
- **Usage:**
  - Detailed product performance analysis
  - Identify best/worst performing products
  - Calculate product-specific loss ratios
  - Compare claims frequency across products

---

#### 4. **claim_status** (VARCHAR(100))
- **Description:** Current status of the claim
- **Nullability:** YES (nullable)
- **Cardinality:** Very low (typically 2-5 distinct values)
- **Expected Values:** Likely includes "Open", "Closed", and possibly intermediate states
- **Usage:**
  - Filter active vs. closed claims
  - Calculate closure rates
  - Monitor claims workflow
  - Identify claims requiring attention
  - Calculate pending reserves (open claims)
- **Analysis Tip:** Check distribution between open/closed for workload assessment

---

#### 5. **accident_date** (DATE)
- **Description:** Date when the incident occurred
- **Nullability:** Implied NOT NULL (critical field)
- **Range:** Depends on data collection period
- **Usage:**
  - Timeline analysis of incidents
  - Seasonality patterns (peak travel months)
  - Calculate reporting lag (accident_date to report_date)
  - Trend analysis over time
  - Identify accident clusters
- **Analysis Considerations:**
  - Should always precede report_date
  - Check for data quality issues if after report_date

---

#### 6. **report_date** (DATE)
- **Description:** Date when the claim was reported to the insurer
- **Nullability:** Implied NOT NULL (required for claim initiation)
- **Range:** Should be >= accident_date
- **Usage:**
  - Calculate reporting lag (days from accident to report)
  - Monthly claims volume analysis
  - Workflow efficiency metrics
  - Identify late reporting patterns
- **Key Metric:** `reporting_lag = report_date - accident_date`

---

#### 7. **closed_date** (DATE)
- **Description:** Date when the claim was closed
- **Nullability:** YES (NULL for open claims)
- **Range:** Should be >= report_date
- **Distribution:** NULL for all open claims, populated for closed claims
- **Usage:**
  - Calculate claim settlement duration
  - Measure claims processing efficiency
  - Identify aging claims (long settlement times)
  - Calculate closure rates by period
- **Key Metrics:**
  - `settlement_duration = closed_date - report_date`
  - `total_lifecycle = closed_date - accident_date`
- **Analysis Tip:** NULL values indicate open/active claims

---

#### 8. **destination** (VARCHAR(100))
- **Description:** Travel destination country/region
- **Nullability:** YES (nullable)
- **Cardinality:** Medium-High (many possible destinations)
- **Distribution:** Likely skewed toward popular travel destinations
- **Usage:**
  - Geographic risk analysis
  - Destination-specific loss patterns
  - Pricing by destination risk
  - Identify high-risk destinations
  - Travel trend analysis
- **Analysis Considerations:**
  - May have data quality issues (spelling variations, abbreviations)
  - Can be grouped into regions for analysis

---

#### 9. **claim_type** (VARCHAR(100))
- **Description:** Type or classification of the claim
- **Nullability:** Implied by schema
- **Cardinality:** Low-Medium (limited claim types)
- **Usage:**
  - Categorize claims by type
  - Analyze type-specific patterns
  - Calculate type-specific loss ratios

---

#### 10. **cause_of_loss** (VARCHAR(100))
- **Description:** Root cause or reason for the loss
- **Nullability:** Implied by schema
- **Cardinality:** Medium (various causes)
- **Usage:**
  - Root cause analysis
  - Identify preventable losses
  - Risk mitigation strategies
  - Claims prevention initiatives

---

#### 11. **loss_type** (VARCHAR(100))
- **Description:** Detailed category of the loss
- **Nullability:** Implied by schema
- **Cardinality:** Medium (multiple loss categories)
- **Expected Categories:** Medical, Baggage, Trip Cancellation, Trip Delay, etc.
- **Usage:**
  - Detailed loss analysis by category
  - Calculate loss-type-specific frequencies
  - Identify most expensive loss types
  - Portfolio composition analysis
  - Underwriting insights
- **Key Analysis:** Cross-tabulate with destination for risk assessment

---

### Financial Fields (All DECIMAL(10,2) in SGD)

#### 12-14. **Gross Fields** (gross_incurred, gross_paid, gross_reserve)
- **Description:** Financial amounts before reinsurance recovery
- **Nullability:** May contain NULL or 0
- **Range:** 0 to potentially millions (SGD)
- **Relationship:** `gross_incurred = gross_paid + gross_reserve`
- **Usage:**
  - Calculate total exposure
  - Measure claim costs before reinsurance
  - Assess reinsurance impact
- **Key Metrics:**
  - Total gross incurred losses
  - Average claim size (gross)

---

#### 15-17. **Net Fields** (net_incurred, net_paid, net_reserve)
- **Description:** Financial amounts after reinsurance recovery (company's actual exposure)
- **Nullability:** May contain NULL or 0
- **Range:** 0 to gross amounts (should be <= gross)
- **Relationship:** `net_incurred = net_paid + net_reserve`
- **Distribution:** 
  - net_paid: Right-skewed (few large claims, many small)
  - net_reserve: Only for open claims; 0 for closed claims
- **Usage:**
  - Calculate actual company loss exposure
  - Determine profitability
  - Reserve adequacy analysis
  - Cash flow projections
  - Loss ratio calculations

Each insight should:
1. Be specific and data-driven (cite numbers from results)
2. Provide clear recommendations for insurance coverage
3. Explain the business implication
4. Be concise but comprehensive (2-3 sentences each)

EXAMPLE INSIGHT:
"Based on historical claims data, 78% of medical claims at destination X exceeded SGD 5,000, with an average of SGD 8,200. We recommend upgrading to the Silver plan (medical coverage up to SGD 10,000) instead of Basic (SGD 3,000) to ensure adequate protection for this destination."

If a query failed, you may still provide insights based on available data, or note the limitation.

OUTPUT FORMAT: Return ONLY a valid JSON object (no markdown, no explanations):
{{
  "insights": [
    "Insight 1 with specific data and recommendation",
    "Insight 2 with specific data and recommendation",
    ...
  ]
}}

Return exactly {sql_num} insights in the "insights" array."""

        try:
            response = await self.openai.chat.completions.create(
                model=self.manager_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=1,  # Slightly creative but mostly factual
                max_completion_tokens=20000,  # o3 uses max_completion_tokens instead of max_tokens
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content.strip()
            logger.debug(f"Manager synthesis response: {content}")
            print(f"\n[DEBUG] Phase 4 Raw Response:\n{content[:500]}...")  # Debug print

            # Parse JSON response using ResponseValidator
            # Try as array first
            json_validation = ResponseValidator.extract_json_array(content)

            if json_validation["is_valid_json"]:
                # Direct array response
                insights = json_validation["parsed_json"]
                print(f"[DEBUG] Parsed as array, {len(insights)} items")
            else:
                # Try as object (might have "insights" key or other key with array)
                validation = ResponseValidator.validate_json_response(content, expected_keys=[])

                if not validation["is_valid_json"]:
                    error_msg = f"JSON validation failed: {validation.get('error_type', 'Unknown error')}"
                    logger.error(error_msg)
                    print(f"[DEBUG] JSON validation failed: {validation}")
                    raise ValueError(error_msg)

                parsed = validation["parsed_json"]
                print(f"[DEBUG] Parsed as object, keys: {list(parsed.keys()) if isinstance(parsed, dict) else type(parsed)}")
                print(f"[DEBUG] Full parsed structure: {parsed}")

                # Handle object with array key
                if isinstance(parsed, dict):
                    if "insights" in parsed:
                        insights = parsed["insights"]
                        print(f"[DEBUG] Found 'insights' key with {len(insights)} items")
                    else:
                        # Try to find any array in the response
                        print(f"[DEBUG] No 'insights' key, searching all keys: {list(parsed.keys())}")
                        for key, value in parsed.items():
                            print(f"[DEBUG] Checking key '{key}': type={type(value)}, is_list={isinstance(value, list)}")
                            if isinstance(value, list):
                                insights = value
                                print(f"[DEBUG] Found array in key '{key}' with {len(insights)} items")
                                break
                        else:
                            print(f"[DEBUG] No array found in any key. Parsed dict: {parsed}")
                            raise ValueError("No insights array found in response")
                else:
                    raise ValueError("Expected JSON object or array")

            logger.info(f"Phase 4 complete: Synthesized {len(insights)} insights")
            return (0, insights)

        except Exception as e:
            logger.error(f"Phase 4 failed: {e}", exc_info=True)
            return (1, None)

    # -------------------------------------------------------------------------
    # Main Orchestration Method
    # -------------------------------------------------------------------------

    async def analyze_claims(self, query: str, sql_num: int = 3) -> Tuple[int, str]:
        """
        Main method: Execute full multi-agent claims analysis workflow.

        Args:
            query: User's question or request
            sql_num: Number of analytical topics/insights to generate

        Returns:
            (status_code, result_string)
            - Success: (0, "insight_1: ..., insight_2: ..., insight_n: ...")
            - Failure: (1, error_message)
        """
        logger.info(f"=== Starting Claims Intelligence Analysis ===")
        logger.info(f"Query: {query}")
        logger.info(f"Requested insights: {sql_num}")

        try:
            # Ensure connected
            await self.connect()

            # Phase 1: Plan topics
            status, topics = await self._plan_topics(query, sql_num)
            if status != 0 or not topics:
                error_msg = "Failed to plan analytical topics"
                logger.error(error_msg)
                return (1, error_msg)

            # Phase 2: Generate SQL (parallel)
            sql_results = await self._generate_all_sql(topics)

            print("SQL Results:")
            print(sql_results) # Debug print

            # Phase 3: Execute queries
            execution_results = await self._execute_queries(sql_results)

            print("Execution Results:")
            print(execution_results) # Debug print

            # Phase 4: Synthesize insights
            status, insights = await self._synthesize_insights(query, sql_num, execution_results)

            print("Synthesis Results:")
            print(status, insights) # Debug print
            if status != 0 or not insights:
                error_msg = "Failed to synthesize insights from results"
                logger.error(error_msg)
                return (1, error_msg)

            # Format insights as requested
            insights_string = ", ".join([
                f"insight_{i+1}: {insight}"
                for i, insight in enumerate(insights)
            ])

            logger.info(f"=== Claims Intelligence Analysis Complete ===")
            logger.info(f"Generated {len(insights)} insights")

            return (0, insights_string)

        except Exception as e:
            error_msg = f"Claims intelligence analysis failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return (1, error_msg)


# Global singleton instance
_claims_intelligence_service: Optional[ClaimsIntelligenceService] = None


async def get_claims_intelligence_service() -> ClaimsIntelligenceService:
    """
    Get or create global claims intelligence service instance.

    Returns:
        Connected ClaimsIntelligenceService instance
    """
    global _claims_intelligence_service

    if _claims_intelligence_service is None:
        logger.info("Creating new ClaimsIntelligenceService instance")
        _claims_intelligence_service = ClaimsIntelligenceService()
        await _claims_intelligence_service.connect()

    return _claims_intelligence_service


# -------------------------------------------------------------------------
# Testing Block (Run this file directly to test)
# -------------------------------------------------------------------------
if __name__ == "__main__":
    import asyncio

    async def diagnose_database():
        """Diagnostic function to check database connection and data."""
        print("\n" + "="*80)
        print("🔍 DATABASE DIAGNOSTICS")
        print("="*80)

        try:
            client = await get_postgres_claims_client()

            # Test 1: Connection
            print("\n[Test 1] Testing connection...")
            is_connected = await client.test_connection()
            print(f"✓ Connection successful: {is_connected}")

            # Test 2: Check if hackathon schema exists
            print("\n[Test 2] Checking schemas...")
            schemas = await client.execute_query(
                "SELECT schema_name FROM information_schema.schemata ORDER BY schema_name"
            )
            print(f"Available schemas: {[s['schema_name'] for s in schemas]}")

            # Test 3: Check if claims table exists
            print("\n[Test 3] Checking tables in hackathon schema...")
            tables = await client.execute_query(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'hackathon'"
            )
            print(f"Tables in hackathon: {[t['table_name'] for t in tables]}")

            # Test 4: Count total rows
            print("\n[Test 4] Counting total rows in hackathon.claims...")
            count = await client.execute_query("SELECT COUNT(*) as total FROM hackathon.claims")
            print(f"Total rows: {count[0]['total'] if count else 0}")

            # Test 5: Check loss_type values
            print("\n[Test 5] Checking distinct loss_type values...")
            loss_types = await client.execute_query(
                "SELECT DISTINCT loss_type, COUNT(*) as count FROM hackathon.claims "
                "GROUP BY loss_type ORDER BY count DESC LIMIT 10"
            )
            print("Loss types found:")
            for lt in loss_types:
                print(f"  - '{lt['loss_type']}': {lt['count']} claims")

            # Test 6: Sample medical claims
            print("\n[Test 6] Checking for medical claims (case-insensitive)...")
            medical_count = await client.execute_query(
                "SELECT COUNT(*) as total FROM hackathon.claims WHERE loss_type ILIKE '%medical%'"
            )
            print(f"Medical claims found: {medical_count[0]['total'] if medical_count else 0}")

            # Test 7: Sample data
            print("\n[Test 7] Sample of first 3 rows...")
            sample = await client.execute_query("SELECT * FROM hackathon.claims LIMIT 3")
            if sample:
                print(f"Sample row keys: {list(sample[0].keys())}")
                for i, row in enumerate(sample):
                    print(f"\nRow {i+1}:")
                    print(f"  claim_number: {row.get('claim_number')}")
                    print(f"  loss_type: {row.get('loss_type')}")
                    print(f"  destination: {row.get('destination')}")
                    print(f"  net_incurred: {row.get('net_incurred')}")

            print("\n" + "="*80)
            print("✓ Diagnostics complete!")
            print("="*80 + "\n")

        except Exception as e:
            print(f"\n❌ Diagnostic failed: {e}")
            import traceback
            traceback.print_exc()

import asyncio

async def main():
    # Step 1: Run diagnostics
    await diagnose_database()

    print("\n🚀 Starting Claims Intelligence Service Test Suite...\n")

    # Step 2: Initialize service
    service = await get_claims_intelligence_service()

    # Step 3: Define multiple realistic insurance / claims / travel queries
    test_cases = [
        {
            "query": "recommend medical coverage for frequent travelers",
            "sql_num": 3,
            "description": "Basic recommendation test for frequent travel medical coverage"
        },
        {
            "query": "what are the exclusions for pre-existing medical conditions in travel insurance",
            "sql_num": 2,
            "description": "Check if system correctly routes to general_conditions for exclusions"
        },
        {
            "query": "does the policy cover trip cancellation due to COVID-19 or government restrictions",
            "sql_num": 4,
            "description": "Pandemic-related coverage under benefits and exclusions"
        },
        {
            "query": "maximum baggage loss compensation for business class travelers",
            "sql_num": 5,
            "description": "Quantitative benefit extraction for lost baggage coverage limits"
        },
        {
            "query": "how to submit a medical reimbursement claim for hospitalization abroad",
            "sql_num": 3,
            "description": "Tests claim conditions and proof requirements"
        },
        {
            "query": "coverage for adventure sports like scuba diving or skiing",
            "sql_num": 2,
            "description": "Checks eligibility and dangerous activity exclusions"
        },
        {
            "query": "are dependents included in family travel insurance plans",
            "sql_num": 3,
            "description": "Tests family policy eligibility logic"
        },
        {
            "query": "is loss of passport during travel covered and what documents are needed to claim",
            "sql_num": 4,
            "description": "Combined benefits and benefit_conditions query"
        },
    ]

    # Step 4: Iterate through test cases
    for i, case in enumerate(test_cases, start=1):
        print(f"\n==============================")
        print(f"🧪 Test Case {i}: {case['description']}")
        print(f"Query: {case['query']}")
        print("==============================\n")

        try:
            status, result = await service.analyze_claims(
                query=case["query"],
                sql_num=case["sql_num"]
            )
            print(f"✅ Status Code: {status}")
            print("Output:\n", result)
        except Exception as e:
            print(f"❌ Error in test case {i}: {e}")

    print("\n🎯 All tests completed.\n")

# Run async main
if __name__ == "__main__":
    asyncio.run(main())

