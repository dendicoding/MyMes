from flask import Blueprint, render_template, request, session, redirect, flash, url_for, jsonify
from config import CONNECTION_STRING
import pyodbc
from routes.orders import get_orders, update_order, update_order_quantity
from routes.operators import get_operators, update_operator
from routes.machines import get_machines, update_machine
from datetime import datetime

task_bp = Blueprint('tasks', __name__)

@task_bp.route('/tasks', methods=['GET'])
def tasks():
    if 'username' in session:
        # Recupera gli ordini dalla funzione get_orders
        orders = get_orders()  
        print("Orders:", orders)  # Stampa per il debug
        
        # Crea un dizionario degli ordini con order_id come chiave
        orders_dict = {order['order_id']: order for order in orders}
        print(orders_dict)
        # Recupera le altre informazioni
        machines = get_machines()  # Get machines from the database
        operators = get_operators()  # Get operators from the database
        tasks = get_tasks()  # Get tasks from the database
        
        # Stampa del cycleID per ogni task
        for task in tasks:
            # Assumiamo che task.order_id sia una chiave nel dizionario orders_dict
            order = orders_dict.get(task['order_id'])
            if order:
                print(f"Task ID: {task['task_id']}, Cycle ID: {order['cycleID']}")
            else:
                print(f"Task ID: {task['task_id']}, Order not found")
        
        return render_template('tasks.html', orders=orders, machines=machines, operators=operators, tasks=tasks, orders_dict=orders_dict)
    else:
        return redirect(url_for('auth.login'))

def insert_task(order_id, task_description):
    # Configura la connessione al database
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    status = 'pending'
    
    query = "INSERT INTO Tasks (order_id, task, status) VALUES (?, ?, ?)"
    cursor.execute(query, (order_id, task_description, status))
    
    conn.commit()
    cursor.close()
    conn.close()

@task_bp.route('/suspend_task/<task_id>', methods=['POST'])
def suspend_task(task_id):
    if 'username' in session and session['role'] == 'manager':
        update_task(task_id, status='suspended', operator='None', operator_name='None')
        machine_id = request.form.get("machine_id")
        operator_id = request.form.get("operator_id")
        update_machine(machine_id, status='idle', current_order='None', current_task='None')
        update_operator(operator_id, status='idle', current_task='None')
        flash('Task suspended successfully!', 'success')
        return redirect(url_for('tasks.tasks'))
    else:
        return redirect(url_for('login'))

@task_bp.route('/complete_task/<task_id>', methods=['POST'])
def complete_task(task_id):
    if 'username' in session and session['role'] == 'manager':
        update_task(task_id, status='completed', end_time=datetime.now())
        machine_id = request.form.get("machine_id")
        operator_id = request.form.get("operator_id")
        update_machine(machine_id, status='idle', current_order='None', current_task='None')
        update_operator(operator_id, status='idle', current_task='None')
        flash('Task suspended successfully!', 'success')
        return redirect(url_for('tasks.tasks'))
    else:
        return redirect(url_for('login'))

@task_bp.route('/assign_task', methods=['POST'])
def assign_task():
    if 'username' in session and session['role'] == 'manager':
        task_id = request.form.get('task_id')
        machine_id = request.form.get('machine_id')
        
        if task_id and machine_id:
            tasks = get_tasks()  # Ottieni i task dal database
            machines = get_machines()  # Ottieni le macchine dal database
            
            tasks_dict = {task['task_id']: task for task in tasks}
            machines_dict = {machine['machine_id']: machine for machine in machines}
            
            task = tasks_dict.get(task_id)
            machine = machines_dict.get(machine_id)
            
            if task and machine:
                if task["status"] == "pending" and machine["status"] == "idle":
                    # Aggiorna la macchina e il task nel database
                    current_time = datetime.now()
                    update_machine(machine_id, "working", task_id, current_time)
                    update_task(task_id, machine_id=machine_id)
                    flash(f'Task {task_id} assigned to machine {machine_id}.', 'success')
                else:
                    flash('Task or machine status is not suitable for assignment.', 'error')
            else:
                flash('Invalid task or machine.', 'error')
        else:
            flash('Task ID and Machine ID are required.', 'error')
        
        return redirect(url_for('tasks.tasks'))
    else:
        return redirect(url_for('auth.login'))

