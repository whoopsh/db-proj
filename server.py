#!/usr/bin/env python2.7

"""
Columbia's COMS W4111.001 Introduction to Databases
To run locally:
    python server.py
"""
import os
import datetime
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, url_for, session
from flask.ext.session import Session

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.secret_key = 'super secret key'
SESSION_TYPE = 'memcached'
sess = Session(app)

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = 'reds209ndsldssdsljdsldsdsljdsldksdksdsdfsfsfsfis'
sess.init_app(app)
# app.secret_key()
# sess.init_app(app)


# tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
# app = Flask(__name__, template_folder=tmpl_dir)
# app.secret_key = 'some_secret'


DATABASEURI = "postgresql://wl2573:2017@35.196.90.148/proj1part2"
engine = create_engine(DATABASEURI)

#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#

# engine.execute("""CREATE TABLE IF NOT EXISTS test (
#   id serial,
#   name text
# );""")
# engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")


@app.before_request
def before_request():
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  try:
    g.conn.close()
  except Exception as e:
    pass

# Main page for guest user.
# Display login and signup url linking to other pages.
@app.route('/')
def index():
  """
  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2
  """
  # print request.args

  # email = request.args.get('email')
  email = request.args.get('email')
  if 'cid' in session:
    cid = session.get('cid')
    email = session.get('email')
    # print "here" + str(cid)

  cursor = g.conn.execute("SELECT ctg_id, ctg_name, cate_url FROM category")
  category = []
  for result in cursor:
    category.append(dict(ctg_id = result['ctg_id'], ctg_name = result['ctg_name'], url = result['cate_url']))  # can also be accessed using result[0]
  cursor.close()

  cursor = g.conn.execute("SELECT c.first_name FROM customer c WHERE c.email = %s", email)
  cname = ''
  for result in cursor:
    cname = result['first_name']
  cursor.close()

  context = dict(data = category, email = email, cname = cname)
  return render_template("index.html", **context)


@app.route('/another')
def another():
  return render_template("another.html")

@app.route('/backmain')
def backmain():
  return redirect('/')

@app.route('/product')
def product():
  catg_id = request.args['catg']
  cursor = g.conn.execute("SELECT c.ctg_name ctg_name, p.pid pid ,p.p_name pname, p.p_image url FROM product p, category c WHERE p.ctg_id = c.ctg_id AND c.ctg_id = %s", catg_id)
  catg_products = []
  cname = ''
  pid = ''
  email = session.get('email')

  for result in cursor:
    catg_products.append(dict(ctg_name = result['ctg_name'], pid = result['pid'], p_name = result['pname'], \
      url = result['url']))
    cname = result['ctg_name']

  context = dict(data = catg_products, ctg_name = cname, email = email, cname = session.get('cname'))
  return render_template("product.html", **context)

# Get product details and reviews here.
@app.route('/pdetails')
def pdetails():
  pid = request.args['prod']
  product_details = []
  product_reviews = []
  prodid = ''
  email = None
  cname = None
  if 'cid' in session:
    cid = session.get('cid')
    email = session.get('email')
    cname = session['cname']

  cursor = g.conn.execute("SELECT p.pid pid, p.p_name p_name, p.p_price p_price ,p.details details, p.p_image url FROM product p WHERE p.pid = %s", pid)
  for result in cursor:
    product_details.append(dict(pname = result['p_name'], price = result['p_price'], \
      details = result['details'], url = result['url']))
    prodid = result['pid']
  cursor.close()

  cursor2 = g.conn.execute("SELECT c.first_name cust, r.content cont, r.rating rating FROM product p, review r, customer c WHERE p.pid = r.pid AND c.cid = r.cid AND p.pid = %s", pid) 
  for result2 in cursor2:
    product_reviews.append(dict(cust = result2['cust'], cont = result2['cont'], rating = result2['rating']))
  cursor2.close()

  context = dict(data = product_details, data2 = product_reviews, prodid = prodid, email = email, cname = cname)
  return render_template("pdetails.html", **context)

# Order products.
@app.route('/checkout')
def checkout():
  cursor = g.conn.execute("SELECT p.pid pid, p.p_name p_name, p.p_image url, a.quantity qty FROM adds_basket a, product p, customer c WHERE a.pid = p.pid AND a.cid = c.cid AND c.cid = %s", session['cid'])
  basket_details = []
  for result in cursor:
    print result['p_name']
    basket_details.append(dict(pid = result['pid'], pname = result['p_name'], url = result['url'], qty = result['qty']))
  cursor.close()

  context = dict(data = basket_details, cid = session['cid'], cname = session['cname'])
  return render_template("checkout.html", **context)

# Delet products.
@app.route('/delete', methods=['POST'])
def delete():
  pid = request.args.get('pid')
  cid = session['cid']
  g.conn.execute("DELETE FROM adds_basket a WHERE a.pid = %s AND a.cid = %s", pid, cid)
  return redirect(url_for('checkout'))

# Delete all products.
@app.route('/deleteall', methods=['POST'])
def deleteall():
  cid = session['cid']
  g.conn.execute("DELETE FROM adds_basket a WHERE a.cid = %s", cid)
  return redirect(url_for('checkout'))

