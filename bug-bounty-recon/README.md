# 🐛 Bug Bounty Recon Toolkit

**Automated reconnaissance pipeline for HackerOne/Bugcrowd/Intigriti.**
Subdomain enum → HTTP probe → Nuclei scan → Professional report.

## 🎯 Target Programs (Pre-configured)

20 high-value programs with **VRT P3/P4 bounties** (typically $100–$5000):
- Shopify, GitLab, Atlassian, Vercel, Netlify, Cloudflare, Stripe
- Discord, Slack, Notion, Linear, Figma, Supabase
- PlanetScale, Railway, Render, Fly.io, Tailscale
- 1Password, Bitwarden, Proton

## 🛠️ Prerequisites (One-time setup)

### Install Go tools (required)
```bash
# Install Go first: https://go.dev/dl/
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
go install -v github.com/hahwul/dalfox/v2@latest
go install -v github.com/projectdiscovery/katana/cmd/katana@latest

# Verify
subfinder -version
httpx -version
nuclei -version
```

### Download Nuclei templates
```bash
nuclei -update-templates
# Templates stored in ~/nuclei-templates
```

### Optional: Wordlists for better enum
```bash
mkdir -p ~/wordlists
cd ~/wordlists
# Subdomains
wget https://github.com/assetnote/commonspeak2-wordlists/raw/master/subdomains/subdomains-top1million-110000.txt
# Directories
wget https://github.com/danielmiessler/SecLists/raw/master/Discovery/Web-Content/raft-medium-directories.txt
# Parameters
wget https://github.com/danielmiessler/SecLists/raw/master/Discovery/Web-Content/param-miner.txt
```

## 🚀 Quick Start

```bash
cd bug-bounty-recon
cp config.yaml.example config.yaml
# Edit config.yaml with your hunter name

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Interactive mode (select program, enter scope)
python recon.py

# Or direct mode
python recon.py --program shopify --domain "*.shopify.com"
```

## 📋 What It Does

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  SUBFINDER  │────▶│    HTTPX    │────▶│   NUCLEI    │────▶│   REPORT    │
│  (passive)  │     │  (probing)  │     │  (scanning) │     │  (markdown) │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
  crt.sh,              Status codes,       3000+ templates,      Professional
  DNSDB,               Tech detect,        CVE/OAST/Exposure,    Markdown + JSON
  VirusTotal,          Titles,             Takeover, Misconfig   Evidence bundle
  Wayback
```

## 📂 Output Structure

```
recon_output/
└── shopify_20250115_143022/
    ├── session.json          # Full session data
    ├── subdomains.txt        # All discovered subdomains
    ├── httpx.json            # HTTP probe results
    ├── nuclei.json           # Raw nuclei findings
    └── report.md             # Professional report (submit-ready)
```

## 📄 Report Example

```markdown
# 🐛 Bug Bounty Report - Shopify

**Program**: Shopify
**Date**: 2025-01-15
**Hunter**: YourHandle
**Scope**: *.shopify.com, shopify.com

## 📋 Executive Summary
Automated reconnaissance completed for Shopify. Discovered 247 subdomains across 2 root domains. Nuclei scan identified 12 potential findings (0 critical, 3 high, 5 medium, 4 low, 0 info).

## ☢️ Vulnerability Findings (12)

### HIGH (3)
#### CVE-2024-XXXX - GitLab RCE
- **Target**: gitlab.shopify.com
- **URL**: https://gitlab.shopify.com/api/v4/projects
- **Evidence**: `{"version":"15.0.0","vulnerable":true}`
- **Reference**: https://gitlab.com/gitlab-org/gitlab/-/issues/XXXXX
```

## 💰 Bounty Expectations (Realistic)

| Severity | Typical Range | Notes |
|----------|---------------|-------|
| Critical | $3,000–$50,000+ | RCE, SQLi, Auth bypass on core |
| High | $1,000–$5,000 | SSRF, IDOR, XSS on sensitive |
| Medium | $250–$1,500 | Info disclosure, CSRF, misconfig |
| Low | $50–$300 | Rate limit, info leak, CSP bypass |
| Info | $0–$100 | Usually no bounty |

**First 3 months target**: 3–5 valid P3/P4 = **$500–$2,500** (your PC budget)

## ⚠️ Rules of Engagement

1. **Read program policy** before testing each target
2. **Stay in scope** - only test listed domains
3. **No DoS, no data exfiltration, no social engineering**
4. **Report via platform** (HackerOne/Bugcrowd/Intigriti) - never email directly
5. **Wait for triage** - don't disclose publicly until resolved

## 🇮🇹 Italy-Specific Notes

- **HackerOne**: Parent signs consent + W-8BEN → 0% US withholding
- **Payout**: PayPal/bank → parent receives → declares "redditi diversi" (730 quadro RL)
- **Threshold**: <€5k/year = no Partita IVA needed
- **Tax**: Ordinary income tax (23–43%) on net amount

## 🎓 Learning Path (If New to Bug Bounty)

1. **Week 1**: PortSwigger Web Security Academy (free labs)
2. **Week 2**: "Bug Bounty Hunter Methodology" (Jason Haddix, NahamSec)
3. **Week 3**: Practice on HackTheBox / TryHackMe / VulnHub
4. **Week 4**: First real program (start with wide-scope like Shopify)

## 📚 Resources

- [HackerOne Hacktivity](https://hackerone.com/hacktivity) - See real reports
- [Bugcrowd University](https://www.bugcrowd.com/hackers/university/)
- [Nuclei Templates](https://github.com/projectdiscovery/nuclei-templates)
- [VRT (Vulnerability Rating Taxonomy)](https://github.com/hackerone/vrt)

## 🤝 Contributing

Add new programs, improve report template, add AI-assisted analysis.

## 📄 License

MIT - Hunt responsibly.