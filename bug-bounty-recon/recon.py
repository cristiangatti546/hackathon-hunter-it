#!/usr/bin/env python3
"""
Bug Bounty Recon Toolkit - Automated reconnaissance for HackerOne/Bugcrowd/Intigriti.
Features: subdomain enum, tech detection, nuclei scanning, report drafting.
Run locally (needs: subfinder, httpx, nuclei installed via Go).
"""

import os
import json
import subprocess
import asyncio
import hashlib
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Set
from pathlib import Path

import yaml
import httpx
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm

console = Console()

# ============================
# CONFIG
# ============================
TOOLS = {
    "subfinder": "subfinder",
    "httpx": "httpx",
    "nuclei": "nuclei",
    "dalfox": "dalfox",
    "katana": "katana",
}

DEFAULT_WORDLISTS = {
    "subdomains": "~/wordlists/subdomains-top1million-110000.txt",
    "fuzzing": "~/wordlists/raft-medium-directories.txt",
    "params": "~/wordlists/param-miner.txt",
}

HACKERONE_PROGRAMS = [
    # High-value, wide scope, good for beginners
    {"handle": "shopify", "name": "Shopify", "url": "https://hackerone.com/shopify", "vrt_p3": True, "vrt_p4": True},
    {"handle": "gitlab", "name": "GitLab", "url": "https://hackerone.com/gitlab", "vrt_p3": True, "vrt_p4": True},
    {"handle": "atlassian", "name": "Atlassian", "url": "https://hackerone.com/atlassian", "vrt_p3": True, "vrt_p4": True},
    {"handle": "vercel", "name": "Vercel", "url": "https://hackerone.com/vercel", "vrt_p3": True, "vrt_p4": True},
    {"handle": "netlify", "name": "Netlify", "url": "https://hackerone.com/netlify", "vrt_p3": True, "vrt_p4": True},
    {"handle": "cloudflare", "name": "Cloudflare", "url": "https://hackerone.com/cloudflare", "vrt_p3": True, "vrt_p4": True},
    {"handle": "stripe", "name": "Stripe", "url": "https://hackerone.com/stripe", "vrt_p3": True, "vrt_p4": True},
    {"handle": "discord", "name": "Discord", "url": "https://hackerone.com/discord", "vrt_p3": True, "vrt_p4": True},
    {"handle": "slack", "name": "Slack", "url": "https://hackerone.com/slack", "vrt_p3": True, "vrt_p4": True},
    {"handle": "notion", "name": "Notion", "url": "https://hackerone.com/notion", "vrt_p3": True, "vrt_p4": True},
    {"handle": "linear", "name": "Linear", "url": "https://hackerone.com/linear", "vrt_p3": True, "vrt_p4": True},
    {"handle": "figma", "name": "Figma", "url": "https://hackerone.com/figma", "vrt_p3": True, "vrt_p4": True},
    {"handle": "supabase", "name": "Supabase", "url": "https://hackerone.com/supabase", "vrt_p3": True, "vrt_p4": True},
    {"handle": "planetscale", "name": "PlanetScale", "url": "https://hackerone.com/planetscale", "vrt_p3": True, "vrt_p4": True},
    {"handle": "railway", "name": "Railway", "url": "https://hackerone.com/railway", "vrt_p3": True, "vrt_p4": True},
    {"handle": "render", "name": "Render", "url": "https://hackerone.com/render", "vrt_p3": True, "vrt_p4": True},
    {"handle": "fly-io", "name": "Fly.io", "url": "https://hackerone.com/fly-io", "vrt_p3": True, "vrt_p4": True},
    {"handle": "tailscale", "name": "Tailscale", "url": "https://hackerone.com/tailscale", "vrt_p3": True, "vrt_p4": True},
    {"handle": "1password", "name": "1Password", "url": "https://hackerone.com/1password", "vrt_p3": True, "vrt_p4": True},
    {"handle": "bitwarden", "name": "Bitwarden", "url": "https://hackerone.com/bitwarden", "vrt_p3": True, "vrt_p4": True},
    {"handle": "proton", "name": "Proton", "url": "https://hackerone.com/proton", "vrt_p3": True, "vrt_p4": True},
]

# ============================
# DATA MODELS
# ============================
@dataclass
class Target:
    program: str
    domain: str
    scope_type: str = "wildcard"  # wildcard, exact, cidr
    notes: str = ""

