# Quotation

## tripType: Round Trip (RT)

req:

```json
{
  "market": "SG",
  "languageCode": "en",
  "channel": "white-label",
  "deviceType": "DESKTOP",
  "context": {
    "tripType": "RT",
    "departureDate": "2025-11-03",
    "returnDate": "2025-11-16",
    "departureCountry": "SG",
    "arrivalCountry": "CN",
    "adultsCount": 1,
    "childrenCount": 0
  }
}
```

res:

```json
{
  "id": "87350109-e351-458b-bb9e-5b8d8b41901f",
  "languageCode": "en",
  "offerCategories": [
    {
      "productType": "travel-insurance",
      "defaultSelectedOffer": null,
      "optOutLabel": null,
      "optOutEltClass": "velocity-travel-insurance-out",
      "offers": [
        {
          "id": "6ae64268-aae9-4724-9ff3-57e0292458f9",
          "productCode": "SG_AXA_SCOOT_COMP",
          "unitPrice": 65.88,
          "priceBreakdown": {
            "priceExc": 65.88,
            "priceInc": 65.88,
            "totalTaxes": 0,
            "paxSplit": [],
            "otherTaxesSplit": 0,
            "commissions": {},
            "priceNoDiscountExc": 65.88,
            "priceNoDiscountInc": 65.88,
            "priceNoDiscount": 65.88,
            "discount": {
              "value": 0,
              "is_percentage": 1
            },
            "salesTax": 0,
            "stampDuty": 0,
            "otherTaxes": []
          },
          "coverDates": {
            "from": "2025-11-03",
            "to": "2025-11-16"
          },
          "coverDateTimes": {
            "from": "2025-11-03T00:00:00+00:00",
            "to": "2025-11-16T23:59:59+00:00"
          },
          "currency": "SGD",
          "optInEltClass": "velocity-travel-insurance-6ae64268-aae9-4724-9ff3-57e0292458f9-in",
          "productInformation": {
            "title": "Scootsurance - Travel Insurance",
            "description": "{\n    \"heading\": \"Scootsurance\",\n    \"subheading\": \"Underwritten by MSIG Insurance (Singapore) Pte Ltd\",\n    \"benefits\": {\n        \"heading\": \"We've got you covered even in difficult times... now enhanced with Covid-19 benefits!\",\n        \"benefitList\": [\n            {\"title\": \"Trip cancellation / curtailment\", \"tooltip\": \"Your irrecoverable travel fare and accommodation will be reimbursed up to the Sum Insured if you have to cancel/curtail your trip due to covered reasons such as being infected with Covid-19.\"},\n            {\"title\": \"Overseas hospitalization / quarantine allowance\", \"tooltip\": \"Receive a daily cash benefit if you're hospitalized/quarantined due to Covid-19.\"},\n            {\"title\": \"Overseas medical expenses\", \"tooltip\": \"Enjoy your trip to the fullest knowing that you will be covered up to the Sum Insured for overseas medical expenses incurred due to an accidental bodily injury or sickness, including Covid-19.\"},\n            {\"title\": \"Medical evacuation / repatriation\", \"tooltip\": \"You can count on us in the event that you are in an emergency medical situation and need to be moved to another location to receive urgent treatment or to be repatriated to Singapore.\"},\n            {\"title\": \"24/7 emergency medical assistance hotline\", \"tooltip\": \"We are here for you round-the-clock! You can call the MSIG Assist 24-hour hotline in the event that you are in an emergency medical situation.\"},\n            {\"title\": \"24/7 travel assistance hotline\", \"tooltip\": \"You can call the MSIG Assist 24-hour hotline at any time for travel assistance.\"}\n        ]\n    },\n    \"selection\": {\n        \"heading\": \"<p>*Covid-19 benefits will become null and void if you, family member, traveling companion or the family you are staying with during the trip is already infected with Covid-19 at the point of purchase or you are commencing a trip against any government's travel advisory. Trip cancellation cover does not apply in the event of a travel ban due to Covid-19.</p><a class='external-link' target='_blank' href='https://static.dev.wl.ancileo.com/axa/scoot/sg/doc/Scootsurance_Table_of_benefits.pdf'>Click here</a> to view the complete table of benefits! <br/><br/>Why tango with lady luck when you can have <b>Scootsurance</b>?\",\n        \"options\": {\n            \"yes\": \"Yes, I would like to be protected by Scootsurance! I accept the <a class='external-link' target='_blank' href='https://static.dev.wl.ancileo.com/axa/scoot/sg/doc/PolicyWording.pdf/'>terms & conditions</a> and <a class='external-link' target='_blank' href='https://www.msig.com.sg/privacy-cookies-policy/'>privacy policy.</a>\",\n            \"no\": \"No, I'll take my chances.\"\n        }\n    },\n    \"supportMessage\": \"<a class='external-link' target='_blank' href='https://static.dev.wl.ancileo.com/axa/scoot/sg/doc/Scootsurance_Table_of_benefits.pdf'>Click here</a> to view the complete table of benefits! <br/><br/><p>Scootsurance is covered under the Policy Owners' Protection Scheme which is administered by the Singapore Deposit Insurance Corporation (SDIC). Coverage for your policy is automatic and no further action is required from you. For more information on the types of benefits that are covered under the scheme as well as the limits of coverage, where applicable, please contact your insurer or visit the GIA/LIA or SDIC websites (<a class='external-link' target='_blank' href='https://www.gia.org.sg/'>www.gia.org.sg</a> or <a class='external-link' target='_blank' href='https://www.lia.org.sg/'>www.lia.org.sg</a> or <a class='external-link' target='_blank' href='https://www.sdic.org.sg/'>www.sdic.org.sg</a>).</p>\",\n    \"inPartnershipWith\": \"<img src='https://static.dev.wl.ancileo.com/axa/scoot/sg/images/msig_logo.png' /><br/>\",\n    \"tableofBenefitsPdfUrl\": \"https://static.dev.wl.ancileo.com/axa/scoot/sg/doc/Scootsurance_Table_of_benefits.pdf\",\n    \"insuranceProvider\": \"AXA\"\n}",
            "imageURL": null,
            "benefits": "",
            "optInLabel": null,
            "attributes": {
              "attribute1": "Scootsurance - Travel Insurance"
            },
            "tcsUrl": "https://static.dev.wl.ancileo.com/axa/scoot/sg/doc/PolicyWording.pdf/",
            "datasheetUrl": "",
            "contractProductCode": null,
            "minBookingClass": null,
            "maxBookingClass": null,
            "isRenewable": 0,
            "extras": []
          },
          "options": []
        }
      ]
    }
  ]
}
```

