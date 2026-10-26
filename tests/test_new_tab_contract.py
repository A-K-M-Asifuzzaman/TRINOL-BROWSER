"""Offline checks of the shipped patch contract, not native browser execution."""
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT/'patches/0003-orbit-native-new-tab.patch').read_text()
RES = 'chrome/browser/resources/new_tab_page_third_party/'
UI = 'chrome/browser/ui/webui/new_tab_page_third_party/'


def additions(name):
    section = PATCH.split(f'diff --git a/{name} b/{name}\n', 1)[1].split('\ndiff --git ', 1)[0]
    return '\n'.join(line[1:] for line in section.splitlines()
                     if line.startswith('+') and not line.startswith('+++'))


class NewTabContractTests(unittest.TestCase):
    def test_localized_copy_has_grit_resources(self):
        tree = ET.parse(ROOT/'trinol/new_tab/strings.grd')
        messages = tree.findall('.//messages/message')
        self.assertEqual(len(messages), 9)
        self.assertEqual(tree.find('.//messages').get('fallback_to_english'), 'true')
        header = tree.find(".//output[@type='rc_header']")
        self.assertIsNotNone(header.find("emit[@emit_type='prepend']"))
        ui = additions(UI+'new_tab_page_third_party_ui.cc')
        self.assertEqual(set(re.findall(r'IDS_TRINOL_NEW_TAB_\w+', ui)),
                         {message.get('name') for message in messages})
        self.assertIn('trinol_new_tab_strings_', additions('chrome/chrome_repack_locales.gni'))

    def test_csp_has_no_remote_scripts_or_network(self):
        ui = additions(UI+'new_tab_page_third_party_ui.cc')
        for directive in ("default-src 'none';", "script-src 'self' chrome://resources;",
                          "connect-src 'none';", "frame-src 'none';",
                          "object-src 'none';", "form-action 'none';"):
            self.assertIn(directive, ui)
        for forbidden in ('unsafe-eval', 'https://', 'http://', 'chrome_send=*/true'):
            self.assertNotIn(forbidden, ui)

    def test_narrow_mojo_requires_native_profile_and_user_activation(self):
        self.assertIn('FocusOmnibox() => (bool focused);', additions(UI+'new_tab_page_third_party.mojom'))
        handler = additions(UI+'new_tab_page_third_party_handler.cc')
        for gate in ('!profile_->IsOffTheRecord()', '!profile_->IsGuestSession()',
                     'GetBrowserContext() == profile_', 'GetProfile() == profile_',
                     'IsNewTabPageOrigin', 'content::Visibility::VISIBLE',
                     'HasTransientUserActivation()', 'SetFocusToLocationBar(true)'):
            self.assertIn(gate, handler)

    def test_real_omnibox_and_explicit_shortcuts_deferral(self):
        html = additions(RES+'new_tab_page_third_party.html')
        ts = additions(RES+'new_tab_page_third_party.ts')
        self.assertIn('chrome://history/', html)
        self.assertIn('chrome://settings/appearance', html)
        self.assertIn('sitesUnavailable', html)
        self.assertNotRegex(html, r'<(?:input|form)\b|autofocus')
        self.assertIn('handler.focusOmnibox()', ts)
        self.assertIn("loadTimeData.getString('focusUnavailable')", ts)
        self.assertNotRegex(ts, r'fetch\(|window\.open\(|google\.com|chrome\.send')

    def test_accessibility_and_responsive_theme_contract(self):
        css = additions(RES+'orbit.css')
        html = additions(RES+'new_tab_page_third_party.html')
        for token in ('[dark]', 'focus-visible', 'prefers-reduced-motion',
                      'forced-colors', 'max-width: 600px', 'overflow-wrap: anywhere'):
            self.assertIn(token, css)
        self.assertIn('aria-describedby="search-hint"', html)
        self.assertIn('aria-live="polite"', html)
        ts = additions(RES+'new_tab_page_third_party.ts')
        self.assertIn('new URLSearchParams({id: theme.id})', ts)
        self.assertIn('theme.useOrbitColors', ts)

    def test_approved_asset_and_native_launch_boundary(self):
        svg = additions(RES+'orbit-mark.svg')+'\n'
        self.assertEqual(svg, (ROOT/'design/assets/orbit-mark.svg').read_text())
        manifest = json.loads((ROOT/'upstream/manifest.json').read_text())
        self.assertFalse(manifest['native_new_tab']['native_launch_authorized'])
        self.assertEqual(len(manifest['customization']['patches']), 3)
        self.assertEqual(len(manifest['overlays']), 2)

    def test_client_harness_does_not_require_production_csp_changes(self):
        test = additions('chrome/test/data/webui/new_tab_page_third_party/orbit_browsertest.cc')
        self.assertIn('CreateAndAddWebUITestDataSource', test)
        self.assertIn('orbit-production/', test)
        self.assertNotIn('OverrideContentSecurityPolicy', test)
        self.assertNotIn('chrome://webui-test', additions(UI+'new_tab_page_third_party_ui.cc'))


if __name__ == '__main__':
    unittest.main()
