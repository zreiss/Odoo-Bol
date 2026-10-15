# Bill of Lading — Odoo 19

Adds **Bill of Lading** to the native Print menu for delivery transfers.

## Install

Requires Odoo 19 and `stock_delivery` (Delivery Costs in Inventory). Deploy this repository as an addons directory, refresh the Apps list, remove the default Apps filter if necessary, and install **Bill of Lading Report** (`bol_report_stock`). Test in staging before production. Connecting GitHub alone does not install the module into an Odoo database; the hosting administrator must configure the deployment/addons path.

## Print

- Open a delivery in Inventory, open the gear / Actions menu, then **Print → Bill of Lading**.
- Or select multiple deliveries in a list and use **Print → Bill of Lading** for a combined PDF with a separate document for each delivery.
- Receipts, internal transfers and cancelled deliveries are rejected with a clear message. A mixed batch containing one is rejected as a whole.
- Pending deliveries are prominently marked **PRELIMINARY** and show planned demand, not reserved quantities. Completed deliveries show actual moved quantities, excluding cancelled/zero lines. Backorders have their own shipment number and document.

## What prints

US Letter portrait, company header/footer, warehouse ship-from and delivery ship-to, shipment number as BOL number, date/order reference, carrier, PRO/tracking reference, package count, shipping weight and unit, goods and quantities, freight payment checkboxes, handling/exception space and shipper/driver/receiver signature lines.

Missing carrier/weight/package count stays blank for manual completion; no package count is invented. Packages count only tracks Odoo package records, not an inferred pallet count. Weight comes from the shipment or calculated product weights; verify it before signing. Missing/incorrect product weights can make totals incomplete. NMFC and freight-class columns are intentionally blank for manual classification. Freight payment choices and handling instructions are completed on paper; the report does not add shipment fields or infer carrier terms. This is a generic freight handoff form, not a carrier-certified or hazardous-materials BOL; check your carrier's requirements before use.

Print is read-only: no shipment validation, carrier API call, payment or inventory mutation, and no PDF attachment cache. Standard Delivery Slip remains unchanged.

## Testing

Run the `bol_report_stock` Odoo test suite. It includes report-content regressions, empty/missing data, batch, partial/backorder, cancelled selections, archived products, inventory-user and multi-company access, plus a browser tour confirming the Print menu alongside Delivery Slip.
