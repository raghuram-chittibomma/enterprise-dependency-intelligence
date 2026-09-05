---
slug: customer-api-notes
title: Customer API v1 Design Notes
related_entities:
  - type: api
    name: Customer API v1
  - type: service
    name: Customer Service
  - type: database
    name: Customer Database
---
# Customer API v1 Design Notes

Customer API v1 is the public contract in front of Customer Service. Profile
reads and writes ultimately land in Customer Database.

## Lifecycle

Customer API v1 has a **planned sunset in Q3 2027**; new consumers should prefer
a future v2 contract. This sunset date is architecture-doc only and is not a
graph relationship.
