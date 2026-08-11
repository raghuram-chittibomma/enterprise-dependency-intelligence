"""The "Meridian Retail Group" MVP1 scenario — the single source of truth for
every synthetic entity/relationship in this project.

This is **hand-authored, not randomized** — determinism here means "the same
data every run," which is a stronger and simpler guarantee than a seeded
random generator, and it's what makes it possible to hand-write an exact-match
golden dataset (`evals/`) against this data in increment-15. If the scenario
ever needs to grow, extend the lists below (and update any golden scenarios
that assert exact counts) rather than introducing randomness.

Every name referenced in a "systems_owned" / "consuming_applications" /
"readers" / "writers" / "backend_service" / integration row below must exactly
match an entity `name` defined in this file — see `tests/unit/test_scenario.py`
for the cross-reference check that enforces this.

Fictional company only. No real company, customer, or personal data — see
`docs/00_project/PROJECT_CHARTER.md` and the `synthetic-data-design` skill.
"""

from __future__ import annotations

from typing import Literal, TypedDict

from src.ingestion.capability_taxonomy import CAPABILITY_AREAS

__all__ = [
    "APIS",
    "APPLICATIONS",
    "CAPABILITY_AREAS",
    "DATABASES",
    "DATA_PIPELINES",
    "INTEGRATIONS",
    "REPORTS",
    "SERVICES",
    "TEAM_OWNERSHIP",
    "SystemRef",
]


class SystemRef(TypedDict):
    name: str
    type: Literal["application", "service", "api", "database", "data_pipeline", "report"]


# Business capabilities are not their own source file — they're derived from
# the `business_capability` field on CMDB and API Catalog records the first
# time each capability name is seen. `CAPABILITY_AREAS` (imported above from
# `src/ingestion/capability_taxonomy.py`, ingestion's own reference data) is
# what supplies the `capability_area` grouping property those records don't
# otherwise carry -- re-exported here so scenario cross-reference tests can
# check every `business_capability` value used below is a known capability.

# --------------------------------------------------------------------------
# Source 1: CMDB / Technology Inventory (-> data/sample/cmdb.csv)
# Covers Application, Service, DataPipeline, and Report node types — a real
# enterprise CMDB commonly tracks all deployable/schedulable technology
# assets, not just user-facing applications.
# --------------------------------------------------------------------------

APPLICATIONS: list[dict[str, str]] = [
    {
        "record_id": "APP-001",
        "name": "Storefront",
        "description": "Customer-facing e-commerce storefront web application.",
        "criticality": "critical",
        "lifecycle_status": "active",
        "environment": "prod",
        "technology": "React / Node.js",
        "business_capability": "Product Catalog",
    },
    {
        "record_id": "APP-002",
        "name": "Order Management",
        "description": "Internal application for managing and tracking customer orders.",
        "criticality": "critical",
        "lifecycle_status": "active",
        "environment": "prod",
        "technology": "Java / Spring Boot",
        "business_capability": "Order Management",
    },
    {
        "record_id": "APP-003",
        "name": "Customer Portal",
        "description": "Self-service portal where customers manage their account and orders.",
        "criticality": "high",
        "lifecycle_status": "active",
        "environment": "prod",
        "technology": "React / Node.js",
        "business_capability": "Customer Management",
    },
    {
        "record_id": "APP-004",
        "name": "Admin Console",
        "description": "Internal back-office admin tool for customer support and operations staff.",
        "criticality": "medium",
        "lifecycle_status": "active",
        "environment": "prod",
        "technology": "Angular / .NET",
        "business_capability": "Customer Management",
    },
    {
        "record_id": "APP-005",
        "name": "Warehouse Management App",
        "description": "Warehouse floor application for picking, packing, and inventory counts.",
        "criticality": "high",
        "lifecycle_status": "active",
        "environment": "prod",
        "technology": "Java",
        "business_capability": "Fulfillment & Shipping",
    },
    {
        "record_id": "APP-006",
        "name": "Point of Sale",
        "description": "In-store point-of-sale application (handheld + register).",
        "criticality": "critical",
        "lifecycle_status": "active",
        "environment": "prod",
        "technology": "Kotlin (Android) + Java backend",
        "business_capability": "Product Catalog",
    },
    {
        "record_id": "APP-007",
        "name": "Marketing Automation Hub",
        "description": "Marketing campaign builder and customer segmentation tool.",
        "criticality": "medium",
        "lifecycle_status": "deprecated",
        "environment": "prod",
        "technology": "Python / Django",
        "business_capability": "Customer Management",
        # REPLACED_BY: -> Customer Engagement Platform (APP-008), both "application".
        "replaced_by": "Customer Engagement Platform",
    },
    {
        "record_id": "APP-008",
        "name": "Customer Engagement Platform",
        "description": "Next-gen customer engagement platform replacing Marketing Automation Hub.",
        "criticality": "medium",
        "lifecycle_status": "planned",
        "environment": "staging",
        "technology": "Python / Django + Segment",
        "business_capability": "Customer Management",
    },
]

