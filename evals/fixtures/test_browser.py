"""Deterministic browser checks for a synthetic fixture, not agent evaluations.

Requires playwright (test-only) and a compatible Chromium browser.
"""
import shutil
import threading
import unittest

from playwright.sync_api import sync_playwright
from activation_lab import server


class ActivationLabBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.servers = {}
        cls.threads = {}
        for variant in ('seeded', 'reference'):
            s = server(variant, 0)
            th = threading.Thread(target=s.serve_forever, daemon=True)
            th.start()
            cls.servers[variant] = s
            cls.threads[variant] = th
        cls.pw = sync_playwright().start()
        path = shutil.which('chromium') or shutil.which('chromium-browser')
        cls.browser = cls.pw.chromium.launch(headless=True, executable_path=path)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        for s in cls.servers.values():
            s.shutdown()
            s.server_close()

    def visit(self, variant, route='/', viewport=None):
        context = self.browser.new_context(viewport=viewport or {'width': 1280, 'height': 800})
        self.addCleanup(context.close)
        tab = context.new_page()
        tab.goto(f'http://127.0.0.1:{self.servers[variant].server_port}{route}')
        return tab

    def test_hero_cta_destination_is_broken_only_in_seeded_variant(self):
        self.assertEqual(self.visit('seeded').locator('#primary-cta').get_attribute('href'), '/pricing')
        self.assertEqual(self.visit('reference').locator('#primary-cta').get_attribute('href'), '/start')

    def test_mobile_button_is_hidden_only_in_seeded_variant(self):
        vp = {'width': 375, 'height': 812}
        self.assertFalse(self.visit('seeded', viewport=vp).locator('#primary-cta').is_visible())
        self.assertTrue(self.visit('reference', viewport=vp).locator('#primary-cta').is_visible())

    def test_skeptic_pricing_is_disclosed_only_in_reference_variant(self):
        self.assertIn('Contact us for pricing', self.visit('seeded', '/pricing').locator('#plan-price').inner_text())
        self.assertIn('$0', self.visit('reference', '/pricing').locator('#plan-price').inner_text())

    def test_empty_workspace_accepted_only_in_seeded_variant(self):
        bad = self.visit('seeded', '/start')
        bad.locator('#submit').click()
        self.assertTrue(bad.get_by_test_id('workspace-ready').is_visible())
        good = self.visit('reference', '/start')
        good.locator('#submit').click()
        self.assertEqual(good.get_by_test_id('workspace-ready').count(), 0)
        self.assertIn('required', good.locator('#error').inner_text())

    def test_duplicate_submit_in_seeded_but_not_reference_variant(self):
        for variant, expected_count in [('seeded', '2'), ('reference', '1')]:
            tab = self.visit(variant, '/start')
            tab.locator('#name').fill('Synthetic Project')
            tab.locator('#submit').click()
            tab.locator('#submit').click()
            self.assertEqual(tab.get_by_test_id('workspace-count').inner_text(), expected_count)


if __name__ == '__main__':
    unittest.main()
