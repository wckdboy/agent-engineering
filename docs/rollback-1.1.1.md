# Rollback — eng 1.1.1

Restore `v1.1.0`'s `.agents/` and `VERSION`, rebuild the site artifact, and redeploy the previous
Worker version. Keep the v1.1.1 tag and evidence immutable; publish a new patch rather than
rewriting assets.
