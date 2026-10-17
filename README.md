# KDP Niche Analyzer

Analizzatore di nicchie editoriali per i marketplace Amazon IT, US, UK, DE, FR, ES, CA, AU, NL, BR e JP. I domini sono selezionati esplicitamente: prezzi e BSR di mercati diversi non vengono fusi.

La sidebar resta aperta sul desktop. Su schermi stretti è richiudibile, così non copre permanentemente il contenuto; questa modalità usa Streamlit 1.59 o successivo.

## Ricerca automatica

1. Ottieni una chiave [Rainforest API](https://docs.trajectdata.com/rainforestapi/search-product) e verifica condizioni e prezzo del servizio.
2. Per usare la chiave del proprietario sul server, aggiungi nei **Secrets della specifica app Streamlit** `RAINFOREST_API_KEY` e un diverso `RAINFOREST_ACCESS_CODE` (codice lungo da comunicare solo ai tester autorizzati). Non inserire questi valori in GitHub. Se la chiave server non è configurata, l'app permette invece una chiave personale inserita per la singola sessione.
3. Scegli 5, 10 o 20 risultati. L'app mostra **prima** il limite stimato di crediti Rainforest: rispettivamente 6, 11 o 21 per una richiesta Search + Product. Il valore effettivo viene letto dalla risposta del fornitore.
4. Se usi la chiave server, inserisci il codice d'accesso nell'app. Conferma il costo e premi **Cerca e analizza**. La chiave non viene mostrata agli utenti né scritta nel progetto o nel CSV.

Esempio della struttura dei Secrets di Streamlit (sostituisci i valori **solo nel pannello Streamlit**, mai nel repository):

```toml
RAINFOREST_API_KEY = "chiave-rainforest"
RAINFOREST_ACCESS_CODE = "codice-privato-lungo"
OPENAI_API_KEY = "chiave-openai"
```

L'app recupera titolo, ASIN, URL, autore, editore, formato, prezzo, valuta, BSR generale e di categoria, valutazioni e data della rilevazione quando la fonte li fornisce. Deduplica per ASIN, scarta i prodotti senza evidenza che siano libri e distingue i risultati sponsorizzati. I dati mancanti restano vuoti: non sono inventati né sostituiti da una stima di vendite. Lo stato di editore indipendente è confermato solo quando la scheda indica espressamente “Independently published” o un equivalente riconosciuto; negli altri casi è **Da verificare**.

La ricerca è automatica **dopo la configurazione della chiave del fornitore**. Se la chiave server è presente ma manca `RAINFOREST_ACCESS_CODE`, la ricerca resta disattivata. Il codice d'accesso è una protezione minima per un test privato, non equivale ad autenticazione utente con quote persistenti: prima di aprire la ricerca al pubblico occorrono account, limiti per utente e un tetto di spesa/overage presso Rainforest. I crediti Rainforest sono separati da quelli di Scrittore Site.

## Recensioni, profilo del lettore e Chat della nicchia

Dopo l'analisi dei concorrenti, una seconda azione facoltativa legge una pagina di recensioni positive e una di recensioni critiche per massimo tre libri con ASIN valido: **al massimo sei richieste/crediti Rainforest stimati**, più una chiamata OpenAI per la sintesi. Il software chiede un'altra conferma esplicita prima di eseguirla, conserva il campione nella sessione per evitare nuove richieste Rainforest in caso di errore della sintesi e mostra il consumo comunicato dal fornitore.

L'analisi propone bisogni del lettore, aspetti apprezzati, criticità e possibili opportunità editoriali solo se sono disponibili recensioni testuali sia positive sia critiche. Non inventa dati demografici né dichiara che il campione rappresenti l'intero mercato. Infine mostra un **prompt da copiare manualmente** nella Chat della nicchia di Scrittore Site; non invia dati automaticamente a Scrittore Site. La sintesi richiede `OPENAI_API_KEY` nei Secrets.

Restano disponibili i CSV Amazon come alternativa. La strategia AI già presente richiede anch'essa `OPENAI_API_KEY` nei Secrets di Streamlit.

## Limiti dell'analisi

- Un singolo BSR è una posizione temporanea, non un numero certo di vendite.
- Il solo prezzo non basta per stabilire il margine KDP: servono formato, pagine, stampa, imposte e royalty.
- La classificazione degli indipendenti è prudente: un autore può essere indipendente anche con un proprio marchio editoriale, ma non viene contrassegnato automaticamente senza evidenza.
- Il servizio dati è esterno e a pagamento. Disponibilità dei campi, limiti e condizioni possono variare.

## Test locali

`python -m unittest discover -s tests -v`

I test usano risposte simulate e non consumano crediti API.