def get_tasks():
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM Tasks")
        tasks = cursor.fetchall()

        tasks_list = []
        for row in tasks:
            tasks_list.append({
                'task_id': row.task_id,
                'order_id': row.order_id,
                'machine_id': row.machine_id,
                'status': row.status,
                'start_time': row.start_time,
                'end_time': row.end_time,
                'cost': row.cost,
                'task': row.task,
                'operator': row.operator,  # Include the operator field
                'operator_name': row.operator_name,
                'prog_start_time': row.prog_start_time,
                'prog_end_time': row.prog_end_time
            })

        return tasks_list

    except Exception as error:
        print(f"Failed to retrieve records from Tasks table {error}")
        return []

    finally:
        if connection:
            cursor.close()
            connection.close()

def update_task(task_id, status=None, operator=None, start_time=None, end_time=None, machine_id=None, operator_name=None, prog_start_time=None, prog_end_time=None):
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()

        # Crea una lista di valori e una lista di colonne da aggiornare
        update_values = []
        update_columns = []

        if status is not None:
            update_values.append(status)
            update_columns.append("status = ?")

        if operator is not None:
            update_values.append(operator)
            update_columns.append("operator = ?")

        if operator_name is not None:
            update_values.append(operator_name)
            update_columns.append("operator_name = ?")

        if start_time is not None:
            update_values.append(start_time)
            update_columns.append("start_time = ?")

        if end_time is not None:
            update_values.append(end_time)
            update_columns.append("end_time = ?")

        if machine_id is not None:
            update_values.append(machine_id)
            update_columns.append("machine_id = ?")

        if prog_start_time is not None:
            update_values.append(prog_start_time)
            update_columns.append("prog_start_time = ?")

        if prog_end_time is not None:
            update_values.append(prog_end_time)
            update_columns.append("prog_end_time = ?")



        # Aggiungi l'ID del task alla fine della lista dei valori
        update_values.append(task_id)

        # Se ci sono colonne da aggiornare, costruisci la query
        if update_columns:
            sql_update_query = f"UPDATE Tasks SET {', '.join(update_columns)} WHERE task_id = ?"
            cursor.execute(sql_update_query, update_values)
            connection.commit()
            print(f"Task with ID {task_id} updated successfully")

        else:
            print(f"No updates provided for Task with ID {task_id}")

    except Exception as error:
        print(f"Failed to update task with ID {task_id}: {error}")

    finally:
        if connection:
            cursor.close()
            connection.close()

