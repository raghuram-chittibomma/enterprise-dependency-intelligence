---
slug: payments-integration
title: Payments Integration Notes
related_entities:
  - type: api
    name: Payment API v1
  - type: database
    name: Payments Database
  - type: external_system
    name: Stripe
---
# Payments Integration Notes

Payment API v1 orchestrates card authorizations through Stripe and records
settlement rows in Payments Database.

## Compliance

Meridian stores only tokenized payment references; PAN data never leaves Stripe.
Card retries use exponential backoff capped at five attempts per order.
