#!/usr/bin/env bash
# نشر مجلد site/ على Cloudflare Pages (مشروع watad-wood → watad-wood.com)
# المفتاح محفوظ في إعدادات البيئة (Network secrets لـ api.cloudflare.com بالمسار /client/v4/accounts/)
# والبروكسي يضيفه تلقائياً، فالقيمة هنا مجرد عنصر نائب.
set -euo pipefail
cd "$(dirname "$0")/.."
export CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-proxy-injected}"
export CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-b5174475bcce6c670f6d69fe9a37b4c8}"
export NODE_EXTRA_CA_CERTS="${NODE_EXTRA_CA_CERTS:-/root/.ccr/ca-bundle.crt}"
npx -y wrangler@3 pages deploy site --project-name watad-wood --branch main --commit-dirty=true
