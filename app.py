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
            cycle = request.form['cycleID']
            
            # Inserisci l'ordine nel database
            production_orders[order_id] = {
                "product": product,
                "quantity": quantity,
                "status": "created",
                "start_time": None,
                "end_time": None,
                "cost": 0,
                "cycleID": cycle,
                "initial_quantity": quantity
            }
            flash('Order created successfully!', 'success')
            
            insert_order(order_id, "created", product, quantity, cycle)  # Inserimento nel database
            

        orders_list = get_orders()  # Ottieni gli ordini dal database
        machines_list = get_machines()  # Ottieni le macchine dal database
        return render_template('orders.html', orders=orders_list, machines=machines_list)
    else:
        return redirect(url_for('login'))



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



@app.route('/emit_order/<order_id>', methods=['POST'])
def emit_order(order_id):
    cycle = request.form['cycleID']
    if 'username' in session and session['role'] == 'manager':
        order = next((o for o in get_orders() if o['order_id'] == order_id), None)
        if order and order['status'] == 'created':
            update_order(order_id, 'emitted')
             # Inserisci i task per ogni operazione associata al ciclo
            operations = get_operations_by_cycle(cycle)  # Recupera le operazioni per il ciclo
            for operation in operations:
                task_description = f"{order_id}/{operation['OperationSequence']}"
                # Passa solo gli argomenti necessari
                insert_task(order_id, task_description)  # Inserimento dei task nel database
            flash(f'Order {order_id} emitted successfully!', 'success')
        else:
            flash('Order cannot be emitted. It may not exist or it is not in "created" status.', 'error')
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

def insert_order(order_id, status, product, quantity, cycleID):
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()
        
        sql_insert_query = """INSERT INTO Ordini (order_id, status, product, quantity, initial_quantity, cycleID) VALUES (?, ?, ?, ?, ?, ?)"""
        record_to_insert = (order_id, status, product, quantity, quantity, cycleID)
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
                'cycleID': row.CycleID,
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
        return redirect(url_for('login'))






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
    
from datetime import datetime

@app.route('/delete_order/<order_id>', methods=['POST'])
def delete_order(order_id):
    try:
        # Connect to the database
        conn = pyodbc.connect(CONNECTION_STRING)
        cursor = conn.cursor()
        
        # Delete the order from the database
        cursor.execute("DELETE FROM Ordini WHERE order_id = ?", (order_id,))
        conn.commit()
        
        # Check if the order was successfully deleted
        if cursor.rowcount > 0:
            flash('Order deleted successfully.', 'success')
        else:
            flash('Order not found.', 'error')
    
    except Exception as e:
        flash(f'Error occurred: {str(e)}', 'error')
    
    finally:
        # Close the connection
        cursor.close()
        conn.close()
    
    return redirect(url_for('orders'))

@app.route('/update_task_schedule', methods=['POST'])
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
                'machine': task['machine_id'],
                'progress': task.get('progress', 0)  # Assumi default 0 se non specificato
            })

        return jsonify({"data": task_list})
    else:
        return redirect(url_for('login'))

@app.route('/machines_json', methods=['GET'])
def machines_json():
    machines = get_machines()  # Ottieni i dati delle macchine come dizionari
    machines_data = [{"id": machine["id"], "name": machine["machine_id"]} for machine in machines]
    
    return jsonify({"data": machines_data})


def get_db_connection():
    conn = pyodbc.connect(CONNECTION_STRING)
    return conn


