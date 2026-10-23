#!/usr/bin/env bash
# نشر مجلد site/ على Cloudflare Pages (مشروع watad-wood → watad-wood.com)
# يحتاج متغيرين في إعدادات البيئة: CLOUDFLARE_API_TOKEN و CLOUDFLARE_ACCOUNT_ID
set -euo pipefail
cd "$(dirname "$0")/.."
: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN غير موجود في إعدادات البيئة}"
: "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID غير موجود في إعدادات البيئة}"
npx -y wrangler@3 pages project create watad-wood --production-branch main 2>/dev/null || true
npx -y wrangler@3 pages deploy site --project-name watad-wood --branch main --commit-dirty=true
