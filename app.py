from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
import pyodbc
from config import CONNECTION_STRING

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Struttura per conservare gli ordini di produzione!
production_orders = {}


#--------------------------------AUTHENTICATION---------------------
# Struttura per conservare gli utenti
users = {
    "manager": {"password": "manager123", "role": "manager"},
    "operator": {"password": "operator123", "role": "operator"},
}

def authenticate(username, password):
    user = users.get(username)
    if user and user["password"] == password:
        return user
    else:
        return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = authenticate(username, password)
        if user:
            session['username'] = username
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('index'))

#--------------------------------MACCHINE----------------------
@app.route('/machines', methods=['GET'])
def view_machines():
    if 'username' in session:
        machine_list = get_machines()  # Ottieni le macchine dal database
        return render_template('machines.html', machines=machine_list)
    else:
        return redirect(url_for('login'))

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

@app.route('/add_machine', methods=['GET', 'POST'])
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
#--------------------------------ORDINI----------------------
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'username' in session:
        if request.method == 'POST' and session['role'] == 'manager':
            order_id = request.form['order_id']
            product = request.form['product']
            quantity = request.form['quantity']
            production_orders[order_id] = {
                "product": product,
                "quantity": quantity,
                "status": "created",  # Stato iniziale 'created'
                "start_time": None,
                "end_time": None,
                "cost": 0,
                "initial_quantity": quantity
            }
            flash('Order created successfully!', 'success')
            insert_order(order_id, "created", product, quantity)  # Inserimento nel database

        orders_list = get_orders()  # Ottieni gli ordini dal database
        machines_list = get_machines()  # Ottieni le macchine dal database
        return render_template('orders.html', orders=orders_list, machines=machines_list)
    else:
        return redirect(url_for('login'))

@app.route('/emit_order/<order_id>', methods=['POST'])
def emit_order(order_id):
    if 'username' in session and session['role'] == 'manager':
        order = next((o for o in get_orders() if o['order_id'] == order_id), None)
        if order and order['status'] == 'created':
            update_order(order_id, 'emitted')
            flash(f'Order {order_id} emitted successfully!', 'success')
        else:
            flash('Order cannot be emitted. It may not exist or it is not in "created" status.', 'error')
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

def insert_order(order_id, status, product, quantity):
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()
        
        sql_insert_query = """INSERT INTO Ordini (order_id, status, product, quantity, initial_quantity) VALUES (?, ?, ?, ?, ?)"""
        record_to_insert = (order_id, status, product, quantity, quantity)
        cursor.execute(sql_insert_query, record_to_insert)

        connection.commit()
        print(f"Record inserted successfully into Ordini table")

    except Exception as error:
        print(f"Failed to insert record into Ordini table {error}")

    finally:
        if connection:
            cursor.close()
            connection.close()

def get_orders():
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()
        
        cursor.execute("SELECT * FROM Ordini WHERE status <> 'completed'")
        orders = cursor.fetchall()

        # Mappa i risultati in dizionari
        orders_list = []
        for row in orders:
            orders_list.append({
                'order_id': row.order_id,
                'status': row.status,
                'product': row.product,
                'quantity': row.quantity,
                'initial_quantity': row.initial_quantity,
                'machine_id': row.machine_id,
                'start_time': row.start_time,
                'end_time': row.end_time,
                'cost': row.cost
            })

        return orders_list

    except Exception as error:
        print(f"Failed to retrieve records from Ordini table {error}")
        return []

    finally:
        if connection:
            cursor.close()
            connection.close()

def update_order(order_id, status, end_time=None, start_time=None):
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()

        sql_update_query = """UPDATE Ordini SET status = ?, end_time = ?, start_time = ? WHERE order_id = ?"""
        cursor.execute(sql_update_query, (status, end_time, start_time, order_id))

        connection.commit()
        print(f"Record updated successfully in Ordini table")

    except Exception as error:
        print(f"Failed to update record in Ordini table {error}")

    finally:
        if connection:
            cursor.close()
            connection.close()

