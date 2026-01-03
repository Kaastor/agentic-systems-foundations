rsync -a --delete --dry-run .././var_platform/ .././var_course/ \
  --exclude 'var/research/' \
  --exclude 'var/apps/research/' \
  --exclude 'var/apps/home/' \
  --exclude 'tests/test_research_*' \
  --exclude 'tests/test_flaky_verification_and_fault_injection.py' \
  --exclude 'README_platform.md' \
  --exclude 'README_research.md'