"""
DynamoDB Payments Table Initialization

Creates the payments table with proper schema and indexes.
Can be run manually or at application startup.

Usage:
    python -m database.dynamodb.init_payments_table

Or from code:
    from database.dynamodb.init_payments_table import create_payments_table
    create_payments_table()
"""

import boto3
import sys
import logging
from botocore.exceptions import ClientError

# Try to import settings, fall back to environment variables
try:
    from backend.config import settings
    AWS_REGION = settings.aws_region
    DDB_ENDPOINT = settings.dynamodb_endpoint
    TABLE_NAME = settings.dynamodb_payments_table
    AWS_ACCESS_KEY_ID = settings.aws_access_key_id or 'dummy'
    AWS_SECRET_ACCESS_KEY = settings.aws_secret_access_key or 'dummy'
except ImportError:
    import os
    AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
    DDB_ENDPOINT = os.getenv("DYNAMODB_ENDPOINT", "http://localhost:8000")
    TABLE_NAME = os.getenv("DYNAMODB_PAYMENTS_TABLE", "lea-payments-local")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "dummy")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "dummy")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_payments_table():
    """
    Create DynamoDB payments table with schema and indexes.

    Table Schema:
    - Primary Key: payment_intent_id (String, HASH)
    - GSI 1: user_id-index
    - GSI 2: quote_id-index
    - GSI 3: stripe_session_id-index

    Features:
    - DynamoDB Streams enabled
    - PAY_PER_REQUEST billing mode
    - All projections include full item

    Returns:
        bool: True if table created or already exists, False on error
    """

    logger.info(f"Connecting to DynamoDB at {DDB_ENDPOINT or 'AWS'}")

    # Initialize DynamoDB resource
    if DDB_ENDPOINT:
        # Local DynamoDB
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=AWS_REGION,
            endpoint_url=DDB_ENDPOINT,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
    else:
        # AWS DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)

    # Check if table already exists
    try:
        existing_table = dynamodb.Table(TABLE_NAME)
        existing_table.load()
        logger.info(f"✓ Table {TABLE_NAME} already exists")
        logger.info(f"  Status: {existing_table.table_status}")
        logger.info(f"  Item count: {existing_table.item_count}")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] != 'ResourceNotFoundException':
            logger.error(f"Error checking table: {e}")
            return False

    # Create table
    try:
        logger.info(f"Creating table {TABLE_NAME}...")

        table = dynamodb.create_table(
            TableName=TABLE_NAME,

            # Primary Key
            KeySchema=[
                {
                    'AttributeName': 'payment_intent_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],

            # Attribute Definitions (only for keys and indexes)
            AttributeDefinitions=[
                {
                    'AttributeName': 'payment_intent_id',
                    'AttributeType': 'S'  # String
                },
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'quote_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'stripe_session_id',
                    'AttributeType': 'S'
                }
            ],

            # Global Secondary Indexes
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
                        'ProjectionType': 'ALL'  # Include all attributes
                    }
                },
                {
                    'IndexName': 'quote_id-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'quote_id',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    }
                },
                {
                    'IndexName': 'stripe_session_id-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'stripe_session_id',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    }
                }
            ],

            # Billing and Streams
            BillingMode='PAY_PER_REQUEST',  # On-demand pricing
            StreamSpecification={
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'  # Include before and after images
            }
        )

        logger.info(f"Waiting for table {TABLE_NAME} to be created...")
        table.wait_until_exists()

        logger.info(f"✓ Table {TABLE_NAME} created successfully!")
        logger.info("Table details:")
        logger.info(f"  Table name: {table.table_name}")
        logger.info(f"  Table status: {table.table_status}")
        logger.info(f"  Item count: {table.item_count}")
        logger.info(f"  Billing mode: PAY_PER_REQUEST")
        logger.info(f"  Streams: Enabled")
        logger.info(f"  GSI count: 3 (user_id, quote_id, stripe_session_id)")

        return True

    except Exception as e:
        logger.error(f"✗ Error creating table: {e}")
        return False


def delete_payments_table():
    """
    Delete the payments table (use with caution!).

    Only use for development/testing.

    Returns:
        bool: True if deleted successfully
    """
    logger.warning(f"Deleting table {TABLE_NAME}...")

    if DDB_ENDPOINT:
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=AWS_REGION,
            endpoint_url=DDB_ENDPOINT,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
    else:
        dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)

    try:
        table = dynamodb.Table(TABLE_NAME)
        table.delete()
        logger.info(f"✓ Table {TABLE_NAME} deleted")
        return True
    except Exception as e:
        logger.error(f"✗ Error deleting table: {e}")
        return False


def table_exists():
    """
    Check if payments table exists.

    Returns:
        bool: True if table exists
    """
    if DDB_ENDPOINT:
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=AWS_REGION,
            endpoint_url=DDB_ENDPOINT,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
    else:
        dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)

    try:
        table = dynamodb.Table(TABLE_NAME)
        table.load()
        return True
    except ClientError:
        return False


if __name__ == "__main__":
    success = create_payments_table()
    sys.exit(0 if success else 1)
