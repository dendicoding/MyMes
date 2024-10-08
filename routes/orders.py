from flask import Blueprint, render_template, request, session, redirect, flash,url_for
from config import CONNECTION_STRING
import pyodbc
from routes.machines import get_machines, update_machine
from datetime import datetime
from routes.operations import get_operations_by_cycle
from routes.operators import get_operators

order_bp = Blueprint('orders', __name__)

# Struttura per conservare gli ordini di produzione!
production_orders = {}

@order_bp.route('/orders', methods=['GET', 'POST'])
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
        return redirect(url_for('auth.login'))
    
@order_bp.route('/emit_order/<order_id>', methods=['POST'])
def emit_order(order_id):
    from routes.tasks import insert_task
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
        return redirect(url_for('misc.dashboard'))
    else:
        return redirect(url_for('auth.login'))

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

@order_bp.route('/suspend_order/<order_id>', methods=['POST'])
def suspend_order(order_id):
    if 'username' in session and session['role'] == 'manager':
        update_order(order_id, 'suspended')
        order = next((o for o in get_orders() if o['order_id'] == order_id), None)
        if order:
            machine_id = order.get("machine_id")  # Ottieni l'ID della macchina dall'ordine
            if machine_id:
                update_machine(machine_id, 'idle', None, None)
        flash('Order suspended successfully and machine set to idle!', 'success')
        return redirect(url_for('misc.dashboard'))
    else:
        return redirect(url_for('auth.login'))


@order_bp.route('/complete_order/<order_id>', methods=['POST'])
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
        return redirect(url_for('misc.dashboard'))
    else:
        return redirect(url_for('auth.login'))


@order_bp.route('/manage_orders', methods=['GET', 'POST'])
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
        return redirect(url_for('auth.login'))


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

@order_bp.route('/assign_order', methods=['POST'])
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

        return redirect(url_for('misc.dashboard'))
    else:
        return redirect(url_for('auth.login'))

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

@order_bp.route('/delete_order/<order_id>', methods=['POST'])
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

@order_bp.route('/create_order', methods=['GET', 'POST'])
def create_order():
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute('SELECT item_id FROM items')
    products = cursor.fetchall()
    cursor.execute("SELECT cycleID FROM ProductionCycle")
    cycles = cursor.fetchall()
    if request.method == 'POST':
        # Handle the order creation logic here
        return redirect(url_for('orders.orders'))
    return render_template('create_order.html', cycles = cycles, products=products)