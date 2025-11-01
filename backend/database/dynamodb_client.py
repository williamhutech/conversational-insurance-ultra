"""
DynamoDB Client for Payment Records

Manages payment records in AWS DynamoDB.
Provides methods for creating, querying, and updating payment statuses.

Usage:
    from backend.database.dynamodb_client import DynamoDBClient

    client = DynamoDBClient()
    await client.create_payment(payment_data)
    payment = await client.get_payment(payment_id)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

import boto3
from botocore.exceptions import ClientError

from backend.config import settings

logger = logging.getLogger(__name__)


class DynamoDBClient:
    """
    DynamoDB client wrapper for payment operations.

    Provides high-level interface for payment record management:
    - Create payment records
    - Update payment statuses
    - Query by payment_id, user_id, quote_id
    - Retrieve payment history
    """

    def __init__(self):
        """Initialize DynamoDB client with credentials from settings."""
        self.region = settings.aws_region
        self.table_name = settings.dynamodb_payments_table
        self.endpoint = settings.dynamodb_endpoint

        # Initialize boto3 resource
        if self.endpoint:
            # Local DynamoDB
            self.dynamodb = boto3.resource(
                'dynamodb',
                region_name=self.region,
                endpoint_url=self.endpoint,
                aws_access_key_id=settings.aws_access_key_id or 'dummy',
                aws_secret_access_key=settings.aws_secret_access_key or 'dummy'
            )
        else:
            # AWS DynamoDB
            self.dynamodb = boto3.resource('dynamodb', region_name=self.region)

        self.table = self.dynamodb.Table(self.table_name)

    async def connect(self):
        """
        Verify connection to DynamoDB.

        TODO: Implement connection verification
        TODO: Check table exists
        """
        try:
            # Verify table exists
            self.table.load()
            logger.info(f"Connected to DynamoDB table: {self.table_name}")
        except ClientError as e:
            logger.error(f"Failed to connect to DynamoDB: {e}")
            raise

    async def disconnect(self):
        """Close DynamoDB connection."""
        # boto3 doesn't require explicit close
        logger.info("Disconnected from DynamoDB")

    # -------------------------------------------------------------------------
    # Payment Creation
    # -------------------------------------------------------------------------

    async def create_payment(
        self,
        payment_intent_id: str,
        user_id: str,
        quote_id: str,
        amount: int,
        currency: str,
        product_name: str,
        stripe_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create new payment record.

        Args:
            payment_intent_id: Unique payment identifier
            user_id: Customer ID
            quote_id: Insurance quote ID
            amount: Payment amount in cents
            currency: Currency code (SGD, USD, etc.)
            product_name: Product description
            stripe_session_id: Stripe checkout session ID (optional)

        Returns:
            Created payment record

        TODO: Add validation for amount > 0
        TODO: Add validation for valid currency codes
        """
        now = datetime.utcnow().isoformat()

        payment_record = {
            'payment_intent_id': payment_intent_id,
            'user_id': user_id,
            'quote_id': quote_id,
            'amount': amount,
            'currency': currency,
            'product_name': product_name,
            'payment_status': 'pending',
            'created_at': now,
            'updated_at': now
        }

        if stripe_session_id:
            payment_record['stripe_session_id'] = stripe_session_id

        try:
            self.table.put_item(Item=payment_record)
            logger.info(f"Created payment record: {payment_intent_id}")
            return payment_record
        except ClientError as e:
            logger.error(f"Failed to create payment: {e}")
            raise

    # -------------------------------------------------------------------------
    # Payment Retrieval
    # -------------------------------------------------------------------------

    async def get_payment(self, payment_intent_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve payment by ID.

        Args:
            payment_intent_id: Payment identifier

        Returns:
            Payment record or None if not found

        TODO: Add caching for frequently accessed payments
        """
        try:
            response = self.table.get_item(Key={'payment_intent_id': payment_intent_id})
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Failed to get payment {payment_intent_id}: {e}")
            raise

    async def get_payment_by_quote(self, quote_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve payment by quote ID.

        Args:
            quote_id: Insurance quote ID

        Returns:
            Payment record or None if not found

        TODO: Implement using quote_id-index GSI
        """
        try:
            response = self.table.query(
                IndexName='quote_id-index',
                KeyConditionExpression='quote_id = :qid',
                ExpressionAttributeValues={':qid': quote_id}
            )
            items = response.get('Items', [])
            return items[0] if items else None
        except ClientError as e:
            logger.error(f"Failed to get payment by quote {quote_id}: {e}")
            raise

    async def get_payment_by_session(self, stripe_session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve payment by Stripe session ID.

        Args:
            stripe_session_id: Stripe checkout session ID

        Returns:
            Payment record or None if not found

        TODO: Implement using stripe_session_id-index GSI
        """
        try:
            response = self.table.query(
                IndexName='stripe_session_id-index',
                KeyConditionExpression='stripe_session_id = :sid',
                ExpressionAttributeValues={':sid': stripe_session_id}
            )
            items = response.get('Items', [])
            return items[0] if items else None
        except ClientError as e:
            logger.error(f"Failed to get payment by session {stripe_session_id}: {e}")
            raise

    # -------------------------------------------------------------------------
    # Payment Updates
    # -------------------------------------------------------------------------

    async def update_payment_status(
        self,
        payment_intent_id: str,
        status: str,
        stripe_payment_intent: Optional[str] = None,
        stripe_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update payment status.

        Args:
            payment_intent_id: Payment identifier
            status: New status (pending, completed, failed, expired)
            stripe_payment_intent: Stripe payment intent ID (optional)
            stripe_session_id: Stripe session ID (optional)

        Returns:
            Updated payment record

        TODO: Add status transition validation
        TODO: Add webhook_processed_at timestamp
        """
        update_expression = "SET payment_status = :status, updated_at = :updated"
        expression_values = {
            ':status': status,
            ':updated': datetime.utcnow().isoformat()
        }

        if stripe_payment_intent:
            update_expression += ", stripe_payment_intent = :intent"
            expression_values[':intent'] = stripe_payment_intent

        if stripe_session_id:
            update_expression += ", stripe_session_id = :session"
            expression_values[':session'] = stripe_session_id

        try:
            response = self.table.update_item(
                Key={'payment_intent_id': payment_intent_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ReturnValues='ALL_NEW'
            )
            logger.info(f"Updated payment {payment_intent_id} to status: {status}")
            return response.get('Attributes', {})
        except ClientError as e:
            logger.error(f"Failed to update payment status: {e}")
            raise

    async def update_payment(
        self,
        payment_intent_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update payment record with arbitrary fields.

        Args:
            payment_intent_id: Payment identifier
            updates: Dictionary of fields to update

        Returns:
            Updated payment record

        TODO: Implement dynamic update expression building
        """
        updates['updated_at'] = datetime.utcnow().isoformat()

        # Build update expression dynamically
        update_parts = []
        expression_values = {}

        for key, value in updates.items():
            update_parts.append(f"{key} = :{key}")
            expression_values[f":{key}"] = value

        update_expression = "SET " + ", ".join(update_parts)

        try:
            response = self.table.update_item(
                Key={'payment_intent_id': payment_intent_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ReturnValues='ALL_NEW'
            )
            return response.get('Attributes', {})
        except ClientError as e:
            logger.error(f"Failed to update payment: {e}")
            raise

    # -------------------------------------------------------------------------
    # Payment History & Queries
    # -------------------------------------------------------------------------

    async def get_user_payments(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get all payments for a user.

        Args:
            user_id: Customer ID
            limit: Maximum number of payments to return

        Returns:
            List of payment records

        TODO: Implement using user_id-index GSI
        TODO: Add pagination support
        """
        try:
            response = self.table.query(
                IndexName='user_id-index',
                KeyConditionExpression='user_id = :uid',
                ExpressionAttributeValues={':uid': user_id},
                Limit=limit,
                ScanIndexForward=False  # Most recent first
            )
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Failed to get user payments: {e}")
            raise

    async def get_payments_by_status(
        self,
        status: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all payments with specific status.

        Args:
            status: Payment status to filter by
            limit: Maximum number of payments

        Returns:
            List of payment records

        TODO: Consider adding status-index GSI for efficiency
        """
        try:
            response = self.table.scan(
                FilterExpression='payment_status = :status',
                ExpressionAttributeValues={':status': status},
                Limit=limit
            )
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Failed to get payments by status: {e}")
            raise

    # -------------------------------------------------------------------------
    # Table Management
    # -------------------------------------------------------------------------

    async def table_exists(self) -> bool:
        """
        Check if payments table exists.

        Returns:
            True if table exists, False otherwise
        """
        try:
            self.table.load()
            return True
        except ClientError:
            return False

    async def get_table_info(self) -> Dict[str, Any]:
        """
        Get table metadata.

        Returns:
            Table information including item count, size, etc.

        TODO: Return formatted table statistics
        """
        try:
            return {
                'table_name': self.table.name,
                'table_status': self.table.table_status,
                'item_count': self.table.item_count,
                'table_size_bytes': self.table.table_size_bytes
            }
        except ClientError as e:
            logger.error(f"Failed to get table info: {e}")
            raise


# Global client instance (optional)
_dynamodb_client: Optional[DynamoDBClient] = None


async def get_dynamodb() -> DynamoDBClient:
    """
    Get or create global DynamoDB client instance.

    Returns:
        DynamoDBClient: Configured client instance

    TODO: Implement connection pooling
    TODO: Add connection lifecycle management
    """
    global _dynamodb_client
    if _dynamodb_client is None:
        _dynamodb_client = DynamoDBClient()
        await _dynamodb_client.connect()
    return _dynamodb_client
