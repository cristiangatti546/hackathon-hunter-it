#!/usr/bin/env python3
"""
Hackathon Hunter IT - Scans Italian hackathon sources for hardware prizes.
Outputs: Markdown report + Notion/Telegram alerts.
Run locally or on GitHub Actions (free).
"""

import os
import re
import json
import asyncio
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Optional
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import feedparser
import yaml
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from dateutil import parser as date_parser

console = Console()

# ============================
# CONFIGURATION
# ============================
SOURCES = {
    "devpost": {
        "url": "https://devpost.com/hackathons?utf8=%E2%9C%93&search=italy&challenge_type=all&sort_by=Submission+Deadline",
        "parser": "devpost",
        "enabled": True,
    },
    "hackerrank": {
        "url": "https://www.hackerrank.com/events/hackathons",
        "parser": "hackerrank",
        "enabled": True,
    },
    "eventbrite_it": {
        "url": "https://www.eventbrite.it/d/italy--all/hackathon/",
        "parser": "eventbrite",
        "enabled": True,
    },
    "mii_istruzione": {
        "url": "https://www.miur.gov.it/web/guest/cerca?keys=hackathon",
        "parser": "mii",
        "enabled": True,
    },
    "regione_lombardia": {
        "url": "https://www.regione.lombardia.it/wps/portal/istituzionale/HP/DettaglioRedazionale/servizi-e-informazioni/enti-e-operatori/ricerca-e-innovazione/hackathon-lombardia",
        "parser": "generic",
        "enabled": True,
    },
    "regione_emilia": {
        "url": "https://opendata.regione.emilia-romagna.it/catalog/dataset?tags=hackathon",
        "parser": "ckan",
        "enabled": True,
    },
    "polimi_hack": {
        "url": "https://www.polimi.it/hackathon/",
        "parser": "generic",
        "enabled": True,
    },
    "unibo_hack": {
        "url": "https://www.unibo.it/it/attivita/hackathon",
        "parser": "generic",
        "enabled": True,
    },
    "hackinbo": {
        "url": "https://hackinbo.it/",
        "parser": "generic",
        "enabled": True,
    },
    "owi_italy": {
        "url": "https://www.openwebitalia.it/hackathon",
        "parser": "generic",
        "enabled": True,
    },
    "github_events": {
        "url": "https://github.com/collections/hackathons",
        "parser": "github",
        "enabled": True,
    },
    "oii_olimpiadi": {
        "url": "https://www.olympiads.it/",
        "parser": "oii",
        "enabled": True,
    },
}

HARDWARE_KEYWORDS = [
    "laptop", "notebook", "macbook", "gpu", "rtx", "nvidia", "amd", "radeon",
    "monitor", "schermo", "display", "tablet", "ipad", "smartphone", "phone",
    "raspberry", "arduino", "microcontrollore", "server", "workstation",
    "ssd", "ram", "memoria", "processore", "cpu", "scheda video", "video card",
    "headset", "cuffie", "keyboard", "tastiera", "mouse", "periferica",
    "drone", "robot", "stampante 3d", "3d printer", "vr", "ar", "oculus",
    "quest", "hololens", "hardware", "device", "dispositivo", "premio fisico",
    "in natura", "materiale", "attrezzatura", "computer", "pc", "desktop"
]

CASH_KEYWORDS = [
    "premio in denaro", "cash prize", "money", "euro", "€", "$", "usd",
    "borsa di studio", "scholarship", "grant", "finanziamento", "funding"
]

EXCLUDE_KEYWORDS = [
    "solo online", "virtual only", "remote only", "da remoto",
    "nessun premio", "no prize", "solo attestato", "certificato only"
]

