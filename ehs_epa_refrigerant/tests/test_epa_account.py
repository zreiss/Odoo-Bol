import base64

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, tagged


PROOF = base64.b64encode(b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF')


@tagged('post_install', '-at_install')
class TestEpaAccount(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account = cls.env['res.partner'].create({'name': 'EPA Test Company', 'is_company': True})
        cls.child = cls.env['res.partner'].create({'name': 'EPA Company Buyer', 'parent_id': cls.account.id})
        cls.individual = cls.env['res.partner'].create({'name': 'EPA Individual'})
        cls.values = {
            'declaration': 'yes', 'credential_type': 'ii', 'number': 'TEST-608',
            'technician_name': 'Test Technician', 'certificate_front': PROOF,
            'certificate_front_name': 'test-license.pdf', 'scope_reviewed': True,
        }

    def _file(self, partner=None, **extra):
        partner = partner or self.individual
        return self.env['ehs.epa.credential'].create({
            **self.values, 'partner_id': partner.id, **extra,
        })

    def test_all_types_can_be_reviewed(self):
        for kind in ('i', 'ii', 'iii', 'universal'):
            partner = self.env['res.partner'].create({'name': kind})
            credential = self._file(partner, credential_type=kind)
            credential.action_verify()
            self.assertEqual(credential.state, 'verified')
            self.assertEqual(credential.verified_by, self.env.user)
            self.assertTrue(credential.verified_at)

    def test_missing_fields_and_company_proof(self):
        credential = self._file(self.account)
        with self.assertRaisesRegex(ValidationError, 'employer evidence'):
            credential.action_verify()
        credential.write({'employer_proof': PROOF, 'employer_proof_name': 'employment.pdf'})
        credential.action_verify()
        self.assertEqual(credential.state, 'verified')
        self.assertEqual(self.child.epa_account_data()['credential_id'], credential.id)
        self.assertEqual(self.child.epa_account_data()['account_id'], self.account.id)
        self.assertEqual(self.child.epa_account_data()['values']['technician_name'], 'Test Technician')

    def test_partial_file_is_saveable_not_verified(self):
        record_id = self.individual.epa_save_account({'declaration': 'yes'})
        credential = self.env['ehs.epa.credential'].browse(record_id)
        self.assertEqual(credential.state, 'draft')
        with self.assertRaises(ValidationError):
            credential.action_verify()
        credential.write({'declaration': 'no'})
        self.assertEqual(credential.declaration, 'no')

    def test_status_cannot_be_forged(self):
        with self.assertRaises(AccessError):
            self._file(state='verified')
        credential = self._file()
        with self.assertRaises(AccessError):
            credential.write({'state': 'verified'})
        with self.assertRaises(AccessError):
            self.individual.epa_save_account({'company_id': self.env.company.id})

    def test_invalid_evidence(self):
        for proof in (base64.b64encode(b'not an image'), b'not base64!'):
            with self.assertRaises(ValidationError):
                self._file(certificate_front=proof)

    def test_verified_content_and_attachment_are_sealed(self):
        credential = self._file()
        credential.action_verify()
        attachment = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', credential._name), ('res_id', '=', credential.id),
            ('res_field', '=', 'certificate_front'),
        ])
        self.assertEqual(len(attachment), 1)
        for vals in ({'datas': PROOF}, {'public': True}, {'access_token': 'shared'},
                     {'res_model': 'res.partner', 'res_id': self.individual.id}):
            with self.assertRaises(UserError):
                attachment.write(vals)
        with self.assertRaises(UserError):
            attachment.sudo().unlink()
        with self.assertRaises(UserError):
            credential.sudo().write({'number': 'Changed'})
        with self.assertRaises(UserError):
            credential.sudo().unlink()
        self.assertEqual(credential.with_context(bin_size=False).certificate_front, PROOF)

    def test_draft_evidence_stays_private(self):
        credential = self._file()
        attachment = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', credential._name), ('res_id', '=', credential.id),
            ('res_field', '=', 'certificate_front'),
        ])
        with self.assertRaises(ValidationError):
            attachment.generate_access_token()
        with self.assertRaises(ValidationError):
            attachment.write({'public': True})

    def test_attachment_defaults_cannot_make_evidence_public(self):
        credential = self._file()
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.env['ir.attachment'].with_context(default_public=True).create({
                'name': 'unsafe.pdf', 'res_model': credential._name,
                'res_id': credential.id, 'res_field': 'certificate_back', 'datas': PROOF,
            })

    def test_replace_and_withdraw_preserve_version(self):
        credential = self._file()
        credential.action_verify()
        credential.action_withdraw('Technician left')
        self.assertEqual(credential.state, 'withdrawn')
        replacement_id = credential.action_replace('New technician')
        replacement = self.env['ehs.epa.credential'].browse(replacement_id)
        self.assertFalse(credential.current)
        self.assertEqual(credential.state, 'superseded')
        self.assertEqual(credential.number, 'TEST-608')
        self.assertEqual(replacement.state, 'draft')
        self.assertFalse(replacement.number)
        self.assertTrue(credential.with_context(bin_size=False).certificate_front)

    def test_no_child_owned_license(self):
        with self.assertRaises(ValidationError):
            self._file(self.child)
        self.child.epa_save_account({'declaration': 'no'})
        self.assertEqual(self.child._epa_current().partner_id, self.account)

    def test_ownership_changes_blocked(self):
        self._file(self.account)
        with self.assertRaises(UserError):
            self.account.write({'is_company': False})
        self.account.write({'phone': '555-0000'})
        self.assertEqual(self.account.phone, '555-0000')

    def test_portal_and_unassigned_internal_cannot_read(self):
        credential = self._file()
        for group in ('base.group_portal', 'base.group_user'):
            user = self.env['res.users'].create({
                'name': group, 'login': group + '-epa',
                'group_ids': [Command.set([self.env.ref(group).id])],
            })
            with self.assertRaises(AccessError):
                credential.with_user(user).read(['number'])
            with self.assertRaises(AccessError):
                self.individual.with_user(user).epa_account_data()

    def test_company_isolation(self):
        other = self.env['res.company'].create({'name': 'EPA Other Company'})
        credential = self.env['ehs.epa.credential'].with_company(other).create({
            **self.values, 'partner_id': self.individual.id, 'company_id': other.id,
        })
        user = self.env['res.users'].create({
            'name': 'EPA Reviewer', 'login': 'epa-reviewer',
            'company_id': self.env.company.id,
            'company_ids': [Command.set(self.env.company.ids)],
            'group_ids': [Command.set([self.env.ref('ehs_epa_refrigerant.group_epa_user').id])],
        })
        restricted = credential.with_user(user).with_context(allowed_company_ids=user.company_ids.ids)
        self.assertFalse(restricted.search([('id', '=', credential.id)]))
        with self.assertRaises(AccessError):
            restricted.read(['number'])