@dataclass
class Subdomain:
    domain: str
    source: str
    ip: Optional[str] = None
    status_code: Optional[int] = None
    tech: List[str] = field(default_factory=list)
    title: str = ""
    content_length: int = 0
    scanned_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Finding:
    target: str
    template: str
    severity: str  # critical, high, medium, low, info
    matched_at: str
    url: str
    evidence: str
    description: str = ""
    reference: str = ""
    tags: List[str] = field(default_factory=list)

@dataclass
class ReconSession:
    program: str
    targets: List[Target]
    subdomains: List[Subdomain] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    notes: str = ""

    def to_dict(self):
        return asdict(self)


# ============================
# TOOL WRAPPERS
# ============================
class ToolRunner:
    @staticmethod
    def check_tools() -> Dict[str, bool]:
        """Check if required tools are installed."""
        results = {}
        for name, cmd in TOOLS.items():
            try:
                subprocess.run([cmd, "-version"], capture_output=True, timeout=5)
                results[name] = True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                results[name] = False
        return results

    @staticmethod
    def run(cmd: List[str], timeout: int = 300) -> subprocess.CompletedProcess:
        console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    @staticmethod
    def run_async(cmd: List[str]) -> asyncio.subprocess.Process:
        return asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )


class SubdomainEnum:
    def __init__(self, session: ReconSession):
        self.session = session

    def run_subfinder(self, domain: str) -> List[str]:
        """Run subfinder for passive subdomain enumeration."""
        cmd = [TOOLS["subfinder"], "-d", domain, "-silent", "-all", "-recursive"]
        result = ToolRunner.run(cmd)
        if result.returncode == 0:
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return []

    def run_crtsh(self, domain: str) -> List[str]:
        """Query crt.sh for certificate transparency logs."""
        try:
            url = f"https://crt.sh/?q=%.{domain}&output=json"
            resp = httpx.get(url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                domains = set()
                for entry in data:
                    name = entry.get("name_value", "")
                    for n in name.split("\n"):
                        n = n.strip().lstrip("*.")
                        if n.endswith(f".{domain}") or n == domain:
                            domains.add(n)
                return list(domains)
        except Exception:
            pass
        return []

    def run_amass(self, domain: str) -> List[str]:
        """Run amass if available (slower but thorough)."""
        cmd = [TOOLS.get("amass", "amass"), "enum", "-passive", "-d", domain]
        result = ToolRunner.run(cmd, timeout=600)
        if result.returncode == 0:
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return []

    def enumerate(self, domain: str) -> List[Subdomain]:
        console.print(f"[cyan]🔍 Enumerating subdomains for {domain}...[/cyan]")

        all_domains = set()

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Running subfinder...", total=1)
            subs = self.run_subfinder(domain)
            all_domains.update(subs)
            progress.update(task, advance=1, description=f"subfinder: {len(subs)} found")

            task = progress.add_task("Querying crt.sh...", total=1)
            subs = self.run_crtsh(domain)
            all_domains.update(subs)
            progress.update(task, advance=1, description=f"crt.sh: {len(subs)} found")

        # Filter to in-scope
        in_scope = [d for d in all_domains if self._in_scope(d, domain)]
        console.print(f"[green]✅ Found {len(in_scope)} in-scope subdomains[/green]")

        return [Subdomain(domain=d, source="passive") for d in sorted(in_scope)]

    def _in_scope(self, subdomain: str, root_domain: str) -> bool:
        return subdomain == root_domain or subdomain.endswith(f".{root_domain}")


class HttpProbe:
    def __init__(self):
        pass

    def probe(self, subdomains: List[Subdomain]) -> List[Subdomain]:
        console.print(f"[cyan]🌐 Probing {len(subdomains)} subdomains with httpx...[/cyan]")

        # Write domains to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for s in subdomains:
                f.write(f"{s.domain}\n")
            temp_file = f.name

        try:
            cmd = [
                TOOLS["httpx"],
                "-l", temp_file,
                "-silent",
                "-status-code",
                "-title",
                "-tech-detect",
                "-content-length",
                "-json",
                "-follow-redirects",
                "-timeout", "10",
                "-retries", "2",
            ]
            result = ToolRunner.run(cmd, timeout=300)

            alive = []
            for line in result.stdout.splitlines():
                try:
                    data = json.loads(line)
                    sub = next((s for s in subdomains if s.domain == data.get("host")), None)
                    if sub:
                        sub.ip = data.get("a", [None])[0]
                        sub.status_code = data.get("status_code")
                        sub.title = data.get("title", "")
                        sub.tech = data.get("tech", [])
                        sub.content_length = data.get("content_length", 0)
                        alive.append(sub)
                except json.JSONDecodeError:
                    continue

            console.print(f"[green]✅ {len(alive)} alive subdomains[/green]")
            return alive

        finally:
            os.unlink(temp_file)


class NucleiScanner:
    def __init__(self):
        self.templates_dir = self._get_nuclei_templates()

    def _get_nuclei_templates(self) -> str:
        # Nuclei stores templates in ~/nuclei-templates
        return os.path.expanduser("~/nuclei-templates")

    def scan(self, subdomains: List[Subdomain], severity: List[str] = None) -> List[Finding]:
        if not subdomains:
            return []

        console.print(f"[cyan]☢️  Running nuclei scan on {len(subdomains)} targets...[/cyan]")

        # Write URLs to temp file
        import tempfile
        urls = []
        for s in subdomains:
            if s.status_code:
                scheme = "https" if s.status_code == 443 else "http"
                urls.append(f"{scheme}://{s.domain}")
            else:
                urls.append(f"http://{s.domain}")
                urls.append(f"https://{s.domain}")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for u in urls:
                f.write(f"{u}\n")
            temp_file = f.name

        try:
            cmd = [
                TOOLS["nuclei"],
                "-l", temp_file,
                "-silent",
                "-json",
                "-rate-limit", "50",
                "-bulk-size", "25",
                "-timeout", "10",
                "-retries", "1",
                "-max-host-error", "10",
            ]

            if severity:
                cmd.extend(["-severity", ",".join(severity)])

            # Add common template tags for bug bounty
            cmd.extend(["-tags", "cve,oast,generic,exposure,misconfig,takeover"])

            result = ToolRunner.run(cmd, timeout=600)

            findings = []
            for line in result.stdout.splitlines():
                try:
                    data = json.loads(line)
                    finding = Finding(
                        target=data.get("host", ""),
                        template=data.get("template", ""),
                        severity=data.get("info", {}).get("severity", "info").lower(),
                        matched_at=datetime.now().isoformat(),
                        url=data.get("matched-at", ""),
                        evidence=data.get("extracted-results", [""])[0] if data.get("extracted-results") else "",
                        description=data.get("info", {}).get("description", ""),
                        reference=", ".join(data.get("info", {}).get("reference", [])),
                        tags=data.get("info", {}).get("tags", []),
                    )
                    findings.append(finding)
                except json.JSONDecodeError:
                    continue

            # Deduplicate by template+target
            seen = set()
            unique = []
            for f in findings:
                key = f"{f.template}:{f.target}"
                if key not in seen:
                    seen.add(key)
                    unique.append(f)

            console.print(f"[green]✅ Nuclei found {len(unique)} unique findings[/green]")
            return unique

        finally:
            os.unlink(temp_file)


class ReportGenerator:
    TEMPLATE = """# 🐛 Bug Bounty Report - {program}

**Program**: {program}
**Platform**: HackerOne / Bugcrowd / Intigriti
**Date**: {date}
**Hunter**: {hunter}
**Scope**: {scope}

---

## 📋 Executive Summary

{summary}

---

## 🎯 Scope & Targets

{targets_table}

---

## 🔍 Reconnaissance Results

### Subdomains Discovered ({subdomain_count})

{subdomains_table}

### Technology Stack

{tech_table}

---

## ☢️ Vulnerability Findings ({finding_count})

{findings_detail}

---

## 📝 Notes & Next Steps

{notes}

---

## 📎 Evidence

All raw outputs saved in session directory:
- `subdomains.txt` - Full subdomain list
- `httpx.json` - HTTP probe results
- `nuclei.json` - Raw nuclei findings
- `session.json` - Full session data

---

*Report generated by Bug Bounty Recon Toolkit*
*Session ID: {session_id}*
"""

    @staticmethod
    def generate(session: ReconSession, hunter_name: str = "Anonymous") -> str:
        # Build tables
        targets_md = "\n".join([f"- `{t.domain}` ({t.scope_type}) - {t.notes}" for t in session.targets])

        subdomains_md = ""
        if session.subdomains:
            subdomains_md = "| Domain | Status | Tech | Title |\n|---|---|---|---|\n"
            for s in session.subdomains[:50]:
                tech = ", ".join(s.tech[:3]) if s.tech else "—"
                title = s.title[:50] if s.title else "—"
                subdomains_md += f"| `{s.domain}` | {s.status_code or '—'} | {tech} | {title} |\n"

        tech_counts = {}
        for s in session.subdomains:
            for t in s.tech:
                tech_counts[t] = tech_counts.get(t, 0) + 1
        tech_md = "\n".join([f"- **{k}**: {v} hosts" for k, v in sorted(tech_counts.items(), key=lambda x: -x[1])[:15]])

        findings_by_sev = {"critical": [], "high": [], "medium": [], "low": [], "info": []}
        for f in session.findings:
            findings_by_sev[f.severity].append(f)

        findings_md = ""
        for sev in ["critical", "high", "medium", "low", "info"]:
            items = findings_by_sev[sev]
            if not items:
                continue
            findings_md += f"\n### {sev.upper()} ({len(items)})\n\n"
            for f in items:
                findings_md += f"#### {f.template}\n"
                findings_md += f"- **Target**: {f.target}\n"
                findings_md += f"- **URL**: {f.url}\n"
                findings_md += f"- **Evidence**: `{f.evidence}`\n"
                if f.description:
                    findings_md += f"- **Description**: {f.description}\n"
                if f.reference:
                    findings_md += f"- **Reference**: {f.reference}\n"
                findings_md += "\n"

        summary = f"Automated reconnaissance completed for **{session.program}**. "
        summary += f"Discovered **{len(session.subdomains)}** subdomains across **{len(session.targets)}** root domains. "
        summary += f"Nuclei scan identified **{len(session.findings)}** potential findings "
        summary += f"({len(findings_by_sev['critical'])} critical, {len(findings_by_sev['high'])} high, "
        summary += f"{len(findings_by_sev['medium'])} medium, {len(findings_by_sev['low'])} low, {len(findings_by_sev['info'])} info)."

        return ReportGenerator.TEMPLATE.format(
            program=session.program,
            date=datetime.now().strftime("%Y-%m-%d"),
            hunter=hunter_name,
            scope=", ".join([t.domain for t in session.targets]),
            summary=summary,
            targets_table=targets_md,
            subdomain_count=len(session.subdomains),
            subdomains_table=subdomains_md,
            tech_table=tech_md,
            finding_count=len(session.findings),
            findings_detail=findings_md,
            notes=session.notes or "Nessuna nota aggiuntiva.",
            session_id=hashlib.md5(session.program.encode()).hexdigest()[:8],
        )

    @staticmethod
    def save_session(session: ReconSession, output_dir: Path):
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON
        with open(output_dir / "session.json", "w") as f:
            json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)

        # Save subdomains
        with open(output_dir / "subdomains.txt", "w") as f:
            for s in session.subdomains:
                f.write(f"{s.domain}\n")

        # Save httpx results
        with open(output_dir / "httpx.json", "w") as f:
            json.dump([{"domain": s.domain, "ip": s.ip, "status": s.status_code,
                       "tech": s.tech, "title": s.title, "cl": s.content_length}
                      for s in session.subdomains], f, indent=2)

        # Save nuclei results
        with open(output_dir / "nuclei.json", "w") as f:
            json.dump([asdict(f) for f in session.findings], f, indent=2, ensure_ascii=False)

        # Save markdown report
        report = ReportGenerator.generate(session)
        with open(output_dir / "report.md", "w") as f:
            f.write(report)

        console.print(f"[green]📄 Session saved to {output_dir}[/green]")


