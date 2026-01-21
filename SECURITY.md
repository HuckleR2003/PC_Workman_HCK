# Security Policy

## Overview

PC_Workman is system monitoring software that requires administrative privileges to access hardware sensors and control fan speeds. This level of access demands rigorous security practices.
This document outlines the security measures implemented in PC_Workman, how to report vulnerabilities, and what users can do to verify the safety of releases.

---

## Security Measures (Active Since v1.6.3)

Starting with v1.6.3 (January 2026), PC_Workman implemented professional-grade security practices:

### Always-On GitHub Security

- **Advanced CodeQL** - Automated code scanning for vulnerabilities on every commit
- **Private Vulnerability Reporting** - Secure channel for security researchers to report issues
- **Security Advisories** - Public disclosure when issues are found and fixed
- **Dependabot Alerts** - Automatic notification of vulnerable dependencies

### Release Security (Every Major Update)

- **Sigstore Digital Signatures** - Cryptographic proof that releases are authentic
- **VirusTotal Scanning** - Every .exe tested against 70+ antivirus engines before release
- **Documented Testing** - Version numbers, dates, and results publicly recorded
- **Reproducible Builds** - Source code tagged and archived for each release

### Sigstore Certificate

**Status:** Active  
**Available Since:** January 20, 2026  
**Valid For:** 90 days  
**Renewal:** Automatic with each stable release

Every PC_Workman release is signed with Sigstore. Verify the signature:

```bash
sigstore verify github \
  PC_Workman_HCK_<version>.exe \
  --bundle sigstore.bundle
```

If signature verification fails, do not run the executable. Report the issue immediately.

### VirusTotal Scanning

**Status:** Active  
**Started:** v1.6.3  
**Frequency:** Every new .exe release  
**Current Status:** 0/70 clean  
**Last Scanned:** v1.6.4 (January 24, 2026)