# ============================
# DATA MODELS
# ============================
@dataclass
class Hackathon:
    name: str
    url: str
    source: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    registration_deadline: Optional[str] = None
    location: str = "Online / Italia"
    format: str = "Hackathon"
    prizes_hardware: List[str] = None
    prizes_cash: List[str] = None
    prizes_other: List[str] = None
    team_size: str = "1-5"
    eligibility: str = "Studenti / Open"
    description: str = ""
    tags: List[str] = None
    scraped_at: str = None
    hash_id: str = None

    def __post_init__(self):
        if self.prizes_hardware is None:
            self.prizes_hardware = []
        if self.prizes_cash is None:
            self.prizes_cash = []
        if self.prizes_other is None:
            self.prizes_other = []
        if self.tags is None:
            self.tags = []
        if self.scraped_at is None:
            self.scraped_at = datetime.now().isoformat()
        if self.hash_id is None:
            self.hash_id = hashlib.md5(f"{self.name}{self.url}".encode()).hexdigest()[:12]

    def has_hardware_prize(self) -> bool:
        return len(self.prizes_hardware) > 0

    def has_cash_prize(self) -> bool:
        return len(self.prizes_cash) > 0

    def is_relevant(self) -> bool:
        """Filter: hardware prizes, Italian, not virtual-only, not past."""
        if not self.has_hardware_prize() and not self.has_cash_prize():
            return False
        # Check not past
        if self.end_date:
            try:
                end = date_parser.parse(self.end_date)
                if end < datetime.now() - timedelta(days=7):
                    return False
            except:
                pass
        # Check exclude keywords
        text = f"{self.name} {self.description}".lower()
        for kw in EXCLUDE_KEYWORDS:
            if kw in text:
                return False
        return True


# ============================
# PARSERS
# ============================
class BaseParser:
    def __init__(self, source_name: str, config: dict):
        self.source_name = source_name
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 HackathonHunter/1.0"
        })

    def fetch(self, url: str) -> Optional[str]:
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            console.print(f"[red]Fetch error {self.source_name}: {e}[/red]")
            return None

    def parse(self, html: str) -> List[Hackathon]:
        raise NotImplementedError

    def extract_prizes(self, text: str) -> tuple:
        """Extract hardware and cash prizes from text."""
        text_lower = text.lower()
        hardware = []
        cash = []
        other = []

        for kw in HARDWARE_KEYWORDS:
            if kw in text_lower:
                # Try to extract context around keyword
                idx = text_lower.find(kw)
                context = text[max(0, idx-80):idx+80].strip()
                hardware.append(context)

        for kw in CASH_KEYWORDS:
            if kw in text_lower:
                idx = text_lower.find(kw)
                context = text[max(0, idx-80):idx+80].strip()
                cash.append(context)

        # Deduplicate
        hardware = list(dict.fromkeys(hardware))[:5]
        cash = list(dict.fromkeys(cash))[:5]

        return hardware, cash, other


class DevpostParser(BaseParser):
    def parse(self, html: str) -> List[Hackathon]:
        hacks = []
        soup = BeautifulSoup(html, "lxml")

        for card in soup.select(".hackathon-tile, .challenge-tile, article.hackathon"):
            try:
                name_el = card.select_one("h3, .challenge-title, .hackathon-name")
                name = name_el.get_text(strip=True) if name_el else "Unknown"

                link_el = card.select_one("a[href*='/hackathons/'], a[href*='/challenges/']")
                url = link_el["href"] if link_el else ""
                if url and not url.startswith("http"):
                    url = "https://devpost.com" + url

                # Dates
                date_text = card.get_text(" ", strip=True)
                dates = self._extract_dates(date_text)

                # Prizes
                prize_text = card.get_text(" ", strip=True)
                hw, cw, _ = self.extract_prizes(prize_text)

                # Location/format
                location = "Online / Globale"
                loc_el = card.select_one(".location, .hackathon-location")
                if loc_el:
                    location = loc_el.get_text(strip=True)

                hack = Hackathon(
                    name=name,
                    url=url,
                    source="devpost",
                    start_date=dates.get("start"),
                    end_date=dates.get("end"),
                    registration_deadline=dates.get("reg_deadline"),
                    location=location,
                    prizes_hardware=hw,
                    prizes_cash=cw,
                    description=prize_text[:500],
                    tags=["devpost", "international"]
                )
                hacks.append(hack)
            except Exception as e:
                console.print(f"[yellow]Devpost parse error: {e}[/yellow]")
        return hacks

    def _extract_dates(self, text: str) -> dict:
        dates = {}
        # Patterns: "Jan 1 - Jan 31, 2024", "Registration: Jan 1", etc.
        patterns = [
            (r"(?:registration|iscrizioni?).*?(\d{1,2}\s+\w+\s+\d{4})", "reg_deadline"),
            (r"(?:starts?|inizia).*?(\d{1,2}\s+\w+\s+\d{4})", "start"),
            (r"(?:ends?|finisce|deadline).*?(\d{1,2}\s+\w+\s+\d{4})", "end"),
            (r"(\d{1,2}\s+\w+\s+\d{4})\s*[-–]\s*(\d{1,2}\s+\w+\s+\d{4})", "range"),
        ]
        for pattern, key in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if key == "range":
                    dates["start"] = match.group(1)
                    dates["end"] = match.group(2)
                else:
                    dates[key] = match.group(1)
        return dates


