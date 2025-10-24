# Evidence úkolů a projektů (FastAPI + Jinja2 + SQLite)

**Build time:** 2025-10-24T05:48:23.818558


## Spuštění
1. (Volitelně) vytvoř a aktivuj virtuální prostředí.
2. Nainstaluj závislosti:
   ```bash
   pip install -r requirements.txt
   ```
3. Spusť vývojový server:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Otevři `http://127.0.0.1:8000`

### Výchozí role a uživatelé
Při prvním spuštění se automaticky vytvoří:
- Admin: **admin@example.com** / **admin123**
- Manager: **manager@example.com** / **manager123**
- User: **user@example.com** / **user123**

### Funkce
- Autentizace (login/registrace, logout), autorizace (role: ADMIN, MANAGER, USER)
- Projekty (vytvoření, členové), úkoly (stav, priorita, přiřazení), komentáře
- Admin: správa rolí
- Jinja2 šablony, rozdělené partials, jednoduché CSS

### Poznámky k bezpečnosti
- Hesla hashovaná pomocí `passlib[bcrypt]`.
- Session přes `SessionMiddleware` (cookie). Pro školní projekt OK.
