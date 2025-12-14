# hck_GPT Module

## 📋 Opis

hck_GPT to moduł AI asystenta dla PC Workman, zapewniający inteligentne optymalizacje systemu i wsparcie użytkownika.

## 🗂️ Struktura Modułu

```
hck_gpt/
├── __init__.py                  # Inicjalizacja modułu
├── chat_handler.py              # Główna logika chatu i przetwarzanie komend
├── service_setup_wizard.py      # Kreator optymalizacji usług Windows
├── services_manager.py          # Manager usług Windows (włączanie/wyłączanie)
└── README.md                    # Dokumentacja (ten plik)
```

## ⚙️ Funkcje

### 1. Service Setup Wizard 🧙

Interaktywny kreator, który pomaga użytkownikowi zoptymalizować PC poprzez wyłączenie niepotrzebnych usług Windows.

**Jak używać:**
```
> service setup
```

**Proces:**
1. Powitanie i wyjaśnienie
2. Seria pytań o użycie konkretnych funkcji (Printer, Bluetooth, Remote Desktop, etc.)
3. Podsumowanie i potwierdzenie
4. Aplikacja optymalizacji
5. Zapis konfiguracji

**Pytania zadawane przez kreator:**
- Do you have a Printer connected to your PC?
- Do you use Bluetooth devices?
- Do you use Remote Desktop or PC sharing?
- Do you use Fax services?
- Do you have a drawing tablet or use pen input?
- Do you use Xbox gaming features?
- Do you want to keep Windows telemetry enabled?

### 2. Services Manager 🔧

Zarządza usługami Windows - wyłącza i włącza je na podstawie preferencji użytkownika.

**Obsługiwane kategorie usług:**
- **Printer** - Print Spooler
- **Bluetooth** - Bluetooth Support Services
- **Remote** - Remote Desktop & Registry
- **Fax** - Fax Service
- **Tablet** - Tablet Input Service
- **Xbox** - Xbox Services (XblAuthManager, XblGameSave, etc.)
- **Telemetry** - Windows Telemetry & Diagnostics

**Konfiguracja zapisywana w:**
```
data/services_config.json
```

### 3. Chat Handler 💬

Przetwarza wiadomości użytkownika i kieruje je do odpowiednich komponentów.

**Dostępne komendy:**

| Komenda | Opis |
|---------|------|
| `service setup` | Uruchom kreator optymalizacji |
| `service status` | Pokaż status usług |
| `restore services` | Przywróć wszystkie wyłączone usługi |
| `help` | Pokaż dostępne komendy |

## 🚀 Integracja

### W UI (hck_gpt_panel.py)

```python
from hck_gpt.chat_handler import ChatHandler

# Inicjalizacja
self.chat_handler = ChatHandler()

# Przetwarzanie wiadomości
responses = self.chat_handler.process_message(user_input)
for response in responses:
    self.add_message(response)
```

## 📊 Przykładowy Flow

### Service Setup - Pełny Proces

```
User: service setup

GPT: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     📋 Service Setup - Welcome!
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

     Do you want to quick setup to disable
     useless services for your PC?

     E.g. Print Spooler, Bluetooth, Remote Desktop
     and more services that take system resources.

     Type 'Yes' to start or 'No' to cancel

User: yes

GPT: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     🔧 Service Setup [1/7]
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

     Do you have a Printer connected to your PC?
     (Yes/No)

User: no

GPT: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     🔧 Service Setup [2/7]
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

     Do you use Bluetooth devices?
     (Yes/No)

... (więcej pytań)

GPT: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     ✅ Service Setup - Summary
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

     Based on your answers, these services
     will be DISABLED to optimize your PC:

       • Print Spooler
       • Bluetooth Support
       • Fax Service

     Type 'Yes' to apply or 'No' to cancel

User: yes

GPT: ⚙️  Applying optimizations...
     ✅ Disabled: Print Spooler
     ✅ Disabled: Bluetooth Support
     ✅ Disabled: Fax Service

     ✨ Optimization Complete!
        3 services optimized
```

## 🔐 Wymagania Uprawnień

**⚠️ WAŻNE:** Zarządzanie usługami Windows wymaga uprawnień administratora!

Aby wyłączać/włączać usługi, aplikacja musi być uruchomiona jako administrator.

## 📝 Konfiguracja

Plik konfiguracyjny: `data/services_config.json`

```json
{
  "disabled": [
    "Spooler",
    "bthserv",
    "BluetoothUserService"
  ],
  "timestamp": "2025-11-26 21:30:00"
}
```

## 🛠️ Development

### Dodawanie Nowej Kategorii Usług

W `services_manager.py`:

```python
SERVICES = {
    "nowa_kategoria": {
        "services": ["ServiceName1", "ServiceName2"],
        "display": "Display Name",
        "description": "Opis usługi"
    }
}
```

W `service_setup_wizard.py`:

```python
self.questions.append({
    "id": "nowa_kategoria",
    "question": "Pytanie do użytkownika?",
    "hint": "(Yes/No)",
    "service_category": "nowa_kategoria"
})
```

### Dodawanie Nowej Komendy

W `chat_handler.py`:

```python
def process_message(self, user_message):
    # ...
    elif "nowa komenda" in message_lower:
        return self._handle_new_command()
```

## 🐛 Debugowanie

```python
# Włącz verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Przyszłe Funkcje (Roadmap)

- [ ] Pełna integracja AI (GPT/LLM)
- [ ] Analiza performance w czasie rzeczywistym
- [ ] Inteligentne sugestie optymalizacji
- [ ] Predykcyjny monitoring
- [ ] Eksport/import konfiguracji
- [ ] Harmonogramy optymalizacji
- [ ] Powiadomienia o problemach

## 📄 Licencja

Part of PC Workman - HCK_Labs
Developed by Marcin "HCK" Firmuga
