from flask import Blueprint, render_template, request, session, redirect, flash,url_for
from config import CONNECTION_STRING
import pyodbc

operators_bp = Blueprint('operators', __name__)

def get_operators():
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()
        
        cursor.execute("SELECT * FROM Operatori")
        operators = cursor.fetchall()

        operators_list = []
        for row in operators:
            operators_list.append({
                'operator_id': row.operator_id,
                'name': row.name,
                'status': row.status,
                'current_task': row.current_task
            })

        return operators_list

    except Exception as error:
        print(f"Failed to retrieve records from Operatori table {error}")
        return []

    finally:
        if connection:
            cursor.close()
            connection.close()

@operators_bp.route('/add_operator', methods=['GET', 'POST'])
def add_operator():
    if 'username' in session and session['role'] == 'manager':
        if request.method == 'POST':
            name = request.form['name']
            # Recupera gli operatori esistenti dal database
            existing_operators = [operator['operator_id'] for operator in get_operators()]
            # Aggiungi l'operatore al database
            insert_operator(name)  # Inserimento nel database
            flash(f"Operator {name} added successfully!", 'success')
        return render_template('add_operator.html')
    else:
        return redirect(url_for('auth.login'))

def insert_operator(name):
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()
        
        sql_insert_query = """INSERT INTO Operatori (name, status) VALUES (?, ?)"""
        record_to_insert = (name, 'idle')
        cursor.execute(sql_insert_query, record_to_insert)

        connection.commit()
        print(f"Record inserted successfully into Operatori table")

    except Exception as error:
        print(f"Failed to insert record into Operatori table {error}")

    finally:
        if connection:
            cursor.close()
            connection.close()


@operators_bp.route('/operators', methods=['GET'])
def view_operators():
    if 'username' in session:
        operators_list = get_operators()  
        return render_template('operators.html', operators=operators_list)
    else:
        return redirect(url_for('auth.login'))

def update_operator(operator_id, status, name=None, current_task=None):
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()

        # Crea una lista di valori e una lista di colonne da aggiornare
        update_values = []
        update_columns = []

        if status is not None:
            update_values.append(status)
            update_columns.append("status = ?")
        
        if current_task is not None:
            update_values.append(current_task)
            update_columns.append("current_task = ?")

        # Aggiungi l'ID del task alla fine della lista dei valori
        update_values.append(operator_id)

        # Se ci sono colonne da aggiornare, costruisci la query
        if update_columns:
            sql_update_query = f"UPDATE Operatori SET {', '.join(update_columns)} WHERE operator_id = ?"
            cursor.execute(sql_update_query, update_values)
            connection.commit()
            print(f"Operator with ID {operator_id} updated successfully")

        else:
            print(f"No updates provided for Operator with ID {operator_id}")

    except Exception as error:
        print(f"Failed to update operator with ID {operator_id}: {error}")

    finally:
        if connection:
            cursor.close()
            connection.close()

@operators_bp.route('/operator/edit/<int:operator_id>', methods=['GET', 'POST'])
def edit_operator(operator_id):
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()

    if request.method == 'POST':
        # Ricevi dati dal form di modifica
        name = request.form['name']

        # Esegui l'aggiornamento del database
        cursor.execute("""
            UPDATE Operatori
            SET name = ?
            WHERE operator_id = ?
        """, (name, operator_id))
        conn.commit()
        conn.close()
        
        flash('Operator updated successfully', 'success')
        return redirect(url_for('operators.view_operators'))

    # Recupera i dati attuali dell'operatore per visualizzarli nel form di modifica
    cursor.execute("SELECT * FROM Operatori WHERE operator_id = ?", (operator_id,))
    operator = cursor.fetchone()
    conn.close()

    return render_template('edit_operator.html', operator=operator)