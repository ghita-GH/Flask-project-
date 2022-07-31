from email import message
from urllib import response
from flask import Flask,render_template, request, jsonify
from chat import get_response
from distutils.log import debug
from flask import Flask, render_template, request, redirect, url_for, session,flash, abort
from functools import wraps
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
from werkzeug.utils import secure_filename
import os
import random
import string,codecs
from flask import *
import json
import csv
import pandas as pd



app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png','.gif','.txt', '.pdf', '.jpeg']
app.config['up_ex']=['.jpg', '.png','.gif','.PNG', '.JPG', '.jpeg']
app.config['UPLOAD_PATH'] = 'static/uploads'
app.config['FILE_UPLOADS']=['.csv']

app.secret_key = 'secret123'


app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'my_db'
app.config['MYSQL_CURSORCLASS']='DictCursor'

# Intialize MySQL
mysql = MySQL(app)

@app.route('/') 
def index_get():
    cur = mysql.connection.cursor()
    cur.execute('select * from annonces where type="0"')
    data = cur.fetchall()
    cur.close()
    
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute('select * from filiere where NAME !="All"')
    filiere = cur.fetchall()
    cur.close()
    
    cur2 = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur2.execute('select * from events')
    events = cur2.fetchall()
    cur2.close()

    return render_template('base.html', annonces = data,filiere=filiere, events=events)
    
@app.route("/index")
def test2():
       return render_template('index.html')

@app.route("/aboutUs")
def aboutUs():
       return render_template('aboutUs.html')

@app.post("/predict")
def predict():
    text= request.get_json().get("message")
    response=get_response(text)
    message={"answer": response}
    return jsonify(message)

