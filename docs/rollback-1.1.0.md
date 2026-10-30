# Rollback — eng 1.1.0

1. Revert the release commit and restore the previous `.agents/` from the kit source or the
   `v1.0.1` tag.
2. Re-run `./.agents/bin/eng verify --profile fast` in every installation.
3. If a deployment is affected, redeploy the previous `site/` artifact and restore the
   Cloudflare Worker version from the Wrangler deployment history.
4. Preserve the release evidence and the deployed artifact digest; do not delete the tag or
   rewrite published assets.