# ============================
# MAIN ORCHESTRATOR
# ============================
class BugBountyRecon:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.session: Optional[ReconSession] = None

    def _load_config(self, path: str) -> dict:
        if Path(path).exists():
            with open(path) as f:
                return yaml.safe_load(f)
        return {
            "output_dir": "recon_output",
            "hunter_name": "Anonymous",
            "default_severity": ["critical", "high", "medium"],
            "max_subdomains": 500,
        }

    def select_program(self) -> dict:
        """Interactive program selection."""
        console.print("\n[bold]🎯 Select target program:[/bold]")
        table = Table()
        table.add_column("#", style="dim")
        table.add_column("Program", style="bold")
        table.add_column("Platform")
        table.add_column("VRT P3/P4")

        for i, p in enumerate(HACKERONE_PROGRAMS, 1):
            table.add_row(str(i), p["name"], "HackerOne", "✅" if p["vrt_p3"] else "—")

        console.print(table)

        choice = Prompt.ask("Enter number", choices=[str(i) for i in range(1, len(HACKERONE_PROGRAMS)+1)] + ["custom"])
        if choice == "custom":
            name = Prompt.ask("Program name")
            handle = Prompt.ask("Handle (for URL)")
            url = Prompt.ask("Program URL")
            return {"name": name, "handle": handle, "url": url, "vrt_p3": True, "vrt_p4": True}
        return HACKERONE_PROGRAMS[int(choice)-1]

    def get_scope(self, program: dict) -> List[Target]:
        """Fetch scope from program (simplified - manual entry for now)."""
        console.print(f"\n[bold]📋 Scope for {program['name']}[/bold]")
        console.print("Enter root domains (one per line, empty to finish):")
        console.print("Example: *.shopify.com, shopify.com, admin.shopify.com")

        targets = []
        while True:
            domain = Prompt.ask("Domain", default="")
            if not domain:
                break
            scope_type = "wildcard" if domain.startswith("*.") else "exact"
            targets.append(Target(program=program["handle"], domain=domain.lstrip("*."), scope_type=scope_type))

        if not targets:
            # Default to main domain
            targets.append(Target(program=program["handle"], domain=program["handle"] + ".com", scope_type="wildcard"))

        return targets

    def run_recon(self, program: dict, targets: List[Target]) -> ReconSession:
        self.session = ReconSession(program=program["name"], targets=targets)

        console.print(f"\n[bold cyan]🚀 Starting recon for {program['name']}[/bold cyan]")

        # Check tools
        tools_ok = ToolRunner.check_tools()
        missing = [k for k, v in tools_ok.items() if not v]
        if missing:
            console.print(f"[red]❌ Missing tools: {', '.join(missing)}[/red]")
            console.print("Install with: `go install -v github.com/projectdiscovery/{subfinder,httpx,nuclei,dalfox,katana}/cmd/...@latest`")
            if not Confirm.ask("Continue anyway?"):
                return self.session

        all_subdomains = []

        # Phase 1: Subdomain enumeration
        for target in targets:
            enum = SubdomainEnum(self.session)
            subs = enum.enumerate(target.domain)
            all_subdomains.extend(subs)

        # Deduplicate
        seen = set()
        unique_subs = []
        for s in all_subdomains:
            if s.domain not in seen:
                seen.add(s.domain)
                unique_subs.append(s)

        self.session.subdomains = unique_subs[:self.config.get("max_subdomains", 500)]

        # Phase 2: HTTP probing
        if unique_subs:
            prober = HttpProbe()
            alive = prober.probe(unique_subs)
            self.session.subdomains = alive

        # Phase 3: Nuclei scanning
        if self.session.subdomains:
            scanner = NucleiScanner()
            severity = self.config.get("default_severity", ["critical", "high", "medium"])
            findings = scanner.scan(self.session.subdomains, severity)
            self.session.findings = findings

        self.session.completed_at = datetime.now().isoformat()

        # Save
        output_dir = Path(self.config["output_dir"]) / f"{program['handle']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ReportGenerator.save_session(self.session, output_dir)

        # Print summary
        self._print_summary()

        return self.session

    def _print_summary(self):
        if not self.session:
            return

        table = Table(title=f"📊 Recon Summary: {self.session.program}")
        table.add_column("Metric", style="bold")
        table.add_column("Value", style="green")

        table.add_row("Root Domains", str(len(self.session.targets)))
        table.add_row("Subdomains Found", str(len([s for s in self.session.subdomains if s.source == "passive"])))
        table.add_row("Alive Subdomains", str(len([s for s in self.session.subdomains if s.status_code])))
        table.add_row("Total Findings", str(len(self.session.findings)))

        sev_counts = {}
        for f in self.session.findings:
            sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1
        for sev in ["critical", "high", "medium", "low", "info"]:
            if sev_counts.get(sev):
                table.add_row(f"  {sev.capitalize()}", str(sev_counts[sev]))

        console.print(table)


# ============================
# CLI
# ============================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Bug Bounty Recon Toolkit")
    parser.add_argument("--config", default="config.yaml", help="Config file")
    parser.add_argument("--program", help="Program handle (skip interactive)")
    parser.add_argument("--domain", help="Single domain to scan (skip interactive)")
    parser.add_argument("--list-programs", action="store_true", help="List known programs")
    args = parser.parse_args()

    recon = BugBountyRecon(args.config)

    if args.list_programs:
        table = Table(title="Known HackerOne Programs (VRT P3/P4)")
        table.add_column("Handle", style="bold")
        table.add_column("Name")
        table.add_column("URL")
        for p in HACKERONE_PROGRAMS:
            table.add_row(p["handle"], p["name"], p["url"])
        console.print(table)
        return

    if args.program and args.domain:
        program = next((p for p in HACKERONE_PROGRAMS if p["handle"] == args.program), {"name": args.program, "handle": args.program})
        targets = [Target(program=program["handle"], domain=args.domain, scope_type="wildcard")]
        recon.run_recon(program, targets)
    else:
        program = recon.select_program()
        targets = recon.get_scope(program)
        recon.run_recon(program, targets)


if __name__ == "__main__":
    main()