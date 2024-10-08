from flask import Blueprint, render_template, request, session, redirect, flash,url_for
from config import CONNECTION_STRING
import pyodbc

storage_movements_bp = Blueprint('storage_movements', __name__)

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


@storage_movements_bp.route('/list_storage_movements', methods=['GET'])
def list_storage_movements():
    if 'username' in session:
        storage_movements = get_storage_movements()
        return render_template('list_storage_movements.html', storage_movements=storage_movements)
    else:
        return redirect(url_for('auth.login'))
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

