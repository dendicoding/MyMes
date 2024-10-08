from flask import Blueprint, render_template, request, session, redirect, flash,url_for, jsonify
from config import CONNECTION_STRING
import pyodbc

notes_bp = Blueprint('notes', __name__)

@notes_bp.route('/notes', methods=['GET', 'POST'])
def notes():
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()

    # Recupera tutti gli operatori per il menu a tendina
    cursor.execute("SELECT operator_id, name FROM Operatori")
    operatori = cursor.fetchall()
    # Recupera tutti i record dei counterparts dal database
    cursor = connection.cursor()
    cursor.execute("SELECT name FROM Counterparts")
    counterparts = cursor.fetchall()

    # Popola la lista dei clienti
    clienti = [row[0] for row in counterparts]

    cursor.execute("SELECT activity FROM Activities")
    attivita = [row[0] for row in cursor.fetchall()]

    selected_operator = request.form.get('operatore')
    selected_client = request.form.get('cliente')
    selected_date = request.form.get('data')

    # Recupera il nome dell'operatore selezionato
    nome_operatore = None
    if selected_operator:
        cursor.execute("SELECT name FROM Operatori WHERE operator_id = ?", selected_operator)
        nome_operatore = cursor.fetchone()[0]

    # Usa direttamente il nome del cliente dalla lista (se esiste)
    nome_cliente = selected_client if selected_client else None

    # Query per le note
    query = """
        SELECT n.creation_time, n.note, n.cliente, n.ore, n.activity, n.away
        FROM Personal_Reports n 
        WHERE n.operator = ?
    """
    params = [selected_operator]

    # Aggiungi filtro cliente se selezionato
    if selected_client:
        query += " AND n.cliente = ?"
        params.append(selected_client)

    # Aggiungi filtro per la data se selezionata
    if selected_date:
        query += " AND CONVERT(date, n.creation_time) = ?"
        params.append(selected_date)

    cursor.execute(query, params)
    note = cursor.fetchall()

    # Chiudi la connessione
    cursor.close()
    connection.close()

    # Passa i dati al template
    return render_template('notes.html',
                           operatori=operatori,
                           clienti=clienti,  # Passiamo la lista dei clienti
                           note=note,
                           selected_operator=selected_operator,
                           selected_client=selected_client,
                           selected_date=selected_date,
                           nome_operatore=nome_operatore,
                           nome_cliente=nome_cliente, attivita=attivita)




@notes_bp.route('/add_note', methods=['POST'])
def add_note():
    operatore_id = request.form['operatore']
    nota = request.form['nota']
    cliente = request.form['cliente']
    ore = request.form['ore']
    attivita = request.form['attivita']
    # Check if the 'away' checkbox was checked (if not, set default value to 0)
    away = request.form.get('away', 0)

    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()

    print("operatore_id:", operatore_id)
    print("nota:", nota)
    print("cliente:", cliente)
    print("ore:", ore)
    print("attivita:", attivita)
    print("away:", away)

    # Inserisci la nuova nota nel database
    cursor.execute("INSERT INTO Personal_Reports (operator, note, cliente, ore, activity, away) VALUES (?, ?, ?, ?, ?, ?)", operatore_id, nota, cliente, ore, attivita, away)
    connection.commit()

    return redirect('/notes')


import pdfkit
from flask import send_file, render_template_string



from flask import send_file
import io

