"""
Create Mock Test Data in DynamoDB

Creates test quotes and payment records for MCP Inspector testing.
This data enables end-to-end testing of all payment MCP tools.

Run with:
    python -m database.dynamodb.create_test_data
"""

import boto3
import uuid
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PAYMENTS_TABLE = "lea-payments-local"
QUOTES_TABLE = "lea-quotes-local"
ENDPOINT_URL = "http://localhost:8000"
REGION = "ap-southeast-1"


def get_dynamodb_client():
    """Get DynamoDB client."""
    return boto3.client(
        'dynamodb',
        endpoint_url=ENDPOINT_URL,
        region_name=REGION,
        aws_access_key_id='dummy',
        aws_secret_access_key='dummy'
    )


def create_test_quotes():
    """Create test quotes in DynamoDB."""
    dynamodb = get_dynamodb_client()

    test_quotes = [
        {
            "quote_id": {"S": "quote_test_001"},
            "user_id": {"S": "user_alice"},
            "product_name": {"S": "Premium Travel Insurance - 7 Days Asia"},
            "amount": {"N": "15000"},
            "currency": {"S": "SGD"},
            "policy_id": {"S": "pol_premium_asia_7d"},
            "coverage_details": {"S": "Medical: $500k, Baggage: $5k, Trip Cancellation: $10k"},
            "created_at": {"S": datetime.now().isoformat()},
            "expires_at": {"S": (datetime.now() + timedelta(days=30)).isoformat()},
            "status": {"S": "active"}
        },
        {
            "quote_id": {"S": "quote_test_002"},
            "user_id": {"S": "user_bob"},
            "product_name": {"S": "Basic Travel Insurance - 14 Days Europe"},
            "amount": {"N": "25000"},
            "currency": {"S": "SGD"},
            "policy_id": {"S": "pol_basic_europe_14d"},
            "coverage_details": {"S": "Medical: $250k, Baggage: $3k, Trip Cancellation: $5k"},
            "created_at": {"S": datetime.now().isoformat()},
            "expires_at": {"S": (datetime.now() + timedelta(days=30)).isoformat()},
            "status": {"S": "active"}
        },
        {
            "quote_id": {"S": "quote_test_003"},
            "user_id": {"S": "user_charlie"},
            "product_name": {"S": "Family Travel Insurance - 10 Days USA"},
            "amount": {"N": "45000"},
            "currency": {"S": "SGD"},
            "policy_id": {"S": "pol_family_usa_10d"},
            "coverage_details": {"S": "Medical: $1M, Baggage: $10k, Trip Cancellation: $20k"},
            "created_at": {"S": datetime.now().isoformat()},
            "expires_at": {"S": (datetime.now() + timedelta(days=30)).isoformat()},
            "status": {"S": "active"}
        }
    ]

    logger.info(f"Creating {len(test_quotes)} test quotes...")

    for quote in test_quotes:
        try:
            dynamodb.put_item(
                TableName=QUOTES_TABLE,
                Item=quote
            )
            logger.info(f"✓ Created quote: {quote['quote_id']['S']}")
        except Exception as e:
            logger.error(f"Error creating quote {quote['quote_id']['S']}: {e}")

    logger.info(f"✓ Created {len(test_quotes)} test quotes")


