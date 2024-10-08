from flask import Blueprint, render_template, request, session, redirect, flash,url_for
from config import CONNECTION_STRING
import pyodbc
from datetime import datetime


lots_bp = Blueprint('lots', __name__)

@lots_bp.route('/create_lot_function', methods=['POST'])
def create_lot_function():
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    lot_code = request.form['lot_code']
    entity_type = request.form['entity_type']  # 'material' o 'product'
    quantity = request.form['quantity']
    unit_of_measure = request.form['unit_of_measure']
    expiration_date = request.form.get('expiration_date')
    status = 'available'
    creation_date = datetime.now()

    # Inserisci nel database
    cursor.execute(
        "INSERT INTO lots (lot_code, entity_type, quantity, unit_of_measure, creation_date, expiration_date, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (lot_code, entity_type, quantity, unit_of_measure, creation_date, expiration_date, status)
    )
    conn.commit()
    return redirect(url_for('lots.view_lots'))

@lots_bp.route('/create_lot', methods=['GET'])
def create_lot():
    return render_template('create_lot.html')

@lots_bp.route('/view_lots', methods=['GET'])
def view_lots():
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()

    # Recupera tutti i lotti dal database
    cursor.execute("SELECT lot_id, lot_code, entity_type, quantity, unit_of_measure, creation_date, expiration_date, status FROM Lots")
    lots = cursor.fetchall()

    return render_template('view_lots.html', lots=lots)

@lots_bp.route('/view_lots_materials/<lot_code>')
def view_lots_materials(lot_code):
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()

    # Recupera i materiali collegati al lot_code
    cursor.execute("SELECT * FROM Materials WHERE lot = ?", (lot_code,))
    materials = cursor.fetchall()

    return render_template('view_lots_materials.html', materials=materials, lot_code=lot_code)

@lots_bp.route('/lot_dashboard')
def lot_dashboard():
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()

    # Query per ottenere il conteggio dei lotti per status
    cursor.execute("SELECT status, COUNT(*) FROM Lots GROUP BY status")
    lots_by_status = cursor.fetchall()
    
    available_count = used_count = expired_count = 0
    for row in lots_by_status:
        if row[0] == 'available ':
            available_count = row[1]
        elif row[0] == 'used ':
            used_count = row[1]
        elif row[0] == 'expired ':
            expired_count = row[1]

    
    # Query per ottenere la quantità di alcuni lotti (ad esempio i primi 4 lotti)
    cursor.execute("SELECT TOP 4 lot_code, quantity FROM Lots")
    lots_quantity = cursor.fetchall()

    # Trasformazione dei dati per i grafici
    lot_1_quantity = lot_2_quantity = lot_3_quantity = lot_4_quantity = 0
    if lots_quantity:
        lot_1_quantity = lots_quantity[0][1] if len(lots_quantity) > 0 else 0
        lot_2_quantity = lots_quantity[1][1] if len(lots_quantity) > 1 else 0
        lot_3_quantity = lots_quantity[2][1] if len(lots_quantity) > 2 else 0
        lot_4_quantity = lots_quantity[3][1] if len(lots_quantity) > 3 else 0

    return render_template('lot_dashboard.html', 
                           available_count=available_count,
                           used_count=used_count,
                           expired_count=expired_count,
                           lot_1_quantity=lot_1_quantity,
                           lot_2_quantity=lot_2_quantity,
                           lot_3_quantity=lot_3_quantity,
                           lot_4_quantity=lot_4_quantity)

conn = pyodbc.connect(CONNECTION_STRING)
cursor = conn.cursor()