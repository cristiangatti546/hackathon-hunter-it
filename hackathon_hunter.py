#!/usr/bin/env python3
"""
Hackathon Hunter IT v2 - Fonti aggiornate che funzionano da GitHub Actions.
Invia notifica Telegram anche se 0 risultati (così sai che è vivo).
"""

import os
import re
import json
import asyncio
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from typing import List, Optional
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import yaml
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# ============================
# CONFIG - FONTI CHE FUNZIONANO DA CLOUD
# ============================
SOURCES = {
    "devpost_italy": {
        "url": "https://devpost.com/hackathons?utf8=%E2%9C%93&search=italy&challenge_type=all&sort_by=Submission+Deadline",
        "parser": "devpost",
        "enabled": True,
    },
    "devpost_europe": {
        "url": "https://devpost.com/hackathons?utf8=%E2%9C%93&search=europe&challenge_type=all&sort_by=Submission+Deadline",
        "parser": "devpost",
        "enabled": True,
    },
    "mlh": {
        "url": "https://mlh.io/seasons/2025/events",
        "parser": "mlh",
        "enabled": True,
    },
    "hackathon_com": {
        "url": "https://hackathon.com/hackathons?location=Italy",
        "parser": "hackathon_com",
        "enabled": True,
    },
    "devfolio": {
        "url": "https://devfolio.co/hackathons",
        "parser": "devfolio",
        "enabled": True,
    },
    "hackclub": {
        "url": "https://hackathons.hackclub.com/",
        "parser": "hackclub",
        "enabled": True,
    },
    "oii": {
        "url": "https://www.olympiads.it/",
        "parser": "oii",
        "enabled": True,
    },
    "github_topics": {
        "url": "https://api.github.com/search/repositories?q=topic:hackathon+language:python&sort=updated&order=desc&per_page=20",
        "parser": "github_api",
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
    "in natura", "materiale", "attrezzatura", "computer", "pc", "desktop",
    "console", "playstation", "xbox", "switch", "steam deck",
]

CASH_KEYWORDS = [
    "premio in denaro", "cash prize", "money", "euro", "€", "$", "usd",
    "borsa di studio", "scholarship", "grant", "finanziamento", "funding",
    "prize pool", "prize money", "winning prize",
]

EXCLUDE_KEYWORDS = [
    "solo online", "virtual only", "remote only", "da remoto",
    "nessun premio", "no prize", "solo attestato", "certificato only",
    "swag only", "sticker", "t-shirt", "hoodie", "merch",
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
    prizes_hardware: List[str] = field(default_factory=list)
    prizes_cash: List[str] = field(default_factory=list)
    prizes_other: List[str] = field(default_factory=list)
    team_size: str = "1-5"
    eligibility: str = "Open"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
    hash_id: str = field(default_factory=lambda: hashlib.md5(f"{datetime.now()}".encode()).hexdigest()[:12])

    def has_hardware_prize(self) -> bool:
        return len(self.prizes_hardware) > 0

    def has_cash_prize(self) -> bool:
        return len(self.prizes_cash) > 0

    def is_relevant(self) -> bool:
        if not self.has_hardware_prize() and not self.has_cash_prize():
            return False
        if self.end_date:
            try:
                end = datetime.fromisoformat(self.end_date.replace('Z', '+00:00'))
                if end < datetime.now() - timedelta(days=7):
                    return False
            except:
                pass
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 HackathonHunter/2.0"
        })

    def fetch(self, url: str) -> Optional[str]:
        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            console.print(f"[red]Fetch error {self.source_name}: {e}[/red]")
            return None

    def parse(self, html: str) -> List[Hackathon]:
        raise NotImplementedError

    def extract_prizes(self, text: str) -> tuple:
        text_lower = text.lower()
        hardware = []
        cash = []
        other = []

        for kw in HARDWARE_KEYWORDS:
            if kw in text_lower:
                idx = text_lower.find(kw)
                context = text[max(0, idx-100):idx+100].strip()
                hardware.append(context)

        for kw in CASH_KEYWORDS:
            if kw in text_lower:
                idx = text_lower.find(kw)
                context = text[max(0, idx-100):idx+100].strip()
                cash.append(context)

        hardware = list(dict.fromkeys(hardware))[:5]
        cash = list(dict.fromkeys(cash))[:5]
        return hardware, cash, other


