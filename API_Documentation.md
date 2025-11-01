# Travel Insurance API Documentation

## Overview

This documentation covers two key endpoints for travel insurance distribution: **Quotation** and **Purchase**. These endpoints will be integrated via MCP (Model Context Protocol) servers for the hackathon.

---

## Authentication

All API requests require authentication via API key in the request header:

```
x-api-key: XXXXXXXXXXXXXX
```

---

## 1. Quotation Endpoint

### Purpose

Retrieve insurance quotes for travel insurance based on trip details.

### Endpoint

- **URL**: `https://dev.api.ancileo.com/v1/travel/front/pricing`
- **Method**: POST

### Supported Trip Types

- **RT** - Round Trip
- **ST** - Single Trip

### Request Structure

#### Common Fields

| Field | Type | Description |
|-------|------|-------------|
| `market` | string | Market code (e.g., "SG" for Singapore) |
| `languageCode` | string | Language preference (e.g., "en") |
| `channel` | string | Distribution channel (e.g., "white-label") |
| `deviceType` | string | Device type (e.g., "DESKTOP") |

#### Context Object

| Field | Type | Description |
|-------|------|-------------|
| `tripType` | string | "RT" (Round Trip) or "ST" (Single Trip) |
| `departureDate` | string | Format: YYYY-MM-DD - Must be greater than today |
| `returnDate` | string | Format: YYYY-MM-DD - Must be greater than today |
| `departureCountry` | string | ISO country code (e.g., "SG") |
| `arrivalCountry` | string | ISO country code (e.g., "CN") |
| `adultsCount` | integer | Number of adults |
| `childrenCount` | integer | Number of children |

### Example Requests

#### Round Trip

**JSON Request:**

```json
{
  "market": "SG",
  "languageCode": "en",
  "channel": "white-label",
  "deviceType": "DESKTOP",
  "context": {
    "tripType": "RT",
    "departureDate": "2025-09-30",
    "returnDate": "2025-10-01",
    "departureCountry": "SG",
    "arrivalCountry": "CN",
    "adultsCount": 1,
    "childrenCount": 0
  }
}
```

**cURL (for Postman import):**

```bash
curl --location 'https://dev.api.ancileo.com/v1/travel/front/pricing' \
--header 'Content-Type: application/json' \
--header 'x-api-key: XXXXXXXXXXXXXX' \
--data '{
  "market": "SG",
  "languageCode": "en",
  "channel": "white-label",
  "deviceType": "DESKTOP",
  "context": {
    "tripType": "ST",
    "departureDate": "2025-11-01",
    "returnDate": "2025-11-15",
    "departureCountry": "SG",
    "arrivalCountry": "CN",
    "adultsCount": 1,
    "childrenCount": 0
  }
}'
```

#### Single Trip

**JSON Request:**

```json
{
  "market": "SG",
  "languageCode": "en",
  "channel": "white-label",
  "deviceType": "DESKTOP",
  "context": {
    "tripType": "ST",
    "departureDate": "2025-09-30",
    "departureCountry": "SG",
    "arrivalCountry": "CN",
    "adultsCount": 1,
    "childrenCount": 0
  }
}
```

**cURL (for Postman import):**

```bash
curl --location 'https://dev.api.ancileo.com/v1/travel/front/pricing' \
--header 'Content-Type: application/json' \
--header 'x-api-key: XXXXXXXXXXXXXX' \
--data '{
  "market": "SG",
  "languageCode": "en",
  "channel": "white-label",
  "deviceType": "DESKTOP",
  "context": {
    "tripType": "ST",
    "departureDate": "2025-11-01",
    "departureCountry": "SG",
    "arrivalCountry": "CN",
    "adultsCount": 1,
    "childrenCount": 0
  }
}'
```

---

## 2. Purchase Endpoint

### Purpose

Complete the purchase of travel insurance after successful payment processing.

### Endpoint

- **URL**: `https://dev.api.ancileo.com/v1/travel/front/purchase`
- **Method**: POST

### Workflow

The purchase endpoint should be called **after payment is successful** (similar to the Whitelabel flow).

### Request Structure

#### Root Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `market` | string | Market code |
| `languageCode` | string | Language preference |
| `channel` | string | Distribution channel |
| `quoteId` | string | UUID from quotation response |

#### Purchase Offers Array

