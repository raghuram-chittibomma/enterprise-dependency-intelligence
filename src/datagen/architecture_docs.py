"""Synthetic Meridian architecture documents for MVP3 Hybrid Doc RAG.

Each entry becomes a markdown file under `data/sample/docs/` with YAML-like
frontmatter. Related entity names must match `scenario.py` exactly.
"""

from __future__ import annotations

from typing import TypedDict


class RelatedEntity(TypedDict):
    type: str
    name: str


class ArchDoc(TypedDict):
    slug: str
    title: str
    related_entities: list[RelatedEntity]
    body: str


ARCHITECTURE_DOCS: list[ArchDoc] = [
    {
        "slug": "storefront-architecture",
        "title": "Storefront Architecture Notes",
        "related_entities": [
            {"type": "application", "name": "Storefront"},
            {"type": "api", "name": "Product API v1"},
            {"type": "api", "name": "Customer API v1"},
        ],
        "body": """# Storefront Architecture Notes

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
""",
    },
    {
        "slug": "customer-api-notes",
        "title": "Customer API v1 Design Notes",
        "related_entities": [
            {"type": "api", "name": "Customer API v1"},
            {"type": "service", "name": "Customer Service"},
            {"type": "database", "name": "Customer Database"},
        ],
        "body": """# Customer API v1 Design Notes

Customer API v1 is the public contract in front of Customer Service. Profile
reads and writes ultimately land in Customer Database.

## Lifecycle

Customer API v1 has a **planned sunset in Q3 2027**; new consumers should prefer
a future v2 contract. This sunset date is architecture-doc only and is not a
graph relationship.
""",
    },
    {
        "slug": "order-service-overview",
        "title": "Order Service Overview",
        "related_entities": [
            {"type": "service", "name": "Order Service"},
            {"type": "api", "name": "Order API v1"},
            {"type": "database", "name": "Order Database"},
        ],
        "body": """# Order Service Overview

Order Service implements Order API v1 and persists order state in Order Database.
It is on the critical path for Storefront checkout and Point of Sale capture.

## SLOs

Order Service targets a **p99 create-order latency of 250ms** in production.
""",
    },
    {
        "slug": "order-database-runbook",
        "title": "Order Database Runbook Excerpt",
        "related_entities": [
            {"type": "database", "name": "Order Database"},
            {"type": "service", "name": "Order Service"},
            {"type": "data_pipeline", "name": "Nightly Order ETL"},
        ],
        "body": """# Order Database Runbook Excerpt

Order Database is the system of record for order headers and line items. Order
Service is the primary writer; Nightly Order ETL extracts into Analytics Warehouse.

## Backup

Order Database backup **RPO is 15 minutes** and RTO is 1 hour for region failover.
""",
    },
    {
        "slug": "payments-integration",
        "title": "Payments Integration Notes",
        "related_entities": [
            {"type": "api", "name": "Payment API v1"},
            {"type": "database", "name": "Payments Database"},
            {"type": "external_system", "name": "Stripe"},
        ],
        "body": """# Payments Integration Notes

Payment API v1 orchestrates card authorizations through Stripe and records
settlement rows in Payments Database.

## Compliance

Meridian stores only tokenized payment references; PAN data never leaves Stripe.
Card retries use exponential backoff capped at five attempts per order.
""",
    },
    {
        "slug": "inventory-service-notes",
        "title": "Inventory Service Notes",
        "related_entities": [
            {"type": "service", "name": "Inventory Service"},
            {"type": "api", "name": "Inventory API v1"},
            {"type": "database", "name": "Inventory Database"},
        ],
        "body": """# Inventory Service Notes

Inventory Service backs Inventory API v1 and Inventory Database. Warehouse
Management App and Point of Sale both depend on near-real-time availability.

## Allocation

Hard reservation of stock occurs at payment authorization, not at cart add.
""",
    },
    {
        "slug": "shipping-fulfillment",
        "title": "Shipping and Fulfillment Notes",
        "related_entities": [
            {"type": "service", "name": "Shipping Service"},
            {"type": "api", "name": "Shipping API v1"},
            {"type": "external_system", "name": "FedEx Shipping API"},
        ],
        "body": """# Shipping and Fulfillment Notes

Shipping Service implements Shipping API v1 and integrates with FedEx Shipping API
for label purchase and tracking webhooks.

## Label policy

Domestic labels default to FedEx Ground; overnight is opt-in per order flag.
""",
    },
    {
        "slug": "analytics-warehouse",
        "title": "Analytics Warehouse Notes",
        "related_entities": [
            {"type": "database", "name": "Analytics Warehouse"},
            {"type": "data_pipeline", "name": "Nightly Order ETL"},
            {"type": "report", "name": "Executive Sales Dashboard"},
        ],
        "body": """# Analytics Warehouse Notes

Analytics Warehouse is refreshed by Nightly Order ETL and feeds the Executive
Sales Dashboard.

## Freshness

Dashboard figures are **as-of 06:00 UTC** after the nightly load completes.
""",
    },
    {
        "slug": "customer-portal-notes",
        "title": "Customer Portal Notes",
        "related_entities": [
            {"type": "application", "name": "Customer Portal"},
            {"type": "api", "name": "Customer API v1"},
            {"type": "api", "name": "Order API v1"},
        ],
        "body": """# Customer Portal Notes

Customer Portal is the authenticated self-service UI. It consumes Customer API v1
for profile and Order API v1 for order history.

## Auth

Portal sessions use Meridian SSO with a 12-hour idle timeout.
""",
    },
    {
        "slug": "marketing-hub-notes",
        "title": "Marketing Automation Hub Notes",
        "related_entities": [
            {"type": "application", "name": "Marketing Automation Hub"},
            {"type": "external_system", "name": "Mailchimp"},
            {"type": "external_system", "name": "Salesforce"},
        ],
        "body": """# Marketing Automation Hub Notes

Marketing Automation Hub synchronizes campaign audiences to Mailchimp and
opportunity stages to Salesforce.

## Sync cadence

Audience sync runs hourly; opportunity sync runs every 15 minutes during business hours.
""",
    },
]