SERVICES: list[dict[str, str]] = [
    {
        "record_id": "SVC-001",
        "name": "Order Service",
        "description": "Backend service owning order creation, state, and history.",
        "criticality": "critical",
        "lifecycle_status": "active",
        "environment": "prod",
        "technology": "Java / Spring Boot",
        "business_capability": "Order Management",
    },
    {
        "record_id": "SVC-002",
        "name": "Customer Service",
        "description": "Backend service owning customer profile and account data.",
        "criticality": "critical",
        "lifecycle_status": "active",
        "environment": "prod",
        "technology": "Python / FastAPI",
        "business_capability": "Customer Management",
    },
    {
        "record_id": "SVC-003",
        "name": "Inventory Service",
        "description": "Backend service tracking stock levels across warehouses.",
        "criticality": "high",
        "lifecycle_status": "active",
        "environment": "prod",
        "technology": "Go",
        "business_capability": "Inventory Management",
    },
    {
        "record_id": "SVC-004",
        "name": "Pricing Service",
        "description": "Backend service owning product catalog and pricing rules.",
        "criticality": "high",
        "lifecycle_status": "active",
        "environment": "prod",
        "technology": "Java",
        "business_capability": "Product Catalog",
    },
    {
        "record_id": "SVC-005",
        "name": "Shipping Service",
        "description": "Backend service coordinating shipment creation and carrier handoff.",
        "criticality": "high",
        "lifecycle_status": "active",
        "environment": "prod",
        "technology": "Go",
        "business_capability": "Fulfillment & Shipping",
    },
]

DATA_PIPELINES: list[dict[str, str]] = [
    {
        "record_id": "PIPE-001",
        "name": "Nightly Order ETL",
        "description": "Nightly extract of order data into the analytics warehouse.",
        "criticality": "medium",
        "lifecycle_status": "active",
        "pipeline_type": "etl",
        "schedule": "0 2 * * *",
    },
    {
        "record_id": "PIPE-002",
        "name": "Customer Data Sync",
        "description": "Hourly sync of customer profile changes into the analytics warehouse.",
        "criticality": "medium",
        "lifecycle_status": "active",
        "pipeline_type": "batch_job",
        "schedule": "hourly",
    },
    {
        "record_id": "PIPE-003",
        "name": "Inventory Reconciliation ETL",
        "description": "Nightly reconciliation of warehouse inventory counts into analytics.",
        "criticality": "medium",
        "lifecycle_status": "active",
        "pipeline_type": "etl",
        "schedule": "0 3 * * *",
    },
]

REPORTS: list[dict[str, str]] = [
    {
        "record_id": "RPT-001",
        "name": "Executive Sales Dashboard",
        "description": "Daily executive-facing sales and revenue dashboard.",
        "criticality": "medium",
        "lifecycle_status": "active",
        "audience": "executive",
        "refresh_frequency": "daily",
    },
    {
        "record_id": "RPT-002",
        "name": "Inventory Health Report",
        "description": "Weekly report on stock-out risk and slow-moving inventory.",
        "criticality": "low",
        "lifecycle_status": "active",
        "audience": "internal-ops",
        "refresh_frequency": "weekly",
    },
]