@app.route('/suspend_order/<order_id>', methods=['POST'])
def suspend_order(order_id):
    if 'username' in session and session['role'] == 'manager':
        update_order(order_id, 'suspended')
        order = next((o for o in get_orders() if o['order_id'] == order_id), None)
        if order:
            machine_id = order.get("machine_id")  # Ottieni l'ID della macchina dall'ordine
            if machine_id:
                update_machine(machine_id, 'idle', None, None)
        flash('Order suspended successfully and machine set to idle!', 'success')
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))


@app.route('/complete_order/<order_id>', methods=['POST'])
def complete_order(order_id):
    if 'username' in session and session['role'] == 'manager':
        orders = get_orders()
        order = next((o for o in orders if o['order_id'] == order_id), None)
        if order and order["status"] == "in_progress":
            # Non passare start_time come None, mantenere il valore esistente
            update_order(order_id, 'completed', end_time=datetime.now(), start_time=order["start_time"])
            machine_id = order.get("machine_id")  # Ottieni l'ID della macchina dall'ordine
            if machine_id:
                update_machine(machine_id, 'idle', None, None)
            flash('Order completed successfully and machine set to idle!', 'success')
        else:
            flash('Order is not in progress or already completed.', 'error')
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))


@app.route('/manage_orders', methods=['GET', 'POST'])
def manage_orders():
    if 'username' in session:
        if request.method == 'POST':
            order_id = request.form.get('order_id')
            action = request.form.get('action')

            orders = get_orders()  # Ottieni gli ordini dal database
            order = next((o for o in orders if o['order_id'] == order_id), None)

            if order:
                if action == 'advance':
                    produced_quantity = int(request.form.get('produced_quantity', 0))
                    if produced_quantity > 0 and order['quantity'] >= produced_quantity:
                        remaining_quantity = order['quantity'] - produced_quantity
                        if remaining_quantity == 0:
                            update_order(order_id, 'completed', datetime.now())
                            machine_id = order.get("machine_id")  # Ottieni l'ID della macchina dall'ordine
                            if machine_id:
                                update_machine(machine_id, 'idle', None, None)
                        else:
                            update_order(order_id, order['status'], order['start_time'])
                            update_order_quantity(order_id, remaining_quantity)
                        flash(f'Updated order {order_id} with {produced_quantity} produced pieces.', 'success')
                    else:
                        flash('Produced quantity exceeds the ordered quantity or is invalid.', 'error')
                elif action == 'suspend':
                    update_order(order_id, 'suspended')
                    machine_id = order.get("machine_id")  # Ottieni l'ID della macchina dall'ordine
                    if machine_id:
                        update_machine(machine_id, 'idle', None, None)
                    flash('Order suspended successfully and machine set to idle!', 'success')
                elif action == 'complete':
                    if order["status"] == "in_progress":
                        update_order(order_id, 'completed', datetime.now())
                        machine_id = order.get("machine_id")  # Ottieni l'ID della macchina dall'ordine
                        if machine_id:
                            update_machine(machine_id, 'idle', None, None)
                        flash('Order completed successfully and machine set to idle!', 'success')
                    else:
                        flash('Order is not in progress or already completed.', 'error')
            else:
                flash('Order not found.', 'error')

        orders_list = get_orders()  # Ottieni gli ordini dal database
        return render_template('manage_orders.html', orders=orders_list)
    else:
        return redirect(url_for('login'))


def update_order_quantity(order_id, remaining_quantity):
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()
        
        sql_update_query = """UPDATE Ordini SET quantity = ? WHERE order_id = ?"""
        cursor.execute(sql_update_query, (remaining_quantity, order_id))

        connection.commit()
        print(f"Order quantity updated successfully in Ordini table")

    except Exception as error:
        print(f"Failed to update order quantity in Ordini table {error}")

    finally:
        if connection:
            cursor.close()
            connection.close()

