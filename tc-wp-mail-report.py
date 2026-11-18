#!/usr/bin/env python3
"""Human-friendly HTML/plain-text reports for TC WordPress maintenance."""
import argparse
import html
import json
import re
import subprocess
import sys
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

TO = ("tc@pef.czu.cz", "lohr@pef.czu.cz")
SENDER = "TC WordPress <tc-wp-updates@tc.pef.czu.cz>"
HOST = "tc.pef.czu.cz"

def file_text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""

def objects(path):
    try:
        data = json.loads(file_text(path))
        return data if isinstance(data, list) else []
    except (ValueError, TypeError):
        return []

def esc(x):
    return html.escape(str(x), quote=True)

def entries(state, kind, is_check):
    before = {x.get("name"): x for x in objects(state / (kind + "-before.json"))}
    after = {x.get("name"): x for x in objects(state / (kind + "-after.json"))}
    result = []
    for name in sorted(before):
        item = before[name]
        old = str(item.get("version", ""))
        if is_check:
            if item.get("update") == "available" and name != "tc-pef-plugin":
                result.append((kind, name, old, str(item.get("update_version", ""))))
        elif name in after:
            new = str(after[name].get("version", ""))
            if old and new and old != new:
                result.append((kind, name, old, new))
    return result

def send(subject, plain, rich):
    msg = EmailMessage()
    msg["To"] = ", ".join(TO)
    msg["From"] = SENDER
    msg["Subject"] = subject
    msg.set_content(plain)
    msg.add_alternative(rich, subtype="html")
    subprocess.run(["/usr/sbin/sendmail", "-t", "-oi"], input=msg.as_bytes(), check=True)