class HackerRankParser(BaseParser):
    def parse(self, html: str) -> List[Hackathon]:
        hacks = []
        soup = BeautifulSoup(html, "lxml")

        for card in soup.select(".event-card, .hackathon-card, [data-testid='event-card']"):
            try:
                name = card.select_one("h3, .event-title")
                name = name.get_text(strip=True) if name else "HackerRank Hackathon"

                link = card.select_one("a[href*='/events/'], a[href*='/hackathon/']")
                url = link["href"] if link else "https://www.hackerrank.com/events/hackathons"
                if url and not url.startswith("http"):
                    url = "https://www.hackerrank.com" + url

                text = card.get_text(" ", strip=True)
                hw, cw, _ = self.extract_prizes(text)

                hack = Hackathon(
                    name=name,
                    url=url,
                    source="hackerrank",
                    prizes_hardware=hw,
                    prizes_cash=cw,
                    description=text[:500],
                    tags=["hackerrank", "coding"]
                )
                hacks.append(hack)
            except Exception as e:
                console.print(f"[yellow]HackerRank parse error: {e}[/yellow]")
        return hacks


class EventbriteParser(BaseParser):
    def parse(self, html: str) -> List[Hackathon]:
        hacks = []
        soup = BeautifulSoup(html, "lxml")

        for card in soup.select(".eds-event-card, .search-event-card, .event-card"):
            try:
                name_el = card.select_one("h3, .eds-event-card__title, .event-title")
                name = name_el.get_text(strip=True) if name_el else "Eventbrite Hackathon"

                link_el = card.select_one("a[href*='/e/'], a[href*='eventbrite']")
                url = link_el["href"] if link_el else ""

                # Date/time
                date_el = card.select_one(".eds-event-card__date, .event-date, time")
                date_text = date_el.get_text(strip=True) if date_el else ""

                text = card.get_text(" ", strip=True)
                hw, cw, _ = self.extract_prizes(text)

                hack = Hackathon(
                    name=name,
                    url=url,
                    source="eventbrite",
                    registration_deadline=date_text if date_text else None,
                    prizes_hardware=hw,
                    prizes_cash=cw,
                    description=text[:500],
                    tags=["eventbrite", "italy"]
                )
                hacks.append(hack)
            except Exception as e:
                console.print(f"[yellow]Eventbrite parse error: {e}[/yellow]")
        return hacks


class GenericParser(BaseParser):
    def parse(self, html: str) -> List[Hackathon]:
        hacks = []
        soup = BeautifulSoup(html, "lxml")

        # Try common patterns
        for link in soup.select("a[href*='hackathon'], a[href*='hack-a-thon']"):
            try:
                name = link.get_text(strip=True)
                if len(name) < 5:
                    continue
                url = link["href"]
                if not url.startswith("http"):
                    # Try to make absolute
                    from urllib.parse import urljoin
                    url = urljoin(self.config["url"], url)

                # Get surrounding context
                parent = link.find_parent(["article", "div", "section", "li"])
                context = parent.get_text(" ", strip=True) if parent else name
                hw, cw, _ = self.extract_prizes(context)

                hack = Hackathon(
                    name=name[:200],
                    url=url,
                    source=self.source_name,
                    prizes_hardware=hw,
                    prizes_cash=cw,
                    description=context[:500],
                    tags=[self.source_name, "italy"]
                )
                hacks.append(hack)
            except Exception:
                continue

        return hacks[:20]  # Limit