@app.route('/cycle/create', methods=['GET', 'POST'])
def create_cycle():
    if request.method == 'POST':
        cycle_name = request.form['cycle_name']
        description = request.form['description']
        estimated_duration = request.form['estimated_duration']
        status = request.form['status']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ProductionCycle (CycleName, Description, EstimatedDuration, Status)
            VALUES (?, ?, ?, ?)
        """, (cycle_name, description, estimated_duration, status))
        conn.commit()
        conn.close()
        flash('Cycle created successfully', 'success')
        return redirect(url_for('list_cycles'))

    return render_template('create_cycle.html')

@app.route('/cycle/edit/<int:cycle_id>', methods=['GET', 'POST'])
def edit_cycle(cycle_id):
    conn = get_db_connection()
    cursor = conn.cursor()

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
        conn.commit()
        conn.close()
        flash('Cycle updated successfully', 'success')
        return redirect(url_for('list_cycles'))

    cursor.execute("SELECT * FROM ProductionCycle WHERE CycleID = ?", (cycle_id,))
    cycle = cursor.fetchone()
    conn.close()
    return render_template('edit_cycle.html', cycle=cycle)

@app.route('/cycle/delete/<int:cycle_id>', methods=['POST'])
def delete_cycle(cycle_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ProductionCycleOperation WHERE CycleID = ?; DELETE FROM ProductionCycle WHERE CycleID = ?", (cycle_id,cycle_id,))
    conn.commit()
    conn.close()
    flash('Cycle deleted successfully', 'success')
    return redirect(url_for('list_cycles'))

@app.route('/cycles', methods=['GET'])
def list_cycles():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ProductionCycle")
    cycles = cursor.fetchall()
    conn.close()
    return render_template('list_cycles.html', cycles=cycles)  # Passa None se non c'è un ciclo specifico

@app.route('/cycle/<int:cycle_id>', methods=['GET'])
def view_cycle(cycle_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ProductionCycle WHERE CycleID = ?", (cycle_id,))
    cycle = cursor.fetchone()

    if not cycle:
        return "Cycle not found", 404
    
    cursor.execute("SELECT * FROM ProductionCycleOperation WHERE CycleID = ?", (cycle_id,))
    operations = cursor.fetchall()
    conn.close()

    return render_template('view_cycle.html', cycle=cycle, operations=operations, cycle_id=cycle_id)


@app.route('/cycle/<int:cycle_id>/operation/add', methods=['GET', 'POST'])
def add_operation(cycle_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        operation_name = request.form['operation_name']
        operation_sequence = request.form['operation_sequence']
        estimated_time = request.form['estimated_time']
        

        cursor.execute("""
            INSERT INTO ProductionCycleOperation (CycleID, OperationName, OperationSequence, EstimatedTime)
            VALUES (?, ?, ?, ?)
        """, (cycle_id, operation_name, operation_sequence, estimated_time))
        conn.commit()
        conn.close()
        flash('Operation added successfully', 'success')
        return redirect(url_for('view_cycle', cycle_id=cycle_id))

    
    conn.close()
    return render_template('add_operation.html', cycle_id=cycle_id)

@app.route('/operation/edit/<int:operation_id>', methods=['GET', 'POST'])
def edit_operation(operation_id):
    conn = get_db_connection()
    cursor = conn.cursor()

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
        conn.commit()
        conn.close()
        flash('Operation updated successfully', 'success')
        return redirect(url_for('view_cycle', cycle_id=operation_id))

    cursor.execute("SELECT * FROM ProductionCycleOperation WHERE OperationID = ?", (operation_id,))
    operation = cursor.fetchone()

    cursor.execute("SELECT * FROM Resource")
    resources = cursor.fetchall()
    conn.close()
    return render_template('edit_operation.html', operation=operation, resources=resources)

@app.route('/operation/delete/<int:operation_id>', methods=['POST'])
def delete_operation(operation_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT CycleID FROM ProductionCycleOperation WHERE OperationID = ?", (operation_id,))
    cycle_id = cursor.fetchone()[0]

    cursor.execute("DELETE FROM ProductionCycleOperation WHERE OperationID = ?", (operation_id,))
    conn.commit()
    conn.close()
    flash('Operation deleted successfully', 'success')
    return redirect(url_for('view_cycle', cycle_id=cycle_id))

@app.route('/resources', methods=['GET'])
def list_resources():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Resource")
    resources = cursor.fetchall()
    conn.close()
    return render_template('list_resources.html', resources=resources)

@app.route('/resource/create', methods=['GET', 'POST'])
def create_resource():
    if request.method == 'POST':
        resource_name = request.form['resource_name']
        resource_type = request.form['resource_type']
        availability_status = request.form['availability_status']
        last_maintenance_date = request.form['last_maintenance_date']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Resource (resource_name, resource_type, availability_status, last_maintenance_date)
            VALUES (?, ?, ?, ?)
        """, (resource_name, resource_type, availability_status, last_maintenance_date))
        conn.commit()
        conn.close()
        flash('Resource created successfully', 'success')
        return redirect(url_for('list_resources'))

    return render_template('create_resource.html')

