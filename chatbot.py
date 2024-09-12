import spacy

# Carica il modello per l'italiano
nlp = spacy.load("it_core_news_sm")

# Definisci intents e risposte
intents = {
    "dashboard": {
        "keywords": ["dashboard", "pannello", "riepilogo"],
        "response": "Puoi trovare la pagina delle dashboard nel menu principale in alto a sinistra."
    },
    "ordini": {
        "keywords": ["ordini", "orders", "comandi"],
        "response": "La pagina degli ordini è nella barra di navigazione in alto, accanto a 'Dashboard'."
    },
    "cicli": {
        "keywords": ["cicli", "cycle", "processo"],
        "response": "La pagina dei cicli si trova nel menu principale, accanto a 'Ordini'."
    },
    "tasks": {
        "keywords": ["tasks", "compiti", "operazioni"],
        "response": "Per gestire i tasks, vai nella sezione 'Tasks' nel menu principale."
    },
    "task": {
        "keywords": ["task", "compiti", "operazioni"],
        "response": "Per gestire i tasks, vai nella sezione 'Tasks' nel menu principale."
    },
    "macchine": {
        "keywords": ["macchine", "machines", "strumenti"],
        "response": "Troverai la gestione delle macchine nel menu 'Machines'."
    },
    "operatori": {
        "keywords": ["operatori", "operators", "utenti"],
        "response": "Puoi visualizzare gli operatori nella sezione 'Operators'."
    },
    "prodotti": {
        "keywords": ["prodotti", "product", "articoli"],
        "response": "La gestione dei prodotti è disponibile nella sezione 'Resources'."
    },
    "materiali": {
        "keywords": ["materiali", "materials", "forniture"],
        "response": "La gestione dei materiali è disponibile nella sezione 'Resources'."
    },
    "report": {
        "keywords": ["report", "reportistica", "statistiche"],
        "response": "Trovi i report nella sezione 'Report' del gruppo 'Orders' nel menu principale."
    },
    "logout": {
        "keywords": ["logout", "esci", "disconnettiti"],
        "response": "Per disconnetterti, clicca su 'Logout' nel menu principale."
    },
    "supporto": {
        "keywords": ["supporto", "assistenza", "help"],
        "response": "Per assistenza, contatta il nostro supporto tecnico attraverso la sezione 'Supporto'."
    }
    # Aggiungi altri intents per altre funzionalità specifiche del tuo MES.
}

# Funzione per analizzare i messaggi
def analyze_message(message):
    """
    Analizza il messaggio e cerca corrispondenze con gli intents definiti.
    
    :param message: stringa del messaggio dell'utente
    :return: risposta basata sull'intent
    """
    doc = nlp(message)  # Analizza il testo usando spaCy
    for intent, data in intents.items():
        for keyword in data["keywords"]:
            if keyword in message.lower():
                return data["response"]
    return "Mi dispiace, non ho capito la tua domanda."

# Funzione per testare il chatbot nel terminale
def test_chatbot():
    """
    Esegui il chatbot in un loop per testarlo nel terminale.
    """
    print("Chatbot avviato. Scrivi 'esci' per terminare.")
    while True:
        user_input = input("Tu: ")
        if user_input.lower() == "esci":
            break
        response = analyze_message(user_input)
        print(f"Chatbot: {response}")

# Funzione principale per gestire la chat nel file app.py
def handle_chat(message):
    """
    Gestisce la chat, riceve un messaggio dall'utente e restituisce la risposta.
    
    :param message: il messaggio dell'utente
    :return: risposta generata dal chatbot
    """
    return analyze_message(message)
