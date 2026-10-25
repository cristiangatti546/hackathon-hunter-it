# 🎯 PC Fund Toolkit - Complete Setup

**Three automated pipelines to fund your PC build. Zero upfront cost. Legal in Italy (minorenne + parent PayPal only).**

---

## 📦 What's Included

```
pc-fund-toolkit/
├── hackathon-hunter-it/       # 🏆 Hackathon scanner → hardware prizes
├── bug-bounty-recon/          # 🐛 Bug bounty automation → cash bounties
└── itch-polymart-starter/     # 🎮 Digital product generator → passive income
```

---

## 🎯 Strategy: Pick ONE, Master It

| Path | Time to First € | Effort | Best If You... |
|------|-----------------|--------|----------------|
| **Hackathon Hunter** | 2–8 weeks | Low | Want hardware (GPU, laptop) directly, like competing |
| **Bug Bounty** | 4–12 weeks | Medium | Enjoy security, want cash, willing to learn |
| **Digital Products** | 2–6 weeks | Medium | Like building tools, want recurring revenue |

**Recommendation**: Start with **Hackathon Hunter** (runs free on GitHub Actions, zero setup) + **Bug Bounty** in parallel. Add Digital Products later.

---

## ⚡ 15-Minute Setup (Do This Now)

### 1. Hackathon Hunter → GitHub Actions (FREE, runs daily)
```bash
# 1. Fork this repo to your GitHub
# 2. Add Secrets in Settings → Secrets → Actions:
#    TELEGRAM_BOT_TOKEN     (from @BotFather)
#    TELEGRAM_CHAT_ID       (from @userinfobot)
#    NOTION_TOKEN           (optional, from notion.so/my-integrations)
#    NOTION_DB_ID           (optional, from database URL)
# 3. Enable Actions tab → "I understand my workflows may run"
# 4. Done! Runs daily at 08:00 CET, sends you Telegram alerts
```

### 2. Bug Bounty Recon → Local Install
```bash
cd bug-bounty-recon

# Install Go tools (REQUIRED)
# Windows: scoop install go  OR  download from go.dev
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
go install -v github.com/hahwul/dalfox/v2@latest

# Verify
subfinder -version && httpx -version && nuclei -version

# Update templates
nuclei -update-templates

# Python deps
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Test run
python recon.py --list-programs
python recon.py --program shopify --domain "*.shopify.com"
```

### 3. Digital Products → Generate First Project
```bash
cd itch-polymart-starter
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # (if any)

# Generate a Discord bot to sell
python generate.py discord_bot "TicketBot Pro" \
  --description "Advanced ticket system with transcripts, categories, ratings" \
  --author "Your Name" \
  --github "yourusername" \
  --price "14.99"

cd ticketbot-pro
git init && git add . && git commit -m "Initial"
gh repo create yourusername/ticketbot-pro --private --source=. --push
# Develop → tag v1.0.0 → push → auto-build → upload to Itch.io/Polymart
```

---

## 🇮🇹 Italy Legal Checklist (Minorenne + Parent PayPal)

| Requirement | Status | Action |
|-------------|--------|--------|
| Parent signs HackerOne consent | ⬜ | Parent creates account → adds you as minor |
| Parent signs W-8BEN (US tax) | ⬜ | HackerOne provides form → parent signs → upload |
| Parent receives PayPal payouts | ⬜ | Parent's PayPal linked to HackerOne/Itch.io/Polymart |
| Parent declares "redditi diversi" | ⬜ | Annual 730 quadro RL (commercialista or DIY) |
| Stay under €5k/year | ⬜ | Track earnings, no Partita IVA needed |

**All platforms (HackerOne, Itch.io, Polymart) are US-based Merchant of Record** — they handle VAT, tax forms, payouts. Your parent only receives money and declares it once a year.

---

## 📅 4-Week Sprint Plan

### Week 1: Foundation
- [ ] Fork Hackathon Hunter → GitHub Actions live
- [ ] Install Go tools + nuclei templates
- [ ] Run first bug bounty scan (Shopify)
- [ ] Generate first digital product (Discord bot)
- [ ] Parent: HackerOne consent + W-8BEN signed

### Week 2: Execute
- [ ] Apply to 3+ hackathons with hardware prizes
- [ ] Run bug bounty on 2 programs (GitLab, Vercel)
- [ ] Build Discord bot core features (tickets + mod)
- [ ] Create Itch.io + Polymart seller accounts (parent)

