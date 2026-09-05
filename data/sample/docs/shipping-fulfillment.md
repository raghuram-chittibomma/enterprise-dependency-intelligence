---
slug: shipping-fulfillment
title: Shipping and Fulfillment Notes
related_entities:
  - type: service
    name: Shipping Service
  - type: api
    name: Shipping API v1
  - type: external_system
    name: FedEx Shipping API
---
# Shipping and Fulfillment Notes

Shipping Service implements Shipping API v1 and integrates with FedEx Shipping API
for label purchase and tracking webhooks.

## Label policy

Domestic labels default to FedEx Ground; overnight is opt-in per order flag.
