# 🎮 Itch.io / Polymart Starter

**Generate ready-to-sell digital product projects in seconds.**
Discord bots, Minecraft plugins, Unity/Godot assets, CLI tools → GitHub Actions build → zip releases → upload to stores.

## 🎯 Supported Product Types

| Type | Platform | Example Ideas |
|------|----------|---------------|
| `discord_bot` | Itch.io, Polymart | Ticket bot, Mod bot, Leveling, Music, Utility |
| `cli_tool` | Itch.io | File converter, API client, Code generator, Linter |
| `minecraft_plugin` | Polymart, Spigot | Economy, Claims, Minigames, Admin tools |
| `unity_asset` | Itch.io, Unity Asset Store | Shader, Tool, System, Template |
| `godot_asset` | Itch.io, Godot Asset Library | Addon, Template, Shader, Tool |

## 🚀 Quick Start

```bash
cd itch-polymart-starter

# Generate a Discord bot project
python generate.py discord_bot "TicketBot Pro" \
  --description "Advanced ticket system with transcripts, categories, ratings" \
  --author "Your Name" \
  --github "yourusername" \
  --price "14.99"

# Generate a CLI tool
python generate.py cli_tool "JSON Wizard" \
  --description "Convert, validate, transform JSON/YAML/TOML with ease" \
  --price "4.99"

# Output: ./ticketbot-pro/ or ./json-wizard/ with full structure
```

## 📁 Generated Structure (Discord Bot Example)

```
ticketbot-pro/
├── src/
│   └── bot/
│       ├── main.py              # Entry point
│       ├── commands/
│       │   ├── ticket.py        # /ticket command
│       │   └── mod.py           # /purge command
│       └── utils/
│           ├── embed.py         # Rich embed helpers
│           └── config.py        # Config management
├── tests/
│   └── test_bot.py
├── meta/
│   ├── itch.json                # Itch.io listing data
│   ├── polymart.json            # Polymart listing data
│   └── manifest.json            # Project metadata
├── .github/workflows/
│   └── build.yml                # Auto-build on tag push
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── README.md
├── LICENSE
├── .env.example
└── .gitignore
```

## 🏗️ Build & Release Pipeline

```bash
cd ticketbot-pro
git init
git add .
git commit -m "🎉 Initial commit"

# Create GitHub repo (requires gh CLI)
gh repo create yourusername/ticketbot-pro --private --source=. --push

# Develop your bot...
# When ready to release:
git tag v1.0.0
git push origin v1.0.0
```

**GitHub Actions automatically:**
1. ✅ Runs tests
2. 📦 Creates zip release package
3. 🏷️ Creates GitHub Release with zip attached
4. 📥 You download zip → upload to Itch.io / Polymart

## 💰 Selling on Itch.io / Polymart

### Itch.io (All digital goods)
1. Create account → "Sell your work" → "New project"
2. Upload zip from GitHub Release
3. Fill metadata from `meta/itch.json`
4. Set price → Publish
5. **Payout**: Monthly, PayPal/bank, 10% platform fee

### Polymart (Minecraft plugins, Discord bots)
1. Create account → "Submit Resource"
2. Upload zip + fill `meta/polymart.json`
3. **Payout**: Monthly, PayPal/crypto, 12.5% platform fee

### Tax (Italy, minorenne + parent PayPal)
- Platform = Merchant of Record (US-based)
- Parent signs W-8BEN → 0% US withholding
- Parent receives PayPal → declares "redditi diversi" (730 quadro RL)
- <€5k/year = no Partita IVA needed

## 💡 Product Ideas for Your Skills (AI + Coding)

### Discord Bots ($10–30)
- **Ticket Pro** - Transcripts, categories, ratings, DM logs
- **Mod Suite** - Auto-mod, logs, warnings, appeals, raid protection
- **Leveling+** - XP, roles, leaderboards, rewards, voice tracking
- **Server Setup** - One-click template: roles, channels, perms, bots
- **AI Assistant** - ChatGPT/Claude integration, conversation memory

### CLI Tools ($5–15)
- **API Client Generator** - OpenAPI → typed client (Python/TS/Go)
- **Config Validator** - JSON Schema + env validation for deployments
- **Log Analyzer** - Parse, filter, visualize logs (nginx, docker, k8s)
- **Dependency Updater** - Auto-PR for outdated deps with changelog

### Minecraft Plugins ($15–50)
- **Economy Plus** - Shops, auctions, jobs, taxes, multi-currency
- **Land Claims** - Grief prevention, sub-claims, rental, admin tools
- **Minigame Framework** - BedWars, SkyBlock, Duels, Party system

## 🛠️ Customization

Edit `generate.py` to add new templates or modify existing ones.

```python
# Add new template type
TEMPLATES["unity_shader"] = {
    "files": {...},
    "context": {...}
}
```

## 📚 Resources

- [Itch.io Seller Guide](https://itch.io/docs/creators/selling)
- [Polymart Developer Docs](https://polymart.org/docs)
- [Discord.py Guide](https://discordpy.readthedocs.io/)
- [GitHub Actions Docs](https://docs.github.com/en/actions)

## 📄 License

MIT - Build and sell freely.