### Week 3: Optimize
- [ ] Review hackathon results → improve applications
- [ ] Triage bug bounty findings → submit valid ones
- [ ] Polish bot → README, demo video, screenshots
- [ ] Upload v1.0.0 to Itch.io + Polymart

### Week 4: Scale
- [ ] Automate: Hackathon Hunter runs daily
- [ ] Bug bounty: 3 programs/week, track submissions
- [ ] Digital: Start second product (CLI tool)
- [ ] Track earnings → project PC build date

---

## 💰 Revenue Targets (Realistic)

| Month | Hackathon Hardware | Bug Bounty Cash | Digital Products | Cumulative |
|-------|-------------------|-----------------|------------------|------------|
| 1 | 0–1 laptop/GPU | $0–500 | $0–50 | Hardware + $50 |
| 2 | +1 monitor/GPU | $200–1000 | $50–200 | Hardware + $500 |
| 3 | +1 laptop | $500–2000 | $200–500 | Hardware + $1500 |
| 4 | — | $1000–3000 | $500–1000 | **PC Funded!** |

**PC Budget**: €1500–2500 (RTX 4070/4080 + Ryzen 7/9 + 32GB + 2TB NVMe)

---

## 🛠️ Daily Workflow (30 min/day)

```bash
# Morning (5 min)
# Check Telegram for hackathon alerts → apply if relevant

# Evening (25 min)
cd bug-bounty-recon
python recon.py --program <next_target> --domain "<scope>"
# Review findings → draft reports → submit

# Weekend (2–4 hours)
# Build digital product features
# Create demo videos / screenshots
# Update store listings
```

---

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| GitHub Actions fails | Check Actions logs; some sites block cloud IPs; add delays |
| Go tools not found | Add `$(go env GOPATH)/bin` to PATH; restart terminal |
| Nuclei no results | Update templates: `nuclei -update-templates` |
| No hackathon results | Normal for some weeks; check manually on Devpost/Eventbrite |
| Parent refuses W-8BEN | Explain: 5 min, no cost, enables $1000s earnings |
| Itch.io rejects product | Ensure zip has README, LICENSE, working demo; check guidelines |

---

## 📚 Learning Resources

### Bug Bounty (Free)
- [PortSwigger Web Security Academy](https://portswigger.net/web-security) — **Start here**
- [HackerOne Hacktivity](https://hackerone.com/hacktivity) — Read real reports
- [NahamSec YouTube](https://youtube.com/@NahamSec) — Methodology
- [Bugcrowd University](https://www.bugcrowd.com/hackers/university/)

### Hackathons
- [Devpost Italy](https://devpost.com/hackathons?search=italy)
- [MLH Events](https://mlh.io/seasons/2025/events)
- [Hackathon Italia Discord](https://discord.gg/hackathon-italia)

### Digital Products
- [Itch.io Creator Docs](https://itch.io/docs/creators)
- [Polymart Developer Guide](https://polymart.org/docs)
- [Indie Hackers](https://www.indiehackers.com/) — Inspiration

---

## 🤝 Parent Conversation Script

> "Mom/Dad, I found a way to earn money for my PC using my coding skills. The platforms (HackerOne, Itch.io) are US companies that handle all taxes and legal stuff. You just need to:
> 1. Sign a consent form on HackerOne (5 min)
> 2. Sign a W-8BEN tax form (5 min, they provide it)
> 3. Receive PayPal payouts → declare once a year on 730 (like interest income)
> 4. I do all the technical work. Can we set this up this weekend?"

---

## 🚀 Start Now

```bash
# 1. Clone/fork the whole toolkit
git clone https://github.com/yourusername/pc-fund-toolkit.git
cd pc-fund-toolkit

# 2. Set up Hackathon Hunter (GitHub Actions) - HIGHEST PRIORITY
#    → Fork hackathon-hunter-it repo, add secrets, enable Actions

# 3. Set up Bug Bounty Recon (local)
cd bug-bounty-recon
# Follow install steps above

# 4. Generate first product
cd ../itch-polymart-starter
python generate.py discord_bot "My First Bot" --github yourusername
```

**You have everything you need. The tools run automatically. You just execute.**

---

## 📞 Support

- **Issues**: GitHub Issues on each repo
- **Questions**: Telegram @yourusername (if you set it up)
- **Discord**: Bug Bounty / Hackathon Italia communities

**Good luck! Your PC is closer than you think.** 🖥️✨