@app.route("/login", methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM personne WHERE email = %s AND password = %s', (email, password,))
        account = cursor.fetchone()
        if account and account['is_admin']==True:
            session['logged_in']=True
            session['username']=account['username']
            session['data']=account
            return redirect('Home_admin')
        elif account and account['is_etu']:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            session['data']=account

            id_pe=session['data']['id']
            cur2 = mysql.connection.cursor()
            cur2.execute("select id_fil from etudiant where id_personne=%s",(id_pe,))
            us = cur2.fetchone()
            cur2.close()
            d = mysql.connection.cursor()
            d.execute("select * from annonces a join filiere f where a.id_fil=f.id and (a.id_fil=%s  or a.id_fil='3')",(us['id_fil'],))
            dd = d.fetchall()
            d.close()

            cur2 = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cur2.execute('select * from events')
            events = cur2.fetchall()
            cur2.close()

            cur3 = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cur3.execute('select * from filiere')
            dep = cur3.fetchall()
            cur3.close()
            
            return render_template('Etudiant/home.html', annonces=dd, events=events, filiere=dep)
        elif account and account['is_ens']:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            session['data']=account
            d = mysql.connection.cursor()
            d.execute("select * from annonces a join filiere b join enseignant c join personne d join appartients e where a.id_fil=b.id and c.id_personne=d.id and c.id=e.id_ens and b.id=e.id_fil and d.id=%s ",(session['id'],))
            annonc = d.fetchall()
            d.close()
            cur2 = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cur2.execute('select * from events')
            events = cur2.fetchall()
            cur2.close()
            cur3 = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cur3.execute('select * from filiere')
            dep = cur3.fetchall()
            cur3.close()
            return render_template('Enseignant/home.html',f=annonc, events=events, filiere=dep)
    return render_template('login.html')

def is_logged_in(f):
	@wraps(f)
	def wrap(*args,**kwargs):
		if 'logged_in' in session:
			return f(*args,**kwargs)
		else:
			flash('Unauthorized, Please Login','danger')
			return redirect(url_for('login'))
	return wrap

@app.route("/infoFiliere/<string:abr>", methods=['GET'])
def infoFiliere(abr):
    
    cur2 = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur2.execute('select * from personne p join enseignant e join appartients a  join filiere f where p.id=e.id_personne and e.id=a.id_ens and a.id_fil=f.id and f.id=%s',(abr,))
    enseignant = cur2.fetchall()

    cur3 = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur3.execute('select * from filiere where filiere.id=%s',(abr,))
    dep = cur3.fetchall()
    cur3.close()

    return render_template('infoFiliere.html',ens=enseignant,filiere=dep)

#---------------------------------------------------------------------------------------------
@app.route("/Home_admin",methods=['POST','GET'])
@is_logged_in
def Home_admin():
    cur = mysql.connection.cursor()
    cur.execute("select * from annonces")
    data = cur.fetchall()
    cur.close()
    return render_template("admin/Home.html",Home=data)

#-------------------------------------gestion annonces admin----------------------------------------------- 
@app.route("/annonces_admin",methods=['POST','GET'])
@is_logged_in
def annonces_admin():
    cur = mysql.connection.cursor()
    cur.execute('select * from annonces a join filiere f where a.id_fil=f.id')
    data = cur.fetchall()
    cur.execute('select * from filiere')
    data1 = cur.fetchall()
    cur.close()
    if request.method == 'POST':
        titre = request.form['titre']
        description =  request.form['description']
        id_fil= request.form['departement']
        if id_fil == '7' or id_fil=='':
            options=0
            id_fil='7'
        else:
            options=1

        uploaded_file = request.files['file']
        filename = secure_filename(uploaded_file.filename)
        if uploaded_file.filename != '':
            file_ext = os.path.splitext(filename)[1]
            if file_ext not in app.config['UPLOAD_EXTENSIONS']:
                abort(400)
            uploaded_file.save(os.path.join(app.config['UPLOAD_PATH'], filename))
            the_file_name=uploaded_file.filename
        else:
            the_file_name=''
            file_ext=''

            
        ann = mysql.connection.cursor()
        ann.execute("INSERT INTO annonces (`titre`, `description`, `file`,`ext`, `type`, `id_fil`) VALUES (%s,%s,%s,%s,%s,%s)", (titre, description, uploaded_file.filename,file_ext,options,id_fil))
        mysql.connection.commit()


        return redirect(url_for('annonces_admin'))
    else :
        return render_template('admin/annonce/home.html', annonces = data, filiere=data1)



@app.route('/delete_annonce/<string:id_data>', methods = ['GET'])
def delete_annonce(id_data):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM annonces WHERE id=%s", (id_data,))
    mysql.connection.commit()
    return redirect(url_for('annonces_admin'))


@app.route('/edite_annonce/<string:id>', methods = ['POST', 'GET'])
def edite_annonce(id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM annonces a join filiere f where a.id_fil=f.id and a.id = %s', (id))
    data = cur.fetchone()
    cur.execute('select * from filiere')
    data1 = cur.fetchall()

    cur.close()
    if request.method == 'POST':

        titre = request.form['titre']
        description = request.form['description']
        id_fil= request.form['departement']
        print(id_fil)
        if id_fil == 'All':
            options=0
        else:
            options=1
        if request.files['file'] !='':
            uploaded_file = request.files['file']
            filename = secure_filename(uploaded_file.filename)
            if filename != '':
                file_ext = os.path.splitext(filename)[1]
                if file_ext not in app.config['UPLOAD_EXTENSIONS']:
                    abort(400)
                uploaded_file.save(os.path.join(app.config['UPLOAD_PATH'], filename))
        
        else :
            uploaded_file=data['file']
            file_ext=data['ext']

        cur = mysql.connection.cursor()
        cur.execute("UPDATE annonces SET titre = %s,description = %s, file = %s, ext=%s , type = %s, id_fil=%s  WHERE id = %s", (titre, description, uploaded_file.filename,file_ext,options,id_fil, id))
        flash('Contact Updated Successfully')
        mysql.connection.commit()
        return redirect(url_for('edite_annonce',id=id))

    return render_template('admin/annonce/update_annonce.html', contact = data, filiere=data1)

#-------------------------------------gestion etudiant admin-----------------------------------------------



@app.route("/etu_admin",methods=['POST','GET'])
@is_logged_in
def etu_admin():
    cur = mysql.connection.cursor()
    cur.execute('select * from personne p join etudiant e where p.id=e.id_personne')
    data = cur.fetchall()
    cur.execute('select * from filiere where NAME !="All" ')
    data1 = cur.fetchall()
    cur.close()
    if request.method == 'POST':
        nom = request.form['nom']
        prenom =  request.form['prenom']
        cne= request.form['cne']
        cni= request.form['cni']
        departement= request.form['departement']
        email=request.form['email']

        letters = string.ascii_lowercase
        password = ''.join(random.choice(letters) for i in range(10))

        username=nom+"."+prenom+"-"+"ETU"

        ann = mysql.connection.cursor()
        ann.execute("INSERT INTO personne ( `nom`, `prenom`, `username`,`cni`, `email`,`password`, `is_admin`, `is_etu`,`is_ens`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", (nom, prenom, username, cni,email,password,"0","1","0"))
        mysql.connection.commit()

        cur2 = mysql.connection.cursor()
        cur2.execute('select id from personne where email=%s and password=%s',(email,password))
        ident = cur2.fetchone()
        cur2.close()

        ann1 = mysql.connection.cursor()
        ann1.execute("INSERT INTO etudiant ( `id_personne`, `cne`, `id_fil`) VALUES (%s,%s,%s)", (ident['id'], cne, departement))
        mysql.connection.commit()
        
        return redirect(url_for('etu_admin'))
    return render_template('admin/etudiant/home.html', etu = data,filiere=data1)


@app.route('/parseCSV', methods = ['POST'])
def parseCSV():
    uploaded_file = request.files['file']
    if uploaded_file.filename != '':
           file_path = os.path.join(app.config['UPLOAD_PATH'], uploaded_file.filename)
           uploaded_file.save(file_path)
           col_names = ['row']
           csvData = pd.read_csv(file_path,names=col_names, header=None)
           for i,row in csvData.iterrows():
                s=re.split(';',row['row'])

                letters = string.ascii_lowercase
                password = ''.join(random.choice(letters) for i in range(10))
                username=s[0]+"."+s[1]+"-"+"ETU"

                ann = mysql.connection.cursor()
                ann.execute("INSERT INTO personne ( `nom`, `prenom`, `username`,`cni`, `email`,`password`, `is_admin`, `is_etu`,`is_ens`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", (s[0], s[1], username, s[2],s[3],password,"0","1","0"))
                mysql.connection.commit()

                cur2 = mysql.connection.cursor()
                cur2.execute('select id from personne where email=%s and password=%s',(s[3],password))
                ident = cur2.fetchone()
                cur2.close()

                ann1 = mysql.connection.cursor()
                ann1.execute("INSERT INTO etudiant ( `id_personne`, `cne`, `id_fil`) VALUES (%s,%s,%s)", (ident['id'], s[4], s[5]))
                mysql.connection.commit()
    return redirect(url_for('etu_admin'))

@app.route('/delete_etu/<string:id>', methods = ['GET'])
def delete_etu(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM personne WHERE id=%s", (id,))
    cur.execute("DELETE FROM etudiant WHERE id_personne=%s", (id,))
    mysql.connection.commit()
    return redirect(url_for('etu_admin'))


@app.route('/edite_etu/<string:id>', methods = ['POST', 'GET'])
def edite_etu(id):
    cur = mysql.connection.cursor()
    cur.execute('select * from personne p join etudiant e where p.id=e.id_personne and p.id = %s', (id,))
    data = cur.fetchone()
    cur.execute('select * from filiere where NAME !="All" ')
    data1 = cur.fetchall()
    cur.close()
    if request.method == 'POST':
        nom = request.form['nom']
        prenom =  request.form['prenom']
        cne= request.form['cne']
        cni= request.form['cni']
        departement= request.form['departement']
        email=request.form['email']
        password=data['password']
        username=nom+"."+prenom+"-"+"ETU"
        cur = mysql.connection.cursor()
        cur.execute("UPDATE personne SET nom = %s, prenom=%s,username = %s,cni=%s, email = %s, password=%s, is_admin=%s, is_etu=%s , is_ens=%s  WHERE id = %s", (nom, prenom, username, cni,email,password,"0","1","0", id))
        cur.execute("update etudiant set id_personne=%s, cne=%s, id_fil=%s  WHERE id_personne = %s", (id, cne, departement, id))
        flash('Contact Updated Successfully')
        mysql.connection.commit()
        return redirect(url_for('etu_admin'))
    return render_template('admin/etudiant/update_etudiant.html', contact = data,filiere=data1)

#-------------------------------------gestion enseignant admin-----------------------------------------------


@app.route("/ens_admin",methods=['POST','GET'])
@is_logged_in
def ens_admin():
    cur = mysql.connection.cursor()
    cur.execute('select * from personne p join enseignant e where p.id=e.id_personne')
    data = cur.fetchall()
    cur.execute('select * from filiere where NAME !="All" ')
    data1 = cur.fetchall()
    cur.close()

    if request.method == 'POST':
        nom = request.form['nom']
        prenom =  request.form['prenom']
        cni= request.form['cni']
        email=request.form['email']
        letters = string.ascii_lowercase
        password = ''.join(random.choice(letters) for i in range(10))
        username=nom+"."+prenom+"-"+"ENS"
        
        uploaded_file = request.files['iamge']
        filename = secure_filename(uploaded_file.filename)
        if uploaded_file.filename != '':
            file_ext = os.path.splitext(filename)[1]
            if file_ext not in app.config['UPLOAD_EXTENSIONS']:
                abort(400)
            uploaded_file.save(os.path.join(app.config['UPLOAD_PATH'], filename))
            the_file_name=uploaded_file.filename
        else:
            the_file_name='annonyme.jpg'

        fili=request.form['res']
        l=fili.split(",")

        ann = mysql.connection.cursor()
        ann.execute("INSERT INTO personne ( `nom`, `prenom`, `username`,`cni`, `email`,`password`, `is_admin`, `is_etu`,`is_ens`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", (nom, prenom, username, cni,email,password,"0","0","1"))
        mysql.connection.commit()

        cur2 = mysql.connection.cursor()
        cur2.execute('select id from personne where email=%s and password=%s',(email,password))
        ident = cur2.fetchone()
        cur2.close()

        ann1 = mysql.connection.cursor()
        ann1.execute("INSERT INTO enseignant ( `id_personne`,`image`) VALUES (%s,%s)", (ident['id'],the_file_name,))
        mysql.connection.commit()

        cur3 = mysql.connection.cursor()
        cur3.execute('select id from enseignant where id_personne=%s',(ident['id'],))
        ide = cur3.fetchone()
        cur3.close()


        ann2 = mysql.connection.cursor()
        for x in l:
            if x!='':
                ann2.execute("INSERT INTO appartients (`id_ens`, `id_fil`) VALUES (%s,%s)", (ide['id'],x))
        mysql.connection.commit()     
        ann2.close()

        return redirect(url_for('ens_admin'))
    return render_template('admin/enseignant/home.html', etu = data,filiere=data1)


@app.route('/edite_ens/<string:id>', methods = ['POST', 'GET'])
def edite_ens(id):
    cur = mysql.connection.cursor()
    cur.execute('select * from personne p join enseignant e where p.id=e.id_personne and p.id = %s', (id,))
    data = cur.fetchone()

    cur.execute('select * from filiere where NAME !="All" ')
    data1 = cur.fetchall()


    cur.execute('select * from filiere f join appartients a where a.id_fil=f.id and a.id_ens = %s', (data["e.id"],))
    affecta=cur.fetchall()
    cur.close()

    if request.method == 'POST':
        id_e=request.form['id']
        nom = request.form['nom']
        prenom =  request.form['prenom']
        cni= request.form['cni']
        email=request.form['email']
        username=nom+"."+prenom+"-"+"ENS"
        uploaded_file = request.files['iamge']
        old=request.form['old_image']
        filename = secure_filename(uploaded_file.filename)
        if uploaded_file.filename != '':
            file_ext = os.path.splitext(filename)[1]
            if file_ext not in app.config['UPLOAD_EXTENSIONS']:
                abort(400)
            uploaded_file.save(os.path.join(app.config['UPLOAD_PATH'], filename))
            the_file_name=uploaded_file.filename
        else:
            the_file_name=old
        cur = mysql.connection.cursor()
        cur.execute("UPDATE personne SET nom = %s, prenom=%s,username = %s,cni=%s, email = %s, is_admin=%s, is_etu=%s , is_ens=%s  WHERE id = %s", (nom, prenom, username, cni,email,"0","0","1", id))
        flash('Contact Updated Successfully')
        cur.execute("UPDATE enseignant set image=%s where id_personne=%s",(the_file_name,id,))
        mysql.connection.commit()

        return redirect(url_for('edite_ens',id=id_e))
    return render_template('admin/enseignant/update_ens.html', contact = data,filiere=data1,affecta=affecta)

@app.route('/mod_aff', methods = ['POST'])
def mod_aff():
    id_p=request.form['id']
    cur = mysql.connection.cursor()
    cur.execute('select e.id from enseignant e join personne p where p.id=e.id_personne and p.id = %s', (id_p,))
    data = cur.fetchone()
    cur.close()
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM appartients WHERE id_ens=%s", (data['id'],))
    mysql.connection.commit()
    print(data)

    fil=request.form['result']
    print(fil.split(','))

    for i in fil.split(','):
        if i != '':
            cur = mysql.connection.cursor()
            cur.execute("insert into appartients (`id_ens`, `id_fil`) VALUES (%s,%s)",(data['id'],i,))
            mysql.connection.commit()

    return redirect(url_for('edite_ens',id=id_p))

@app.route('/delete_ens/<string:id_data>', methods = ['GET'])
def delete_ens(id_data):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM personne WHERE id=%s", (id_data,))
    mysql.connection.commit()
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM enseignant WHERE id_personne=%s", (id_data,))
    mysql.connection.commit()
    return redirect(url_for('ens_admin'))
#-------------------------------------gestion filiere admin-----------------------------------------------
@app.route("/fil_admin",methods=['POST','GET'])
@is_logged_in
def fil_admin():
    cur = mysql.connection.cursor()
    cur.execute('select * from filiere where NAME !="All" ')
    data1 = cur.fetchall()
    cur.close()
    if request.method == 'POST':
        NAME = request.form['NAME']
        abreviation =  request.form['abreviation']
        description= request.form['description']

        ann = mysql.connection.cursor()
        ann.execute("INSERT INTO filiere ( `NAME`, `abreviation`, `description`) VALUES (%s,%s,%s)", (NAME, abreviation, description))
        mysql.connection.commit()

        return redirect(url_for('fil_admin'))
    return render_template('admin/filiere/home.html',filiere=data1)


@app.route('/delete_fil/<string:id_data>', methods = ['GET'])
def delete_fil(id_data):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM filiere WHERE id=%s", (id_data,))
    mysql.connection.commit()
    return redirect(url_for('fil_admin'))

@app.route('/edite_fil/<string:id>', methods = ['POST', 'GET'])
def edite_fil(id):
    cur = mysql.connection.cursor()
    cur.execute('select * from filiere where id=%s',(id))
    data = cur.fetchone()
    cur.close()
    if request.method == 'POST':
        NAME = request.form['NAME']
        abreviation =  request.form['abreviation']
        description= request.form['description']
        cur = mysql.connection.cursor()
        cur.execute("UPDATE filiere SET NAME = %s, abreviation=%s,description = %s WHERE id = %s", (NAME, abreviation, description,id))
        flash('Contact Updated Successfully')
        mysql.connection.commit()
        return redirect(url_for('fil_admin'))
    return render_template('admin/filiere/update.html', contact = data)


#-------------------------------------SIMPLE ETUDIANT---------------------------------------------- 
@app.route("/etudiant",methods=['GET'])
@is_logged_in
def etudiant():
    id_pe=session['data']['id']
    cur2 = mysql.connection.cursor()
    cur2.execute("select id_fil from etudiant where id_personne=%s",(id_pe,))
    data = cur2.fetchone()
    cur2.close()
    print(data)
    return render_template('Etudiant/home.html', annonces = data)

#--------------------------------------GESTION EVENT -------------------------------------------------
@app.route("/ev_admin",methods=['POST','GET'])
@is_logged_in
def ev_admin():
    cur = mysql.connection.cursor()
    cur.execute('select * from events ')
    data = cur.fetchall()
    cur.close()
    if request.method == 'POST':
        nom = request.form['nom']
        heur =  request.form['heure']
        date= request.form['date']
        uploaded_file = request.files['file']
        filename = secure_filename(uploaded_file.filename)
        if filename != '':
            file_ext = os.path.splitext(filename)[1]
            if file_ext not in app.config['up_ex']:
                abort(400)
            uploaded_file.save(os.path.join(app.config['UPLOAD_PATH'], filename))

        ann = mysql.connection.cursor()
        ann.execute("INSERT INTO events ( `nom`, `date`, `heure`, `image`) VALUES (%s,%s,%s,%s)", (nom, date,heur, uploaded_file.filename))
        mysql.connection.commit()

        return redirect(url_for('ev_admin'))
    else :
        return render_template('admin/events/home.html', events = data)




@app.route('/delete_ev/<string:id_data>', methods = ['GET'])
def delete_ev(id_data):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM events WHERE id=%s", (id_data,))
    mysql.connection.commit()
    return redirect(url_for('ev_admin'))


@app.route('/edite_ev/<string:id>', methods = ['POST', 'GET'])
def edite_ev(id):
    cur = mysql.connection.cursor()
    cur.execute('select * from events where id=%s',(id,))
    data = cur.fetchone()
    cur.close()
    if request.method == 'POST':
        id=request.form['id']
        nom = request.form['nom']
        heur =  request.form['heure']
        date= request.form['date']
        uploaded_file = request.files['file']
        filename = secure_filename(uploaded_file.filename)
        if filename != '':
            file_ext = os.path.splitext(filename)[1]
            if file_ext not in app.config['up_ex']:
                abort(400)
            uploaded_file.save(os.path.join(app.config['UPLOAD_PATH'], filename))
        cur = mysql.connection.cursor()
        cur.execute("UPDATE events SET nom = %s, date=%s,heure = %s,image=%s WHERE id = %s", (nom, date,heur, uploaded_file.filename,id))
        mysql.connection.commit()
        return redirect(url_for('ev_admin',id=id))
    return render_template('admin/events/update.html', contact = data)






#------------------------------------------------logout-----------------------------------------------
@app.route("/logout")
def logout():
	session.clear()
	flash('You are now logged out','success')
	return redirect(url_for('login'))


if __name__=='__main__':
    app.secret_key='aya'
    app.run(debug=True)