Before publishing any executable, it is uploaded to VirusTotal and verified against 70+ antivirus engines. Users can verify this independently at [virustotal.com](https://www.virustotal.com).

### OpenSSF Best Practices Badge

**Status:** In Progress (25% complete)  
**Target:** 100% compliance by v2.0

PC_Workman is working toward full compliance with [OpenSSF Best Practices](https://bestpractices.coreinfrastructure.org/) criteria:

**Completed:**
- Public version control (GitHub)
- Public discussion forums (Issues, Discussions)
- Clear contribution policy (CONTRIBUTING.md)
- Security reporting mechanism (this document)
- License declaration (MIT)
- Documented security practices

**In Progress:**
- Automated testing framework
- Code review process for all changes
- Continuous integration pipeline
- Automated dependency updates
- Security-focused code review guidelines

All requirements will be implemented systematically. Security recommendations from OpenSSF are treated as mandatory requirements, not suggestions.

---

## Supported Versions

Only the latest stable version receives active security support.

| Version | Supported | Security Updates | Notes |
|---------|-----------|------------------|-------|
| 1.6.x (latest) | Yes | Immediate | Active development branch |
| 1.5.x | Limited | Critical only | Upgrade recommended |
| < 1.5 | No | None | End of life |

**Alpha/Beta builds** receive security patches but may contain other stability issues. Production environments should use stable releases only.

---

## Reporting a Vulnerability

### Reporting Channels

**Primary: GitHub Private Vulnerability Reporting**

1. Navigate to the [Security tab](https://github.com/HuckleR2003/PC_Workman_HCK/security)
2. Click "Report a vulnerability"
3. Provide detailed information:
   - Affected version(s)
   - Reproduction steps
   - Potential impact assessment
   - Proof of concept (if applicable)
   - Suggested fix (if known)

**Alternative: Direct Email**

If GitHub reporting is not accessible:
- Email: `firmuga.marcin.s@gmail.com`
- Subject: `[SECURITY] PC_Workman Vulnerability Report`
- Include all details listed above

### What NOT to Do

- Do not open public issues for security vulnerabilities
- Do not disclose vulnerabilities publicly before patches are available
- Do not test exploits on production systems without explicit permission

### Response Timeline

**Within 24 hours:**
- Initial acknowledgment of report
- Confirmation that investigation has begun

**Within 72 hours:**
- Vulnerability validation or rejection
- Initial severity assessment
- Request for additional information (if needed)

**Within 7 days:**
- Fix available for critical vulnerabilities (CVSS 7.0+)
- Timeline provided for less critical issues

**After Fix:**
- Patched version released
- Security advisory published
- Reporter credited (unless anonymity requested)
- CVE assigned if applicable

### Severity Classification

Vulnerabilities are classified using CVSS v3.1:

- **Critical (9.0-10.0):** Remote code execution, privilege escalation
- **High (7.0-8.9):** Authentication bypass, data exposure
- **Medium (4.0-6.9):** Denial of service, information disclosure
- **Low (0.1-3.9):** Minor information leaks, configuration issues

Response urgency is prioritized based on severity and exploitability.

---

## Security Best Practices for Users

### Download from Official Sources Only

**Official Distribution Channels:**
- GitHub Releases: [github.com/HuckleR2003/PC_Workman_HCK/releases](https://github.com/HuckleR2003/PC_Workman_HCK/releases)
- Project Website: [huckler2003.github.io/PC_Workman_HCK](https://huckler2003.github.io/PC_Workman_HCK)

**Unofficial sources are not endorsed and may distribute modified or malicious versions:**
- Third-party download sites
- File sharing platforms
- Mirror sites
- Torrent networks

Executables received via email, Discord, or other messaging platforms should be considered untrusted.

### Verify Digital Signatures

After download, verify the Sigstore signature before execution:

```bash
# Install sigstore CLI if not present
pip install sigstore

# Verify signature
sigstore verify github PC_Workman_HCK_<version>.exe --bundle sigstore.bundle
```

Expected output: `Signature verified successfully`

If verification fails, delete the file immediately and report the issue.

### Scan with VirusTotal

Independent verification is recommended:

1. Visit [virustotal.com](https://www.virustotal.com)
2. Upload the downloaded .exe file
3. Review scan results

**Expected result:** 0/70+ detections

Any detections should be reported immediately. False positives are possible but rare.

### Verify File Hashes

Release notes include SHA256 hashes. Verify file integrity:

**Windows PowerShell:**
```powershell
Get-FileHash PC_Workman_HCK_<version>.exe -Algorithm SHA256
```

**Linux/macOS:**
```bash
sha256sum PC_Workman_HCK_<version>.exe
```

Compare output with published hash in release notes.

### Review Source Code

PC_Workman is open source. Users can audit the code before use:

```bash
git clone https://github.com/HuckleR2003/PC_Workman_HCK.git
cd PC_Workman_HCK
git checkout tags/v<version>
```

All releases are tagged and archived. Source code is available for inspection.

---

## Security Implementation Details

### Before Every Major Release

1. **Manual Code Review**
   - Review all changes since last release
   - Focus on privilege escalation vectors
   - Verify input validation
   - Check for hardcoded credentials or secrets

2. **Automated Security Scanning**
   - CodeQL analysis (Python security queries)
   - Dependency vulnerability scan (pip-audit)
   - Static analysis (bandit, pylint security plugins)

3. **Binary Security Testing**
   - VirusTotal scan (70+ engines)
   - Sandbox execution testing
   - Anti-malware false positive check

4. **Cryptographic Signing**
   - Sigstore signature generation
   - Signature bundle creation
   - Public transparency log verification

5. **Documentation Updates**
   - Update SECURITY.md with version/date
   - Publish changelog with security fixes
   - Update verification instructions

### Continuous Security Monitoring

**GitHub Security Features:**
- CodeQL scans on every push to main branch
- Dependabot alerts for vulnerable dependencies
- Secret scanning for accidentally committed credentials
- Security advisories for disclosed vulnerabilities

**Manual Monitoring:**
- Daily review of GitHub issues and discussions
- Weekly dependency update checks
- Monthly security audit of core modules

### Dependency Management

PC_Workman uses third-party libraries documented in `requirements.txt` and `DEPENDENCIES.md`.

**Dependency Security Process:**
1. All dependencies pinned to specific versions
2. `pip-audit` run before each release
3. Security advisories monitored for all dependencies
4. Vulnerable dependencies updated within 24 hours
5. Breaking changes tested in isolation before merge

**Current Dependencies with Security Implications:**
- `psutil` - System monitoring (regular security audits by maintainers)
- `pyqt5` - GUI framework (maintained by Riverbank Computing)
- Additional dependencies listed in DEPENDENCIES.md

---

## Security Update Log

### v1.6.4 (January 24, 2026)

**Security Improvements:**
- Sigstore signature renewed
- VirusTotal scan: 0/70 clean (verified)
- SECURITY.md published and linked in README
- Private vulnerability reporting enabled on GitHub
- CodeQL configuration updated with additional security queries

**Dependencies:**
- No security updates required
- All dependencies current as of scan date

### v1.6.3 (January 23, 2026)

**Security Implementations:**
- First release with Sigstore digital signatures
- CodeQL automated scanning enabled
- GitHub Security Advisories configured
- VirusTotal testing implemented as standard practice
- Security policy documented

**Dependencies:**
- Initial pip-audit baseline scan: 0 vulnerabilities

---

## Security Researcher Information

### Scope

**In Scope:**
- PC_Workman application code (Python source)
- Compiled executables (.exe)
- Build and release process
- Dependencies and supply chain

**Out of Scope:**
- Third-party services (GitHub, VirusTotal, etc.)
- User's local environment or system configuration
- Social engineering attacks
- Physical security

### Testing Guidelines

**Permitted:**
- Source code review and static analysis
- Sandboxed executable testing
- Dependency vulnerability research
- Build process verification

**Not Permitted:**
- Testing on production systems without permission
- Attacks targeting GitHub infrastructure
- Unauthorized access to development systems
- DoS attacks against any infrastructure

### Recognition

Security researchers who report valid vulnerabilities will be:
- Acknowledged in release notes (unless anonymity requested)
- Credited in SECURITY.md
- Listed in project contributors
- Provided with early access to fixes for verification

---

## Frequently Asked Questions

### Why should PC_Workman be trusted with administrative access?

PC_Workman should not be blindly trusted. All security measures are transparent and verifiable:
- Source code is public and auditable
- Releases are cryptographically signed
- Executables are scanned by 70+ antivirus engines
- Security practices are documented and enforced

Users should verify these measures before granting administrative access.

### What data does PC_Workman collect or transmit?

**No telemetry or analytics are collected.**

Network activity is limited to:
- Optional AI diagnostic features (HCK_GPT) - only when explicitly used
- Manual update checks (if implemented in future versions)

Core system monitoring functions operate entirely offline. No data is transmitted to external servers without explicit user action.

### Does PC_Workman require internet access?

No. Core functionality operates completely offline:
- System monitoring
- Fan control
- Performance tracking
- Diagnostic reporting

Internet access is only used for optional AI features, which require explicit user activation.

### What happens if development stops?

The repository remains public indefinitely. The license (MIT) permits:
- Forking the project
- Continuing development independently
- Commercial and non-commercial use

Source code and documentation will remain accessible.

### Is there a bug bounty program?

Not currently. PC_Workman is developed by a single person with no funding.

However:
- All security reports are taken seriously
- Researchers are publicly credited
- Fixes are prioritized based on severity
- Transparency is maintained throughout the process

---

## Contact Information

**Security Vulnerabilities:**  
Use GitHub Private Vulnerability Reporting (preferred) or email `firmuga.marcin.s@gmail.com`

**General Security Questions:**  
Open a GitHub Discussion in the Security category

**Developer Contact:**  
Marcin Firmuga  
- GitHub: [@HuckleR2003](https://github.com/HuckleR2003)
- X/Twitter: [@hck_lab](https://x.com/hck_lab)
- LinkedIn: [/marcinfirmuga](https://linkedin.com/in/marcinfirmuga)

---

## Policy Updates

**Last Updated:** January 24, 2026  
**Version:** 1.0

Changes to this security policy are tracked in git commit history. Significant changes will be announced in release notes and project communications.

This policy is reviewed quarterly and updated as needed to reflect current practices and requirements.

---

**PC_Workman Security Policy**  
Maintained by Marcin Firmuga | HCK_Labs  
MIT | Open Source | Transparent by Design
