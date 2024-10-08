from flask import Blueprint, render_template, request, session, redirect, flash,url_for

auth_bp = Blueprint('auth', __name__)
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

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = authenticate(username, password)
        if user:
            session['username'] = username
            session['role'] = user['role']
            return redirect(url_for('misc.dashboard'))
        else:
            flash('Invalid credentials', 'error')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('misc.index'))
