# 🏆 Hackathon Hunter IT

**Automated scanner for Italian hackathons with hardware/cash prizes.**
Runs free on GitHub Actions daily → sends you Telegram/Notion alerts + Markdown reports.

## 🎯 What it finds
- Hackathons with **hardware prizes** (laptop, GPU, monitor, Raspberry Pi, etc.)
- Hackathons with **cash prizes** (€/$)
- **Italian sources**: Devpost, HackerRank, Eventbrite, MIUR, Regioni, Università, OII, GitHub, community
- Filters out: virtual-only, no-prize, past events

## 🚀 Quick Start (5 minutes)

### Option A: GitHub Actions (FREE, runs daily automatically) ✅ RECOMMENDED

1. **Fork this repo** → your GitHub account
2. **Add secrets** in Settings → Secrets → Actions:
   - `TELEGRAM_BOT_TOKEN` (from @BotFather)
   - `TELEGRAM_CHAT_ID` (from @userinfobot)
   - `NOTION_TOKEN` (optional, from notion.so/my-integrations)
   - `NOTION_DB_ID` (optional, from database URL)
3. **Enable Actions** in the Actions tab
4. **Done!** Runs daily at 08:00 CET, commits reports to repo, sends Telegram

### Option B: Run locally

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/hackathon-hunter-it.git
cd hackathon-hunter-it

# Install
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Config
cp config.yaml.example config.yaml
# Edit config.yaml with your tokens (or use env vars)

# Run once
python hackathon_hunter.py --once
```

## 📱 Telegram Setup (2 minutes)

1. Open Telegram → search `@BotFather` → `/newbot` → follow steps → **copy token**
2. Search `@userinfobot` → **copy your Chat ID**
3. Add both to GitHub Secrets or `config.yaml`

## 📝 Notion Setup (optional)

1. Create integration at https://notion.so/my-integrations → **copy token**
2. Create database with properties: Name (title), Source (select), URL (url), Registration Deadline (date), End Date (date), Hardware Prizes (text), Cash Prizes (text), Location (text), Eligibility (text), Tags (multi_select)
3. Share database with your integration
4. Copy database ID from URL: `https://notion.so/xxx/DATABASE_ID?v=...`
5. Add to secrets/config

## 📂 Output

```
output/
├── hackathon_2025-01-15.md    # Human-readable report
├── hackathon_2025-01-15.json  # Machine-readable data
└── ...
```

**Markdown example:**
```markdown
## 1. Hackathon Lombardia 2025
- Fonte: regione_lombardia
- URL: https://regione.lombardia.it/...
- Scadenza iscrizioni: 2025-02-15
- Premi Hardware:
  - Laptop Lenovo ThinkPad X1 Carbon (1° classificato)
  - Monitor 27" 4K (2° classificato)
  - Raspberry Pi 5 kit (3° classificato)
```

## ⚙️ Customization

Edit `SOURCES` dict in `hackathon_hunter.py` to add/remove sources.
Edit `HARDWARE_KEYWORDS` / `CASH_KEYWORDS` to tune prize detection.

## 🐛 Troubleshooting

| Issue | Fix |
|-------|-----|
| No results | Check GitHub Actions logs; some sites block cloud IPs |
| Telegram not working | Verify bot token & chat ID; test with `curl "https://api.telegram.org/bot<TOKEN>/getMe"` |
| Notion not working | Verify token has database access; check DB property names match code |
| Too many false positives | Add keywords to `EXCLUDE_KEYWORDS` |

## 📊 Sources Monitored

| Source | Type | Prizes |
|--------|------|--------|
| Devpost | International | Hardware + Cash |
| HackerRank | Coding comps | Cash + Swag |
| Eventbrite Italia | Local events | Hardware + Cash |
| MIUR / Scuola | Student | Hardware (laptop, tablet) |
| Regione Lombardia | Regional | Hardware |
| Regione Emilia-Romagna | Open Data | Hardware + Cash |
| PoliMi / UniBo / HackInBo | University | Hardware |
| OII (Olimpiadi Informatica) | National student | **Laptop/GPU guaranteed** |
| GitHub Events | Open source | Swag + Cash |

## 🤝 Contributing

PRs welcome! Add new Italian sources, improve parsers, add keywords.

## 📄 License

MIT - Use freely for your PC fund.