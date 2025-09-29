# Work Tracker (CLI + API) — Projeto Integrador

**Aluno:** 
Francisco Eduardo Barros Tangerino

**RA:** 25002174

**Curso/Turma:** Projeto Integrado de Desenvolvimento de Sistemas (EAD.101_1-16.A)

Meu Projeto Integrado é: um monitor de horas de trabalho com **POO**, **persistência em JSON**, um **painel em linha de comando** (mostrando **Tempo Total** x **Tempo Efetivo** com pausas) e uma **API HTTP (FastAPI)** para integrar com um possível front-end.

> **Contexto:** A ideia é ajudar no cuidado com a produtividade e com a saúde ao trabalhar sentado por longos períodos. O sistema sugere **pausas**, lembra de **hidratação** (💧) e manda levantar para **esticar as pernas** (“de pé”), além de gerar relatórios.

---

## 🎯 Objetivos do Projeto

* Aplicar **POO “clássico”**: classes, encapsulamento, composição e polimorfismo (interfaces via ABC).
* Registrar sessões de trabalho em **JSON** (UTC/ISO) e gerar **relatórios** diários/semanas + **CSV**.
* Fornecer um **CLI** prático (com painel “ao vivo” sem spam de logs) e uma **API REST** simples.
* Organizar o repositório com **branches** (`main`/`dev`) e README/documentação.

**Justificativa (CNPJ próprio / cenário de negócio):**

* Reduz **sedentarismo** (alertas de levantar) e incentiva **hidratação**.
* Evita jornadas contínuas (pausas guiadas), reduzindo **fadiga**.
* Diferencia **tempo total** de **tempo efetivo** (descontando pausas).
* Facilita integração com sistemas da empresa via **API**.

---

## 🧱 Arquitetura (visão geral)

```
src/
  monitor/
    core/
      session.py    # WorkSession (modelo da sessão)
      tracker.py    # TimeTracker (regras de negócio)
      policy.py     # Policies (Hydration, Break, Stand) - polimorfismo/Strategy
    io/
      storage.py    # StorageJSON (persistência em arquivo)
      report.py     # ReportService (resumos + export CSV)
    cli.py          # CLI: start/stop/status/report/watch
    api.py          # API HTTP (FastAPI)
data/
  data.json         # "banco" em JSON (sessions)
docs/
  relatorio-tecnico.md  # rascunho seguindo o modelo da faculdade
```

**POO aplicado:**

* **Composição**: `TimeTracker` usa `StorageJSON` e `WorkSession`.
* **Polimorfismo/Strategy**: `Policy` (ABC) + `HydrationPolicy`, `BreakPolicy`, `StandPolicy`.
* **Encapsulamento**: `WorkSession` cuida da (de)serialização (`to_dict`/`from_dict`); `TimeTracker` centraliza regras.

---

## ✅ Funcionalidades

* **Iniciar/encerrar sessão** (CLI e API).
* **Painel ao vivo (CLI)**:

  * Mostra **Total** (bruto) e **Efetivo** (desconta pausas confirmadas).
  * **Pausa (Break)**: baseada no **tempo efetivo** (congela e pede **ENTER** para voltar).
  * **Hidratação**: alerta **💧** por ~60s (base **tempo total**, só aviso).
  * **De pé**: alerta “**AGORA**” por ~60s (base **tempo total**, só aviso).
* **Relatórios**: diário/semanal (CLI e API).
* **Export CSV**: consolida N dias (CLI e API).
* **API HTTP**: endpoints para start/stop/status/report/export.

---

## 🧩 Tecnologias

* **Python 3.7+** (recomendo 3.10+)
* **CLI/CORE**: apenas **stdlib** (`argparse`, `json`, `csv`, `datetime`, `pathlib`)
* **API**: `fastapi`, `uvicorn`
* (Opcional no Windows) `windows-curses` para o modo fullscreen do watch

`requirements.txt`:

```
# stdlib only (argparse, json, csv, datetime, pathlib)
fastapi
uvicorn
```

> Obs.: CORS da API está aberto para facilitar desenvolvimento local. Em produção, restringir `allow_origins`.

---

## ⚙️ Instalação

```bash
# Windows PowerShell (exemplo)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 🖥️ CLI — Como usar

```bash
# Status (sem sessão)
python -m src.monitor.cli status

# Iniciar sessão
python -m src.monitor.cli start

# Painel ao vivo (sem spam de logs)
python -m src.monitor.cli watch
# Ctrl+C para sair | quando a pausa disparar, o painel pede ENTER para voltar

# Encerrar sessão
python -m src.monitor.cli stop

# Relatório do dia
python -m src.monitor.cli report --today

# Relatório da semana (últimos 7 dias)
python -m src.monitor.cli report --week

# Exportar CSV (últimos N dias)
python -m src.monitor.cli export out.csv --days 7
```

**Tempos de demonstração (em `src/monitor/cli.py`):**

```python
HYDRATION_SECONDS = 5     # 💧 aviso (base total)
BREAK_SECONDS     = 10    # pausa com ENTER (base efetivo)
STAND_SECONDS     = 8     # "de pé" (base total)
```


## 🌐 API — Endpoints

Subir a API:

```bash
python -m uvicorn src.monitor.api:app --reload --port 8000
```

Docs interativos: **[http://localhost:8000/docs](http://localhost:8000/docs)**

Principais rotas:

* `POST /sessions/start` → inicia sessão
* `POST /sessions/stop` → encerra sessão ativa
* `GET  /status` → `{ active, started_at, elapsed_seconds, elapsed_hms, next_hints }`
* `GET  /report?scope=today|week`
* `GET  /export?days=7` → CSV para download

Exemplos (cURL):

```bash
curl -X POST http://localhost:8000/sessions/start
curl http://localhost:8000/status
curl "http://localhost:8000/report?scope=today"
curl -X POST http://localhost:8000/sessions/stop
curl -L "http://localhost:8000/export?days=7" -o semana.csv
```

---

## 🗂️ Persistência

* Arquivo: `data/data.json`
* Estrutura: lista de sessões `{ id, started_at, ended_at }` com **UTC/ISO** (`YYYY-MM-DDTHH:MM:SS.sssZ`).

> Observação: o **tempo efetivo** (descontando pausas) é controlado no painel. Persistência de pausas como entidade é um **passo futuro** (ver roadmap).

## 📌 Observações

* **Sem dataclasses**: escolha proposital para mostrar POO “na unha” sem auxílio de libs.
* **Limitação atual**: pausa é controlada no painel apenas ou API

## ✍️ Autor

**Francisco Eduardo Barros Tangerino** — RA **25002174** 

Projeto Integrado de Desenvolvimento de Sistemas (**EAD.101_1-16.A**)

---

### Anexo: arquivos principais

* `src/monitor/core/policy.py`: `Policy`, `HydrationPolicy`, `BreakPolicy`, `StandPolicy`
* `src/monitor/core/session.py`: `WorkSession` (POO clássico + serialização)
* `src/monitor/core/tracker.py`: `TimeTracker` (status, soma, humanize)
* `src/monitor/cli.py`: painel **Total x Efetivo**, pausa (ENTER), 💧, “de pé”
* `src/monitor/api.py`: FastAPI (start/stop/status/report/export)