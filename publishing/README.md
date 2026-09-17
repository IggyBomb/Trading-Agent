# publishing/ — il binario pubblico

Questa cartella è **staccata** dal resto di Trading-Agent.

- Non importa niente dal repo padre.
- Non modifica niente nel repo padre.
- Legge soltanto i JSON che la pipeline esistente già scrive in `../data/`, e il
  giornale operazioni in `../logs/trades.jsonl`.

Il tuo sistema di trading personale continua a funzionare esattamente come prima.
`sentiment_agent.py`, `fundamental_agent.py`, `No financial Advice/disclaimer.py`
e tutti i file in `.trading/agents/` non sono stati toccati.

## Perché esiste

Il sistema che hai costruito calcola la size sul tuo conto, valida gli stop
contro le tue regole e dà verdetti approva/rifiuta. Per te va benissimo: non
c'è nessuna norma su cosa dici a te stesso sui tuoi soldi.

Diventa un problema solo nel momento in cui quell'output lo vendi a qualcuno.
A quel punto è una raccomandazione personale, e vendere raccomandazioni
personali richiede un'autorizzazione che non hai.

Quindi: due binari dallo stesso motore dati.

```
        ../data/*.json  (pipeline esistente, neutra)
                 │
        ┌────────┴────────┐
        │                 │
   binario privato    binario pubblico
   .trading/agents/   publishing/
   size, stop,        analisi sul titolo,
   verdetti           niente size, niente verdetti
        │                 │
      per te          per gli abbonati
```

## Come si usa

```bash
cd publishing

python3 publish.py data GLE.PA            # cosa sa la pipeline su questo titolo
python3 publish.py new drafts/gle.md      # crea una bozza con i campi obbligatori
# ... scrivi l'analisi ...
python3 publish.py check drafts/gle.md    # cerca frasi che parlano al lettore
python3 publish.py render drafts/gle.md --save
```

`render` si rifiuta di produrre la pubblicazione se manca una delle informazioni
obbligatorie, se il rating non è uno di quelli definiti, se il testo si rivolge
al lettore, o se non riesce a stabilire con certezza la tua posizione sul titolo.

`--save` scrive il file in `publications/` e aggiunge una riga a
`recommendation_history.jsonl`, che è lo storico a 12 mesi che devi tenere.

## I file

| File | Cosa fa |
|---|---|
| `agents/research-writer.md` | Le regole di scrittura per chi produce il testo. È il gemello pubblico dei tuoi `.trading/agents/`. |
| `publish.py` | I tre comandi qui sopra. |
| `config.py` | Percorsi, dati dell'entità, impostazioni posizioni. **Da compilare.** |
| `analysis_style.py` | Le regole in forma importabile, per generare testo da codice. |
| `compliance_guard.py` | Il controllore: gate sulle domande, validatore sul testo, costruttore della pubblicazione. |
| `disclosures.py` | Legge `../logs/trades.jsonl` e scrive la riga "detengo / non detengo". |
| `tests/` | 117 test. `python3 -m pytest tests/ -q` |

## Due cose da fare prima di pubblicare davvero

**1. Compila `config.py`.** `PRODUCER` e `AUTHOR` sono segnaposto. Senza quelli
la pubblicazione esce con `[ENTITY]` stampato sopra.

**2. La riga `position:` la scrivi tu, in ogni bozza.**

```
position: The author holds no position in PETR4.SA as at the date of production.
position: The author holds a long position in PETR4.SA as at the date of production.
```

È un obbligo MAR: dichiarare se detieni lo strumento di cui scrivi. Non ha un
default sicuro — "non l'ho scritto" e "non detengo posizioni" non sono la stessa
frase — quindi `render` si rifiuta senza. La riga deve nominare il ticker della
bozza, così se copi una bozza da un altro titolo e ti dimentichi di aggiornarla,
viene bloccata invece che pubblicata.

*(Opzionale, per dopo:* se un giorno allinei `../logs/trades.jsonl` con il
broker, metti `POSITIONS_COMPLETE = True` e `POSITIONS_RECONCILED_AT` in
`config.py` e la riga viene generata da sola dal giornale operazioni.*)*

## Limiti

Questo è un controllo tecnico, non una consulenza legale e non un parere di
conformità. Non rende lecito un output illecito.

- Una regex non legge le intenzioni. "Nessuna corrispondenza" non vuol dire
  "conforme". Rileggi comunque.
- Copre il testo, non l'attività. Blocco delle giurisdizioni al pagamento,
  diritto di recesso, IVA, conservazione dei documenti, polizza RC professionale
  e revisione legale dei termini restano tutti da fare, e restano obbligatori.
- Il rischio più grande non è tecnico: è rispondere a un abbonato che paga e
  ti scrive "ok ma io che faccio?". Quello lo blocca solo la tua disciplina.