@task_bp.route('/start_task', methods=['POST'])
def start_task():
    if 'username' in session and session['role'] == 'manager':
        task_id = request.form.get('task_id')
        task = request.form.get('task')
        machine_id = request.form.get("machine_id")
        current_order = request.form.get("order_id")
        operator_id = request.form.get("operator_id")  # Assicurati che questo campo venga corretto
        operator_name = request.form.get("operator_name")  # Aggiunto per il nome dell'operatore

        # Stampa per debugging
        print("Received data:", {
            'task_id': task_id,
            'task': task,
            'machine_id': machine_id,
            'order_id': current_order,
            'operator_id': operator_id,
            'operator_name': operator_name  # Aggiunto per il nome dell'operatore
        })

        if task_id and machine_id:
            try:
                task_id = int(task_id)  # Assicurati che task_id sia un intero

                # Connessione al database
                connection = pyodbc.connect(CONNECTION_STRING)
                cursor = connection.cursor()

                # Verifica lo stato della macchina
                machine_query = "SELECT status FROM Macchine WHERE machine_id = ?"
                cursor.execute(machine_query, (machine_id,))
                machine_result = cursor.fetchone()

                if machine_result and machine_result.status == 'working':
                    flash('The machine is already working on another task.', 'error')
                else:
                    # Trova lo stato del task
                    task_query = "SELECT status FROM Tasks WHERE task_id = ?"
                    cursor.execute(task_query, (task_id,))
                    task_result = cursor.fetchone()

                    if task_result and (task_result.status == 'pending' or task_result.status == 'suspended'):
                        # Aggiorna il task, la macchina e l'ordine
                        update_task(task_id, status='in_progress', start_time=datetime.now(), operator=operator_id, operator_name=operator_name)
                        update_machine(machine_id, status='working', current_order=current_order, start_time=datetime.now(), current_task=task)
                        update_order(order_id=current_order, status='in_progress')
                        update_operator(operator_id, status='busy', current_task=task)
                        flash(f'Task {task_id} started.', 'success')
                    else:
                        flash('Task status is not suitable for starting.', 'error')
               
            except Exception as error:
                flash(f"Failed to start task: {error}", 'error')
            
            finally:
                if connection:
                    cursor.close()
                    connection.close()
        else:
            flash('Task ID and Machine are required.', 'error')

        return redirect(url_for('tasks.tasks'))
    else:
        return redirect(url_for('auth.login'))

@task_bp.route('/manage_tasks/<int:task_id>', methods=['GET', 'POST'])
def manage_tasks(task_id):
    if 'username' in session:
        if request.method == 'POST':
            # Ottieni i valori dal form
            good_pieces = int(request.form.get('good_pieces', 0))
            scrap_pieces = int(request.form.get('scrap_pieces', 0))

            # Ottieni i task dal database
            tasks = get_tasks()
            task = next((t for t in tasks if t['task_id'] == task_id), None)

            if task:
                order_id = task['order_id']
                orders = get_orders()  # Ottieni tutti gli ordini
                order = next((o for o in orders if o['order_id'] == order_id), None)

                if order:
                    if good_pieces >= 0 and scrap_pieces >= 0:
                        new_quantity = order['quantity'] - good_pieces + scrap_pieces
                        if new_quantity < 0:
                            flash('The resulting quantity cannot be negative.', 'error')
                        else:
                            # Aggiorna la quantità dell'ordine
                            update_order_quantity(order_id, new_quantity)

                            # Aggiorna lo stato del task e dell'ordine se necessario
                            if new_quantity == 0:
                                update_task(task_id, status='completed', end_time=datetime.now())
                                update_order(order_id, status='completed', end_time=datetime.now())
                                machine_id = task.get("machine_id")
                                if machine_id:
                                    update_machine(machine_id, status='idle', current_order='None', current_task='None')
                                flash(f'Task {task_id} completed and order {order_id} completed.', 'success')
                            else:
                                flash(f'Task {task_id} updated with {good_pieces} good pieces e {scrap_pieces} scrap pieces.', 'success')
                    else:
                        flash('Invalid Values for Good pieces and Scrap Pieces.', 'error')
                else:
                    flash('Related Order not found.', 'error')
            else:
                flash('Task not found.', 'error')

        elif request.method == 'GET':
            # Ottieni i dettagli del task
            tasks = get_tasks()
            task = next((t for t in tasks if t['task_id'] == task_id), None)

            if task:
                return render_template('manage_tasks.html', task_id=task_id)
            else:
                flash('Task not found.', 'error')
                return redirect(url_for('tasks.tasks'))  # Redirigi alla pagina dei task

        # Reindirizza alla pagina dei task se la richiesta non è POST né GET valida
        return redirect(url_for('tasks'))
    else:
        return redirect(url_for('login'))

@task_bp.route('/scheduler')
def scheduler():
    if 'username' in session:
        return render_template('scheduler.html')
    else:
        return redirect(url_for('auth.login'))


