---
slug: order-service-overview
title: Order Service Overview
related_entities:
  - type: service
    name: Order Service
  - type: api
    name: Order API v1
  - type: database
    name: Order Database
---
# Order Service Overview

Order Service implements Order API v1 and persists order state in Order Database.
It is on the critical path for Storefront checkout and Point of Sale capture.

## SLOs

Order Service targets a **p99 create-order latency of 250ms** in production.