# --------------------------------------------------------------------------
# Source 2: API Catalog (-> data/sample/api_catalog.json)
# --------------------------------------------------------------------------

APIS: list[dict[str, object]] = [
    {
        "record_id": "API-001",
        "name": "Customer API v1",
        "version": "v1",
        "protocol": "REST",
        "criticality": "critical",
        "lifecycle_status": "active",
        "implementing_application": "Customer Service",
        "backend_service": "Customer Service",
        "consuming_applications": [
            {"name": "Storefront", "type": "application"},
            {"name": "Customer Portal", "type": "application"},
            {"name": "Order Service", "type": "service"},
        ],
        "business_capability": "Customer Management",
    },
    {
        "record_id": "API-002",
        "name": "Order API v1",
        "version": "v1",
        "protocol": "REST",
        "criticality": "critical",
        "lifecycle_status": "active",
        "implementing_application": "Order Service",
        "backend_service": "Order Service",
        "consuming_applications": [
            {"name": "Storefront", "type": "application"},
            {"name": "Point of Sale", "type": "application"},
            {"name": "Order Management", "type": "application"},
        ],
        "business_capability": "Order Management",
    },
    {
        "record_id": "API-003",
        "name": "Product API v1",
        "version": "v1",
        "protocol": "REST",
        "criticality": "high",
        "lifecycle_status": "active",
        "implementing_application": "Pricing Service",
        "backend_service": "Pricing Service",
        "consuming_applications": [
            {"name": "Storefront", "type": "application"},
            {"name": "Point of Sale", "type": "application"},
            {"name": "Order Management", "type": "application"},
        ],
        "business_capability": "Product Catalog",
    },
    {
        "record_id": "API-004",
        "name": "Inventory API v1",
        "version": "v1",
        "protocol": "REST",
        "criticality": "high",
        "lifecycle_status": "active",
        "implementing_application": "Inventory Service",
        "backend_service": "Inventory Service",
        "consuming_applications": [
            {"name": "Order Management", "type": "application"},
            {"name": "Warehouse Management App", "type": "application"},
            {"name": "Point of Sale", "type": "application"},
        ],
        "business_capability": "Inventory Management",
    },
    {
        "record_id": "API-005",
        "name": "Payment API v1",
        "version": "v1",
        "protocol": "REST",
        "criticality": "critical",
        "lifecycle_status": "active",
        # No backend_service: this API is a thin facade with its own direct
        # database access (see db_metadata) rather than fronting a service.
        "implementing_application": None,
        "backend_service": None,
        "consuming_applications": [
            {"name": "Order Management", "type": "application"},
            {"name": "Point of Sale", "type": "application"},
        ],
        "business_capability": "Payments & Billing",
    },
    {
        "record_id": "API-006",
        "name": "Shipping API v1",
        "version": "v1",
        "protocol": "REST",
        "criticality": "high",
        "lifecycle_status": "active",
        "implementing_application": "Shipping Service",
        "backend_service": "Shipping Service",
        "consuming_applications": [
            {"name": "Order Management", "type": "application"},
            {"name": "Warehouse Management App", "type": "application"},
        ],
        "business_capability": "Fulfillment & Shipping",
    },
]

# --------------------------------------------------------------------------
# Source 3: Database Metadata (-> data/sample/db_metadata.json)
# --------------------------------------------------------------------------