def create_test_payments():
    """Create test payment records in various states."""
    dynamodb = get_dynamodb_client()

    test_payments = [
        # Completed payment
        {
            "payment_intent_id": {"S": "pi_test_completed_001"},
            "user_id": {"S": "user_alice"},
            "quote_id": {"S": "quote_test_completed"},
            "amount": {"N": "15000"},
            "currency": {"S": "SGD"},
            "product_name": {"S": "Premium Travel Insurance - 7 Days Asia"},
            "payment_status": {"S": "completed"},
            "stripe_session_id": {"S": "cs_test_completed_001"},
            "stripe_payment_intent": {"S": "pi_stripe_completed_001"},
            "created_at": {"S": (datetime.now() - timedelta(hours=2)).isoformat()},
            "updated_at": {"S": (datetime.now() - timedelta(hours=1)).isoformat()}
        },
        # Pending payment
        {
            "payment_intent_id": {"S": "pi_test_pending_001"},
            "user_id": {"S": "user_bob"},
            "quote_id": {"S": "quote_test_pending"},
            "amount": {"N": "25000"},
            "currency": {"S": "SGD"},
            "product_name": {"S": "Basic Travel Insurance - 14 Days Europe"},
            "payment_status": {"S": "pending"},
            "stripe_session_id": {"S": "cs_test_pending_001"},
            "created_at": {"S": (datetime.now() - timedelta(hours=1)).isoformat()},
            "updated_at": {"S": (datetime.now() - timedelta(hours=1)).isoformat()}
        },
        # Failed payment
        {
            "payment_intent_id": {"S": "pi_test_failed_001"},
            "user_id": {"S": "user_charlie"},
            "quote_id": {"S": "quote_test_failed"},
            "amount": {"N": "45000"},
            "currency": {"S": "SGD"},
            "product_name": {"S": "Family Travel Insurance - 10 Days USA"},
            "payment_status": {"S": "failed"},
            "stripe_session_id": {"S": "cs_test_failed_001"},
            "failure_reason": {"S": "Card declined - insufficient funds"},
            "created_at": {"S": (datetime.now() - timedelta(hours=3)).isoformat()},
            "updated_at": {"S": (datetime.now() - timedelta(hours=3)).isoformat()}
        },
        # Expired payment
        {
            "payment_intent_id": {"S": "pi_test_expired_001"},
            "user_id": {"S": "user_alice"},
            "quote_id": {"S": "quote_test_expired"},
            "amount": {"N": "18000"},
            "currency": {"S": "SGD"},
            "product_name": {"S": "Premium Travel Insurance - 10 Days Asia"},
            "payment_status": {"S": "expired"},
            "stripe_session_id": {"S": "cs_test_expired_001"},
            "created_at": {"S": (datetime.now() - timedelta(days=2)).isoformat()},
            "updated_at": {"S": (datetime.now() - timedelta(days=1)).isoformat()}
        }
    ]

    logger.info(f"Creating {len(test_payments)} test payment records...")

    for payment in test_payments:
        try:
            dynamodb.put_item(
                TableName=PAYMENTS_TABLE,
                Item=payment
            )
            logger.info(f"✓ Created payment: {payment['payment_intent_id']['S']} ({payment['payment_status']['S']})")
        except Exception as e:
            logger.error(f"Error creating payment {payment['payment_intent_id']['S']}: {e}")

    logger.info(f"✓ Created {len(test_payments)} test payment records")


def verify_test_data():
    """Verify test data was created successfully."""
    dynamodb = get_dynamodb_client()

    # Count quotes
    try:
        quotes_response = dynamodb.scan(TableName=QUOTES_TABLE)
        quote_count = quotes_response.get('Count', 0)
        logger.info(f"✓ Quotes table has {quote_count} records")
    except Exception as e:
        logger.error(f"Error scanning quotes: {e}")

    # Count payments
    try:
        payments_response = dynamodb.scan(TableName=PAYMENTS_TABLE)
        payment_count = payments_response.get('Count', 0)
        logger.info(f"✓ Payments table has {payment_count} records")

        # Show payment statuses
        if payment_count > 0:
            statuses = {}
            for item in payments_response.get('Items', []):
                status = item.get('payment_status', {}).get('S', 'unknown')
                statuses[status] = statuses.get(status, 0) + 1

            logger.info("Payment status breakdown:")
            for status, count in statuses.items():
                logger.info(f"  {status}: {count}")

    except Exception as e:
        logger.error(f"Error scanning payments: {e}")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Creating Mock Test Data for MCP Testing")
    logger.info("=" * 60)

    # Create test quotes
    create_test_quotes()
    print()

    # Create test payment records
    create_test_payments()
    print()

    # Verify data
    verify_test_data()

    logger.info("")
    logger.info("=" * 60)
    logger.info("✓ Test data creation complete!")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Test Users:")
    logger.info("  - user_alice (has completed, expired payments)")
    logger.info("  - user_bob (has pending payment)")
    logger.info("  - user_charlie (has failed payment)")
    logger.info("")
    logger.info("Available Quotes:")
    logger.info("  - quote_test_001 (Premium Asia 7d - $150)")
    logger.info("  - quote_test_002 (Basic Europe 14d - $250)")
    logger.info("  - quote_test_003 (Family USA 10d - $450)")
    logger.info("")
    logger.info("You can now test MCP tools using this data!")
