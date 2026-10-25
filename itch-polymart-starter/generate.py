# Itch.io / Polymart Starter - Project Generator
# Run: python generate.py

import os
import json
import shutil
from pathlib import Path
from string import Template

TEMPLATES = {
    "discord_bot": {
        "files": {
            "src/bot/__init__.py": '"""{{project_name}} - Discord Bot"""\n__version__ = "{{version}}"\n',
            "src/bot/main.py": '''import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()

# Load cogs
async def load_cogs():
    for filename in os.listdir("./src/bot/commands"):
        if filename.endswith(".py") and not filename.startswith("_"):
            await bot.load_extension(f"bot.commands.{filename[:-3]}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(load_cogs())
    bot.run(os.getenv("DISCORD_TOKEN"))
''',
            "src/bot/commands/__init__.py": "",
            "src/bot/commands/ticket.py": '''import discord
from discord.ext import commands
from discord import app_commands

class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ticket", description="Create a support ticket")
    async def ticket(self, interaction: discord.Interaction):
        await interaction.response.send_message("Ticket system coming soon!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ticket(bot))
''',
            "src/bot/commands/mod.py": '''import discord
from discord.ext import commands
from discord import app_commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="purge", description="Delete messages")
    @app_commands.default_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: int):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"Deleted {len(deleted)} messages", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
''',
            "src/bot/utils/__init__.py": "",
            "src/bot/utils/embed.py": '''import discord

def success(title: str, description: str) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=discord.Color.green())

def error(title: str, description: str) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=discord.Color.red())

def info(title: str, description: str) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=discord.Color.blue())
''',
            "src/bot/utils/config.py": '''import os
from dataclasses import dataclass

@dataclass
class Config:
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    PREFIX: str = "!"
    OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))

config = Config()
''',
            "tests/test_bot.py": '''import pytest
from src.bot.main import bot

@pytest.mark.asyncio
async def test_bot_startup():
    assert bot is not None
''',
            "meta/itch.json": '''{
  "title": "{{project_name}}",
  "short_text": "{{description}}",
  "description": "# {{project_name}}\n\n{{description}}\n\n## Features\n- Feature 1\n- Feature 2\n- Feature 3\n\n## Requirements\n- Python 3.11+\n- Discord.py 2.3+\n\n## Installation\n```bash\npip install -r requirements.txt\ncp .env.example .env\n# Edit .env with your token\npython -m src.bot.main\n```\n\n## Commands\n- `/ticket` - Create support ticket\n- `/purge` - Delete messages (mods only)\n\n## License\n{{license}}",
  "category": "tools",
  "tags": ["discord", "bot", "python", "ticket", "moderation"],
  "price": "{{price_usd}}",
  "author": "{{author_name}}",
  "website": "https://github.com/{{github_username}}/{{project_slug}}"
}''',
            "meta/polymart.json": '''{
  "name": "{{project_name}}",
  "description": "{{description}}",
  "version": "{{version}}",
  "author": "{{author_name}}",
  "website": "https://github.com/{{github_username}}/{{project_slug}}",
  "category": "Discord Bots",
  "price": {{price_usd}},
  "currency": "USD",
  "tags": ["discord", "bot", "ticket", "moderation", "python"],
  "requirements": ["Python 3.11+"],
  "installation": "Upload the zip to your bot host, install requirements, configure .env"
}''',
            "meta/manifest.json": '''{
  "name": "{{project_slug}}",
  "version": "{{version}}",
  "description": "{{description}}",
  "author": "{{author_name}}",
  "license": "{{license}}",
  "repository": "https://github.com/{{github_username}}/{{project_slug}}",
  "main": "src/bot/main.py",
  "scripts": {
    "start": "python -m src.bot.main",
    "dev": "python -m src.bot.main",
    "test": "pytest"
  },
  "dependencies": {
    "discord.py": ">=2.3.0",
    "python-dotenv": ">=1.0.0"
  },
  "devDependencies": {
    "pytest": ">=7.0.0",
    "pytest-asyncio": ">=0.21.0"
  }
}''',
            ".github/workflows/build.yml": '''name: Build & Release

on:
  push:
    tags:
      - "v*"
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run tests
        run: pytest

      - name: Create release package
        run: |
          mkdir -p dist
          zip -r dist/{{project_slug}}-${{ github.ref_name }}.zip \\
            src/ \\
            meta/ \\
            README.md \\
            LICENSE \\
            requirements.txt \\
            .env.example

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: {{project_slug}}-${{ github.ref_name }}
          path: dist/
          retention-days: 30

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        if: startsWith(github.ref, 'refs/tags/')
        with:
          files: dist/*.zip
          generate_release_notes: true
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
''',
            "requirements.txt": "discord.py>=2.3.0\npython-dotenv>=1.0.0\n",
            "requirements-dev.txt": "pytest>=7.0.0\npytest-asyncio>=0.21.0\n",
            "pyproject.toml": '''[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "{{project_slug}}"
version = "{{version}}"
description = "{{description}}"
authors = [{name = "{{author_name}}", email = "{{author_email}}"}]
license = {text = "{{license}}"}
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "discord.py>=2.3.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
]

[project.urls]
Homepage = "https://github.com/{{github_username}}/{{project_slug}}"
Repository = "https://github.com/{{github_username}}/{{project_slug}}"
Issues = "https://github.com/{{github_username}}/{{project_slug}}/issues"

[tool.setuptools.packages.find]
where = ["src"]
include = ["{{project_slug}}*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
''',
            "README.md": '''# {{project_name}}

{{description}}

## 🚀 Features
- ✅ Feature 1
- ✅ Feature 2
- ✅ Feature 3

## 📦 Installation

### Option 1: Download Release (Recommended)
1. Go to [Releases](https://github.com/{{github_username}}/{{project_slug}}/releases)
2. Download latest `{{project_slug}}-vX.Y.Z.zip`
3. Extract and follow setup below

### Option 2: From Source
```bash
git clone https://github.com/{{github_username}}/{{project_slug}}.git
cd {{project_slug}}
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## ⚙️ Configuration
```bash
cp .env.example .env
# Edit .env with your values
```

Required environment variables:
| Variable | Description |
|----------|-------------|
| `DISCORD_TOKEN` | Your bot token from Discord Developer Portal |
| `OWNER_ID` | Your Discord user ID (for owner-only commands) |

## 🎮 Usage
```bash
python -m src.bot.main
```

Bot commands:
- `/ticket` - Create a support ticket
- `/purge <amount>` - Delete messages (moderators only)

## 🏪 Store Listings
- **Itch.io**: [{{project_name}}](https://itch.io/)
- **Polymart**: [{{project_name}}](https://polymart.org/)

## 🧪 Testing
```bash
pip install -r requirements-dev.txt
pytest
```

## 📄 License
{{license}} - See [LICENSE](LICENSE) for details.

## 👨‍💻 Author
{{author_name}} - [GitHub](https://github.com/{{github_username}})
''',
            "LICENSE": "MIT License\n\nCopyright (c) {{year}} {{author_name}}\n\nPermission is hereby granted...",
            ".env.example": "DISCORD_TOKEN=your_bot_token_here\nOWNER_ID=your_discord_user_id\n",
            ".gitignore": "__pycache__/\n*.py[cod]\n.venv/\n.env\n.env.*\n!.env.example\n.pytest_cache/\n.coverage\ndist/\n*.egg-info/\n.DS_Store\n",
        },
        "context": {
            "version": "1.0.0",
            "year": "2025",
        }
    },
    "cli_tool": {
        "files": {
            "src/{{project_slug}}/__init__.py": '"""{{project_name}} - CLI Tool"""\n__version__ = "{{version}}"\n',
            "src/{{project_slug}}/cli.py": '''import click
from rich.console import Console
from .core import main_function

console = Console()

@click.group()
@click.version_option(version="{{version}}")
def cli():
    """{{project_name}} - {{description}}"""
    pass

@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output file")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def process(input_file, output, verbose):
    """Process input file."""
    if verbose:
        console.log(f"Processing {input_file}")
    result = main_function(input_file)
    if output:
        with open(output, "w") as f:
            f.write(result)
        console.log(f"[green]Output written to {output}[/green]")
    else:
        console.print(result)

if __name__ == "__main__":
    cli()
''',
            "src/{{project_slug}}/core.py": '''def main_function(input_path: str) -> str:
    """Core processing logic."""
    with open(input_path, "r") as f:
        content = f.read()
    # TODO: Implement your logic here
    return f"Processed: {len(content)} characters\n{content[:100]}..."
''',
            "src/{{project_slug}}/utils.py": '''from rich.console import Console
console = Console()

def log_info(msg: str):
    console.log(f"[blue]INFO[/blue] {msg}")

def log_success(msg: str):
    console.log(f"[green]SUCCESS[/green] {msg}")

def log_error(msg: str):
    console.log(f"[red]ERROR[/red] {msg}")
''',
            "tests/test_core.py": '''import pytest
from src.{{project_slug}}.core import main_function

def test_main_function(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")
    result = main_function(str(test_file))
    assert "Processed" in result
    assert "hello world" in result
''',
            "meta/itch.json": '''{
  "title": "{{project_name}}",
  "short_text": "{{description}}",
  "description": "# {{project_name}}\n\n{{description}}\n\n## Installation\n```bash\npip install {{project_slug}}\n```\n\n## Usage\n```bash\n{{project_slug}} process input.txt -o output.txt\n```\n\n## License\n{{license}}",
  "category": "tools",
  "tags": ["cli", "tool", "python", "utility"],
  "price": "{{price_usd}}",
  "author": "{{author_name}}",
  "website": "https://github.com/{{github_username}}/{{project_slug}}"
}''',
            ".github/workflows/build.yml": '''name: Build & Release

on:
  push:
    tags:
      - "v*"
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install build

      - name: Run tests
        run: pytest

      - name: Build package
        run: python -m build

      - name: Create release zip
        run: |
          mkdir -p dist
          cp -r src/ dist/
          cp README.md LICENSE requirements.txt dist/
          cd dist
          zip -r ../{{project_slug}}-${{ github.ref_name }}.zip .

      - name: Upload to GitHub Release
        uses: softprops/action-gh-release@v1
        if: startsWith(github.ref, 'refs/tags/')
        with:
          files: |
            dist/*.whl
            dist/*.tar.gz
            {{project_slug}}-${{ github.ref_name }}.zip
          generate_release_notes: true
''',
            "requirements.txt": "click>=8.1.0\nrich>=13.0.0\n",
            "requirements-dev.txt": "pytest>=7.0.0\nbuild>=1.0.0\n",
            "pyproject.toml": '''[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "{{project_slug}}"
version = "{{version}}"
description = "{{description}}"
authors = [{name = "{{author_name}}", email = "{{author_email}}"}]
license = {text = "{{license}}"}
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1.0",
    "rich>=13.0.0",
]

[project.scripts]
{{project_slug}} = "{{project_slug}}.cli:cli"

[project.optional-dependencies]
dev = ["pytest>=7.0.0", "build>=1.0.0"]

[tool.setuptools.packages.find]
where = ["src"]
include = ["{{project_slug}}*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
''',
            "README.md": '''# {{project_name}}

{{description}}

## 🚀 Installation
```bash
pip install {{project_slug}}
# or download from releases
```

## 📖 Usage
```bash
{{project_slug}} process input.txt -o output.txt --verbose
```

## 🏪 Store Listings
- **Itch.io**: [{{project_name}}](https://itch.io/)

## 📄 License
{{license}}
''',
            "LICENSE": "MIT License\n\nCopyright (c) {{year}} {{author_name}}\n\nPermission is hereby granted...",
            ".gitignore": "__pycache__/\n*.py[cod]\n.venv/\n.env\n.pytest_cache/\n.coverage\ndist/\n*.egg-info/\nbuild/\n.DS_Store\n",
        },
        "context": {
            "version": "1.0.0",
            "year": "2025",
        }
    },
}


