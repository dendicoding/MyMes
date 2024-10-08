from flask import Blueprint, render_template, request, session, redirect, flash, url_for, jsonify
from config import CONNECTION_STRING
import pyodbc

machine_bp = Blueprint('machines', __name__)

@machine_bp.route('/machines', methods=['GET'])
def view_machines():
    if 'username' in session:
        machine_list = get_machines()  # Ottieni le macchine dal database
        return render_template('machines.html', machines=machine_list)
    else:
        return redirect(url_for('auth.login'))

def insert_machine(machine_id, status="idle"):
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()
        
        sql_insert_query = """INSERT INTO Macchine (machine_id, status) VALUES (?, ?)"""
        record_to_insert = (machine_id, status)
        cursor.execute(sql_insert_query, record_to_insert)

        connection.commit()
        print(f"Record inserted successfully into Macchine table")

    except Exception as error:
        print(f"Failed to insert record into Macchine table {error}")

    finally:
        if connection:
            cursor.close()
            connection.close()

def get_machines():
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()
        
        cursor.execute("SELECT * FROM Macchine")
        machines = cursor.fetchall()

        # Mapping dei risultati a dizionari
        machines_list = []
        for row in machines:
            machines_list.append({
                'id': row.id,
                'machine_id': row.machine_id,
                'status': row.status,
                'current_order': row.current_order,
                'current_task': row.current_task,
                'start_time': row.start_time
            })

        return machines_list

    except Exception as error:
        print(f"Failed to retrieve records from Macchine table {error}")
        return []

    finally:
        if connection:
            cursor.close()
            connection.close()

def update_machine(machine_id, status, current_order, current_task, start_time = None):
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()

        # Se start_time è None, passarlo come NULL
        start_time = None if start_time is None else start_time

        sql_update_query = """UPDATE Macchine SET status = ?, current_order = ?, current_task = ?, start_time = ? WHERE machine_id = ?"""
        cursor.execute(sql_update_query, (status, current_order, current_task, start_time, machine_id))

        connection.commit()
        print(f"Record updated successfully in Macchine table")

    except pyodbc.Error as e:
        print(f"Database error: {e}")
    except Exception as error:
        print(f"Failed to update record in Macchine table: {error}")

    finally:
        if connection:
            cursor.close()
            connection.close()

@machine_bp.route('/add_machine', methods=['GET', 'POST'])
def add_machine():
    if 'username' in session and session['role'] == 'manager':
        if request.method == 'POST':
            machine_id = request.form['machine_id']
            # Recupera le macchine esistenti dal database
            existing_machines = [machine['machine_id'] for machine in get_machines()]
            if machine_id in existing_machines:
                flash("Machine ID already exists.", 'error')
            else:
                # Aggiungi la macchina al database
                insert_machine(machine_id)  # Inserimento nel database
                flash(f"Machine {machine_id} added successfully!", 'success')
        return render_template('add_machine.html')
    else:
        return redirect(url_for('login'))

@machine_bp.route('/machines_json', methods=['GET'])
def machines_json():
    machines = get_machines()  # Ottieni i dati delle macchine come dizionari
    machines_data = [{"id": machine["id"], "name": machine["machine_id"]} for machine in machines]
    
    return jsonify({"data": machines_data})

@machine_bp.route('/block_machine/<machine_id>', methods=['GET', 'POST'])
def block_machine(machine_id):
    if request.method == 'POST':
        causal = request.form.get('causal')
        
        # Connessione al database
        conn = pyodbc.connect(CONNECTION_STRING)
        cursor = conn.cursor()
        
        # Aggiorna lo stato della macchina a 'blocked' e aggiungi la causale
        cursor.execute("""
            UPDATE Macchine 
            SET status = ?, causal = ? 
            WHERE machine_id = ?
        """, ('blocked', causal, machine_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        flash('Machine blocked successfully!', 'success')
        return redirect(url_for('machines.view_machines'))
    
    # Se la richiesta è GET, ottieni i dettagli della macchina
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Macchine WHERE machine_id = ?", (machine_id,))
    machine = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return render_template('block_machine.html', machine=machine)
    

@machine_bp.route('/unblock_machine/<machine_id>', methods=['GET'])
def unblock_machine(machine_id):
    # Connessione al database
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    
    
    cursor.execute("""
        UPDATE Macchine 
        SET status = ? 
        WHERE machine_id = ?
    """, ('idle',machine_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    flash('Machine unblocked successfully!', 'success')
    return redirect(url_for('machines.view_machines'))  # Reindirizza alla pagina delle macchine