class CKANParser(BaseParser):
    def parse(self, html: str) -> List[Hackathon]:
        hacks = []
        soup = BeautifulSoup(html, "lxml")

        for dataset in soup.select(".dataset-item, .resource-item"):
            try:
                name_el = dataset.select_one("h3, .dataset-title")
                name = name_el.get_text(strip=True) if name_el else "Open Data Hackathon"

                link_el = dataset.select_one("a[href*='/dataset/']")
                url = link_el["href"] if link_el else ""
                if url and not url.startswith("http"):
                    url = "https://opendata.regione.emilia-romagna.it" + url

                text = dataset.get_text(" ", strip=True)
                hw, cw, _ = self.extract_prizes(text)

                hack = Hackathon(
                    name=name,
                    url=url,
                    source="regione_emilia",
                    prizes_hardware=hw,
                    prizes_cash=cw,
                    description=text[:500],
                    tags=["open-data", "emilia-romagna"]
                )
                hacks.append(hack)
            except Exception:
                continue
        return hacks


class GitHubParser(BaseParser):
    def parse(self, html: str) -> List[Hackathon]:
        hacks = []
        soup = BeautifulSoup(html, "lxml")

        for repo in soup.select("article.Box-row, .repo-list-item"):
            try:
                name_el = repo.select_one("h3 a, h1 a")
                name = name_el.get_text(strip=True) if name_el else "GitHub Hackathon"

                link_el = repo.select_one("h3 a")
                url = "https://github.com" + link_el["href"] if link_el else ""

                desc_el = repo.select_one("p, .repo-description")
                desc = desc_el.get_text(strip=True) if desc_el else ""

                text = f"{name} {desc}"
                hw, cw, _ = self.extract_prizes(text)

                if hw or cw:  # Only if prizes mentioned
                    hack = Hackathon(
                        name=name,
                        url=url,
                        source="github",
                        prizes_hardware=hw,
                        prizes_cash=cw,
                        description=desc[:500],
                        tags=["github", "open-source"]
                    )
                    hacks.append(hack)
            except Exception:
                continue
        return hacks


class OIIParser(BaseParser):
    def parse(self, html: str) -> List[Hackathon]:
        hacks = []
        soup = BeautifulSoup(html, "lxml")

        # OII specific - look for competition info
        for section in soup.select(".competition, .event, .gara, article"):
            try:
                name_el = section.select_one("h2, h3, .title")
                name = name_el.get_text(strip=True) if name_el else "OII Olimpiadi Informatica"

                text = section.get_text(" ", strip=True)
                hw, cw, _ = self.extract_prizes(text)

                # OII always has hardware prizes at national level
                if "nazionale" in text.lower() or "finale" in text.lower():
                    hw.append("Laptop / Tablet / Attrezzatura informatica (finale nazionale)")

                hack = Hackathon(
                    name=name,
                    url=self.config["url"],
                    source="oii",
                    prizes_hardware=hw,
                    prizes_cash=cw,
                    description=text[:500],
                    eligibility="Studenti scuole superiori",
                    tags=["oii", "olimpiadi", "studenti", "miur"]
                )
                hacks.append(hack)
            except Exception:
                continue
        return hacks


PARSER_MAP = {
    "devpost": DevpostParser,
    "hackerrank": HackerRankParser,
    "eventbrite": EventbriteParser,
    "generic": GenericParser,
    "ckan": CKANParser,
    "github": GitHubParser,
    "oii": OIIParser,
    "mii": GenericParser,
}


