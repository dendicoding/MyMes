from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from config import CONNECTION_STRING
from routes.machines import get_machines
from routes.operators import get_operators
from datetime import datetime
import pyodbc

maintenance_bp = Blueprint('maintenance', __name__)

@maintenance_bp.route('/preventive_maintenance')
def view_preventive_maintenance():
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM preventive_maintenance")
    maintenance_list = cursor.fetchall()
    connection.close()

    return render_template('view_preventive_maintenance.html', maintenance_list=maintenance_list)

@maintenance_bp.route('/preventive_maintenance/add', methods=['GET', 'POST'])
def add_preventive_maintenance():
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()
    machines = get_machines()
    operators = get_operators()

    if request.method == 'POST':
        machine_id = request.form['machine_id']
        scheduled_date = request.form['scheduled_date']
        technician = request.form['technician']
        planned_activity = request.form['planned_activity']

        try:
            # Converti la data ricevuta dal form in un oggetto datetime
            formatted_date = datetime.strptime(scheduled_date, '%Y-%m-%dT%H:%M')

            # Esegui l'inserimento nel database
            cursor.execute("""
                INSERT INTO preventive_maintenance (machine_id, scheduled_date, technician, planned_activity)
                VALUES (?, ?, ?, ?)
            """, (machine_id, formatted_date, technician, planned_activity))
            connection.commit()
            flash('Preventive maintenance added successfully', 'success')
        except ValueError as e:
            flash(f'Error in date format: {e}', 'danger')
        finally:
            connection.close()

        return redirect(url_for('maintenance.view_preventive_maintenance'))

    connection.close()
    return render_template('add_preventive_maintenance.html', machines=machines, operators=operators)

@maintenance_bp.route('/preventive_maintenance/calendar')
def preventive_maintenance_calendar():
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()

    cursor.execute("SELECT maintenance_id, machine_id, scheduled_date, planned_activity FROM preventive_maintenance")
    maintenance_list = cursor.fetchall()
    connection.close()

    events = [
        {
            'id': maintenance.maintenance_id,
            'title': f'Machine {maintenance.machine_id}: {maintenance.planned_activity}',
            'start': maintenance.scheduled_date.strftime('%Y-%m-%dT%H:%M:%S'),
        }
        for maintenance in maintenance_list
    ]

    return render_template('preventive_maintenance_calendar.html', events=events)

@maintenance_bp.route('/get_maintenance_events')
def get_maintenance_events():
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()

    # Ottieni gli eventi di manutenzione preventiva
    cursor.execute("""
        SELECT maintenance_id, machine_id, scheduled_date, technician, planned_activity
        FROM preventive_maintenance
    """)
    
    events = []
    for row in cursor.fetchall():
        events.append({
            'id': row.maintenance_id,
            'title': f'{row.planned_activity} - Machine {row.machine_id}',
            'start': row.scheduled_date.strftime('%Y-%m-%dT%H:%M:%S'),
            'description': f'Technician: {row.technician}'
        })

    connection.close()
    return jsonify(events)

@maintenance_bp.route('/maintenance_requests', methods=['GET'])
def view_maintenance_requests():
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT r.request_id, m.machine_id, r.request_date, o.name as requester, r.problem_description, r.request_status
        FROM maintenance_requests r
        JOIN Macchine m ON r.machine_id = m.id
        JOIN Operatori o ON r.requester = o.operator_id
        ORDER BY r.request_date DESC
    """)
    maintenance_requests = cursor.fetchall()
    connection.close()

    return render_template('maintenance_requests.html', maintenance_requests=maintenance_requests)

@maintenance_bp.route('/maintenance_requests/add', methods=['GET', 'POST'])
def add_maintenance_request():
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()

    if request.method == 'POST':
        machine_id = request.form['machine_id']
        requester = request.form['requester']
        problem_description = request.form['problem_description']

        cursor.execute("""
            INSERT INTO maintenance_requests (machine_id, request_date, requester, problem_description, request_status)
            VALUES (?, GETDATE(), ?, ?, 'pending')
        """, (machine_id, requester, problem_description))
        connection.commit()
        connection.close()
        
        flash('Maintenance request added successfully', 'success')
        return redirect(url_for('maintenance.view_maintenance_requests'))

    # Get machine and operator options for the dropdown menus
    cursor.execute("SELECT id, machine_id FROM Macchine")
    machines = cursor.fetchall()

    cursor.execute("SELECT operator_id, name FROM Operatori")
    operators = cursor.fetchall()

    connection.close()
    return render_template('add_maintenance_request.html', machines=machines, operators=operators)

@maintenance_bp.route('/self_maintenance', methods=['GET'])
def view_self_maintenance():
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT s.self_maintenance_id, m.machine_id, s.control_date, o.name as operator, s.control_result
        FROM self_maintenance s
        JOIN Macchine m ON s.machine_id = m.id
        JOIN Operatori o ON s.operator = o.operator_id
        ORDER BY s.control_date DESC
    """)
    self_maintenance_records = cursor.fetchall()
    connection.close()

    return render_template('self_maintenance.html', self_maintenance_records=self_maintenance_records)

