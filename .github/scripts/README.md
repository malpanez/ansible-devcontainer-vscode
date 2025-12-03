# Security Alert Management Scripts

This directory contains automation scripts for managing GitHub Code Scanning alerts.

## Overview

GitHub Code Scanning generates alerts for security vulnerabilities found by tools like Trivy. However, alerts don't automatically close when:
- Vulnerabilities are fixed (you must manually dismiss them)
- False positives are identified
- Base image CVEs are accepted as risks

These scripts automate the cleanup process.

## Files

### [manage-code-scanning-alerts.sh](./manage-code-scanning-alerts.sh)

Main script for managing code scanning alerts.

**Features**:
- ✅ Identifies and dismisses stale alerts
- ✅ Supports custom dismissal rules
- ✅ Dry-run mode for safe testing
- ✅ Detailed logging and statistics
- ✅ Adds context comments to dismissals

**Usage**:
```bash
# Preview what would be dismissed (dry run)
DRY_RUN=true MAX_ALERT_AGE_DAYS=90 ./manage-code-scanning-alerts.sh

# Execute dismissals
DRY_RUN=false MAX_ALERT_AGE_DAYS=90 ./manage-code-scanning-alerts.sh
```

**Environment Variables**:
- `DRY_RUN` (default: `true`): Set to `false` to execute dismissals
- `MAX_ALERT_AGE_DAYS` (default: `90`): Age threshold for stale alerts
- `GITHUB_TOKEN`: Authentication token (auto-provided in GitHub Actions)
- `GITHUB_REPOSITORY`: Repository name (auto-provided in GitHub Actions)

## GitHub Actions Integration

This script is integrated with GitHub Actions via the [security-alert-management.yml](../.github/workflows/security-alert-management.yml) workflow.

**Automatic runs**: Every Monday at 9 AM UTC
**Manual trigger**: Via GitHub Actions UI or CLI

```bash
# Run via GitHub CLI
gh workflow run security-alert-management.yml -f dry_run=true -f max_age_days=90
```

## Configuration

Alert exceptions and custom rules are defined in [security-alert-exceptions.yml](../security-alert-exceptions.yml).

Edit this file to:
- Define false positives
- Document accepted risks
- Customize age thresholds
- Add tool-specific rules

## Customization

### Adding Custom Dismissal Rules

Edit the script to add logic for specific CVEs or patterns:

```bash
# Example: Dismiss a specific CVE as false positive
if [[ "${RULE_ID}" == "CVE-2024-XXXXX" ]]; then
    SHOULD_DISMISS=true
    DISMISS_REASON="false positive"
    DISMISS_COMMENT="This CVE doesn't apply to our use case."
    log_warning "  → Marked for dismissal: Known false positive"
fi
```

### Severity-Based Rules

```bash
# Example: Auto-dismiss low severity alerts after 30 days
if [[ "${SEVERITY}" == "note" ]] && [ "${AGE_DAYS}" -gt 30 ]; then
    SHOULD_DISMISS=true
    DISMISS_REASON="won't fix"
    DISMISS_COMMENT="Low severity alert auto-dismissed after 30 days."
fi
```

### Location-Based Rules

```bash
# Example: Dismiss alerts in specific paths
if [[ "${LOCATION}" =~ ^usr/local/bin/podman ]] && [ "${AGE_DAYS}" -gt 60 ]; then
    SHOULD_DISMISS=true
    DISMISS_REASON="used in tests"
    DISMISS_COMMENT="Podman binary from official image. Risk accepted for dev environment."
fi
```

## Best Practices

### Do ✅
- Run in dry-run mode first
- Review dismissed alerts weekly
- Document exceptions thoroughly
- Update custom rules as needed
- Monitor the workflow reports

### Don't ❌
- Dismiss without investigation
- Use aggressive age thresholds
- Ignore high-severity alerts
- Skip dry-run validation
- Dismiss fixable issues

## Testing

### Local Testing

```bash
# Install dependencies
# - GitHub CLI: https://cli.github.com/
# - jq: https://stedolan.github.io/jq/

# Authenticate
gh auth login

# Test in dry-run mode
cd .github/scripts
DRY_RUN=true ./manage-code-scanning-alerts.sh
```

### CI Testing

The workflow runs automatically, but you can trigger it manually:

```bash
# Dry run via GitHub UI
# 1. Go to Actions → Security Alert Management
# 2. Click "Run workflow"
# 3. Set dry_run: true
# 4. Click "Run workflow" button

# Or via CLI
gh workflow run security-alert-management.yml -f dry_run=true
```

## Monitoring

### View Reports

Reports are generated in GitHub Actions:
1. Go to Actions → Security Alert Management
2. Click on the latest run
3. Check the "Summary" tab

### Metrics Tracked

- Total alerts (open, fixed, dismissed)
- Alert breakdown by severity
- Dismissal counts
- Error counts
- Age distribution

## Troubleshooting

### Script fails with "Not authenticated"
```bash
# Solution: Authenticate with GitHub CLI
gh auth login
```

### No alerts being dismissed
```bash
# Check: Are you in dry-run mode?
echo $DRY_RUN

# Solution: Set to false
DRY_RUN=false ./manage-code-scanning-alerts.sh
```

### Permission denied errors
```bash
# Check: Does your token have security-events:write permission?
gh auth status

# Solution: Re-authenticate with correct scopes
gh auth refresh -s security-events:write
```

## Maintenance

### Review Schedule

- **Weekly**: Monitor workflow runs
- **Monthly**: Review dismissed alerts
- **Quarterly**: Update exception rules
- **Annually**: Audit security policies

### Updates

When updating the script:
1. Test locally in dry-run mode
2. Create a PR with changes
3. Review workflow run on PR branch
4. Merge after validation

## Support

For issues or questions:
- Open an issue in the repository
- Review the security review document: [SECURITY_REVIEW.md](../../SECURITY_REVIEW.md)
- Check GitHub Actions logs for detailed output

## License

Same as the main repository.