@task_bp.route('/scheduler/events')
def scheduler_events():
    if 'username' in session:
        tasks = get_tasks()  # Get tasks from the database
        # Convert the tasks to a format compatible with FullCalendar
        task_events = [
            {
                'id': task['task_id'],
                'title': task['task'],
                'start': task['prog_start_time'].isoformat() if task['prog_start_time'] else None,
                'end': task['prog_end_time'].isoformat() if task['prog_end_time'] else None
            }
            for task in tasks
        ]
        return jsonify(task_events)
    else:
        return redirect(url_for('auth.login'))


@task_bp.route('/delete_task', methods=['POST'])
def delete_task():
    if 'username' in session and session['role'] == 'manager':
        data = request.json
        task_id = data.get('task_id')
        
        if not task_id:
            return jsonify({'success': False, 'error': 'Task ID is required'}), 400
        
        try:
            # Chiamata alla funzione per aggiornare il task, impostando gli orari a NULL
            update_task(task_id, prog_start_time=None, prog_end_time=None)
            return jsonify({'success': True})
        except Exception as e:
            print(f"Failed to update task schedule: {e}")
            return jsonify({'success': False, 'error': str(e)}), 400
    else:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
from datetime import datetime

@task_bp.route('/update_task_schedule', methods=['POST'])
def update_task_schedule():
    if 'username' in session and session['role'] == 'manager':
        data = request.json
        task_id = data.get('task_id')
        prog_start_time_str = data.get('prog_start_time')
        prog_end_time_str = data.get('prog_end_time')
        machine_id = data.get('machine_id')

        default_date_str = "1900-01-01 00:00"
        
        try:
            # Verifica se le date sono stringhe valide prima di convertirle
            if isinstance(prog_start_time_str, str) and prog_start_time_str != default_date_str:
                prog_start_time = datetime.fromisoformat(prog_start_time_str)
            else:
                prog_start_time = None

            if isinstance(prog_end_time_str, str) and prog_end_time_str != default_date_str:
                prog_end_time = datetime.fromisoformat(prog_end_time_str)
            else:
                prog_end_time = None

            print('Received data:', {
                'task_id': task_id,
                'prog_start_time': prog_start_time,
                'prog_end_time': prog_end_time,
                'machine_id': machine_id
            })
            
            # Aggiorna il task nel database (devi implementare la funzione update_task)
            update_task(task_id, prog_start_time=prog_start_time, prog_end_time=prog_end_time, machine_id=machine_id)
            
            return jsonify({'success': True})
        except Exception as e:
            print(f"Failed to update task schedule: {e}")
            return jsonify({'success': False, 'error': str(e)}), 400
    else:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

from flask import jsonify, redirect, url_for
from datetime import datetime

@task_bp.route('/tasks_json')
def get_task_list():
    if 'username' in session:
        tasks = get_tasks()  # Ottieni i task dal database
        
        # Filtra i task il cui status non è 'completed'
        filtered_tasks = [task for task in tasks if task.get('status') != 'completed']
        
        task_list = []
        default_start_date = datetime(1900, 1, 1, 0, 0)  # Data di default molto indietro nel tempo
        default_end_date = datetime(1900, 1, 1, 0, 0)  # Data di default molto indietro nel tempo

        for task in filtered_tasks:
            # Usa la data di default se start_date o end_date sono None
            start_date = task.get('prog_start_time') or default_start_date
            end_date = task.get('prog_end_time') or default_end_date

            # Assicurati che start_date e end_date siano oggetti datetime
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date)
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date)

            task_list.append({
                'id': task['task_id'],
                'text': task['task'],
                'start_date': start_date.strftime('%Y-%m-%d %H:%M'),
                'end_date': end_date.strftime('%Y-%m-%d %H:%M'),
                'machine': task['machine_id'],
                'progress': task.get('progress', 0)  # Assumi default 0 se non specificato
            })

        return jsonify({"data": task_list})
    else:
        return redirect(url_for('login'))
    

@task_bp.route('/create_task', methods=['GET', 'POST'])
def create_task():
    if request.method == 'POST':
        # Handle the order creation logic here
        return redirect(url_for('tasks.tasks'))
    return render_template('create_task.html')