## tripType: Single Trip (ST)

req:

```json
{
  "market": "SG",
  "languageCode": "en",
  "channel": "white-label",
  "deviceType": "DESKTOP",
  "context": {
    "tripType": "ST",
    "departureDate": "2025-11-03",
    "returnDate": "2025-11-16",
    "departureCountry": "SG",
    "arrivalCountry": "CN",
    "adultsCount": 1,
    "childrenCount": 0
  }
}
```

res:

```json
{
  "id": "c6dae132-6ad4-45e4-b57a-79b69d63606c",
  "languageCode": "en",
  "offerCategories": [
    {
      "productType": "travel-insurance",
      "defaultSelectedOffer": null,
      "optOutLabel": null,
      "optOutEltClass": "velocity-travel-insurance-out",
      "offers": [
        {
          "id": "1fec0770-18ca-47de-b766-7240581da19e",
          "productCode": "SG_AXA_SCOOT_COMP",
          "unitPrice": 17.6,
          "priceBreakdown": {
            "priceExc": 17.6,
            "priceInc": 17.6,
            "totalTaxes": 0,
            "paxSplit": [],
            "otherTaxesSplit": 0,
            "commissions": {},
            "priceNoDiscountExc": 17.6,
            "priceNoDiscountInc": 17.6,
            "priceNoDiscount": 17.6,
            "discount": {
              "value": 0,
              "is_percentage": 1
            },
            "salesTax": 0,
            "stampDuty": 0,
            "otherTaxes": []
          },
          "coverDates": {
            "from": "2025-11-03",
            "to": "2025-11-16"
          },
          "coverDateTimes": {
            "from": "2025-11-03T00:00:00+00:00",
            "to": "2025-11-16T23:59:59+00:00"
          },
          "currency": "SGD",
          "optInEltClass": "velocity-travel-insurance-1fec0770-18ca-47de-b766-7240581da19e-in",
          "productInformation": {
            "title": "Scootsurance - Travel Insurance",
            "description": "{\n    \"heading\": \"Scootsurance\",\n    \"subheading\": \"Underwritten by MSIG Insurance (Singapore) Pte Ltd\",\n    \"benefits\": {\n        \"heading\": \"We've got you covered even in difficult times... now enhanced with Covid-19 benefits!\",\n        \"benefitList\": [\n            {\"title\": \"Trip cancellation / curtailment\", \"tooltip\": \"Your irrecoverable travel fare and accommodation will be reimbursed up to the Sum Insured if you have to cancel/curtail your trip due to covered reasons such as being infected with Covid-19.\"},\n            {\"title\": \"Overseas hospitalization / quarantine allowance\", \"tooltip\": \"Receive a daily cash benefit if you're hospitalized/quarantined due to Covid-19.\"},\n            {\"title\": \"Overseas medical expenses\", \"tooltip\": \"Enjoy your trip to the fullest knowing that you will be covered up to the Sum Insured for overseas medical expenses incurred due to an accidental bodily injury or sickness, including Covid-19.\"},\n            {\"title\": \"Medical evacuation / repatriation\", \"tooltip\": \"You can count on us in the event that you are in an emergency medical situation and need to be moved to another location to receive urgent treatment or to be repatriated to Singapore.\"},\n            {\"title\": \"24/7 emergency medical assistance hotline\", \"tooltip\": \"We are here for you round-the-clock! You can call the MSIG Assist 24-hour hotline in the event that you are in an emergency medical situation.\"},\n            {\"title\": \"24/7 travel assistance hotline\", \"tooltip\": \"You can call the MSIG Assist 24-hour hotline at any time for travel assistance.\"}\n        ]\n    },\n    \"selection\": {\n        \"heading\": \"<p>*Covid-19 benefits will become null and void if you, family member, traveling companion or the family you are staying with during the trip is already infected with Covid-19 at the point of purchase or you are commencing a trip against any government's travel advisory. Trip cancellation cover does not apply in the event of a travel ban due to Covid-19.</p><a class='external-link' target='_blank' href='https://static.dev.wl.ancileo.com/axa/scoot/sg/doc/Scootsurance_Table_of_benefits.pdf'>Click here</a> to view the complete table of benefits! <br/><br/>Why tango with lady luck when you can have <b>Scootsurance</b>?\",\n        \"options\": {\n            \"yes\": \"Yes, I would like to be protected by Scootsurance! I accept the <a class='external-link' target='_blank' href='https://static.dev.wl.ancileo.com/axa/scoot/sg/doc/PolicyWording.pdf/'>terms & conditions</a> and <a class='external-link' target='_blank' href='https://www.msig.com.sg/privacy-cookies-policy/'>privacy policy.</a>\",\n            \"no\": \"No, I'll take my chances.\"\n        }\n    },\n    \"supportMessage\": \"<a class='external-link' target='_blank' href='https://static.dev.wl.ancileo.com/axa/scoot/sg/doc/Scootsurance_Table_of_benefits.pdf'>Click here</a> to view the complete table of benefits! <br/><br/><p>Scootsurance is covered under the Policy Owners' Protection Scheme which is administered by the Singapore Deposit Insurance Corporation (SDIC). Coverage for your policy is automatic and no further action is required from you. For more information on the types of benefits that are covered under the scheme as well as the limits of coverage, where applicable, please contact your insurer or visit the GIA/LIA or SDIC websites (<a class='external-link' target='_blank' href='https://www.gia.org.sg/'>www.gia.org.sg</a> or <a class='external-link' target='_blank' href='https://www.lia.org.sg/'>www.lia.org.sg</a> or <a class='external-link' target='_blank' href='https://www.sdic.org.sg/'>www.sdic.org.sg</a>).</p>\",\n    \"inPartnershipWith\": \"<img src='https://static.dev.wl.ancileo.com/axa/scoot/sg/images/msig_logo.png' /><br/>\",\n    \"tableofBenefitsPdfUrl\": \"https://static.dev.wl.ancileo.com/axa/scoot/sg/doc/Scootsurance_Table_of_benefits.pdf\",\n    \"insuranceProvider\": \"AXA\"\n}",
            "imageURL": null,
            "benefits": "",
            "optInLabel": null,
            "attributes": {
              "attribute1": "Scootsurance - Travel Insurance"
            },
            "tcsUrl": "https://static.dev.wl.ancileo.com/axa/scoot/sg/doc/PolicyWording.pdf/",
            "datasheetUrl": "",
            "contractProductCode": null,
            "minBookingClass": null,
            "maxBookingClass": null,
            "isRenewable": 0,
            "extras": []
          },
          "options": []
        }
      ]
    }
  ]
}
```

# Purchase

req:

```json
{
  {
  "market": "SG",
  "languageCode": "en",
  "channel": "white-label",
  "quoteId": "89e57de5-83e9-4f17-988f-1adceafc2e58",
  "purchaseOffers": [
    {
      "productType": "travel-insurance",
      "offerId": "4171cded-12fd-4598-9a50-9a02eb56d049",
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
}
```

res:

```json
{
  "id": "139cd7c3-c361-420c-a6ee-cc5b239b0ed0",
  "quoteId": "89e57de5-83e9-4f17-988f-1adceafc2e58",
  "purchasedOffers": [
    {
      "productType": "travel-insurance",
      "offerId": "4171cded-12fd-4598-9a50-9a02eb56d049",
      "productCode": "SG_AXA_SCOOT_COMP",
      "unitPrice": 17.6,
      "currency": "SGD",
      "quantity": 1,
      "totalPrice": 17.6,
      "purchasedOfferId": "870000001-18261",
      "coverDates": {
        "from": "2025-11-03",
        "to": "2025-11-16"
      },
      "coverDateTimes": {
        "from": "2025-11-03T00:00:00+00:00",
        "to": "2025-11-16T23:59:59+00:00"
      }
    }
  ]
}
```