# ============================
# MAIN ORCHESTRATOR
# ============================
class HackathonHunter:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.all_hackathons: List[Hackathon] = []
        self.seen_hashes = set()

    def _load_config(self) -> dict:
        if self.config_path.exists():
            with open(self.config_path) as f:
                return yaml.safe_load(f)
        return {
            "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
            "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID"),
            "notion_token": os.getenv("NOTION_TOKEN"),
            "notion_db_id": os.getenv("NOTION_DB_ID"),
            "output_dir": "output",
            "max_age_days": 90,
        }

    def run(self) -> List[Hackathon]:
        console.print("[bold cyan]🏁 Hackathon Hunter IT - Starting scan...[/bold cyan]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Scanning sources...", total=len([s for s in SOURCES.values() if s["enabled"]]))

            for source_name, source_config in SOURCES.items():
                if not source_config.get("enabled", True):
                    continue

                progress.update(task, description=f"Scanning {source_name}...")
                hacks = self._scan_source(source_name, source_config)
                self.all_hackathons.extend(hacks)
                progress.advance(task)

        # Deduplicate
        self._deduplicate()

        # Filter relevant
        relevant = [h for h in self.all_hackathons if h.is_relevant()]

        # Sort by date (soonest first)
        relevant.sort(key=lambda h: h.registration_deadline or h.end_date or "9999")

        console.print(f"[green]✅ Found {len(relevant)} relevant hackathons (from {len(self.all_hackathons)} total)[/green]")

        # Output
        self._save_markdown(relevant)
        self._save_json(relevant)
        self._print_table(relevant)

        # Notifications
        if relevant:
            self._send_telegram(relevant)
            self._send_notion(relevant)

        return relevant

    def _scan_source(self, name: str, config: dict) -> List[Hackathon]:
        parser_class = PARSER_MAP.get(config["parser"], GenericParser)
        parser = parser_class(name, config)

        html = parser.fetch(config["url"])
        if not html:
            return []

        hacks = parser.parse(html)
        console.print(f"  [blue]{name}:[/blue] {len(hacks)} hackathons found")
        return hacks

    def _deduplicate(self):
        unique = []
        for h in self.all_hackathons:
            if h.hash_id not in self.seen_hashes:
                self.seen_hashes.add(h.hash_id)
                unique.append(h)
        self.all_hackathons = unique

    def _save_markdown(self, hacks: List[Hackathon]):
        out_dir = Path(self.config.get("output_dir", "output"))
        out_dir.mkdir(exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = out_dir / f"hackathon_{date_str}.md"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# 🏆 Hackathon Italia - {date_str}\n\n")
            f.write(f"*Generato automaticamente il {datetime.now().strftime('%d/%m/%Y %H:%M')}*\n\n")
            f.write(f"**Totale rilevanti: {len(hacks)}**\n\n")
            f.write("---\n\n")

            for i, h in enumerate(hacks, 1):
                f.write(f"## {i}. {h.name}\n\n")
                f.write(f"- **Fonte**: {h.source}\n")
                f.write(f"- **URL**: [{h.url}]({h.url})\n")
                if h.start_date:
                    f.write(f"- **Inizio**: {h.start_date}\n")
                if h.end_date:
                    f.write(f"- **Fine**: {h.end_date}\n")
                if h.registration_deadline:
                    f.write(f"- **Scadenza iscrizioni**: {h.registration_deadline}\n")
                f.write(f"- **Luogo**: {h.location}\n")
                f.write(f"- **Team**: {h.team_size}\n")
                f.write(f"- **Eleggibilità**: {h.eligibility}\n")

                if h.prizes_hardware:
                    f.write(f"- **🎁 Premi Hardware**:\n")
                    for p in h.prizes_hardware:
                        f.write(f"  - {p}\n")

                if h.prizes_cash:
                    f.write(f"- **💰 Premi Cash**:\n")
                    for p in h.prizes_cash:
                        f.write(f"  - {p}\n")

                if h.prizes_other:
                    f.write(f"- **📦 Altri premi**:\n")
                    for p in h.prizes_other:
                        f.write(f"  - {p}\n")

                if h.tags:
                    f.write(f"- **Tag**: {', '.join(h.tags)}\n")

                f.write(f"\n---\n\n")

        console.print(f"[green]📄 Markdown saved: {filepath}[/green]")

    def _save_json(self, hacks: List[Hackathon]):
        out_dir = Path(self.config.get("output_dir", "output"))
        out_dir.mkdir(exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = out_dir / f"hackathon_{date_str}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([asdict(h) for h in hacks], f, ensure_ascii=False, indent=2)

    def _print_table(self, hacks: List[Hackathon]):
        table = Table(title="🏆 Hackathon Rilevanti (Hardware/Cash Prizes)")
        table.add_column("#", style="dim", width=3)
        table.add_column("Nome", style="bold", width=30)
        table.add_column("Fonte", width=12)
        table.add_column("Scadenza", width=12)
        table.add_column("Premi Hardware", style="green", width=35)
        table.add_column("Premi Cash", style="yellow", width=25)
        table.add_column("Link", width=10)

        for i, h in enumerate(hacks[:30], 1):
            hw = "; ".join(h.prizes_hardware[:2]) if h.prizes_hardware else "—"
            cw = "; ".join(h.prizes_cash[:2]) if h.prizes_cash else "—"
            deadline = h.registration_deadline or h.end_date or "—"
            if len(deadline) > 12:
                deadline = deadline[:12] + "…"

            table.add_row(
                str(i),
                h.name[:30],
                h.source,
                deadline,
                hw[:35],
                cw[:25],
                "🔗" if h.url else "—"
            )

        console.print(table)

    def _send_telegram(self, hacks: List[Hackathon]):
        token = self.config.get("telegram_bot_token") or os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = self.config.get("telegram_chat_id") or os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            return

        try:
            from telegram import Bot
            bot = Bot(token=token)

            msg = f"🏆 *Hackathon Hunter IT* - {len(hacks)} nuovi hackathon con premi!\n\n"
            for h in hacks[:10]:
                hw = ", ".join(h.prizes_hardware[:2]) if h.prizes_hardware else "—"
                msg += f"• *{h.name}* ({h.source})\n  🎁 {hw}\n  🔗 {h.url}\n\n"

            asyncio.run(bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown"))
            console.print("[green]📱 Telegram notification sent[/green]")
        except Exception as e:
            console.print(f"[yellow]Telegram error: {e}[/yellow]")

    def _send_notion(self, hacks: List[Hackathon]):
        token = self.config.get("notion_token") or os.getenv("NOTION_TOKEN")
        db_id = self.config.get("notion_db_id") or os.getenv("NOTION_DB_ID")
        if not token or not db_id:
            return

        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
            }

            for h in hacks:
                # Check if already exists
                # (simplified - in production you'd query first)
                data = {
                    "parent": {"database_id": db_id},
                    "properties": {
                        "Name": {"title": [{"text": {"content": h.name}}]},
                        "Source": {"select": {"name": h.source}},
                        "URL": {"url": h.url},
                        "Registration Deadline": {"date": {"start": h.registration_deadline}} if h.registration_deadline else {},
                        "End Date": {"date": {"start": h.end_date}} if h.end_date else {},
                        "Hardware Prizes": {"rich_text": [{"text": {"content": "; ".join(h.prizes_hardware)}}]},
                        "Cash Prizes": {"rich_text": [{"text": {"content": "; ".join(h.prizes_cash)}}]},
                        "Location": {"rich_text": [{"text": {"content": h.location}}]},
                        "Eligibility": {"rich_text": [{"text": {"content": h.eligibility}}]},
                        "Tags": {"multi_select": [{"name": t} for t in h.tags]},
                    }
                }
                requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)

            console.print("[green]📝 Notion database updated[/green]")
        except Exception as e:
            console.print(f"[yellow]Notion error: {e}[/yellow]")


# ============================
# CLI ENTRY
# ============================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Hackathon Hunter IT")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--schedule", action="store_true", help="Run daily via GitHub Actions")
    args = parser.parse_args()

    hunter = HackathonHunter(args.config)
    hunter.run()

    if args.schedule:
        console.print("[cyan]⏰ Scheduled run complete. Next run in 24h.[/cyan]")


if __name__ == "__main__":
    main()