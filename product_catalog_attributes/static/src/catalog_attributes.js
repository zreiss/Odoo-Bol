/** @odoo-module */
import { Component, useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { useBus } from "@web/core/utils/hooks";
import { SearchModel } from "@web/search/search_model";
import { SearchPanel } from "@web/search/search_panel/search_panel";

const ATTRIBUTE_FIELD = "catalog_attribute_value_ids";

class CatalogAttributeStatus extends Component {
    static template = "product_catalog_attributes.Status";
    static props = { sectionId: Number };

    setup() {
        this.state = useState({ loading: false, error: false, empty: false, selected: false });
        this.refresh();
        useBus(this.env.searchModel, "catalog-attributes-status", () => this.refresh());
        useBus(this.env.searchModel, "update", () => this.refresh());
    }

    refresh() {
        const section = this.env.searchModel.sections.get(this.props.sectionId);
        this.state.loading = Boolean(section.catalogAttributeLoading);
        this.state.error = Boolean(section.catalogAttributeError);
        this.state.empty = !section.values.size;
        this.state.selected = [...section.values.values()].some((value) => value.checked);
    }

    clear() {
        this.env.searchModel.clearSections([this.props.sectionId]);
    }

    async retry() {
        await this.env.searchModel._notify();
    }
}

patch(SearchModel.prototype, {
    _createFilterTree(sectionId, result) {
        const section = this.sections.get(sectionId);
        if (section.fieldName === ATTRIBUTE_FIELD && !result.error_msg) {
            const values = result.values.filter((value) =>
                value.__count > 0 || section.values.get(value.id)?.checked
            );
            const returnedIds = new Set(values.map((value) => value.id));
            // A new text search must not silently discard checked constraints.
            for (const value of section.values.values()) {
                if (value.checked && !returnedIds.has(value.id)) {
                    values.push({ ...value, __count: 0 });
                }
            }
            result = { ...result, values };
        }
        return super._createFilterTree(sectionId, result);
    },

    async _fetchFilters(filters) {
        const attributes = filters.filter((filter) => filter.fieldName === ATTRIBUTE_FIELD);
        const others = filters.filter((filter) => filter.fieldName !== ATTRIBUTE_FIELD);
        await super._fetchFilters(others);
        if (!attributes.length) {
            return;
        }
        for (const section of attributes) {
            section.catalogAttributeLoading = true;
        }
        this.trigger("catalog-attributes-status");
        try {
            await super._fetchFilters(attributes);
            for (const section of attributes) {
                section.catalogAttributeError = false;
            }
        } catch {
            // Keep the catalog and current selections usable if facet loading fails.
            for (const section of attributes) {
                section.catalogAttributeError = true;
            }
        } finally {
            for (const section of attributes) {
                section.catalogAttributeLoading = false;
            }
            this.trigger("catalog-attributes-status");
        }
    },
});

patch(SearchPanel, {
    components: { ...SearchPanel.components, CatalogAttributeStatus },
});

patch(SearchPanel.prototype, {
    get sections() {
        return this.env.searchModel.getSections((section) =>
            !section.empty || section.fieldName === ATTRIBUTE_FIELD
        );
    },
});
