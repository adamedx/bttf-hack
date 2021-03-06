from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify
from form_definitions import SeekerFormData, FormDataError

import psycopg2

from flask.ext.bcrypt import Bcrypt
import re
import time
from time import mktime
from datetime import datetime
EMAIL_REGEX = re.compile(r'^[a-za-z0-9\.\+_-]+@[a-za-z0-9\._-]+\.[a-za-z]*$')

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = '=\xb3\xb0iAb\x93\xec\x9f\x0f\xde\xf3\x06R\xd8\xa0*\x1fh\xd7%Q\x88\xaf'

conn = psycopg2.connect("host=192.168.99.100 dbname=postgres user=postgres password=pw")

def seeker_row_to_json(seeker):
        uid = seeker[0]
        sid = seeker[1]
        matched = seeker[2]
        active = seeker[3]

        json = {'user_id': uid, 'seeker_id': sid, 'is_matched': matched, 'is_active': active}
        return jsonify(json)

def selections_to_json(selections):
        print(selections)
        return jsonify([(s[0], s[1]) for s in selections])

@app.route('/selections/barriers', methods=['GET'])
def barrier_selections():
        qry = "select * from barrier_selection"
        cur = conn.cursor()
        cur.execute(qry)
        results = cur.fetchall()
        
        return selections_to_json(results)

@app.route('/selections/historical_connection', methods=['GET'])
def historical_connections():
        qry = "select * from historical_connection_selection"
        cur = conn.cursor()
        cur.execute(qry)
        results = cur.fetchall()
        
        return selections_to_json(results)

@app.route('/selections/visitor_reasons', methods=['GET'])
def visitor_reasons():
        qry = "select * from visitor_reason_selection"
        cur = conn.cursor()
        cur.execute(qry)
        results = cur.fetchall()
        
        return selections_to_json(results)

@app.route('/seeker/<user_id>', methods=['GET'])
def get_seeker(user_id):
        qry = "select * from seeker where user_id = {}".format(user_id)
        cur = conn.cursor()

        cur.execute(qry)
        results = cur.fetchone()

        return seeker_row_to_json(results)
        
@app.route('/seeker/<sid>/form_response/create', methods=['POST'])
def new_seeker_form_response(sid):
        content = request.get_json(silent=False)
        print("new form data for seeker {}: {}".format(sid, content))

        try:
                formdata = SeekerFormData(sid, content)

                cur = conn.cursor()
                qry = formdata.insert_statement()
                cur.execute(qry)

                conn.commit()
                res = {"ok": 1}

                return jsonify(res)
                
        except FormDataError as constructor_err:
                res = {"error": constructor_err.args[0]}
                return jsonify(res)
        except Exception as err:
                conn.rollback()
                res = {"error": err.args}
                return jsonify(res)
        
@app.route('/')
def index():
	return render_template('signup.html')

@app.route('/users', methods=['POST'])
def create():
	error = False
	email = request.form['email']
	first_name = request.form['first_name']
	last_name = request.form['last_name']
	password = request.form['password']
	password_confirmation = request.form['password_confirmation']

	if len(first_name) < 1:
		error = True
		flash('First name cannot be blank', 'danger')
	if len(last_name) < 1:
		error = True
		flash('Last name cannot be blank', 'danger')
	if len(email) < 1:
		error = True
		flash('Email cannot be blank', 'danger')
	if len(password) < 1:
		error = True
		flash('Password cannot be blank', 'danger')
	if password != password_confirmation:
		error = True
		flash('Passwords do not match', 'danger')
	if not EMAIL_REGEX.match(email):
		error = True
		flash('Email is invalid', 'danger')

	if error:
		return redirect(url_for('index'))
	# run validations and if they are successful we can create the password hash with bcrypt
	pw_hash = bcrypt.generate_password_hash(password)
	
	# now we insert the new user into the database
	insert_query = "INSERT INTO users (email, first_name, last_name, password_bc, created_dtm, updated_dtm) VALUES ('{}', '{}', '{}', '{}', NOW(), NOW())".format(email, first_name, last_name, pw_hash)
	cur.execute(insert_query)
        conn.commit()
	flash("You've successfully registered!", 'success')
	return redirect(url_for('signin'))

@app.route('/signin', methods=['POST','GET'])
def signin():
	if request.method == 'GET':
		return render_template('signin.html')
	email = request.form['email']
	password = request.form['password']
	user_query = "SELECT * FROM users WHERE email = '{}' LIMIT 1".format(email)
	cur.execute(user_query)
	user = cur.fetchone()
        print(user)
	
	if user and bcrypt.check_password_hash(user[4], password):
			session['id'] = user[0]
			session['first_name'] = user[1]
			return redirect(url_for('show'))
	flash('Invalid email or password', 'danger')
	return redirect(url_for('signin'))

@app.route('/signout')
def signout():
	session.pop('id')
	session.pop('first_name')
	return redirect(url_for('index'))

app.run(debug=True)
