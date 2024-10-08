from flask import Blueprint, render_template, request, session, redirect, flash,url_for
from config import CONNECTION_STRING
import pyodbc
from routes.operators import get_operators
from routes.storage_movements import insert_storage_movement

misc_bp = Blueprint('misc', __name__)

@misc_bp.route('/')
def index():
    return render_template('index.html')

@misc_bp.route('/dashboard')
def dashboard():
    from routes.orders import get_orders
    from routes.machines import get_machines
    if 'username' in session:
        orders_list = get_orders()  # Ottieni gli ordini dal database
        machines_list = get_machines()  # Ottieni le macchine dal database
        operators_list = get_operators()  # Ottieni gli operatori dal database
        return render_template('dashboard.html', orders=orders_list, machines=machines_list, operators=operators_list)
    else:
        return redirect(url_for('auth.login'))

@misc_bp.route('/report')
def report():
    from routes.orders import get_completed_orders
    if 'username' in session:
        # Recupera solo gli ordini completati dal database
        orders = get_completed_orders()
        return render_template('report.html', orders=orders)
    else:
        return redirect(url_for('auth.login'))