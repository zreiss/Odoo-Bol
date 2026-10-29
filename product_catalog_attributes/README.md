# Product Catalog Attribute Filters

Adds an Attributes section alongside the existing Categories and Tags in
Odoo 19's internal product catalog (including the quotation Catalog button).

- Shows only attributes assigned to products matching the current search,
  category, document domain and the current user's product access rules.
- Uses global attribute values, avoiding repeated entries for each template.
- Descriptive `no_variant` attributes are included. Variant-creating
  attributes match the actual product variant, not all sibling variants.
- Choices within an attribute are OR; separate attributes are AND.
- Counters exclude the choices within their own attribute, allowing another
  value to be selected. Checked choices remain visible with zero results so
  a later search cannot silently remove a filter.
- Clear attributes resets only specifications, not Categories or Tags.
- Keeps the native responsive sidebar, catalog cards and quantity controls.

No product, price, inventory, attribute definition or variant is modified by
filtering. Existing ACLs apply; there are no new access rights or sudo paths.
The grouped native search panel is extended only for the new field. Its
server range method is overridden to avoid SQL grouping of a non-stored field
and a separate query for every global attribute value.

## Install / rollout

Deploy this addon in the target server's addons path, refresh the Apps list,
then install **Product Catalog Attribute Filters**. Reload the browser to
load the backend assets. This addon does not depend on or install the Bill
of Lading addon in this repository. Test on Staging before any Production
rollout. Uninstalling removes the sidebar addition without changing product
attributes or product data.

## Tests

Backend tests cover descriptive and actual variant matching, same-attribute
OR/cross-attribute AND, counts, search/category/tag compatibility, archived
records, company and product record rules, and read-only behavior. A browser
tour combines and clears filters, recovers from no matches and adds a product
to a draft quotation without changing its price or quantity behavior.
