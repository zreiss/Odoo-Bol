# EPA Refrigerant Account Records

Stage 1 of the EPA refrigerant compliance project for Odoo 19.

## Included

- An EPA 608 section on the existing customer form.
- Company-account qualification shared with purchasing contacts.
- Yes/no declaration, Type I/II/III/Universal, separate license number and
  technician name, certificate front/back and company-employment proof.
- Staff review with reviewer/date, manager replacement/withdrawal with reason.
- Private, versioned evidence. Reviewed records and files cannot be edited,
  shared publicly, relinked, or deleted through the supported ORM paths.
- Multi-company isolation and no portal/public access to credentials.

Sales staff inherit the EPA Entry and Review permission. Sales administrators
also inherit EPA Account Manager. Other users can be granted these explicitly.

## Not yet included

**This version does not block refrigerant sales and does not generate the
retailer sales log or account PDF.** The UI makes that limitation explicit.
Do not rely on the account's reviewed status as a transactional sales control.

Product classification, order/payment/invoice/delivery enforcement, POS
protection, invoice/delivery reconciliation and printable/exportable reports
remain the next stages. Existing custom credit/payment integration source and
Staging integration testing are required before enabling those controls live.

## Evidence

JPG, PNG and PDF only, maximum 10 MB per file. Reviewers must inspect readable
proof and check certification scope; this does not validate with a registry.
Files use private authenticated downloads, not public URLs or sharing tokens.
A replacement creates a blank new version; original proof stays retained.
No automated deletion is provided. Maintain database and filestore backups.
Section 608 credentials do not expire; there is no artificial expiry field.

## Tests

Run the full `ehs_epa_refrigerant` module suite. The backend tests cover account
sharing, required evidence, all four types, forged review attempts, evidence
immutability, private access, replacement/withdrawal and company isolation.
An HttpCase tour covers form entry, validation feedback and preserving input.
