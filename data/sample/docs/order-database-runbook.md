---
slug: order-database-runbook
title: Order Database Runbook Excerpt
related_entities:
  - type: database
    name: Order Database
  - type: service
    name: Order Service
  - type: data_pipeline
    name: Nightly Order ETL
---
# Order Database Runbook Excerpt

Order Database is the system of record for order headers and line items. Order
Service is the primary writer; Nightly Order ETL extracts into Analytics Warehouse.

## Backup

Order Database backup **RPO is 15 minutes** and RTO is 1 hour for region failover.