@maintenance_bp.route('/self_maintenance/add', methods=['GET', 'POST'])
def add_self_maintenance():
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()

    if request.method == 'POST':
        machine_id = request.form['machine_id']
        operator_id = request.form['operator']
        control_result = request.form['control_result']

        cursor.execute("""
            INSERT INTO self_maintenance (machine_id, control_date, operator, control_result)
            VALUES (?, GETDATE(), ?, ?)
        """, (machine_id, operator_id, control_result))
        connection.commit()
        connection.close()
        
        flash('Self maintenance record added successfully', 'success')
        return redirect(url_for('maintenance.view_self_maintenance'))

    # Get machine and operator options for the dropdown menus
    cursor.execute("SELECT id, machine_id FROM Macchine")
    machines = cursor.fetchall()

    cursor.execute("SELECT operator_id, name FROM Operatori")
    operators = cursor.fetchall()

    connection.close()
    return render_template('add_self_maintenance.html', machines=machines, operators=operators)

@maintenance_bp.route('/repair_maintenance', methods=['GET'])
def view_repair_maintenance():
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT r.repair_id, m.machine_id, r.intervention_date, o.name as technician, r.intervention_type, r.intervention_description
        FROM repair_maintenance r
        JOIN Macchine m ON r.machine_id = m.id
        JOIN Operatori o ON r.technician = o.operator_id
        ORDER BY r.intervention_date DESC
    """)
    repair_maintenance_records = cursor.fetchall()
    connection.close()

    return render_template('repair_maintenance.html', repair_maintenance_records=repair_maintenance_records)

@maintenance_bp.route('/repair_maintenance/add', methods=['GET', 'POST'])
def add_repair_maintenance():
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()

    if request.method == 'POST':
        machine_id = request.form['machine_id']
        technician_id = request.form['technician']
        intervention_type = request.form['intervention_type']
        intervention_description = request.form['intervention_description']

        cursor.execute("""
            INSERT INTO repair_maintenance (machine_id, intervention_date, technician, intervention_type, intervention_description)
            VALUES (?, GETDATE(), ?, ?, ?)
        """, (machine_id, technician_id, intervention_type, intervention_description))
        connection.commit()
        connection.close()

        flash('Repair maintenance record added successfully', 'success')
        return redirect(url_for('maintenance.view_repair_maintenance'))

    # Get machine and technician options for the dropdown menus
    cursor.execute("SELECT id, machine_id FROM Macchine")
    machines = cursor.fetchall()

    cursor.execute("SELECT operator_id, name FROM Operatori")
    technicians = cursor.fetchall()

    connection.close()
    return render_template('add_repair_maintenance.html', machines=machines, technicians=technicians)

@maintenance_bp.route('/preventive_maintenance/complete/<int:maintenance_id>', methods=['GET'])
def complete_preventive_maintenance(maintenance_id):
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE preventive_maintenance
        SET status = 'completed'
        WHERE maintenance_id = ?
    """, (maintenance_id,))
    connection.commit()
    connection.close()

    flash('Preventive maintenance marked as completed', 'success')
    return redirect(url_for('maintenance.view_preventive_maintenance'))

@maintenance_bp.route('/complete_maintenance_request/<int:request_id>', methods=['GET'])
def complete_maintenance_request(request_id):
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()
    # Aggiorna lo stato della richiesta di manutenzione a 'completed'
    cursor.execute("UPDATE maintenance_requests SET request_status = 'completed' WHERE request_id = ?", request_id)
    connection.commit()  # Salva le modifiche nel database
    cursor.close()
    
    flash('Maintenance request has been marked as completed.', 'success')
    return redirect(url_for('maintenance.view_maintenance_requests'))