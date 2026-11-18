# TC PEF – automatická správa aktualizací WordPressu

Nástroje pro bezpečně řízené aktualizace produkčního WordPressu Testovacího centra PEF: **jádro, pluginy (včetně Wordfence a SoSeRe), šablony a překlady**.

**Režimy:** `--check` (bez zásahu), `--run` (záloha, aktualizace, smoke testy, případně rollback), `--mail-test` (test odeslání).

E-mail se odesílá **jen při skutečně provedené aktualizaci, při nalezení aktualizací v režimu kontroly nebo při chybě** (a při výslovném testu pošty), nikoliv při každodenním běhu bez změn. Zpráva má přehledný HTML formát a textovou alternativu. Příjemci: **tc@pef.czu.cz** a **lohr@pef.czu.cz**. Výjimka z automatických aktualizací: vlastní `tc-pef-plugin`.

> ⚠️ Produkční nasazení: rollback se spouští pouze při **zjištěné** chybě. Neodhalí všechny aplikační závady, zejména průchod Wordfence 2FA a oprávnění po přihlášení. Obnovení databáze může přepsat změny vzniklé od pořízení zálohy. Doporučujeme servisní okno a předem ověřenou obnovu na testovacím prostředí.

## Soubory

- `tc-wp-maintenance` – hlavní aktualizační nástroj, zálohy, kontroly, rollback a pošta.
- `tc-wp-mail-report.py` – lidsky čitelná HTML a textová verze reportu (změněné verze, překlady, výsledek, upozornění 2FA).
- `tc-wp-prune-backups.py` – automatická retence: **nejvýše 10 posledních záloh, maximální stáří šest kalendářních měsíců**; splněny musí být obě podmínky.
- `tc-wp-maintenance.service` a `.timer` – denní spouštění systemd kolem 04:35 (s náhodným posunem nejvýše 10 minut).
- `install.sh` – instalace souborů a záloha předešlé verze, bez automatické změny stavu timeru.
- `update-server.sh` – nasazení a následný `--check`.
- `update-from-github.sh` – bezpečný `git pull --ff-only` a nasazení ze serveru.

## Nasazení z /home/lohr

Repozitář naklonujte pod účtem `lohr` (použijte HTTPS nebo nastavené SSH):

```bash
cd /home/lohr
git clone https://github.com/vaclavlohr/tc-wordpress-maintenance.git
sudo bash /home/lohr/tc-wordpress-maintenance/update-server.sh
```

Další aktualizace:

```bash
bash /home/lohr/tc-wordpress-maintenance/update-from-github.sh
```

Skript `update-server.sh` provede pouze nasazení souborů a `--check`. Při aktualizaci jsou zálohovány také dosavadní verze Python pomocných skriptů. **Nespouští ostré aktualizace ani automaticky nepřepíná timery.**

## Ovládání

```bash
sudo /usr/local/sbin/tc-wp-maintenance --mail-test
sudo /usr/local/sbin/tc-wp-maintenance --check
sudo /usr/local/sbin/tc-wp-maintenance --run
systemctl list-timers --all | grep tc-wp
journalctl -u tc-wp-maintenance.service -n 60 --no-pager
```

Pokud není dostupná žádná aktualizace, nevzniká nová záloha a neodesílá se e-mail. Při chybě přijde upozornění vždy. Aktualizace pluginů Wordfence i SoSeRe jsou zahrnuty, zatímco `tc-pef-plugin` zůstává mimo automatické aktualizace.

Denní časovač `tc-wp-maintenance.timer` aktivujte až po otestování zálohy, obnovy a doručování reportů. Před aktivací vypněte staré časovače `tc-wp-updater.timer` a `tc-wp-language-updater.timer`, aby nedocházelo k souběhu aktualizací.

## Předpoklady

AlmaLinux, WordPress v `/var/www/wp`, `wpdeploy`, WP-CLI v `/usr/local/bin/wp`, prefix databázových tabulek `tc_wp_`, externí `/usr/local/sbin/tc-wp-core-updater`; dostupné `rsync`, `curl`, `flock`, `sendmail`. Účet `wpdeploy` musí smět zapisovat do aktualizovaných pluginů, šablon a překladů.

Redis Object Cache musí zůstat vypnutá (`WP_REDIS_DISABLED=true`, žádný aktivní `wp-content/object-cache.php`) do vyřešení dřívějšího problému s přihlášením a 2FA.

## Omezení bezpečnosti

- Zálohy a logy zůstávají **pouze na produkčním serveru**; `wp-config.php`, databázové exporty, přístupové údaje ani interní certifikáty do GitHubu nepatří.
- Rollback obnovuje WordPress soubory a tabulky `tc_wp_`, nikoliv ostatní databáze, externí služby nebo průběžně zapisované složky `uploads`, `wflogs`, `litespeed`, `cache`.
- E-mail doručený programu `sendmail` není automaticky potvrzením doručení do schránky.
- Po aktualizaci Wordfence / SoSeRe ručně ověřte přihlášení s 2FA a personalizaci.

V případě zpřístupnění repozitáře veřejnosti jde o zdrojový kód, **nikoli** o úplnou produkční konfiguraci serveru.
