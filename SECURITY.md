# Security policy

This repository is a Phase 0 foundation, not a supported browser release. Do not
use an eventual development binary for sensitive browsing until its security,
update and release gates have been reviewed.

Preserve Chromium sandboxing, process isolation, TLS validation, permission
mediation and profile separation. Web content is untrusted. Trinol WebUI needs
strict content security policy and narrow, validated browser-side interfaces.
Passwords remain in Chromium's credential storage integrated with the OS;
Trinol must not create plaintext password stores or log page/profile secrets.

AI and sync features are future designs. Require explicit consent for sending
page content, bounded access, retention controls and incognito isolation before
implementation. Signing credentials and service secrets belong in approved
local/CI secret storage, never Git, patches, generated logs or documentation.

Do not publish exploit details or credentials in a public issue. Report sensitive
findings privately to the repository owner through an established private channel.
No dedicated vulnerability intake or response SLA has been established yet.

Before public distribution, establish a private vulnerability intake, upstream
security monitoring, signed updates, rollback protection, incident response,
macOS signing/notarization and license/notice review. Phase 0 does not claim any
of these release capabilities exist.
