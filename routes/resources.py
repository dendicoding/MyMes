from flask import Blueprint, render_template, request, session, redirect, flash,url_for
from config import CONNECTION_STRING
import pyodbc
from routes.operators import get_operators
from routes.storage_movements import insert_storage_movement

resources_bp = Blueprint('resources', __name__)

@resources_bp.route('/resources', methods=['GET'])
def list_resources():
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM Resource")
    resources = cursor.fetchall()
    connection.close()
    return render_template('list_resources.html', resources=resources)

@resources_bp.route('/resource/create', methods=['GET', 'POST'])
def create_resource():
    if request.method == 'POST':
        resource_name = request.form['resource_name']
        resource_type = request.form['resource_type']
        availability_status = request.form['availability_status']
        last_maintenance_date = request.form['last_maintenance_date']

        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO Resource (resource_name, resource_type, availability_status, last_maintenance_date)
            VALUES (?, ?, ?, ?)
        """, (resource_name, resource_type, availability_status, last_maintenance_date))
        connection.commit()
        connection.close()
        flash('Resource created successfully', 'success')
        return redirect(url_for('resources.list_resources'))

    return render_template('create_resource.html')

@resources_bp.route('/resource/edit/<int:resource_id>', methods=['GET', 'POST'])
def edit_resource(resource_id):
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()

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
        connection.commit()
        connection.close()
        flash('Resource updated successfully', 'success')
        return redirect(url_for('resources.list_resources'))

    cursor.execute("SELECT * FROM Resource WHERE resource_id = ?", (resource_id,))
    resource = cursor.fetchone()
    connection.close()
    return render_template('edit_resource.html', resource=resource)

@resources_bp.route('/resource/delete/<int:resource_id>', methods=['POST'])
def delete_resource(resource_id):
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()
    cursor.execute("DELETE FROM Resource WHERE resource_id = ?", (resource_id,))
    connection.commit()
    connection.close()
    flash('Resource deleted successfully', 'success')
    return redirect(url_for('resources.list_resources'))


@resources_bp.route('/create_material', methods=['GET', 'POST'])
def create_material():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        available_quantity = request.form['available_quantity']
        unit_of_measure = request.form['unit_of_measure']
        unit_cost = request.form['unit_cost']
        cycle = request.form['cycle_id']
        lot_code = request.form['lot_code']  # Aggiungi il lot_code

        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO materials (name, description, initial_quantity, available_quantity, unit_of_measure, unit_cost, cycleID, lot)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, description, available_quantity, available_quantity, unit_of_measure, unit_cost, cycle, lot_code))
        connection.commit()
        connection.close()

        
        return redirect(url_for('resources.view_all_materials'))
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()
    cursor.execute('SELECT CycleID FROM ProductionCycle')
    cycles = cursor.fetchall()
    cursor.execute("SELECT lot_code FROM lots")
    lots = cursor.fetchall()

    return render_template('create_material.html', cycles=cycles, lots=lots)

@resources_bp.route('/create_product', methods=['GET', 'POST'])
def create_product():
    if request.method == 'POST':
        
        name = request.form['name']
        description = request.form['description']
        available_quantity = request.form['available_quantity']
        unit_of_measure = request.form['unit_of_measure']
        price = request.form['price']

        connection = pyodbc.connect(CONNECTION_STRING)
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO items (name, description, available_quantity, unit_of_measure, price)
            VALUES (?, ?, ?, ?, ?)
        """, (name, description, available_quantity, unit_of_measure, price))
        connection.commit()
        connection.close()

        return redirect(url_for('resources.view_all_products'))

    return render_template('create_product.html')

@resources_bp.route('/view_all_materials')
def view_all_materials():
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM Materials')
    materials = cursor.fetchall()
    connection.close()

    return render_template('list_materials.html', materials=materials)

@resources_bp.route('/view_all_products')
def view_all_products():
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM items')
    items = cursor.fetchall()
    connection.close()

    return render_template('list_products.html', items=items)


@resources_bp.route('/view_materials/<cycle_id>')
def view_materials(cycle_id):
    # Esegui una query per ottenere tutti i materiali con lo stesso cycleID
    materials = get_cycle_material(cycle_id)
    
    # Passa i materiali alla tua template per la visualizzazione
    return render_template('list_cycle_materials.html', materials=materials)

def get_cycle_material(cycle_id):
    query = "SELECT * FROM Materials WHERE cycleID = ?"
    params = (cycle_id,)
    connection = pyodbc.connect(CONNECTION_STRING)
    cursor = connection.cursor()
    cursor.execute(query, params)
    return cursor.fetchall()

@resources_bp.route('/withdraw_material/<material_id>', methods=['GET', 'POST'])
def withdraw_material(material_id):
    if 'username' in session:
        if request.method == 'GET':
            material = get_material_by_id(material_id)
            operators = get_operators()  # Fetch operators for dropdown
            if material is None:
                flash('Material not found.', 'error')
            return render_template('withdraw_material.html', material=material, operators=operators)
        
        if request.method == 'POST':
            operator_id = request.form['operator_id']
            quantity = int(request.form['quantity'])
            material_id = request.form['material_id']
            material = get_material_by_id(material_id)
            if material is None:
                flash('Material not found.', 'error')
            if quantity <= material['available_quantity']:  # Access as dictionary
                # Insert into Storage_Movements
                insert_storage_movement(material_id, operator_id, quantity)
                return redirect(url_for('tasks'))
            else:
                # Handle error if quantity exceeds available quantity
                flash('Requested quantity exceeds available quantity.', 'error')
                return redirect(url_for('resources.withdraw_material', material_id=material_id))
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