| Field | Type | Description |
|-------|------|-------------|
| `productType` | string | Product type (e.g., "travel-insurance") |
| `offerId` | string | UUID from quotation response |
| `productCode` | string | Product identifier (e.g., "SG_AXA_SCOOT_COMP") |
| `unitPrice` | number | Price per unit in local currency |
| `currency` | string | Currency code (e.g., "SGD") |
| `quantity` | integer | Quantity purchased |
| `totalPrice` | number | Total price for this offer |
| `isSendEmail` | boolean | Whether to send confirmation email |

#### Insureds Array

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for insured |
| `title` | string | Title (e.g., "Mr", "Ms") |
| `firstName` | string | First name |
| `lastName` | string | Last name |
| `nationality` | string | ISO country code |
| `dateOfBirth` | string | Format: YYYY-MM-DD |
| `passport` | string | Passport number |
| `email` | string | Email address |
| `phoneType` | string | Phone type (e.g., "mobile") |
| `phoneNumber` | string | Phone number |
| `relationship` | string | Relationship (e.g., "main") |

#### Main Contact Object

Includes all fields from Insureds plus:

| Field | Type | Description |
|-------|------|-------------|
| `address` | string | Street address |
| `city` | string | City |
| `zipCode` | string | Postal code |
| `countryCode` | string | ISO country code |

### Example Request

**JSON Request:**

```json
{
  "market": "SG",
  "languageCode": "en",
  "channel": "white-label",
  "quoteId": "1d178b7a-3058-4719-b9b5-43d2491005b4",
  "purchaseOffers": [
    {
      "productType": "travel-insurance",
      "offerId": "89cf93d9-2736-40fa-ad74-4b78c8b38590",
      "productCode": "SG_AXA_SCOOT_COMP",
      "unitPrice": 17.6,
      "currency": "SGD",
      "quantity": 1,
      "totalPrice": 17.6,
      "isSendEmail": true
    }
  ],
  "insureds": [
    {
      "id": "1",
      "title": "Mr",
      "firstName": "John",
      "lastName": "Doe",
      "nationality": "SG",
      "dateOfBirth": "2000-01-01",
      "passport": "123456",
      "email": "john.doe@gmail.com",
      "phoneType": "mobile",
      "phoneNumber": "081111111",
      "relationship": "main"
    }
  ],
  "mainContact": {
    "id": "1",
    "title": "Mr",
    "firstName": "John",
    "lastName": "Doe",
    "nationality": "SG",
    "dateOfBirth": "2000-01-01",
    "passport": "123456",
    "email": "john.doe@gmail.com",
    "phoneType": "mobile",
    "phoneNumber": "081111111",
    "address": "12 test test 12",
    "city": "SG",
    "zipCode": "12345",
    "countryCode": "SG"
  }
}
```

**cURL (for Postman import):**

```bash
curl --location 'https://dev.api.ancileo.com/v1/travel/front/purchase' \
--header 'Content-Type: application/json' \
--header 'X-API-Key: XXXXXXXXXX' \
--data-raw '{
  "market": "SG",
  "languageCode": "en",
  "channel": "white-label",
  "quoteId": "9473a27b-7c46-4870-9e33-aea613942d28",
  "purchaseOffers": [
    {
      "productType": "travel-insurance",
      "offerId": "f80dfc75-36e3-433a-b561-f182383cd342",
      "productCode": "SG_AXA_SCOOT_COMP",
      "unitPrice": 17.6,
      "currency": "SGD",
      "quantity": 1,
      "totalPrice": 17.6,
      "isSendEmail": true
    }
  ],
  "insureds": [
    {
      "id": "1",
      "title": "Mr",
      "firstName": "John",
      "lastName": "Doe",
      "nationality": "SG",
      "dateOfBirth": "2000-01-01",
      "passport": "123456",
      "email": "john.doe@gmail.com",
      "phoneType": "mobile",
      "phoneNumber": "081111111",
      "relationship": "main"
    }
  ],
  "mainContact": {
    "id": "1",
    "title": "Mr",
    "firstName": "John",
    "lastName": "Doe",
    "nationality": "SG",
    "dateOfBirth": "2000-01-01",
    "passport": "123456",
    "email": "john.doe@gmail.com",
    "phoneType": "mobile",
    "phoneNumber": "081111111",
    "address": "12 test test 12",
    "city": "SG",
    "zipCode": "12345",
    "countryCode": "SG"
  }
}'
```

---

## Notes

- The purchase endpoint should only be called after payment has been successfully processed
  - **This point must be discussed to mock it!**
- Ensure all dates are in YYYY-MM-DD format
- All timestamps should follow ISO 8601 format
- The `quoteId` and `offerId` must be obtained from a prior quotation request
