---
slug: storefront-architecture
title: Storefront Architecture Notes
related_entities:
  - type: application
    name: Storefront
  - type: api
    name: Product API v1
  - type: api
    name: Customer API v1
---
# Storefront Architecture Notes

The Meridian Storefront is the customer-facing commerce UI. It consumes
Product API v1 for catalog browsing and Customer API v1 for session profile
lookups during checkout.

## Operations

Storefront uses a **blue-green deploy window every Tuesday at 02:00 UTC**.
That maintenance window is documented here only — it is not represented as a
graph edge. Traffic switches after smoke checks on the green slot pass.

## Resilience

Checkout degradation mode serves a cached catalog for up to 15 minutes if
Product API v1 is unavailable.
