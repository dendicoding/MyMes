import spacy
import pyodbc
from config import CONNECTION_STRING
import re
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

# Funzione per estrarre l'ID della macchina
def extract_machine_id(message):
    match = re.search(r"\b(\d+)\b", message)  # Cerca un numero nella stringa
    if match:
        return int(match.group(1))
    return None

# Funzione per ottenere lo stato della macchina dal database
def get_machine_status(identifier):
    """
    Restituisce lo stato della macchina data un ID o un nome della macchina.
    
    :param identifier: ID o nome della macchina
    :return: stato della macchina o None se non trovata
    """
    # Connessione al database
    connection = pyodbc.connect(CONNECTION_STRING)

    cursor = connection.cursor()
    
    # Prova a cercare per ID solo se l'identificatore è un numero
    if isinstance(identifier, int):
        cursor.execute("SELECT status FROM Macchine WHERE id = ?", (identifier,))
        result = cursor.fetchone()
        if result:
            return result[0]
    
    # Se non trovato o se non era un ID, prova a cercare per nome
    cursor.execute("SELECT status FROM Macchine WHERE machine_id = ?", (identifier,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    
    return None


# Funzione per analizzare i messaggi
def analyze_message(message):
    """
    Analizza il messaggio e cerca corrispondenze con gli intents definiti.
    
    :param message: stringa del messaggio dell'utente
    :return: risposta basata sull'intent
    """
    doc = nlp(message)  # Analizza il testo usando spaCy

    # Controlla se la domanda riguarda lo stato di una macchina
    if "stato della macchina" in message.lower():
        # Prova a estrarre l'ID della macchina
        machine_id = extract_machine_id(message)
        
        # Se l'ID è trovato, chiama get_machine_status con l'ID
        if machine_id is not None:
            status = get_machine_status(machine_id)
            return f"Lo stato della macchina con ID '{machine_id}' è {status}." if status else f"Nessuna macchina trovata con ID '{machine_id}'."
        
        # Altrimenti, cerca il nome della macchina
        machine_name = message.lower().replace("stato della macchina ", "").strip()
        status = get_machine_status(machine_name)

        if status:
            return f"Lo stato della macchina '{machine_name}' è {status}."
        else:
            return f"Nessuna macchina trovata con nome '{machine_name}'."
    
    for intent, data in intents.items():
        for keyword in data["keywords"]:
            if keyword in message.lower():
                return data["response"]
    
    return "Mi dispiace, non ho capito la tua domanda."


# Funzione principale per gestire la chat nel file app.py
def handle_chat(message):
    """
    Gestisce la chat, riceve un messaggio dall'utente e restituisce la risposta.
    
    :param message: il messaggio dell'utente
    :return: risposta generata dal chatbot
    """
    return analyze_message(message)