@app.route('/assign_order', methods=['POST'])
def assign_order():
    if 'username' in session and session['role'] == 'manager':
        order_id = request.form.get('order_id')
        machine_id = request.form.get('machine_id')
        name = request.form.get('name')

        if order_id and machine_id and name:
            orders = get_orders()  # Ottieni gli ordini dal database
            machines = get_machines()  # Ottieni le macchine dal database
            operators = get_operators()  # Ottieni  gli operatori dal database

            machines_dict = {machine['machine_id']: machine for machine in machines}
            order = next((o for o in orders if o['order_id'] == order_id), None)
            machine = machines_dict.get(machine_id)

            if order and machine:
                if (order["status"] == "emitted") and machine["status"] == "idle":
                    # Aggiorna la macchina e l'ordine nel database
                    current_time = datetime.now()
                    update_machine(machine_id, "working", order_id, current_time)
                    update_order(order_id, "in_progress", start_time=current_time)
                    # Aggiorna l'ordine con l'ID della macchina e dell'operatore
                    update_order_machine_id(order_id, machine_id)
                    update_order_operator_id(order_id, name)
                    flash(f'Order {order_id} assigned to {machine_id} and operator {name}.', 'success')
                else:
                    flash('Order or machine status is not suitable for assignment.', 'error')
            else:
                flash('Invalid order or machine ID.', 'error')
        else:
            flash('Order ID, Machine ID, and Operator ID are required.', 'error')

        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

def update_order_operator_id(order_id, name):
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()
        
        sql_update_query = """UPDATE Ordini SET operator = ? WHERE order_id = ?"""
        cursor.execute(sql_update_query, (name, order_id))

        connection.commit()
        print(f"Order {order_id} updated with operator ID {name}")

    except Exception as error:
        print(f"Failed to update order with operator ID {error}")

    finally:
        if connection:
            cursor.close()
            connection.close()

def update_order_machine_id(order_id, machine_id):
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()
        
        sql_update_query = """UPDATE Ordini SET machine_id = ? WHERE order_id = ?"""
        cursor.execute(sql_update_query, (machine_id, order_id))

        connection.commit()
        print(f"Order {order_id} updated with machine ID {machine_id}")

    except Exception as error:
        print(f"Failed to update order with machine ID {error}")

    finally:
        if connection:
            cursor.close()
            connection.close()

def get_completed_orders():
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()
        
        cursor.execute("SELECT * FROM Ordini WHERE status = 'completed'")
        orders = cursor.fetchall()

        orders_list = []
        for row in orders:
            orders_list.append({
                'order_id': row.order_id,
                'status': row.status,
                'product': row.product,
                'initial_quantity': row.initial_quantity,
                'start_time': row.start_time,
                'end_time': row.end_time,
                'cost': row.cost
            })

        return orders_list

    except Exception as error:
        print(f"Failed to retrieve completed orders from Ordini table {error}")
        return []

    finally:
        if connection:
            cursor.close()
            connection.close()

#-----------------------------------OPERATORI------------------
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

@app.route('/add_operator', methods=['GET', 'POST'])
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
        return redirect(url_for('login'))

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


@app.route('/operators', methods=['GET'])
def view_operators():
    if 'username' in session:
        operators_list = get_operators()  
        return render_template('operators.html', operators=operators_list)
    else:
        return redirect(url_for('login'))

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
#-----------------------------------TASKS------------------
@app.route('/tasks', methods=['GET'])
def tasks():
    if 'username' in session:
        orders = get_orders()  # Get orders from the database
        machines = get_machines()  # Get machines from the database
        operators = get_operators()  # Get operators from the database
        tasks = get_tasks()  # Get tasks from the database
        return render_template('tasks.html', orders=orders, machines=machines, operators=operators, tasks=tasks)
    else:
        return redirect(url_for('login'))

@app.route('/create_task', methods=['POST'])
def create_task():
    if 'username' in session and session['role'] == 'manager':
        order_id = request.form['order_id']
        machine_id = request.form['machine_id']
        task_description = request.form['task']

        if order_id and machine_id and task_description:
            # Pass the operator name when inserting the task
            insert_task(order_id, machine_id, task_description)
            flash('Task created successfully!', 'success')
        else:
            flash('All fields are required.', 'error')
        return redirect(url_for('tasks'))
    else:
        return redirect(url_for('login'))


