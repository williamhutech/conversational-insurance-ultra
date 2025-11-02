"""
PostgreSQL Claims Database Client

Async client for MSIG's claims database on AWS RDS PostgreSQL.
Executes SQL queries for claims data analysis and intelligence.

Usage:
    client = await get_postgres_claims_client()
    results = await client.execute_query("SELECT * FROM hackathon.claims LIMIT 10")
"""

import re
import logging
import os
from typing import List, Dict, Any, Optional
import asyncpg
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class PostgresClaimsClient:
    """
    Async PostgreSQL client for MSIG claims database.

    Features:
    - Connection pooling for performance
    - Read-only query validation (blocks INSERT/UPDATE/DELETE/DROP)
    - Structured error handling
    - Query result formatting as List[Dict]
    """

    def __init__(self):
        """Initialize client with configuration from environment variables."""
        self.host = os.getenv("POSTGRES_CLAIMS_HOST")
        self.port = int(os.getenv("POSTGRES_CLAIMS_PORT", "5432"))
        self.database = os.getenv("POSTGRES_CLAIMS_DATABASE")
        self.user = os.getenv("POSTGRES_CLAIMS_USER")
        self.password = os.getenv("POSTGRES_CLAIMS_PASSWORD")

        self.pool: Optional[asyncpg.Pool] = None

        logger.info(
            f"PostgresClaimsClient initialized for {self.host}:{self.port}/{self.database}"
        )

    async def connect(self) -> None:
        """
        Establish connection pool to PostgreSQL database.

        Raises:
            ConnectionError: If connection fails
        """
        if self.pool is not None:
            logger.info("Connection pool already exists")
            return

        try:
            logger.info(f"Connecting to PostgreSQL: {self.host}:{self.port}/{self.database}")

            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=2,  # Minimum connections
                max_size=10,  # Maximum connections
                command_timeout=30,  # 30 second query timeout
                timeout=10  # 10 second connection timeout
            )

            # Test connection
            async with self.pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                logger.info(f"Connected to PostgreSQL: {version}")

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}", exc_info=True)
            raise ConnectionError(f"Failed to connect to PostgreSQL: {str(e)}")

    async def close(self) -> None:
        """Close connection pool gracefully."""
        if self.pool is not None:
            logger.info("Closing PostgreSQL connection pool")
            await self.pool.close()
            self.pool = None

    def _validate_read_only(self, sql: str) -> None:
        """
        Validate that SQL query is read-only (SELECT statements only).

        Args:
            sql: SQL query to validate

        Raises:
            ValueError: If query contains write operations
        """
        # Normalize SQL: remove comments and extra whitespace
        sql_clean = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)  # Remove single-line comments
        sql_clean = re.sub(r'/\*.*?\*/', '', sql_clean, flags=re.DOTALL)  # Remove multi-line comments
        sql_clean = sql_clean.strip().upper()

        # Check for dangerous operations
        dangerous_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'TRUNCATE',
            'ALTER', 'CREATE', 'GRANT', 'REVOKE', 'EXECUTE',
            'CALL', 'MERGE', 'REPLACE', 'RENAME'
        ]

        for keyword in dangerous_keywords:
            # Use word boundaries to avoid false positives (e.g., "INSERTED_AT" is fine)
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, sql_clean):
                logger.warning(f"Blocked non-read-only SQL query containing: {keyword}")
                raise ValueError(
                    f"Only SELECT queries are allowed. Query contains: {keyword}"
                )

        # Ensure query starts with SELECT (after CTEs if present)
        # Support CTE (Common Table Expressions): WITH ... AS (...) SELECT ...
        if not re.match(r'^(WITH\b.*?\bSELECT\b|SELECT\b)', sql_clean):
            logger.warning(f"Blocked non-SELECT SQL query: {sql_clean[:100]}")
            raise ValueError(
                "Only SELECT queries are allowed. Query must start with SELECT or WITH...SELECT"
            )

    async def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """
        Execute read-only SQL query and return results.

        Args:
            sql: SQL SELECT query to execute

        Returns:
            List of dictionaries containing query results

        Raises:
            ValueError: If query is not read-only
            ConnectionError: If not connected to database
            RuntimeError: If query execution fails
        """
        # Validate query is read-only
        self._validate_read_only(sql)

        # Ensure connected
        if self.pool is None:
            await self.connect()

        logger.info(f"Executing SQL query: {sql[:200]}...")

        try:
            async with self.pool.acquire() as conn:
                # Execute query
                rows = await conn.fetch(sql)

                # Convert asyncpg.Record to List[Dict]
                results = [dict(row) for row in rows]

                logger.info(f"Query executed successfully, returned {len(results)} rows")
                return results

        except asyncpg.PostgresError as e:
            logger.error(f"PostgreSQL error executing query: {e}", exc_info=True)
            raise RuntimeError(f"Database query failed: {str(e)}")

        except Exception as e:
            logger.error(f"Unexpected error executing query: {e}", exc_info=True)
            raise RuntimeError(f"Query execution failed: {str(e)}")

    async def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            await self.connect()
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


# Global singleton instance
_postgres_claims_client: Optional[PostgresClaimsClient] = None


async def get_postgres_claims_client() -> PostgresClaimsClient:
    """
    Get or create global PostgreSQL claims client instance.

    Returns:
        Connected PostgresClaimsClient instance
    """
    global _postgres_claims_client

    if _postgres_claims_client is None:
        logger.info("Creating new PostgresClaimsClient instance")
        _postgres_claims_client = PostgresClaimsClient()
        await _postgres_claims_client.connect()

    return _postgres_claims_client


async def close_postgres_claims_client() -> None:
    """Close global PostgreSQL claims client instance."""
    global _postgres_claims_client

    if _postgres_claims_client is not None:
        await _postgres_claims_client.close()
        _postgres_claims_client = None
        logger.info("PostgresClaimsClient closed")
