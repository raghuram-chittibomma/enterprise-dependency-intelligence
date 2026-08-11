"""The enterprise's business-capability-to-area taxonomy -- small reference
("master") data that ingestion uses to enrich a `BusinessCapability` node the
first time a capability name is encountered in a source record. Realistic
stand-in for what a real enterprise architecture/capability-model repository
would provide.
"""

from __future__ import annotations

CAPABILITY_AREAS: dict[str, str] = {
    "Customer Management": "Customer",
    "Product Catalog": "Commerce",
    "Order Management": "Commerce",
    "Inventory Management": "Commerce",
    "Payments & Billing": "Finance",
    "Fulfillment & Shipping": "Operations",
}


def area_for(capability_name: str) -> str:
    return CAPABILITY_AREAS.get(capability_name, "Unspecified")