DATABASES: list[dict[str, object]] = [
    {
        "record_id": "DB-001",
        "name": "Customer Database",
        "engine": "PostgreSQL",
        "key_tables": ["customers", "customer_addresses", "customer_preferences"],
        "criticality": "critical",
        "lifecycle_status": "active",
        "writers": [{"name": "Customer Service", "type": "service"}],
        "readers": [
            {"name": "Customer Service", "type": "service"},
            {"name": "Admin Console", "type": "application"},
            {"name": "Marketing Automation Hub", "type": "application"},
            {"name": "Customer Data Sync", "type": "data_pipeline"},
        ],
    },
    {
        "record_id": "DB-002",
        "name": "Order Database",
        "engine": "PostgreSQL",
        "key_tables": ["orders", "order_items"],
        "criticality": "critical",
        "lifecycle_status": "active",
        "writers": [{"name": "Order Service", "type": "service"}],
        "readers": [
            {"name": "Order Service", "type": "service"},
            {"name": "Order Management", "type": "application"},
            {"name": "Nightly Order ETL", "type": "data_pipeline"},
        ],
    },
    {
        "record_id": "DB-003",
        "name": "Product Database",
        "engine": "MySQL",
        "key_tables": ["products", "categories", "pricing_rules"],
        "criticality": "high",
        "lifecycle_status": "active",
        "writers": [{"name": "Pricing Service", "type": "service"}],
        "readers": [
            {"name": "Pricing Service", "type": "service"},
            {"name": "Point of Sale", "type": "application"},
        ],
    },
    {
        "record_id": "DB-004",
        "name": "Inventory Database",
        "engine": "PostgreSQL",
        "key_tables": ["inventory_levels", "warehouses"],
        "criticality": "high",
        "lifecycle_status": "active",
        "writers": [
            {"name": "Inventory Service", "type": "service"},
            {"name": "Warehouse Management App", "type": "application"},
        ],
        "readers": [
            {"name": "Inventory Service", "type": "service"},
            {"name": "Warehouse Management App", "type": "application"},
            {"name": "Inventory Reconciliation ETL", "type": "data_pipeline"},
            {"name": "Inventory Health Report", "type": "report"},
        ],
    },
    {
        "record_id": "DB-005",
        "name": "Payments Database",
        "engine": "PostgreSQL",
        "key_tables": ["transactions", "refunds"],
        "criticality": "critical",
        "lifecycle_status": "active",
        "writers": [{"name": "Payment API v1", "type": "api"}],
        "readers": [{"name": "Payment API v1", "type": "api"}],
    },
    {
        "record_id": "DB-006",
        "name": "Analytics Warehouse",
        "engine": "Snowflake",
        "key_tables": ["fact_orders", "fact_customers", "fact_inventory"],
        "criticality": "medium",
        "lifecycle_status": "active",
        "writers": [
            {"name": "Nightly Order ETL", "type": "data_pipeline"},
            {"name": "Customer Data Sync", "type": "data_pipeline"},
            {"name": "Inventory Reconciliation ETL", "type": "data_pipeline"},
        ],
        "readers": [
            {"name": "Executive Sales Dashboard", "type": "report"},
            {"name": "Inventory Health Report", "type": "report"},
        ],
    },
]

# --------------------------------------------------------------------------
# Source 4: Team Ownership (-> data/sample/team_ownership.json)
# The authoritative (and only) source of OWNED_BY edges — no other source
# carries an "owning_team" field, so ownership can never conflict across
# sources. Not every entity has an owner: Team, BusinessCapability, and
# ExternalSystem are intentionally left unowned in MVP1 (see
# `docs/01_architecture/DATA_MODEL.md`).
# --------------------------------------------------------------------------