# Order for products in basket.
@app.route('/order', methods=['POST'])
def order():
  cid = session['cid']
  currentDT = datetime.datetime.now()
  date = currentDT.strftime("%Y-%m-%d")
  # place all prducts in basket into order.
  cursor = g.conn.execute("SELECT c.cid cid, p.pid pid, p.p_name p_name, p.p_image url, a.quantity qty FROM adds_basket a, product p, customer c WHERE a.pid = p.pid AND a.cid = c.cid AND c.cid = %s", cid)
  basket_details = []
  for result in cursor:
    g.conn.execute("INSERT INTO purchase (cid, pid, amount, order_date) VALUES (%s, %s, %s, %s)",\
     result['cid'], result['pid'], result['qty'], date)
  cursor.close()

  # empty basket after order placed.
  g.conn.execute("DELETE FROM adds_basket a WHERE a.cid = %s", cid)
  return redirect(url_for('checkout'))

# Display order history.
@app.route('/orderhistory')
def orderhistory():
  if 'cid' in session:
    cid = session.get('cid')
  order_history = []
  orderid = ''

  cursor = g.conn.execute("SELECT o.order_id order_id, p.pid pid, p.p_name pname, p.p_image url,o.cid cid ,o.amount amount, o.order_date or_date, o.status status FROM purchase o, product p WHERE o.pid = p.pid AND o.cid = %s", cid)
  for result in cursor:
    order_history.append(dict(orderid = result['order_id'], pid = result['pid'], pname = result['pname'], url = result['url'], productamount = result['amount'], orderdate = result['or_date'],  \
    orderstatus = result['status']))
  cursor.close()

  context = dict(data = order_history, cname = session['cname'])
  return render_template("orderhistory.html", **context)
  # else:
  #   error = 'You have no order history!'
  #   return render_template("orderhistory.html", error = error)

@app.route('/review', methods=['POST', 'GET'])
def review():
  if request.method == 'GET':
    pid = request.args.get('pid')
    pname = ''
    url = ''
    cursor = g.conn.execute("SELECT p.pid pid, p.p_name pname, p.p_image url FROM product p WHERE p.pid = %s", pid)
    for result in cursor:
      pname = result['pname']
      url = result['url']
    cursor.close()

    context = dict(pname = pname, url = url, pid = pid)
    return render_template("review.html", **context)
  else:
    pid = request.args.get('pid')
    currentDT = datetime.datetime.now()
    date = currentDT.strftime("%Y-%m-%d")
    g.conn.execute("""INSERT INTO review (content, rating, order_id, cid, pid, review_date) VALUES (%s, %s, %s, %s, %s, %s)""",\
    request.form['content'],request.form['rating'], request.args.get('pid'), session['cid'], pid, date)
    return redirect('orderhistory')

# Add to basket.
@app.route('/addbasket', methods=['POST'])
def addbasket():
  # insert to basket
  # g.conn.execute('INSERT INTO test (name) VALUES (%s)', name)
  pid = request.args['pid']
  cid = session['cid']
  qty = request.form['qty']

  prev_qty = None
  cursor = g.conn.execute("SELECT quantity FROM adds_basket WHERE cid = %s AND pid = %s", cid, pid)
  for result in cursor:
    prev_qty = result['quantity']
  cursor.close()

  if prev_qty == None:
    g.conn.execute("INSERT INTO adds_basket (cid, pid, quantity) VALUES (%s, %s, %s)",\
       cid, pid, str(qty))
  else:
    qty = str((int) (prev_qty) + int(qty))
    print qty
    g.conn.execute("UPDATE adds_basket SET (quantity) = (%s) WHERE cid = %s AND pid = %s",\
      str(qty), cid, pid)
  return redirect('/')

# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
  name = request.form['name']
  g.conn.execute('INSERT INTO test VALUES (NULL, ?)', name)
  return redirect('/')
    # return render_template("login.html")
    # abort(401)
    # this_is_never_executed()


# User login. Check username and pw.
@app.route('/login', methods=['POST', 'GET'])
def login():

    error = None
    if request.method == 'POST':
      email =  request.form['email']
      password = request.form['password']
      session['email'] = email
      cid = ''
      cname = ''

      result = g.conn.execute("SELECT cid, first_name, password FROM customer WHERE email = %s", email)
      flag = False
      for row in result:
          if row['password'] == password:
            cid = row['cid']
            cname = row['first_name']
            flag = True
      # check user e xist and password correct
      if flag == False:
        error = 'Invalid credentials, please enter again!'
      else:
        # password correct, enter main page
        print cname
        print cid
        session['cid'] = cid
        session['cname'] = cname

        return redirect(url_for('index', email = email))
      return render_template("login.html", error = error)
    else:
      return render_template("login.html", error = error)

@app.route('/logout')
def logout():
    # remove the username from the session if it's there
    session.pop('cid', None)
    session.pop('cname', None)
    session.pop('email', None)
    return redirect(url_for('index'))
# post product
# @app.route('/login', methods=['POST', 'GET'])

# User sign up.
@app.route('/signup', methods=['POST', 'GET'])
def signup():
  if request.method == 'GET':
    return render_template("signup.html")
  else:
    g.conn.execute("""INSERT INTO customer (first_name, last_name, gender, age, email, phone_num, password) VALUES (%s, %s, %s, %s, %s, %s, %s)""",\
     request.form['firstname'],request.form['lastname'],request.form['gender'],\
     request.form['age'],request.form['email'],request.form['phonenum'],\
     request.form['password'])
    return redirect('/')


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using:

        python server.py

    Show the help text using:

        python server.py --help

    """
    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=True, threaded=threaded)


  run()
