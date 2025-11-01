"""
Payment Success/Cancel Pages Service

Serves HTML pages for payment completion flows.
Provides beautiful, responsive pages for success and cancellation scenarios.

Usage:
    # Can be run standalone or mounted in main FastAPI app
    uvicorn backend.services.payment.payment_pages:app --port 8085
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI(
    title="Insurance Payment Pages",
    version="1.0.0",
    description="Success and cancel pages for insurance payments"
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "payment-pages"}


@app.get("/success", response_class=HTMLResponse)
async def payment_success(request: Request):
    """
    Payment success page.

    Shows after successful Stripe payment completion.
    Displays session ID and next steps for the customer.

    Query Params:
        session_id: Stripe checkout session ID

    Returns:
        HTMLResponse: Styled success page
    """
    session_id = request.query_params.get("session_id", "")

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Payment Successful - Travel Insurance</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}

            .container {{
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                padding: 40px;
                text-align: center;
                max-width: 500px;
                width: 100%;
            }}

            .success-icon {{
                width: 80px;
                height: 80px;
                background: #10b981;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 24px;
                animation: pulse 2s infinite;
            }}

            .success-icon svg {{
                width: 40px;
                height: 40px;
                color: white;
            }}

            @keyframes pulse {{
                0% {{ transform: scale(1); }}
                50% {{ transform: scale(1.05); }}
                100% {{ transform: scale(1); }}
            }}

            h1 {{
                color: #1f2937;
                font-size: 28px;
                font-weight: 700;
                margin-bottom: 16px;
            }}

            .subtitle {{
                color: #6b7280;
                font-size: 16px;
                margin-bottom: 32px;
                line-height: 1.5;
            }}

            .info-box {{
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 32px;
            }}

            .info-label {{
                color: #374151;
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 8px;
            }}

            .session-id {{
                color: #6b7280;
                font-family: 'Monaco', 'Menlo', monospace;
                font-size: 12px;
                word-break: break-all;
                background: #f3f4f6;
                padding: 8px;
                border-radius: 4px;
            }}

            .next-steps {{
                text-align: left;
                margin-bottom: 32px;
            }}

            .next-steps h3 {{
                color: #1f2937;
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 16px;
            }}

            .next-steps ul {{
                color: #4b5563;
                font-size: 14px;
                line-height: 1.6;
                padding-left: 20px;
            }}

            .next-steps li {{
                margin-bottom: 8px;
            }}

            .close-button {{
                background: #667eea;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: background 0.2s;
            }}

            .close-button:hover {{
                background: #5a67d8;
            }}

            .footer {{
                margin-top: 32px;
                padding-top: 24px;
                border-top: 1px solid #e5e7eb;
                color: #9ca3af;
                font-size: 12px;
            }}

            @media (max-width: 480px) {{
                .container {{
                    padding: 24px;
                }}

                h1 {{
                    font-size: 24px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="success-icon">
                <svg fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
                </svg>
            </div>

            <h1>Payment Successful!</h1>
            <p class="subtitle">
                Your travel insurance payment has been processed successfully.
                Your policy will be created and sent to your email shortly.
            </p>

            <div class="info-box">
                <div class="info-label">Payment Session ID:</div>
                <div class="session-id">{session_id or 'Not provided'}</div>
            </div>

            <div class="next-steps">
                <h3>What happens next?</h3>
                <ul>
                    <li>You will receive a confirmation email with your policy details</li>
                    <li>Your policy documents will be available within 5-10 minutes</li>
                    <li>Return to the chat to continue or ask any questions</li>
                    <li>Keep your payment confirmation for your records</li>
                </ul>
            </div>

            <button class="close-button" onclick="window.close()">
                Return to Chat
            </button>

            <div class="footer">
                MSIG Travel Insurance • Secure Payment Processing
            </div>
        </div>

        <script>
            // Auto-close if opened as popup
            if (window.opener) {{
                setTimeout(() => {{
                    window.close();
                }}, 10000);
            }}

            console.log('Payment Success - Session ID:', '{session_id}');
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


@app.get("/cancel", response_class=HTMLResponse)
async def payment_cancel(request: Request):
    """
    Payment cancellation page.

    Shows when user cancels payment or closes Stripe checkout.

    Returns:
        HTMLResponse: Styled cancellation page
    """

    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Payment Cancelled - Travel Insurance</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }

            .container {
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                padding: 40px;
                text-align: center;
                max-width: 500px;
                width: 100%;
            }

            .cancel-icon {
                width: 80px;
                height: 80px;
                background: #ef4444;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 24px;
            }

            .cancel-icon svg {
                width: 40px;
                height: 40px;
                color: white;
            }

            h1 {
                color: #1f2937;
                font-size: 28px;
                font-weight: 700;
                margin-bottom: 16px;
            }

            .subtitle {
                color: #6b7280;
                font-size: 16px;
                margin-bottom: 32px;
                line-height: 1.5;
            }

            .actions {
                display: flex;
                gap: 16px;
                justify-content: center;
                flex-wrap: wrap;
                margin-bottom: 32px;
            }

            .button {
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                text-decoration: none;
                cursor: pointer;
                border: none;
                transition: all 0.2s;
                min-width: 120px;
            }

            .button-primary {
                background: #667eea;
                color: white;
            }

            .button-primary:hover {
                background: #5a67d8;
            }

            .button-secondary {
                background: #f3f4f6;
                color: #374151;
                border: 1px solid #d1d5db;
            }

            .button-secondary:hover {
                background: #e5e7eb;
            }

            .footer {
                margin-top: 32px;
                padding-top: 24px;
                border-top: 1px solid #e5e7eb;
                color: #9ca3af;
                font-size: 12px;
            }

            @media (max-width: 480px) {
                .container {
                    padding: 24px;
                }

                h1 {
                    font-size: 24px;
                }

                .actions {
                    flex-direction: column;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="cancel-icon">
                <svg fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                </svg>
            </div>

            <h1>Payment Cancelled</h1>
            <p class="subtitle">
                Your payment was cancelled. No charges have been made to your account.
                You can return to the chat to try again or get help with your insurance purchase.
            </p>

            <div class="actions">
                <button class="button button-primary" onclick="window.close()">
                    Return to Chat
                </button>
            </div>

            <div class="footer">
                MSIG Travel Insurance • No Payment Processed
            </div>
        </div>

        <script>
            // Auto-close if opened as popup
            if (window.opener) {
                setTimeout(() => {
                    window.close();
                }, 15000);
            }
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


# TODO: Add error page for payment failures
# TODO: Add loading/processing page for pending payments
# TODO: Add customization based on policy details