@notes_bp.route('/notes/pdf', methods=['POST'])
def generate_pdf():
    path_to_wkhtmltopdf = r'C:\Users\Xenture\OneDrive - ONE OFF Services scpa\Desktop\MyMes\wkhtmltopdf\bin\wkhtmltopdf.exe'
    config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()

    selected_operator = request.form.get('operatore')
    selected_client = request.form.get('cliente')
    selected_date = request.form.get('data')

    # Recupera il nome dell'operatore selezionato
    cursor.execute("SELECT name FROM Operatori WHERE operator_id = ?", selected_operator)
    nome_operatore = cursor.fetchone()[0]

    # Usa direttamente il nome del cliente dalla lista (se esiste)
    nome_cliente = selected_client if selected_client else None
    print(selected_operator, selected_client, selected_date, nome_cliente)
    # Query per le note
    query = """
        SELECT n.creation_time, n.note, n.cliente, n.ore, n.activity
        FROM Personal_Reports n 
        WHERE n.operator = ?
    """
    params = [selected_operator]

    # Aggiungi filtro cliente se selezionato
    if selected_client:
        query += " AND n.cliente = ?"
        params.append(selected_client)

    # Aggiungi filtro per la data se selezionata
    if selected_date:
        query += " AND CONVERT(date, n.creation_time) = ?"
        params.append(selected_date)

    cursor.execute(query, params)
    note = cursor.fetchall()
    totale_ore = sum(float(nota[3]) for nota in note)
    # Chiudi la connessione
    cursor.close()
    connection.close()

    import base64

    # Leggi il file immagine
    with open('static/logo.png', 'rb') as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')


    # Genera l'HTML per le note
    html = render_template_string("""
        <html>
        <head>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
                
                body {
                    font-family: 'Poppins', sans-serif;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                    background-color: #f9f9f9;
                }

                h1 {
                    font-size: 24px;
                    font-weight: 600;
                    color: #2c3e50;
                    text-align: center;
                    margin-bottom: 20px;
                    border-bottom: 2px solid #2c3e50;
                    padding-bottom: 10px;
                }

                ul {
                    list-style-type: none;
                    padding-left: 0;
                }

                li {
                    background-color: #fff;
                    border: 1px solid #ddd;
                    padding: 10px;
                    margin-bottom: 10px;
                    border-radius: 5px;
                }

                .logo {
                    text-align: left;
                    margin-bottom: 20px;
                }

                .logo img {
                    width: 150px;
                }

                .note-header {
                    font-weight: 600;
                    color: #2980b9;
                }

                .note-content {
                    font-weight: 400;
                    color: #34495e;
                }

                .total-hours {
                    font-weight: 600;
                    color: #e74c3c;
                    font-size: 18px;
                    text-align: right;
                    margin-top: 20px;
                    border-top: 2px solid #2c3e50;
                    padding-top: 10px;
                }

                footer {
                    text-align: center;
                    font-size: 12px;
                    color: #95a5a6;
                    margin-top: 30px;
                }
            </style>
        </head>
        <body>
            <!-- Inserisci il logo in alto a sinistra -->
            <div class="logo">
                <img src="data:image/png;base64,{{ encoded_image }}" alt="Logo">
            </div>

            <h1>Rapportino Intervento di {{ nome_operatore }}{% if nome_cliente %} per {{ nome_cliente }}{% endif %}{% if selected_date %} del {{ selected_date }}{% endif %}</h1>

            <ul>
                {% for nota in note %}
                    <li>
                        <span class="note-header">Intervento:</span> <span class="note-content">{{ nota[1] }}</span> <br>
                        <span class="note-header">Ore:</span> <span class="note-content">{{ nota[3] }}</span> <br>
                        <span class="note-header">Tipologia:</span> <span class="note-content">{{ nota[4] }}</span>
                    </li>
                {% endfor %}
            </ul>

            <!-- Totale delle ore -->
            <div class="total-hours">
                Totale Ore: {{ totale_ore }}
            </div>

            <footer>
                Generato automaticamente dal sistema FactoryAI | {{ nome_operatore }} | KIBSStudio | {{ selected_date }}
            </footer>
        </body>
        </html>
        """, nome_operatore=nome_operatore, nome_cliente=nome_cliente, selected_date=selected_date, note=note, encoded_image=encoded_image, totale_ore=totale_ore)





    # Genera il PDF senza salvare direttamente su file
    pdf = pdfkit.from_string(html, False, configuration=config)

    # Usa un oggetto BytesIO per inviare il PDF direttamente al client
    pdf_stream = io.BytesIO(pdf)

    # Restituisci il PDF al client
    flash('File sent successfully!', 'success')
    return send_file(pdf_stream, as_attachment=True, download_name='notes.pdf', mimetype='application/pdf')

    
