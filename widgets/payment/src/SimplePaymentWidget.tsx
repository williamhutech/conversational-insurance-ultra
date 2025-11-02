import React from 'react'

interface PaymentData {
  payment_intent_id: string
  checkout_url: string
  product_name: string
  amount: string
  currency: string
  status: string
}

// Extend Window interface to include openai
declare global {
  interface Window {
    openai?: {
      toolOutput?: PaymentData
    }
  }
}

export default function SimplePaymentWidget() {
  // Access data from ChatGPT runtime
  const data = window.openai?.toolOutput

  if (!data) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: '#6b7280' }}>
        Loading payment data...
      </div>
    )
  }

  const statusColor =
    data.status === 'succeeded' ? '#10b981' :
    data.status === 'pending' ? '#f59e0b' :
    data.status === 'failed' ? '#ef4444' : '#6b7280'

  return (
    <div style={{
      maxWidth: '400px',
      border: '1px solid #e5e7eb',
      borderRadius: '8px',
      padding: '20px',
      fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      backgroundColor: '#ffffff'
    }}>
      {/* Header */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '8px'
        }}>
          <span style={{ fontSize: '12px', color: '#6b7280', fontWeight: '500' }}>
            Insurance Checkout
          </span>
          <span style={{
            fontSize: '12px',
            padding: '4px 8px',
            borderRadius: '4px',
            backgroundColor: `${statusColor}20`,
            color: statusColor,
            fontWeight: '600',
            textTransform: 'uppercase'
          }}>
            {data.status}
          </span>
        </div>
        <h3 style={{
          margin: 0,
          fontSize: '18px',
          fontWeight: '600',
          color: '#111827'
        }}>
          {data.product_name}
        </h3>
      </div>

      {/* Divider */}
      <hr style={{
        border: 'none',
        borderTop: '1px solid #e5e7eb',
        margin: '16px 0'
      }} />

      {/* Price Breakdown */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginBottom: '8px'
        }}>
          <span style={{ fontSize: '14px', color: '#374151' }}>Amount</span>
          <span style={{ fontSize: '14px', color: '#111827', fontWeight: '500' }}>
            {data.currency} {data.amount}
          </span>
        </div>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginBottom: '8px'
        }}>
          <span style={{ fontSize: '14px', color: '#374151' }}>Sales Tax</span>
          <span style={{ fontSize: '14px', color: '#6b7280' }}>N.A.</span>
        </div>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          paddingTop: '8px',
          borderTop: '1px solid #f3f4f6'
        }}>
          <span style={{ fontSize: '14px', color: '#111827', fontWeight: '600' }}>
            Total Amount
          </span>
          <span style={{ fontSize: '14px', color: '#111827', fontWeight: '600' }}>
            {data.currency} {data.amount}
          </span>
        </div>
      </div>

      {/* Divider */}
      <hr style={{
        border: 'none',
        borderTop: '1px solid #e5e7eb',
        margin: '16px 0'
      }} />

      {/* Action Button */}
      <div>
        <a
          href={data.checkout_url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'block',
            width: '100%',
            padding: '12px 16px',
            backgroundColor: '#3b82f6',
            color: 'white',
            textAlign: 'center',
            borderRadius: '6px',
            textDecoration: 'none',
            fontWeight: '600',
            fontSize: '14px',
            marginBottom: '12px',
            transition: 'background-color 0.2s',
            boxSizing: 'border-box'
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.backgroundColor = '#2563eb'
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.backgroundColor = '#3b82f6'
          }}
        >
          Pay via Stripe →
        </a>
        <div style={{
          fontSize: '12px',
          color: '#9ca3af',
          textAlign: 'center'
        }}>
          Payment ID: {data.payment_intent_id.substring(0, 20)}...
        </div>
      </div>
    </div>
  )
}
