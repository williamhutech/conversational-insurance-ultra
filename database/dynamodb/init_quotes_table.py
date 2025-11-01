"""
Initialize DynamoDB Quotes Table

Creates a local DynamoDB table for storing insurance quotations.
This is a temporary solution until the full quotation system is implemented.

Run with:
    python -m database.dynamodb.init_quotes_table
"""

import boto3
import logging
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
TABLE_NAME = "lea-quotes-local"
ENDPOINT_URL = "http://localhost:8000"
REGION = "ap-southeast-1"


def create_quotes_table():
    """Create quotes table in DynamoDB Local."""

    dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url=ENDPOINT_URL,
        region_name=REGION,
        aws_access_key_id='dummy',
        aws_secret_access_key='dummy'
    )

    try:
        logger.info(f"Connecting to DynamoDB at {ENDPOINT_URL}")

        # Check if table exists
        existing_tables = list(dynamodb.tables.all())
        if any(table.name == TABLE_NAME for table in existing_tables):
            logger.info(f"Table {TABLE_NAME} already exists")
            return

        logger.info(f"Creating table {TABLE_NAME}...")

        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {
                    'AttributeName': 'quote_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'quote_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'user_id-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'user_id',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    }
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        logger.info(f"Waiting for table {TABLE_NAME} to be created...")
        table.wait_until_exists()

        logger.info(f"✓ Table {TABLE_NAME} created successfully!")
        logger.info("Table details:")
        logger.info(f"  Table name: {table.table_name}")
        logger.info(f"  Table status: {table.table_status}")
        logger.info(f"  Item count: {table.item_count}")
        logger.info(f"  Billing mode: PAY_PER_REQUEST")
        logger.info(f"  GSI count: 1 (user_id)")

    except ClientError as e:
        logger.error(f"Error creating table: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


if __name__ == "__main__":
    create_quotes_table()
