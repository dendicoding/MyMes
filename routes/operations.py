from flask import Blueprint, render_template, request, session, redirect, flash,url_for
from config import CONNECTION_STRING
import pyodbc

operations_bp = Blueprint('operations', __name__)

@operations_bp.route('/cycle/<int:cycle_id>/operation/add', methods=['GET', 'POST'])
def add_operation(cycle_id):
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()

    if request.method == 'POST':
        operation_name = request.form['operation_name']
        operation_sequence = request.form['operation_sequence']
        estimated_time = request.form['estimated_time']
        

        cursor.execute("""
            INSERT INTO ProductionCycleOperation (CycleID, OperationName, OperationSequence, EstimatedTime)
            VALUES (?, ?, ?, ?)
        """, (cycle_id, operation_name, operation_sequence, estimated_time))
        connection.commit()
        connection.close()
        flash('Operation added successfully', 'success')
        return redirect(url_for('cycles.view_cycle', cycle_id=cycle_id))

    
    connection.close()
    return render_template('add_operation.html', cycle_id=cycle_id)

@operations_bp.route('/operation/edit/<int:operation_id>', methods=['GET', 'POST'])
def edit_operation(operation_id):
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()

    if request.method == 'POST':
        operation_name = request.form['operation_name']
        operation_sequence = request.form['operation_sequence']
        estimated_time = request.form['estimated_time']
        resource_id = request.form['resource_id']

        cursor.execute("""
            UPDATE ProductionCycleOperation
            SET OperationName = ?, OperationSequence = ?, EstimatedTime = ?, ResourceID = ?
            WHERE operation_id = ?
        """, (operation_name, operation_sequence, estimated_time, resource_id, operation_id))
        connection.commit()
        connection.close()
        flash('Operation updated successfully', 'success')
        return redirect(url_for('cycles.view_cycle', cycle_id=operation_id))

    cursor.execute("SELECT * FROM ProductionCycleOperation WHERE OperationID = ?", (operation_id,))
    operation = cursor.fetchone()

    cursor.execute("SELECT * FROM Resource")
    resources = cursor.fetchall()
    connection.close()
    return render_template('edit_operation.html', operation=operation, resources=resources)

@operations_bp.route('/operation/delete/<int:operation_id>', methods=['POST'])
def delete_operation(operation_id):
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()

    cursor.execute("SELECT CycleID FROM ProductionCycleOperation WHERE OperationID = ?", (operation_id,))
    cycle_id = cursor.fetchone()[0]

    cursor.execute("DELETE FROM ProductionCycleOperation WHERE OperationID = ?", (operation_id,))
    connection.commit()
    connection.close()
    flash('Operation deleted successfully', 'success')
    return redirect(url_for('cycles.view_cycle', cycle_id=cycle_id))


def get_operations_by_cycle(cycle_id):
    # Configura la connessione al database
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    
    # Esegui la query per ottenere le operazioni per il ciclo specificato
    query = "SELECT OperationSequence FROM ProductionCycleOperation WHERE CycleID = ?"
    cursor.execute(query, (cycle_id,))
    
    # Recupera i risultati e costruisci la lista delle operazioni
    operations = [{'OperationSequence': row.OperationSequence} for row in cursor.fetchall()]
    print(operations)
    # Chiudi la connessione
    cursor.close()
    conn.close()
    
    return operations