TEAM_OWNERSHIP: list[dict[str, object]] = [
    {
        "team_id": "TEAM-001",
        "name": "Commerce Platform Team",
        "business_area": "Commerce",
        "description": "Owns the storefront, point-of-sale, and product/pricing platform.",
        "architecture_contact": "[email protected]",
        "support_contact": "[email protected]",
        "systems_owned": [
            {"name": "Storefront", "type": "application"},
            {"name": "Point of Sale", "type": "application"},
            {"name": "Pricing Service", "type": "service"},
            {"name": "Product API v1", "type": "api"},
            {"name": "Product Database", "type": "database"},
        ],
    },
    {
        "team_id": "TEAM-002",
        "name": "Order & Fulfillment Team",
        "business_area": "Operations",
        "description": "Owns order management, inventory, and shipping.",
        "architecture_contact": "[email protected]",
        "support_contact": "[email protected]",
        "systems_owned": [
            {"name": "Order Management", "type": "application"},
            {"name": "Warehouse Management App", "type": "application"},
            {"name": "Order Service", "type": "service"},
            {"name": "Inventory Service", "type": "service"},
            {"name": "Shipping Service", "type": "service"},
            {"name": "Order API v1", "type": "api"},
            {"name": "Inventory API v1", "type": "api"},
            {"name": "Shipping API v1", "type": "api"},
            {"name": "Order Database", "type": "database"},
            {"name": "Inventory Database", "type": "database"},
        ],
    },
    {
        "team_id": "TEAM-003",
        "name": "Customer Experience Team",
        "business_area": "Customer",
        "description": "Owns customer-facing account, support, and engagement surfaces.",
        "architecture_contact": "[email protected]",
        "support_contact": "[email protected]",
        "systems_owned": [
            {"name": "Customer Portal", "type": "application"},
            {"name": "Admin Console", "type": "application"},
            {"name": "Marketing Automation Hub", "type": "application"},
            {"name": "Customer Engagement Platform", "type": "application"},
            {"name": "Customer Service", "type": "service"},
            {"name": "Customer API v1", "type": "api"},
            {"name": "Customer Database", "type": "database"},
        ],
    },
    {
        "team_id": "TEAM-004",
        "name": "Payments Team",
        "business_area": "Finance",
        "description": "Owns payment processing and the payments ledger.",
        "architecture_contact": "[email protected]",
        "support_contact": "[email protected]",
        "systems_owned": [
            {"name": "Payment API v1", "type": "api"},
            {"name": "Payments Database", "type": "database"},
        ],
    },
    {
        "team_id": "TEAM-005",
        "name": "Data Platform Team",
        "business_area": "Data & Analytics",
        "description": "Owns the analytics warehouse and enterprise reporting pipelines.",
        "architecture_contact": "[email protected]",
        "support_contact": "[email protected]",
        "systems_owned": [
            {"name": "Nightly Order ETL", "type": "data_pipeline"},
            {"name": "Customer Data Sync", "type": "data_pipeline"},
            {"name": "Inventory Reconciliation ETL", "type": "data_pipeline"},
            {"name": "Analytics Warehouse", "type": "database"},
            {"name": "Executive Sales Dashboard", "type": "report"},
            {"name": "Inventory Health Report", "type": "report"},
        ],
    },
]

# --------------------------------------------------------------------------
# Source 5: Integration Catalog (-> data/sample/integration_catalog.csv)
# --------------------------------------------------------------------------

INTEGRATIONS: list[dict[str, str]] = [
    {
        "source_system_name": "Order Management",
        "source_system_type": "application",
        "target_system_name": "Stripe",
        "target_system_vendor": "Stripe",
        "target_system_category": "payment-gateway",
        "integration_type": "api",
        "protocol": "HTTPS/REST",
        "frequency": "real-time",
    },
    {
        "source_system_name": "Warehouse Management App",
        "source_system_type": "application",
        "target_system_name": "FedEx Shipping API",
        "target_system_vendor": "FedEx",
        "target_system_category": "logistics-carrier",
        "integration_type": "api",
        "protocol": "HTTPS/REST",
        "frequency": "real-time",
    },
    {
        "source_system_name": "Shipping Service",
        "source_system_type": "service",
        "target_system_name": "FedEx Shipping API",
        "target_system_vendor": "FedEx",
        "target_system_category": "logistics-carrier",
        "integration_type": "api",
        "protocol": "HTTPS/REST",
        "frequency": "real-time",
    },
    {
        "source_system_name": "Marketing Automation Hub",
        "source_system_type": "application",
        "target_system_name": "Mailchimp",
        "target_system_vendor": "Mailchimp",
        "target_system_category": "marketing-saas",
        "integration_type": "batch-file",
        "protocol": "SFTP",
        "frequency": "daily",
    },
    {
        "source_system_name": "Admin Console",
        "source_system_type": "application",
        "target_system_name": "Salesforce",
        "target_system_vendor": "Salesforce",
        "target_system_category": "saas-crm",
        "integration_type": "api",
        "protocol": "HTTPS/REST",
        "frequency": "real-time",
    },
]
