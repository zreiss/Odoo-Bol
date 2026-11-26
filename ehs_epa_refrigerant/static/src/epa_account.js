/** @odoo-module */
import { Component, onWillStart, useState, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { FileUploader } from "@web/views/fields/file_handler";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useSetupAction } from "@web/search/action_hook";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const SCALARS = ["declaration", "credential_type", "number", "technician_name", "authorized_buyers", "notes", "scope_reviewed"];
const FILES = ["certificate_front", "certificate_back", "employer_proof"];
const errorText = (error) => error.data?.message || error.message || _t("The EPA file could not be saved. Please try again.");

class ChangeDialog extends Component {
    static template = "ehs_epa_refrigerant.ChangeDialog";
    static components = { Dialog };
    static props = { close: Function, operation: String, onConfirm: Function };
    setup() {
        this.state = useState({ reason: "", busy: false, error: "" });
    }
    get title() { return this.props.operation === "replace" ? _t("Replace EPA account file") : _t("Withdraw EPA account file"); }
    async confirm() {
        if (!this.state.reason.trim()) {
            this.state.error = _t("Enter a reason. The existing proof will be retained.");
            return;
        }
        this.state.busy = true;
        try {
            await this.props.onConfirm(this.state.reason);
            this.props.close();
        } catch (error) {
            this.state.error = errorText(error);
        } finally {
            this.state.busy = false;
        }
    }
}

class EpaBase extends Component {
    static props = standardWidgetProps;
    setup() {
        this.orm = useService("orm");
        this.state = useState({ loading: false, busy: false, error: "", data: null, values: {}, uploads: {}, dirty: false });
        onWillStart(() => this.load());
        useBus(this.env.bus, "EHS_EPA_UPDATED", (event) => {
            if (event.detail !== this && !this.state.dirty) { this.load(); }
        });
        this.loadedRecordId = this.props.record.resId;
        useEffect(() => {
            if (this.loadedRecordId !== this.props.record.resId) {
                this.loadedRecordId = this.props.record.resId;
                this.load();
            }
        }, () => [this.props.record.resId]);
    }
    async load() {
        if (!this.props.record.resId) { return; }
        this.state.loading = true;
        this.state.error = "";
        try {
            const data = await this.orm.call("res.partner", "epa_account_data", [[this.props.record.resId]]);
            this.state.data = data;
            this.state.values = { ...data.values };
            this.state.uploads = {};
            this.state.dirty = false;
        } catch (error) {
            this.state.error = errorText(error);
        } finally {
            this.state.loading = false;
        }
    }
    get frozen() { return this.state.data && !["missing", "draft"].includes(this.state.data.status); }
}

export class EpaSummary extends EpaBase {
    static template = "ehs_epa_refrigerant.Summary";
}

export class EpaAccount extends EpaBase {
    static template = "ehs_epa_refrigerant.Account";
    static components = { FileUploader };
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        useSetupAction({
            beforeLeave: () => this.confirmLeave(),
            beforeUnload: (event) => {
                if (this.state.dirty) { event.preventDefault(); event.returnValue = ""; }
            },
        });
    }
    async confirmLeave() {
        if (!this.state.dirty) { return true; }
        return new Promise((resolve) => {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Unsaved EPA account information"),
                body: _t("Save the EPA file before leaving, or discard these changes?"),
                confirmLabel: _t("Save file"),
                cancelLabel: _t("Discard changes"),
                confirm: async () => { await this.persist(false); resolve(!this.state.error); },
                cancel: () => { this.state.dirty = false; resolve(true); },
                dismiss: () => resolve(false),
            });
        });
    }
    setValue(name, value) {
        this.state.values[name] = value;
        this.state.dirty = true;
    }
    async upload(field, file) {
        this.state.uploads[field] = file;
        this.state.dirty = true;
    }
    fileName(field) {
        return this.state.uploads[field]?.name || (this.state.data.files[field]?.present ? this.state.data.files[field].name : "");
    }
    async persist(verify) {
        if (this.state.busy) { return; }
        this.state.busy = true;
        this.state.error = "";
        try {
            if (!(await this.props.record.save())) {
                this.state.error = _t("Save the customer details before saving the EPA file.");
                return;
            }
            const values = {};
            for (const field of SCALARS) {
                values[field] = this.state.values[field] || false;
            }
            for (const field of FILES) {
                if (this.state.uploads[field]) {
                    values[field] = this.state.uploads[field].data;
                    values[field + "_name"] = this.state.uploads[field].name;
                }
            }
            await this.orm.call("res.partner", "epa_save_account", [[this.props.record.resId], values]);
            this.state.dirty = false;
            if (verify) {
                await this.orm.call("res.partner", "epa_verify_account", [[this.props.record.resId]]);
            }
            await this.load();
            this.env.bus.trigger("EHS_EPA_UPDATED", this);
        } catch (error) {
            this.state.error = errorText(error);
        } finally {
            this.state.busy = false;
        }
    }
    change(operation) {
        this.dialog.add(ChangeDialog, {
            operation,
            onConfirm: async (reason) => {
                await this.orm.call("res.partner", "epa_change_account", [[this.props.record.resId], operation, reason]);
                await this.load();
                this.env.bus.trigger("EHS_EPA_UPDATED", this);
            },
        });
    }
}

registry.category("view_widgets").add("ehs_epa_summary", { component: EpaSummary });
registry.category("view_widgets").add("ehs_epa_account", { component: EpaAccount });