@app.route('/suspend_task/<task_id>', methods=['POST'])
def suspend_task(task_id):
    if 'username' in session and session['role'] == 'manager':
        update_task(task_id, status='suspended', operator='None', operator_name='None')
        machine_id = request.form.get("machine_id")
        operator_id = request.form.get("operator_id")
        update_machine(machine_id, status='idle', current_order='None', current_task='None')
        update_operator(operator_id, status='idle', current_task='None')
        flash('Task suspended successfully!', 'success')
        return redirect(url_for('tasks'))
    else:
        return redirect(url_for('login'))

@app.route('/complete_task/<task_id>', methods=['POST'])
def complete_task(task_id):
    if 'username' in session and session['role'] == 'manager':
        update_task(task_id, status='completed', end_time=datetime.now())
        machine_id = request.form.get("machine_id")
        operator_id = request.form.get("operator_id")
        update_machine(machine_id, status='idle', current_order='None', current_task='None')
        update_operator(operator_id, status='idle', current_task='None')
        flash('Task suspended successfully!', 'success')
        return redirect(url_for('tasks'))
    else:
        return redirect(url_for('login'))

def insert_task(order_id, machine_id, task_description):
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()

        # Update the SQL query to include the operator
        sql_insert_query = """INSERT INTO Tasks (order_id, machine_id, status, task) VALUES (?, ?, 'pending', ?)"""
        cursor.execute(sql_insert_query, (order_id, machine_id, task_description))

        connection.commit()
        print(f"Task inserted successfully into Tasks table")

    except Exception as error:
        print(f"Failed to insert record into Tasks table {error}")

    finally:
        if connection:
            cursor.close()
            connection.close()

@app.route('/assign_task', methods=['POST'])
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
        
        return redirect(url_for('tasks'))
    else:
        return redirect(url_for('login'))


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

        #if prog_start_time is not None:
        update_values.append(prog_start_time)
        update_columns.append("prog_start_time = ?")

        #if prog_end_time is not None:
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

@app.route('/start_task', methods=['POST'])
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

        return redirect(url_for('tasks'))
    else:
        return redirect(url_for('login'))

@app.route('/manage_tasks/<int:task_id>', methods=['GET', 'POST'])
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
                return redirect(url_for('tasks'))  # Redirigi alla pagina dei task

        # Reindirizza alla pagina dei task se la richiesta non è POST né GET valida
        return redirect(url_for('tasks'))
    else:
        return redirect(url_for('login'))

@app.route('/scheduler')
def scheduler():
    if 'username' in session:
        return render_template('scheduler.html')
    else:
        return redirect(url_for('login'))


@app.route('/scheduler/events')
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
        return redirect(url_for('login'))


@app.route('/delete_task', methods=['POST'])
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
    
@app.route('/update_task_schedule', methods=['POST'])
def update_task_schedule():
    if 'username' in session and session['role'] == 'manager':
        data = request.json
        task_id = data.get('task_id')
        prog_start_time = datetime.fromisoformat(data.get('prog_start_time'))
        prog_end_time = datetime.fromisoformat(data.get('prog_end_time'))

        try:
            update_task(task_id, prog_start_time=prog_start_time, prog_end_time=prog_end_time)
            return jsonify({'success': True})
        except Exception as e:
            print(f"Failed to update task schedule: {e}")
            return jsonify({'success': False, 'error': str(e)}), 400
    else:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

from flask import jsonify, redirect, url_for
from datetime import datetime

from flask import jsonify, redirect, url_for
from datetime import datetime

@app.route('/tasks_json')
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
                'progress': task.get('progress', 0)  # Assumi default 0 se non specificato
            })

        return jsonify({"data": task_list})
    else:
        return redirect(url_for('login'))






#---------------------------------------------------------ALTRO--------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        orders_list = get_orders()  # Ottieni gli ordini dal database
        machines_list = get_machines()  # Ottieni le macchine dal database
        operators_list = get_operators()  # Ottieni gli operatori dal database
        return render_template('dashboard.html', orders=orders_list, machines=machines_list, operators=operators_list)
    else:
        return redirect(url_for('login'))

@app.route('/report')
def report():
    if 'username' in session:
        # Recupera solo gli ordini completati dal database
        orders = get_completed_orders()
        return render_template('report.html', orders=orders)
    else:
        return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
