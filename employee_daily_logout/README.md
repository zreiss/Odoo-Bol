# Employee Daily Logout

Odoo 19 addon for daily employee sign-out at **6:30 PM America/New_York**,
including weekends and daylight-saving changes. Employees can sign back in
immediately. Customer/vendor portal and public sessions are excluded.

## Enforcement

Employee browser-session signatures change at each cutoff. Odoo's native
session validation rejects the old signature on HTTP requests and websocket
authentication, rather than depending on a scheduled job or deleting session
files. A backend browser timer also checks the session
at the cutoff so an open app displays Odoo's normal expired-session prompt.
Sleeping/offline devices enforce the rule when they reconnect or next make a
request. Previously displayed or downloaded information cannot be erased by
logging out. In-flight requests started before the cutoff are not cancelled.

Install this addon separately from the existing Bill of Lading addon. It does
not modify shipment reports, passwords, API keys, or customer records.

## Two-step verification

Use Odoo's existing **Settings > General Settings > Enforce two-factor
 authentication > Employees only** setting. Installation of this addon does
**not** enable it automatically. Each person enrolls their own authenticator;
Odoo otherwise uses email verification. Remembered-device rules remain Odoo's
standard rules; daily logout does not itself force a new two-step challenge on
a remembered device.

Before enforcing two-step verification:

1. Confirm each employee can complete sign-in using an authenticator app or
   receive email codes. Do not enable outbound email on a neutralized staging
   database just for this: configure deliberate test-only delivery or enroll
   authenticators first.
2. Use API keys, not employee passwords, for integrations and the administration
   connection. Odoo rejects password-based API access once two-step verification
   is required. The daily session rule does not revoke API keys.
3. Test employee sign-in and an excluded portal user before rollout.

## Staging-first rollout and rollback

- Deploy the reviewed branch to Staging using the project's normal deployment
  controls, then install **Employee Daily Logout** from Apps.
- Installation expires existing employee sessions immediately; staff will need
  to sign in on their next request. Notify staff to save work before installation and each
  evening's cutoff.
- Verify logout, immediate re-login, portal exclusion, and integration access.
- Enable native employee-only two-step verification only after the prerequisites
  above; it is independent of this addon's installation.
- Production is a separate, explicit rollout after Staging approval.
- To roll back daily logout, uninstall this addon normally. To roll back native
  enforcement, turn off the existing two-factor enforcement setting using an
  administrator with working access. Users' own authenticators remain enrolled.