class DevpostParser(BaseParser):
    def parse(self, html: str) -> List[Hackathon]:
        hacks = []
        soup = BeautifulSoup(html, "lxml")

        for card in soup.select(".hackathon-tile, .challenge-tile, article.hackathon, [data-hackathon-id]"):
            try:
                name_el = card.select_one("h3, .challenge-title, .hackathon-name, [data-hackathon-name]")
                name = name_el.get_text(strip=True) if name_el else "Unknown"

                link_el = card.select_one("a[href*='/hackathons/'], a[href*='/challenges/']")
                url = link_el["href"] if link_el else ""
                if url and not url.startswith("http"):
                    url = "https://devpost.com" + url

                date_text = card.get_text(" ", strip=True)
                dates = self._extract_dates(date_text)

                prize_text = card.get_text(" ", strip=True)
                hw, cw, _ = self.extract_prizes(prize_text)

                location = "Online / Globale"
                loc_el = card.select_one(".location, .hackathon-location, [data-location]")
                if loc_el:
                    location = loc_el.get_text(strip=True)

                hack = Hackathon(
                    name=name,
                    url=url,
                    source=self.source_name,
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
        patterns = [
            (r"(?:registration|iscrizioni?|register).*?(\d{1,2}\s+\w+\s+\d{4})", "reg_deadline"),
            (r"(?:starts?|inizia|begin).*?(\d{1,2}\s+\w+\s+\d{4})", "start"),
            (r"(?:ends?|finisce|deadline|submission).*?(\d{1,2}\s+\w+\s+\d{4})", "end"),
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


class MLHParser(BaseParser):
    def parse(self, html: str) -> List[Hackathon]:
        hacks = []
        soup = BeautifulSoup(html, "lxml")

        for card in soup.select(".event, .event-wrapper, [data-event-id]"):
            try:
                name_el = card.select_one("h3, .event-name, .event-title")
                name = name_el.get_text(strip=True) if name_el else "MLH Hackathon"

                link_el = card.select_one("a[href*='/event/']")
                url = link_el["href"] if link_el else "https://mlh.io/seasons/2025/events"
                if url and not url.startswith("http"):
                    url = "https://mlh.io" + url

                date_el = card.select_one(".event-date, .date, time")
                date_text = date_el.get_text(strip=True) if date_el else ""

                prize_el = card.select_one(".prizes, .prize, .rewards")
                prize_text = prize_el.get_text(strip=True) if prize_el else card.get_text(" ", strip=True)
                hw, cw, _ = self.extract_prizes(prize_text)

                location_el = card.select_one(".location, .event-location")
                location = location_el.get_text(strip=True) if location_el else "Vari locations"

                hack = Hackathon(
                    name=name,
                    url=url,
                    source="mlh",
                    registration_deadline=date_text if date_text else None,
                    location=location,
                    prizes_hardware=hw,
                    prizes_cash=cw,
                    description=prize_text[:500],
                    tags=["mlh", "student", "global"]
                )
                hacks.append(hack)
            except Exception:
                continue
        return hacks


class HackathonComParser(BaseParser):
    def parse(self, html: str) -> List[Hackathon]:
        hacks = []
        soup = BeautifulSoup(html, "lxml")

        for card in soup.select(".hackathon-item, .event-card, .listing-item"):
            try:
                name_el = card.select_one("h3, .title, .hackathon-title")
                name = name_el.get_text(strip=True) if name_el else "Hackathon.com Event"

                link_el = card.select_one("a[href*='/hackathon/']")
                url = link_el["href"] if link_el else ""
                if url and not url.startswith("http"):
                    url = "https://hackathon.com" + url

                text = card.get_text(" ", strip=True)
                hw, cw, _ = self.extract_prizes(text)

                hack = Hackathon(
                    name=name,
                    url=url,
                    source="hackathon_com",
                    prizes_hardware=hw,
                    prizes_cash=cw,
                    description=text[:500],
                    tags=["hackathon.com", "global"]
                )
                hacks.append(hack)
            except Exception:
                continue
        return hacks[:15]


class DevfolioParser(BaseParser):
    def parse(self, html: str) -> List[Hackathon]:
        hacks = []
        soup = BeautifulSoup(html, "lxml")

        for card in soup.select(".hackathon-card, .event-card, [data-hackathon-id]"):
            try:
                name_el = card.select_one("h3, .hackathon-name, .title")
                name = name_el.get_text(strip=True) if name_el else "Devfolio Hackathon"

                link_el = card.select_one("a[href*='/hackathon/']")
                url = link_el["href"] if link_el else "https://devfolio.co/hackathons"
                if url and not url.startswith("http"):
                    url = "https://devfolio.co" + url

                text = card.get_text(" ", strip=True)
                hw, cw, _ = self.extract_prizes(text)

                hack = Hackathon(
                    name=name,
                    url=url,
                    source="devfolio",
                    prizes_hardware=hw,
                    prizes_cash=cw,
                    description=text[:500],
                    tags=["devfolio", "web3", "global"]
                )
                hacks.append(hack)
            except Exception:
                continue
        return hacks[:15]


class HackClubParser(BaseParser):
    def parse(self, html: str) -> List[Hackathon]:
        hacks = []
        soup = BeautifulSoup(html, "lxml")

        for card in soup.select(".hackathon, .event, article"):
            try:
                name_el = card.select_one("h2, h3, .title")
                name = name_el.get_text(strip=True) if name_el else "Hack Club Hackathon"

                link_el = card.select_one("a[href*='hackathon'], a[href*='event']")
                url = link_el["href"] if link_el else "https://hackathons.hackclub.com/"
                if url and not url.startswith("http"):
                    url = "https://hackathons.hackclub.com" + url

                text = card.get_text(" ", strip=True)
                hw, cw, _ = self.extract_prizes(text)

                # Hack Club spesso ha hardware per studenti
                if "high school" in text.lower() or "student" in text.lower():
                    hw.append("Premi hardware per studenti (tipico Hack Club)")

                hack = Hackathon(
                    name=name,
                    url=url,
                    source="hackclub",
                    prizes_hardware=hw,
                    prizes_cash=cw,
                    description=text[:500],
                    eligibility="Studenti high school / università",
                    tags=["hackclub", "students", "global"]
                )
                hacks.append(hack)
            except Exception:
                continue
        return hacks


class OIIParser(BaseParser):
    def parse(self, html: str) -> List[Hackathon]:
        hacks = []
        soup = BeautifulSoup(html, "lxml")

        text = soup.get_text(" ", strip=True)
        hw, cw, _ = self.extract_prizes(text)

        # OII = premi hardware garantiti alle finali
        hw.append("Laptop / tablet / attrezzatura informatica (finali nazionali OII)")

        hack = Hackathon(
            name="OII - Olimpiadi Italiane Informatica",
            url="https://www.olympiads.it/",
            source="oii",
            prizes_hardware=hw,
            prizes_cash=cw,
            description="Competizione nazionale MIUR per studenti scuole superiori. Premi hardware alle finali.",
            eligibility="Studenti scuole superiori italiane",
            tags=["oii", "olimpiadi", "studenti", "miur", "hardware-garantito"]
        )
        hacks.append(hack)
        return hacks


class GitHubAPIParser(BaseParser):
    def parse(self, html: str) -> List[Hackathon]:
        hacks = []
        try:
            data = json.loads(html)
            for repo in data.get("items", []):
                name = repo.get("full_name", "")
                url = repo.get("html_url", "")
                desc = repo.get("description", "") or ""
                text = f"{name} {desc}"
                hw, cw, _ = self.extract_prizes(text)
                if hw or cw:
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
            pass
        return hacks


PARSER_MAP = {
    "devpost": DevpostParser,
    "mlh": MLHParser,
    "hackathon_com": HackathonComParser,
    "devfolio": DevfolioParser,
    "hackclub": HackClubParser,
    "oii": OIIParser,
    "github_api": GitHubAPIParser,
}


# ============================
# MAIN ORCHESTRATOR
# ============================
class HackathonHunter:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.all_hackathons: List[Hackathon] = []
        self.seen_hashes = set()

    def _load_config(self, path: str) -> dict:
        if Path(path).exists():
            with open(path) as f:
                return yaml.safe_load(f)
        return {
            "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
            "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID"),
            "output_dir": "output",
            "max_age_days": 90,
        }

    def run(self) -> List[Hackathon]:
        console.print("[bold cyan]🏁 Hackathon Hunter IT v2 - Starting scan...[/bold cyan]")

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Scanning sources...", total=len([s for s in SOURCES.values() if s["enabled"]]))

            for source_name, source_config in SOURCES.items():
                if not source_config.get("enabled", True):
                    continue
                progress.update(task, description=f"Scanning {source_name}...")
                hacks = self._scan_source(source_name, source_config)
                self.all_hackathons.extend(hacks)
                progress.advance(task)

        self._deduplicate()
        relevant = [h for h in self.all_hackathons if h.is_relevant()]
        relevant.sort(key=lambda h: h.registration_deadline or h.end_date or "9999")

        console.print(f"[green]✅ Found {len(relevant)} relevant hackathons (from {len(self.all_hackathons)} total)[/green]")

        self._save_markdown(relevant)
        self._save_json(relevant)
        self._print_table(relevant)

        # SEMPRE invia notifica Telegram (anche se 0 risultati)
        self._send_telegram(relevant)

        return relevant

    def _scan_source(self, name: str, config: dict) -> List[Hackathon]:
        parser_class = PARSER_MAP.get(config["parser"])
        if not parser_class:
            return []
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

            if not hacks:
                f.write("## 📭 Nessun hackathon con premi hardware/cash trovato oggi\n\n")
                f.write("Le fonti sono state controllate ma non ci sono eventi con premi rilevanti al momento.\n")
                f.write("Riprova domani - nuovi hackathon vengono aggiunti continuamente.\n\n")
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
            console.print("[yellow]⚠️ Telegram token/chat_id non configurati[/yellow]")
            return

        try:
            from telegram import Bot
            bot = Bot(token=token)

            date_str = datetime.now().strftime("%d/%m/%Y")
            if hacks:
                msg = f"🏆 *Hackathon Hunter IT* - {date_str}\n"
                msg += f"Trovati **{len(hacks)}** hackathon con premi hardware/cash:\n\n"
                for h in hacks[:8]:
                    hw = ", ".join(h.prizes_hardware[:2]) if h.prizes_hardware else "—"
                    msg += f"• *{h.name}* ({h.source})\n  🎁 {hw}\n  🔗 {h.url}\n\n"
                if len(hacks) > 8:
                    msg += f"...e altri {len(hacks)-8}.\n"
            else:
                msg = f"🏆 *Hackathon Hunter IT* - {date_str}\n"
                msg += "Nessun hackathon con premi hardware/cash trovato oggi.\n"
                msg += "Fonti controllate: Devpost, MLH, Hackathon.com, Devfolio, Hack Club, OII, GitHub.\n"
                msg += "Riprova domani! 🔍"

            asyncio.run(bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown"))
            console.print("[green]📱 Telegram notification sent[/green]")
        except Exception as e:
            console.print(f"[red]Telegram error: {e}[/red]")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Hackathon Hunter IT v2")
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
