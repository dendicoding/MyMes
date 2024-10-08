from flask import Blueprint, render_template, request, session, redirect, flash,url_for
from config import CONNECTION_STRING
import pyodbc
from routes.machines import get_machines, update_machine
from datetime import datetime

cycles_bp = Blueprint('cycles', __name__)

@cycles_bp.route('/cycle/create', methods=['GET', 'POST'])
def create_cycle():
    if request.method == 'POST':
        cycle_name = request.form['cycle_name']
        description = request.form['description']
        estimated_duration = request.form['estimated_duration']
        status = request.form['status']

        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO ProductionCycle (CycleName, Description, EstimatedDuration, Status)
            VALUES (?, ?, ?, ?)
        """, (cycle_name, description, estimated_duration, status))
        connection.commit()
        connection.close()
        flash('Cycle created successfully', 'success')
        return redirect(url_for('cycles.list_cycles'))

    return render_template('create_cycle.html')

@cycles_bp.route('/cycle/edit/<int:cycle_id>', methods=['GET', 'POST'])
def edit_cycle(cycle_id):
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()

    if request.method == 'POST':
        cycle_name = request.form['cycle_name']
        description = request.form['description']
        estimated_duration = request.form['estimated_duration']
        status = request.form['status']

        cursor.execute("""
            UPDATE ProductionCycle
            SET CycleName = ?, Description = ?, EstimatedDuration = ?, Status = ?
            WHERE CycleID = ?
        """, (cycle_name, description, estimated_duration, status, cycle_id))
        connection.commit()
        connection.close()
        flash('Cycle updated successfully', 'success')
        return redirect(url_for('cycles.list_cycles'))

    cursor.execute("SELECT * FROM ProductionCycle WHERE CycleID = ?", (cycle_id,))
    cycle = cursor.fetchone()
    connection.close()
    return render_template('edit_cycle.html', cycle=cycle)

@cycles_bp.route('/cycle/delete/<int:cycle_id>', methods=['POST'])
def delete_cycle(cycle_id):
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()
    cursor.execute("DELETE FROM ProductionCycleOperation WHERE CycleID = ?; DELETE FROM ProductionCycle WHERE CycleID = ?", (cycle_id,cycle_id,))
    connection.commit()
    connection.close()
    flash('Cycle deleted successfully', 'success')
    return redirect(url_for('cycles.list_cycles'))

@cycles_bp.route('/cycles', methods=['GET'])
def list_cycles():
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM ProductionCycle")
    cycles = cursor.fetchall()
    connection.close()
    return render_template('list_cycles.html', cycles=cycles)  # Passa None se non c'è un ciclo specifico

@cycles_bp.route('/cycle/<int:cycle_id>', methods=['GET'])
def view_cycle(cycle_id):
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM ProductionCycle WHERE CycleID = ?", (cycle_id,))
    cycle = cursor.fetchone()

    if not cycle:
        return "Cycle not found", 404
    
    cursor.execute("SELECT * FROM ProductionCycleOperation WHERE CycleID = ?", (cycle_id,))
    operations = cursor.fetchall()
    connection.close()

    return render_template('view_cycle.html', cycle=cycle, operations=operations, cycle_id=cycle_id)