@notes_bp.route('/add_activity', methods=['GET', 'POST'])
def add_activity():
    if request.method == 'POST':
        new_activity = request.form['attivita']
        
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()
        
        # Query per inserire la nuova attività
        query = "INSERT INTO activities (activity) VALUES (?)"
        cursor.execute(query, new_activity)
        connection.commit()
        
        cursor.close()
        connection.close()
        flash('Activity inserted successfully!', 'success')
        # Reindirizza dopo l'inserimento per evitare il reinvio del modulo
        return redirect(url_for('add_activity'))

    # Se è una richiesta GET, recupera tutte le attività
    activities = recupera_tutte_le_attivita()
    
    return render_template('add_activity.html', activities=activities)

# Funzione per recuperare tutte le attività
def recupera_tutte_le_attivita():
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()
    
    query = "SELECT activity FROM activities"
    cursor.execute(query)
    activities = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    return [{"name": activity.activity} for activity in activities]


# Route per la dashboard
@notes_bp.route('/personal_reports_dashboard')
def personal_reports_dashboard():
    # Recupera tutti i report personali
    all_reports = recupera_tutti_i_report()
    # Recupera tutti gli operatori
    operators = recupera_operatori()
    
    return render_template('personal_reports_dashboard.html', all_reports=all_reports, operators=operators)

# Route per recuperare i report dell'operatore selezionato
@notes_bp.route('/get_reports_for_operator/<int:operator_id>')
def get_reports_for_operator(operator_id):
    reports = recupera_report_per_operatore(operator_id)
    return jsonify(reports)

# Funzioni per recuperare i report e gli operatori dal database
def recupera_tutti_i_report():
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()
    
    # Query per recuperare attività e ore da tutti i report
    query = "SELECT activity, ore FROM personal_reports"
    cursor.execute(query)
    reports = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    return [{"activity": report.activity, "hours": report.ore} for report in reports]

def recupera_operatori():
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()
    
    # Query per recuperare gli operatori
    query = "SELECT operator_id, name FROM Operatori"
    cursor.execute(query)
    operators = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    return [{"id": operator.operator_id, "name": operator.name} for operator in operators]

def recupera_report_per_operatore(operator_id):
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()
    
    # Query per recuperare attività e ore per l'operatore selezionato
    query = "SELECT activity, ore FROM personal_reports WHERE operator = ?"
    cursor.execute(query, operator_id)
    reports = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    # Restituisce sia l'attività che le ore per ogni report
    return [{"activity": report.activity, "hours": report.ore} for report in reports]


@notes_bp.route('/edit_activity/<string:activity_name>', methods=['GET', 'POST'])
def edit_activity(activity_name):
    if request.method == 'POST':
        new_activity_name = request.form['attivita']
        # Funzione per aggiornare l'attività nel database
        aggiorna_attivita(activity_name, new_activity_name)
        flash('Activity updated successfully!', 'success')
        return redirect(url_for('notes.add_activity'))
    
    return render_template('edit_activity.html', activity_name=activity_name)

@notes_bp.route('/delete_activity/<string:activity_name>', methods=['GET', 'POST'])
def delete_activity(activity_name):
    if request.method == 'POST':
        # Funzione per eliminare l'attività dal database
        elimina_attivita(activity_name)
        flash('Activity deleted successfully!', 'success')
        return redirect(url_for('notes.add_activity'))
    


# Funzione per aggiornare l'attività nel database
def aggiorna_attivita(old_name, new_name):
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()
    
    query = "UPDATE activities SET activity = ? WHERE activity = ?"
    cursor.execute(query, (new_name, old_name))
    
    connection.commit()
    cursor.close()
    connection.close()

# Funzione per eliminare l'attività dal database
def elimina_attivita(activity_name):
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()
    
    query = "DELETE FROM activities WHERE activity = ?"
    cursor.execute(query, (activity_name,))
    
    connection.commit()
    cursor.close()
    connection.close()