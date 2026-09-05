---
slug: inventory-service-notes
title: Inventory Service Notes
related_entities:
  - type: service
    name: Inventory Service
  - type: api
    name: Inventory API v1
  - type: database
    name: Inventory Database
---
# Inventory Service Notes

Inventory Service backs Inventory API v1 and Inventory Database. Warehouse
Management App and Point of Sale both depend on near-real-time availability.

## Allocation

Hard reservation of stock occurs at payment authorization, not at cart add.
