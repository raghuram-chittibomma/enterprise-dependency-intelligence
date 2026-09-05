---
slug: customer-portal-notes
title: Customer Portal Notes
related_entities:
  - type: application
    name: Customer Portal
  - type: api
    name: Customer API v1
  - type: api
    name: Order API v1
---
# Customer Portal Notes

Customer Portal is the authenticated self-service UI. It consumes Customer API v1
for profile and Order API v1 for order history.

## Auth

Portal sessions use Meridian SSO with a 12-hour idle timeout.