@app.route('/resource/edit/<int:resource_id>', methods=['GET', 'POST'])
def edit_resource(resource_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        resource_name = request.form['resource_name']
        resource_type = request.form['resource_type']
        availability_status = request.form['availability_status']
        last_maintenance_date = request.form['last_maintenance_date']

        cursor.execute("""
            UPDATE Resource
            SET resource_name = ?, resource_type = ?, availability_status = ?, last_maintenance_date = ?
            WHERE resource_id = ?
        """, (resource_name, resource_type, availability_status, last_maintenance_date, resource_id))
        conn.commit()
        conn.close()
        flash('Resource updated successfully', 'success')
        return redirect(url_for('list_resources'))

    cursor.execute("SELECT * FROM Resource WHERE resource_id = ?", (resource_id,))
    resource = cursor.fetchone()
    conn.close()
    return render_template('edit_resource.html', resource=resource)

@app.route('/resource/delete/<int:resource_id>', methods=['POST'])
def delete_resource(resource_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Resource WHERE resource_id = ?", (resource_id,))
    conn.commit()
    conn.close()
    flash('Resource deleted successfully', 'success')
    return redirect(url_for('list_resources'))


@app.route('/create_material', methods=['GET', 'POST'])
def create_material():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        available_quantity = request.form['available_quantity']
        unit_of_measure = request.form['unit_of_measure']
        unit_cost = request.form['unit_cost']
        cycle = request.form['cycle_id']
        lot_code = request.form['lot_code']  # Aggiungi il lot_code

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO materials (name, description, initial_quantity, available_quantity, unit_of_measure, unit_cost, cycleID, lot)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, description, available_quantity, available_quantity, unit_of_measure, unit_cost, cycle, lot_code))
        conn.commit()
        conn.close()

        
        return redirect(url_for('view_all_materials'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT CycleID FROM ProductionCycle')
    cycles = cursor.fetchall()
    cursor.execute("SELECT lot_code FROM lots")
    lots = cursor.fetchall()

    return render_template('create_material.html', cycles=cycles, lots=lots)

@app.route('/create_product', methods=['GET', 'POST'])
def create_product():
    if request.method == 'POST':
        
        name = request.form['name']
        description = request.form['description']
        available_quantity = request.form['available_quantity']
        unit_of_measure = request.form['unit_of_measure']
        price = request.form['price']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO items (name, description, available_quantity, unit_of_measure, price)
            VALUES (?, ?, ?, ?, ?)
        """, (name, description, available_quantity, unit_of_measure, price))
        conn.commit()
        conn.close()

        return redirect(url_for('view_all_products'))

    return render_template('create_product.html')

@app.route('/view_all_materials')
def view_all_materials():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Materials')
    materials = cursor.fetchall()
    conn.close()

    return render_template('list_materials.html', materials=materials)

@app.route('/view_all_products')
def view_all_products():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM items')
    items = cursor.fetchall()
    conn.close()

    return render_template('list_products.html', items=items)


@app.route('/view_materials/<cycle_id>')
def view_materials(cycle_id):
    # Esegui una query per ottenere tutti i materiali con lo stesso cycleID
    materials = get_cycle_material(cycle_id)
    
    # Passa i materiali alla tua template per la visualizzazione
    return render_template('list_cycle_materials.html', materials=materials)

def get_cycle_material(cycle_id):
    query = "SELECT * FROM Materials WHERE cycleID = ?"
    params = (cycle_id,)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    return cursor.fetchall()

@app.route('/withdraw_material/<material_id>', methods=['GET', 'POST'])
def withdraw_material(material_id):
    if 'username' in session:
        if request.method == 'GET':
            material = get_material_by_id(material_id)
            operators = get_operators()  # Fetch operators for dropdown
            if material is None:
                flash('Material not found.', 'error')
                return redirect(url_for('some_other_route'))  # Redirect if material not found
            return render_template('withdraw_material.html', material=material, operators=operators)
        
        if request.method == 'POST':
            operator_id = request.form['operator_id']
            quantity = int(request.form['quantity'])
            material_id = request.form['material_id']
            material = get_material_by_id(material_id)
            if material is None:
                flash('Material not found.', 'error')
                return redirect(url_for('some_other_route'))  # Redirect if material not found
            if quantity <= material['available_quantity']:  # Access as dictionary
                # Insert into Storage_Movements
                insert_storage_movement(material_id, operator_id, quantity)
                return redirect(url_for('tasks'))
            else:
                # Handle error if quantity exceeds available quantity
                flash('Requested quantity exceeds available quantity.', 'error')
                return redirect(url_for('withdraw_material', material_id=material_id))
    else:
        return redirect(url_for('login'))
def get_material_by_id(material_id):
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM Materials WHERE material_id = ?", (material_id,))
        row = cursor.fetchone()
        if row:
            return {
                'material_id': row.material_id,
                'name': row.name,
                'available_quantity': row.available_quantity,
                'description': row.description,
                'unit_of_measure': row.unit_of_measure,
                'unit_cost': row.unit_cost,
                'cycleID': row.cycleID
            }
    except Exception as error:
        print(f"Failed to retrieve material {material_id}: {error}")
    finally:
        if connection:
            cursor.close()
            connection.close()
    return None

def insert_storage_movement(material_id, operator_id, quantity):
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()
        
        # Insert into Storage_Movements
        cursor.execute("""
            INSERT INTO Storage_Movements (material_id, operator_id, quantity, movement_time, type_of_movement)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
        """, (material_id, operator_id, quantity, 'withdrawal'))
        
        # Update available_quantity in Materials
        cursor.execute("""
            UPDATE Materials
            SET available_quantity = available_quantity - ?
            WHERE material_id = ?
        """, (quantity, material_id))
        
        connection.commit()
    except Exception as error:
        print(f"Failed to insert storage movement or update material quantity: {error}")
    finally:
        if connection:
            cursor.close()
            connection.close()


@app.route('/list_storage_movements', methods=['GET'])
def list_storage_movements():
    if 'username' in session:
        storage_movements = get_storage_movements()
        return render_template('list_storage_movements.html', storage_movements=storage_movements)
    else:
        return redirect(url_for('login'))
def get_storage_movements():
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM Storage_Movements")
        rows = cursor.fetchall()
        
        # Convert rows to a list of dictionaries
        movements_list = []
        for row in rows:
            movements_list.append({
                'movement_id': row.movement_id,
                'material_id': row.material_id,
                'type_of_movement': row.type_of_movement,
                'operator_id': row.operator_id,
                'quantity': row.quantity,
                'movement_time': row.movement_time
            })
        
        return movements_list

    except Exception as error:
        print(f"Failed to retrieve records from Storage_Movements table: {error}")
        return []

    finally:
        if connection:
            cursor.close()
            connection.close()

@app.route('/create_lot_function', methods=['POST'])
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
    return redirect(url_for('view_lots'))

@app.route('/create_lot', methods=['GET'])
def create_lot():
    return render_template('create_lot.html')

@app.route('/view_lots', methods=['GET'])
def view_lots():
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()

    # Recupera tutti i lotti dal database
    cursor.execute("SELECT lot_id, lot_code, entity_type, quantity, unit_of_measure, creation_date, expiration_date, status FROM Lots")
    lots = cursor.fetchall()

    return render_template('view_lots.html', lots=lots)

@app.route('/view_lots_materials/<lot_code>')
def view_lots_materials(lot_code):
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()

    # Recupera i materiali collegati al lot_code
    cursor.execute("SELECT * FROM Materials WHERE lot = ?", (lot_code,))
    materials = cursor.fetchall()

    return render_template('view_lots_materials.html', materials=materials, lot_code=lot_code)

@app.route('/lot_dashboard')
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

@app.route('/notes', methods=['GET', 'POST'])
def notes():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Recupera tutti gli operatori per il menu a tendina
    cursor.execute("SELECT operator_id, name FROM Operatori")
    operatori = cursor.fetchall()

    selected_operator = request.form.get('operatore')
    selected_client = request.form.get('cliente')
    selected_date = request.form.get('data')

    clienti = ['VegaPlast', 'Serigroup']

    # Recupera il nome dell'operatore selezionato
    nome_operatore = None
    if selected_operator:
        cursor.execute("SELECT name FROM Operatori WHERE operator_id = ?", selected_operator)
        nome_operatore = cursor.fetchone()[0]

    # Usa direttamente il nome del cliente dalla lista (se esiste)
    nome_cliente = selected_client if selected_client else None

    # Query per le note
    query = """
        SELECT n.creation_time, n.note, n.cliente
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
    conn.close()

    # Passa i dati al template
    return render_template('notes.html',
                           operatori=operatori,
                           clienti=clienti,  # Passiamo la lista dei clienti
                           note=note,
                           selected_operator=selected_operator,
                           selected_client=selected_client,
                           selected_date=selected_date,
                           nome_operatore=nome_operatore,
                           nome_cliente=nome_cliente)




@app.route('/add_note', methods=['POST'])
def add_note():
    operatore_id = request.form['operatore']
    nota = request.form['nota']
    cliente = request.form['cliente']

    print("operatore_id:", operatore_id)
    print("nota:", nota)
    print("cliente:", cliente)

    # Inserisci la nuova nota nel database
    cursor.execute("INSERT INTO Personal_Reports (operator, note, cliente) VALUES (?, ?, ?)", operatore_id, nota, cliente)
    conn.commit()

    return redirect('/notes')


import pdfkit
from flask import send_file, render_template_string



from flask import send_file
import io

@app.route('/notes/pdf', methods=['POST'])
def generate_pdf():
    path_to_wkhtmltopdf = r'C:\Users\Xenture\OneDrive - ONE OFF Services scpa\Desktop\MyMes\wkhtmltopdf\bin\wkhtmltopdf.exe'
    config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)
    conn = get_db_connection()
    cursor = conn.cursor()

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
        SELECT n.creation_time, n.note, n.cliente
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
    conn.close()

    # Genera l'HTML per le note
    html = render_template_string("""
    <h1>Note per {{ nome_operatore }}{% if nome_cliente %} per {{ nome_cliente }}{% endif %}{% if selected_date %} del {{ selected_date }}{% endif %}</h1>
    <ul>
        {% for nota in note %}
            <li><strong>{{ nota[0] }}</strong>: {{ nota[1] }} - {{ nota[2] }}</li>
        {% endfor %}
    </ul>
    """, nome_operatore=nome_operatore, nome_cliente=nome_cliente, selected_date=selected_date, note=note)


    # Genera il PDF senza salvare direttamente su file
    pdf = pdfkit.from_string(html, False, configuration=config)

    # Usa un oggetto BytesIO per inviare il PDF direttamente al client
    pdf_stream = io.BytesIO(pdf)

    # Restituisci il PDF al client
    return send_file(pdf_stream, as_attachment=True, download_name='notes.pdf', mimetype='application/pdf')

    

    


    
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

@app.route('/create_order', methods=['GET', 'POST'])
def create_order():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT item_id FROM items')
    products = cursor.fetchall()
    cursor.execute("SELECT cycleID FROM ProductionCycle")
    cycles = cursor.fetchall()
    if request.method == 'POST':
        # Handle the order creation logic here
        return redirect(url_for('orders'))
    return render_template('create_order.html', cycles = cycles, products=products)

@app.route('/create_task', methods=['GET', 'POST'])
def create_task():
    if request.method == 'POST':
        # Handle the order creation logic here
        return redirect(url_for('tasks'))
    return render_template('create_task.html')


from chatbot import handle_chat  # Importa la funzione dal modulo chatbot.py
@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get("message")
    response = handle_chat(user_input)
    return jsonify({"response": response})

# Rotta per la chat specifica (chat.html)
@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    return render_template('chatbot.html')

if __name__ == '__main__':
    app.run(debug=True)