def main():
    p = argparse.ArgumentParser()
    for opt in ("updated", "pending", "translations", "sensitive", "rollback", "rollback-failed", "result"):
        p.add_argument("--" + opt, type=int, default=0)
    for opt in ("mode", "start", "end", "log", "backup", "state"):
        p.add_argument("--" + opt, default="")
    p.add_argument("--mail-test", action="store_true")
    a = p.parse_args()
    state = Path(a.state or "/nonexistent")
    check = a.mode == "--check"
    if a.mail_test:
        title = "Test e-mailových oznámení"
        introduction = "Toto je zkušební e-mail systému automatické správy webu."
        outcome = "TEST"
        rows = []
    elif a.result != 0:
        title = "Údržba webu vyžaduje pozornost"
        introduction = "Během aktualizací WordPressu byla zjištěna chyba."
        outcome = "CHYBA"
        rows = entries(state, "plugins", False) + entries(state, "themes", False)
    elif check:
        title = "Byly nalezeny dostupné aktualizace"
        introduction = "Pravidelná kontrola zjistila aktualizace. Zatím se nic neinstalovalo."
        outcome = "KONTROLA"
        rows = entries(state, "plugins", True) + entries(state, "themes", True)
    else:
        title = "Aktualizace webu proběhla úspěšně"
        introduction = "Dostupné aktualizace byly nainstalovány. Kontroly webu proběhly úspěšně."
        outcome = "ÚSPĚCH"
        rows = entries(state, "plugins", False) + entries(state, "themes", False)
    if not a.mail_test:
        cb = file_text(state / "core-before").strip()
        ca = file_text(state / "core-after").strip()
        if cb and ca and cb != ca:
            rows.insert(0, ("Jádro WordPressu", "WordPress", cb, ca))
        if check and a.pending and not rows:
            introduction += " K dispozici mohou být nové překlady nebo aktualizace jádra."
    pretty = {"plugins": "Plugin", "themes": "Šablona", "Jádro WordPressu": "Jádro"}
    tr = "".join(
        '<tr><td style="padding:12px;border-bottom:1px solid #e2e8f0;">{}</td>'
        '<td style="padding:12px;border-bottom:1px solid #e2e8f0;">{}</td>'
        '<td style="padding:12px;border-bottom:1px solid #e2e8f0;">{} → <b>{}</b></td></tr>'.format(
            esc(pretty.get(k, k)), esc(n), esc(old), esc(new)
        ) for k, n, old, new in rows
    )
    changes = ("<h2 style='font-size:17px;margin-top:26px;'>"
               + ("Dostupné aktualizace" if check else "Provedené změny") + "</h2>"
               + "<table style='width:100%;border-collapse:collapse;font-size:14px;'>"
               + "<tr style='background:#f1f5f9;text-align:left;'>"
               + "<th style='padding:12px;'>Typ</th><th style='padding:12px;'>Součást</th>"
               + "<th style='padding:12px;'>Verze</th></tr>" + tr + "</table>") if rows else ""
    if a.translations:
        changes += "<p>🌐 <strong>Překlady:</strong> aktualizováno {} jazykových balíčků.</p>".format(a.translations)
    if not changes:
        changes = "<p style='color:#64748b;'>Podrobnosti jsou zaznamenány v protokolu na serveru.</p>"
    notes = ""
    if a.sensitive:
        notes += ("<p style='background:#fff7ed;padding:14px;border-left:4px solid #d97706;'>"
                  "<strong>Po aktualizaci Wordfence nebo SoSeRe:</strong> "
                  "ověřte přihlášení včetně 2FA a správné fungování personalizace.</p>")
    if a.result:
        result = ("Rollback proveden." if a.rollback else
                  "Rollback se nezdařil – je nutný ruční zásah." if a.rollback_failed else
                  "Aktualizace byla přerušena bez potvrzeného rollbacku.")
        notes += "<p style='background:#fef2f2;padding:14px;'>⚠️ <strong>{}</strong></p>".format(esc(result))
        error_lines = [re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", line).strip()
                       for line in file_text(a.log).splitlines()
                       if re.search(r"\b(ERROR|CRITICAL|CHYBA):", line, flags=re.I)]
        if error_lines:
            notes += "<p style='color:#b91c1c;'>Poslední chyba: {}</p>".format(esc(error_lines[-1][:400]))
    stamp = a.end or datetime.now().astimezone().isoformat(timespec="minutes")
    meta = "<strong>Web:</strong> {}<br><strong>Dokončeno:</strong> {}".format(esc(HOST), esc(stamp))
    if not a.mail_test:
        meta += "<br><strong>Výsledek:</strong> {}<br><strong>Záloha:</strong> {}<br><strong>Log:</strong> {}".format(
            esc(outcome), esc(a.backup or "nevytvářena"), esc(a.log)
        )
    accent = "#b91c1c" if a.result else "#2563eb" if check else "#047857"
    rich = """<!doctype html><html lang="cs"><head><meta charset="utf-8"></head>
<body style="margin:0;background:#f3f6fb;font-family:Arial,Helvetica,sans-serif;color:#243044;">
<div style="max-width:670px;margin:30px auto;background:white;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;">
<div style="background:#193452;color:#fff;padding:28px 32px;">
<div style="font-size:12px;letter-spacing:1px;color:#c6d6e8;">TESTOVACÍ CENTRUM PEF • WORDPRESS</div>
<h1 style="font-size:24px;line-height:1.3;margin:14px 0 0;">{title}</h1></div>
<div style="padding:28px 32px;">
<div style="color:{accent};font-weight:bold;font-size:13px;">● {outcome}</div>
<p style="font-size:16px;line-height:1.6;">{intro}</p>
{changes}{notes}
<div style="border-top:1px solid #e2e8f0;margin-top:26px;padding-top:18px;color:#64748b;font-size:13px;line-height:1.8;">{meta}</div>
</div><div style="padding:16px 32px;background:#f1f5f9;color:#64748b;font-size:12px;">
Automatická zpráva správce webu Testovacího centra PEF.</div></div></body></html>""".format(
        title=esc(title), accent=accent, outcome=esc(outcome), intro=esc(introduction),
        changes=changes, notes=notes, meta=meta
    )
    plain_rows = "\n".join("{} {}: {} → {}".format(pretty.get(k,k), n, old, new) for k,n,old,new in rows)
    plain = "{}\n\n{}\n\n{}\nPřeklady: {}\n\nWeb: {}\nVýsledek: {}\nČas: {}\nZáloha: {}\nProtokol: {}\n".format(
        title, introduction, plain_rows, a.translations, HOST, outcome, stamp,
        a.backup or "nevytvářena", a.log
    )
    if a.sensitive:
        plain += "\nOVĚŘIT: přihlášení s 2FA a personalizaci SoSeRe.\n"
    send("[TC WordPress] {} – {}".format(title, HOST), plain, rich)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR: Cannot prepare/send mail report: {}".format(exc), file=sys.stderr)
        sys.exit(1)
