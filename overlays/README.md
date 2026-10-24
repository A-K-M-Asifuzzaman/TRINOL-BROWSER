# Overlay contract

No overlays exist yet. Future manifest entries must declare a product-relative
source and Chromium-src-relative destination. Reject absolute paths, traversal,
symlinks escaping either tree, collisions and undocumented overwrites. Stage
owned modules beneath a dedicated upstream trinol/ directory where practical;
modify Chromium integration points using reviewed patches. Verify destinations
against the pinned revision before writing. Never recursively copy an unchecked
folder over Chromium source. Phase 2A provides scripts/apply_product_patches.py, tested only on synthetic
repositories. Its overlay entries require source, destination and sha256. It
creates only new files beneath upstream trinol/, never overwrites content, and
requires explicit --apply to write. No actual overlay is declared or applied.
