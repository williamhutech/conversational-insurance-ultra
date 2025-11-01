#!/usr/bin/env python3
"""
Test MCP initiate_purchase tool directly to capture error logs.
"""
import asyncio
import sys
import logging

# Set up logging to see all details
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

from mcp_server.client.backend_client import BackendClient


async def test_initiate_purchase():
    """Test the initiate_purchase flow."""
    client = BackendClient(base_url="http://localhost:8085")

    try:
        print("=" * 60)
        print("Testing initiate_purchase via BackendClient...")
        print("=" * 60)

        result = await client.initiate_payment(
            user_id="test_user_mcp",
            quote_id="test_quote_mcp",
            amount=15000,
            currency="SGD",
            product_name="Test Insurance MCP",
            customer_email="mcp@test.com"
        )

        print("\n✅ SUCCESS!")
        print(f"Result: {result}")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_initiate_purchase())