def generate_project(project_type: str, output_dir: Path, **kwargs):
    """Generate project from template."""
    if project_type not in TEMPLATES:
        raise ValueError(f"Unknown project type: {project_type}")

    template = TEMPLATES[project_type]
    context = {**template["context"], **kwargs}

    # Ensure project_slug is set
    if "project_slug" not in context:
        context["project_slug"] = context["project_name"].lower().replace(" ", "-").replace("_", "-")

    output_dir.mkdir(parents=True, exist_ok=True)

    for rel_path, content in template["files"].items():
        # Replace template variables in path
        final_path = Template(rel_path).safe_substitute(context)
        full_path = output_dir / final_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Replace template variables in content
        final_content = Template(content).safe_substitute(context)
        full_path.write_text(final_content, encoding="utf-8")
        print(f"Created: {final_path}")

    print(f"\n✅ Project generated at {output_dir}")
    print("\nNext steps:")
    print(f"  cd {output_dir}")
    print("  git init && git add . && git commit -m 'Initial commit'")
    print("  # Edit source code in src/")
    print("  # Update meta/*.json for store listings")
    print("  # Push to GitHub, create tag v1.0.0 to trigger build")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Itch.io / Polymart Project Generator")
    parser.add_argument("type", choices=list(TEMPLATES.keys()), help="Project type")
    parser.add_argument("name", help="Project name")
    parser.add_argument("--output", "-o", default=".", help="Output directory")
    parser.add_argument("--description", default="A cool tool for developers")
    parser.add_argument("--author", default="Your Name")
    parser.add_argument("--email", default="you@example.com")
    parser.add_argument("--github", default="yourusername")
    parser.add_argument("--license", default="MIT", choices=["MIT", "BSD-3", "Proprietary"])
    parser.add_argument("--price", default="9.99")
    parser.add_argument("--category", default="tools")

    args = parser.parse_args()

    output_path = Path(args.output) / args.name.lower().replace(" ", "-")
    generate_project(
        args.type,
        output_path,
        project_name=args.name,
        description=args.description,
        author_name=args.author,
        author_email=args.email,
        github_username=args.github,
        license=args.license,
        price_usd=args.price,
        itch_category=args.category,
    )


if __name__ == "__main__":
    main()