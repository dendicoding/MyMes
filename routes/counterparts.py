from flask import Blueprint, render_template, request, session, redirect, flash,url_for
from config import CONNECTION_STRING
import pyodbc

counterparts_bp = Blueprint('counterparts', __name__)

@counterparts_bp.route('/counterparts')
def display_counterparts():
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()

    # Query to retrieve all counterparts
    cursor.execute("SELECT counterpart_id, name, type, address, phone, email FROM Counterparts")
    counterparts = cursor.fetchall()

    # Close the database connection
    cursor.close()
    conn.close()

    return render_template('counterparts.html', counterparts=counterparts)

@counterparts_bp.route('/counterparts/create', methods=['POST'])
def create_counterpart():
    name = request.form['name']
    type = request.form['type']
    address = request.form.get('address', None)  # Use None if not provided
    phone = request.form.get('phone', None)      # Use None if not provided
    email = request.form.get('email', None)      # Use None if not provided

    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()

    # Insert the new counterpart into the database
    cursor.execute("""
        INSERT INTO Counterparts (name, type, address, phone, email)
        VALUES (?, ?, ?, ?, ?)
    """, (name, type, address, phone, email))

    # Commit the transaction
    conn.commit()

    # Close the database connection
    cursor.close()
    conn.close()

    # Redirect back to the display page
    return redirect(url_for('counterparts.display_counterparts'))

@counterparts_bp.route('/edit_counterpart/<int:counterpart_id>', methods=['GET', 'POST'])
def edit_counterpart(counterpart_id):
    # Ottieni i dati della controparte dal database
    counterpart = get_counterpart_by_id(counterpart_id)
    
    if request.method == 'POST':
        # Aggiorna la controparte con i nuovi dati dal form
        name = request.form['name']
        type = request.form['type']
        address = request.form['address']
        phone = request.form['phone']
        email = request.form['email']
        
        # Esegui l'aggiornamento nel database
        update_counterpart(counterpart_id, name, type, address, phone, email)
        
        return redirect(url_for('counterparts.display_counterparts'))  # Reindirizza alla lista delle controparti dopo la modifica
    
    # Visualizza la pagina di modifica
    return render_template('edit_counterpart.html', counterpart=counterpart)

def get_counterpart_by_id(counterpart_id):
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    query = "SELECT counterpart_id, name, type, address, phone, email FROM counterparts WHERE counterpart_id = ?"
    cursor.execute(query, counterpart_id)
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if row:
        counterpart = {
            'counterpart_id': row[0],
            'name': row[1],
            'type': row[2],
            'address': row[3],
            'phone': row[4],
            'email': row[5]
        }
        return counterpart
    else:
        return None

def update_counterpart(counterpart_id, name, type, address, phone, email):
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    query = """
        UPDATE counterparts
        SET name = ?, type = ?, address = ?, phone = ?, email = ?
        WHERE counterpart_id = ?
    """
    cursor.execute(query, (name, type, address, phone, email, counterpart_id))
    conn.commit()
    cursor.close()
    conn.close()

def delete_counterpart_by_id(counterpart_id):
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    query = "DELETE FROM counterparts WHERE counterpart_id = ?"
    cursor.execute(query, (counterpart_id,))
    conn.commit()
    cursor.close()
    conn.close()

@counterparts_bp.route('/delete_counterpart/<int:counterpart_id>', methods=['POST'])
def delete_counterpart(counterpart_id):
    # Cancella la controparte dal database
    delete_counterpart_by_id(counterpart_id)
    return redirect(url_for('counterparts.display_counterparts'))

