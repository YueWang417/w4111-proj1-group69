import os
  # accessible as a variable in index.html:
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response
from flask import redirect, url_for


tmpl_dir = os.path.join(os.path.dirname(os.path.abspath('/Users/yuewang/Desktop/webserver/templates')), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

DATABASE_USERNAME = "yw3930"
DATABASE_PASSWRD = "3089"
DATABASE_HOST = "34.148.107.47" # change to 34.28.53.86 if you used database 2 for part 2
DATABASEURI = f"postgresql://{DATABASE_USERNAME}:{DATABASE_PASSWRD}@{DATABASE_HOST}/project1"

engine = create_engine(DATABASEURI)
#
# try:
#     connection = engine.connect()
#     # get column names and data for drug table
#     select_query = "SELECT * FROM drug;"
#     result = connection.execute(text(select_query))
#     columns = result.keys()
#     data = result.fetchall()
#     print("Columns in drug table:")
#     print(columns)
#     print("Data in drug table:")
#     for row in data:
#         print(row)
#
#     print('---------------------------------------')
#
#     # get column names and data for pharmacy_storage table
#     select_query = "SELECT * FROM pharmacy_storage;"
#     result = connection.execute(text(select_query))
#     columns = result.keys()
#     data = result.fetchall()
#     print("Columns in pharmacy_storage table:")
#     print(columns)
#     print("Data in pharmacy_storage table:")
#     for row in data:
#         print(row)
#     connection.close()
#
# except Exception as e:
#     print(f"Error connecting to database: {e}")

@app.before_request
def before_request():
    """
    This function is run at the beginning of every web request
    (every time you enter an address in the web browser).
    We use it to setup a database connection that can be used throughout the request.

    The variable g is globally accessible.
    """
    try:
        g.conn = engine.connect()
    except:
        print("uh oh, problem connecting to database")
        import traceback; traceback.print_exc()
        g.conn = None

@app.teardown_request
def teardown_request(exception):
    """
    At the end of the web request, this makes sure to close the database connection.
    If you don't, the database could run out of memory!
    """
    try:
        g.conn.close()
    except Exception as e:
        pass

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/search', methods=['POST'])
def search():
    drug_id = request.form['drug_id']
    select_query = "SELECT * FROM pharmacy_storage WHERE drug_id = " + str(drug_id)
    cursor = g.conn.execute(text(select_query))
    if not cursor.rowcount:
        return render_template("error.html", drug_id=drug_id)
    else:
        results = [result for result in cursor]
        cursor.close()
        # print(results)
        return render_template("drug_information.html", drug_id=drug_id, drug_name=results[0][0], category=results[0][1], safety_stock=results[0][2], dosage=results[0][3])

@app.route('/add_drug', methods=['GET', 'POST'])
def add_drug():
    if request.method == 'POST':
        # get form data
        drug_id = request.form['drug_id']
        drug_name = request.form['drug_name']
        quantity = int(request.form['quantity'])
        expire_date = request.form['expire_date']
        # check if drug exists in drug table
        select_query = f"SELECT * FROM drug WHERE drug_id = '{drug_id}' and drug_name = '{drug_name}'"
        cursor = g.conn.execute(text(select_query))
        if not cursor.rowcount:
            cursor.close()
            error_message = f"Drug with ID '{drug_id}' or name '{drug_name}' does not exist in the database."
            return render_template("error.html", error_message=error_message)
        # check if drug exists in pharmacy storage
        select_query = f"SELECT * FROM pharmacy_storage WHERE drug_id = '{drug_id}' and drug_name = '{drug_name}' and expire_date = '{expire_date}'"
        cursor = g.conn.execute(text(select_query))
        if cursor.rowcount:
            # if drug exists in storage with same expiration date, add quantity
            results = [result for result in cursor]
            print(results)
            new_quantity = int(results[0][5]) + int(quantity)
            update_query = f"UPDATE pharmacy_storage SET quantity = {new_quantity} WHERE drug_id = '{drug_id}' and drug_name = '{drug_name}' and expire_date = '{expire_date}'"
            g.conn.execute(text(update_query))
        else:
            # if drug doesn't exist in storage, add new record
            insert_query = f"INSERT INTO pharmacy_storage (drug_id, drug_name, expire_date, quantity) VALUES ('{drug_id}', '{drug_name}', '{expire_date}', {quantity})"
            g.conn.execute(text(insert_query))
        cursor.close()
        # render updated pharmacy storage page
        select_query = "SELECT * FROM pharmacy_storage ORDER BY drug_id, drug_name, expire_date"
        cursor = g.conn.execute(text(select_query))
        storage_results = [result for result in cursor]
        cursor.close()
        g.conn.commit()
        return render_template("pharmacy_storage.html", storage_results=storage_results)
    else:
        return render_template("add_drug.html")

@app.route('/take_drug', methods=['GET', 'POST'])
def take_drug():
    if request.method == 'POST':
        # get form data
        drug_id = request.form['drug_id']
        drug_name = request.form['drug_name']
        quantity = int(request.form['quantity'])
        expire_date = request.form['expire_date']
        # check if drug exists in drug table
        select_query = f"SELECT * FROM drug WHERE drug_id = '{drug_id}' and drug_name = '{drug_name}'"
        cursor = g.conn.execute(text(select_query))
        if not cursor.rowcount:
            cursor.close()
            error_message = f"Drug with ID '{drug_id}' or name '{drug_name}' does not exist in the database."
            return render_template("error.html", error_message=error_message)
        # check if drug exists in pharmacy storage
        select_query = f"SELECT * FROM pharmacy_storage WHERE drug_id = '{drug_id}' and drug_name = '{drug_name}' and expire_date = '{expire_date}'"
        cursor = g.conn.execute(text(select_query))
        if not cursor.rowcount:
            cursor.close()
            error_message = f"Drug with ID '{drug_id}', name '{drug_name}', and expiration date '{expire_date}' does not exist in the pharmacy storage."
            return render_template("error.html", error_message=error_message)
        results = [result for result in cursor]
        cursor.close()
        # check if quantity is sufficient
        if int(results[0][5]) < quantity:
            error_message = f"Insufficient quantity of drug with ID '{drug_id}', name '{drug_name}', and expiration date '{expire_date}' in the pharmacy storage."
            return render_template("error.html", error_message=error_message)
        # calculate new quantity and update database
        new_quantity = int(results[0][5]) - quantity
        if new_quantity < 0:
            error_message = f"Invalid quantity of drug with ID '{drug_id}', name '{drug_name}', and expiration date '{expire_date}'. Quantity after taking cannot be less than 0."
            return render_template("error.html", error_message=error_message)
        elif new_quantity == 0:
            delete_query = f"DELETE FROM pharmacy_storage WHERE drug_id = '{drug_id}' and drug_name = '{drug_name}' and expire_date = '{expire_date}'"
            g.conn.execute(text(delete_query))
        else:
            update_query = f"UPDATE pharmacy_storage SET quantity = {new_quantity} WHERE drug_id = '{drug_id}' and drug_name = '{drug_name}' and expire_date = '{expire_date}'"
            g.conn.execute(text(update_query))
        # render updated pharmacy storage page
        select_query = "SELECT * FROM pharmacy_storage ORDER BY drug_id, drug_name, expire_date"
        cursor = g.conn.execute(text(select_query))
        storage_results = [result for result in cursor]
        cursor.close()
        g.conn.commit()
        return render_template("pharmacy_storage.html", storage_results=storage_results)
    else:
        return render_template("take_drug.html")

@app.route('/pharmacy_storage')
def pharmacy_storage():
    select_query = "SELECT * FROM pharmacy_storage;"
    cursor = g.conn.execute(text(select_query))
    storage_results = [result for result in cursor]
    cursor.close()
    return render_template('pharmacy_storage.html', storage_results=storage_results)

if __name__ == "__main__":
    import click
    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8111, type=int)
    def run(debug, threaded, host, port):
        HOST, PORT = host, port
        print("running on %s:%d" % (HOST, PORT))
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)
run()
