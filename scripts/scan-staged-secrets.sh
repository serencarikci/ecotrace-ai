#!/usr/bin/env bash
# Portable staged-change secret / sensitive-path scan (macOS + Linux CI).
# Exit 0 = clean. Exit 1 = findings. Does not print matched secret values.
#
# Usage (after staging):
#   ./scripts/scan-staged-secrets.sh
# Or scan unstaged+untracked paths from git status:
#   ./scripts/scan-staged-secrets.sh --worktree

set -euo pipefail

SCOPE="${1:---staged}"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${ROOT}"

TMPDIR_SCAN="${TMPDIR:-/tmp}"
REPORT="$(mktemp "${TMPDIR_SCAN}/ecotrace-secret-scan.XXXXXX")"
PATHS_FILE="$(mktemp "${TMPDIR_SCAN}/ecotrace-secret-paths.XXXXXX")"
DIFF_FILE="$(mktemp "${TMPDIR_SCAN}/ecotrace-secret-diff.XXXXXX")"
trap 'rm -f "${REPORT}" "${PATHS_FILE}" "${DIFF_FILE}"' EXIT

note() {
  printf '%s\n' "$1" >>"${REPORT}"
}

if [ "${SCOPE}" = "--worktree" ]; then
  git status --porcelain -z | perl -0ne 'print $1,"\0" if /^.. (?:.* -> )?([^\0]+)\0/' >"${PATHS_FILE}"
else
  git diff --cached --name-only -z >"${PATHS_FILE}"
fi

if [ ! -s "${PATHS_FILE}" ]; then
  echo "secret-scan: no paths in scope (${SCOPE}); nothing to check."
  exit 0
fi

# --- Filename checks ---
while IFS= read -r -d '' path; do
  base="$(basename "${path}")"
  case "${base}" in
    .env|.env.*|*.env)
      case "${base}" in
        *.example|*.sample|*.template) ;;
        *) note "SENSITIVE_ENV_FILE path=${path}" ;;
      esac
      ;;
  esac
  case "${path}" in
    *.xlsx|*.xlsm|*.xls)
      case "${path}" in
        apps/api/official-see/template.xlsx)
          if [ -f "${path}" ]; then
            actual="$(python3 - "${path}" <<'PY'
import hashlib, sys
print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())
PY
)"
            expected="83170fde547c418dcae7f6a32852555d6874e092769f387b263108a231b2dd64"
            if [ "${actual}" != "${expected}" ]; then
              note "OFFICIAL_SEE_TEMPLATE_SHA_MISMATCH path=${path}"
            fi
          fi
          ;;
        *) note "STAGED_XLSX path=${path}" ;;
      esac
      ;;
    .tmp-validation|.tmp-validation/*|*/.tmp-validation|/*/.tmp-validation/*)
      note "TMP_VALIDATION_PATH path=${path}"
      ;;
    /Users/*|/home/*|/private/var/*)
      note "ABSOLUTE_PATH_FILENAME path=${path}"
      ;;
  esac
  # Also catch .tmp-validation anywhere in path
  case "${path}" in
    *.tmp-validation*|.tmp-validation*|*/*/.tmp-validation/*|*/.tmp-validation/*)
      note "TMP_VALIDATION_PATH path=${path}"
      ;;
  esac
done <"${PATHS_FILE}"

# --- Diff text checks (staged / worktree patch) ---
if [ "${SCOPE}" = "--worktree" ]; then
  git diff HEAD >"${DIFF_FILE}" 2>/dev/null || git diff >"${DIFF_FILE}"
else
  git diff --cached >"${DIFF_FILE}"
fi

scan_diff_rule() {
  local rule="$1"
  local pattern="$2"
  python3 - "${DIFF_FILE}" "${pattern}" "${rule}" <<'PY' >>"${REPORT}" || true
import re, sys
diff_path, pattern, rule = sys.argv[1], sys.argv[2], sys.argv[3]
rx = re.compile(pattern)
current = "?"
hits = set()
with open(diff_path, "r", encoding="utf-8", errors="replace") as fh:
    for line in fh:
        if line.startswith("+++ b/"):
            current = line[6:].strip()
            continue
        if line.startswith("+") and not line.startswith("+++"):
            if rx.search(line[1:]):
                hits.add(current)
for path in sorted(hits):
    print(f"{rule} path={path}")
PY
}

scan_diff_rule "PRIVATE_KEY_HEADER" '-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----'
scan_diff_rule "GITHUB_TOKEN" 'gh[pousr]_[A-Za-z0-9_]{20,}'
scan_diff_rule "OPENAI_LIKE_KEY" 'sk-[A-Za-z0-9]{20,}'
scan_diff_rule "JWT_OR_SECRET_ASSIGN" '(?i)(jwt_secret|secret_key|api_key|access_token)\s*[:=]\s*['\''\"][^'\''\"]{8,}'
scan_diff_rule "DATABASE_PASSWORD_ASSIGN" '(?i)(database_url|postgres_password|db_password)\s*[:=]\s*['\''\"][^'\''\"]+'
scan_diff_rule "ACCEPTANCE_CREDENTIAL" '(?i)(acceptance|e2e).{0,40}(password|passwd|secret)\s*[:=]'
scan_diff_rule "LOCAL_ABSOLUTE_PATH" '(/Users/[A-Za-z0-9._-]+|/home/[A-Za-z0-9._-]+)'

# --- Staged file content checks (text-ish only) ---
while IFS= read -r -d '' path; do
  [ -f "${path}" ] || continue
  case "${path}" in
    *.png|*.jpg|*.jpeg|*.gif|*.webp|*.pdf|*.xlsx|*.xlsm|*.xls|*.zip|*.gz|*.whl|*.pyc)
      continue
      ;;
  esac
  size="$(wc -c <"${path}" | tr -d ' ')"
  if [ "${size}" -gt 2000000 ]; then
    continue
  fi
  python3 - "${path}" <<'PY' >>"${REPORT}" || true
import re, sys
path = sys.argv[1]
try:
    text = open(path, "r", encoding="utf-8", errors="ignore").read()
except OSError:
    raise SystemExit(0)
rules = [
    ("PRIVATE_KEY_HEADER", r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    ("GITHUB_TOKEN", r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    ("OPENAI_LIKE_KEY", r"sk-[A-Za-z0-9]{20,}"),
]
for rule, pat in rules:
    if re.search(pat, text):
        print(f"{rule} path={path}")
PY
done <"${PATHS_FILE}"

if [ -s "${REPORT}" ]; then
  uniq_hits="$(sort -u "${REPORT}" | wc -l | tr -d ' ')"
  echo "secret-scan: FAILED (${uniq_hits} finding(s)). Paths/rules only — values not printed:"
  sort -u "${REPORT}"
  exit 1
fi

echo "secret-scan: OK (${SCOPE})"
exit 0
