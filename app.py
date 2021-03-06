"""Flask Login Example"""
import os
import json
from flask import Flask, url_for, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import backref, relationship


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)

class User(db.Model):
	""" Create user table"""

	__tablename__ = 'User'
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(80), unique=True)
	password = db.Column(db.String(80))
	is_superuser = db.Column(db.Boolean, default=False)
	
	user_course_role = db.relationship('UserCourseRole', cascade='all,delete-orphan')

	def __init__(self, username, password):
		self.username = username
		self.password = password

	def set_superuser(self, is_superuser):
		self.is_superuser = is_superuser


class Role(db.Model):
	__tablename__ = 'Role'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(255), nullable=False)

	def __init__(self, name):
		self.name = name


class UserCourseRole(db.Model):
	__tablename__ = 'UserCourseRole'
	id = db.Column(db.Integer, primary_key=True)
	u_id = db.Column(db.Integer, db.ForeignKey('User.id'), nullable=False)
	c_id = db.Column(db.Integer, db.ForeignKey('Course.id'), nullable=True)
	r_id = db.Column(db.Integer, db.ForeignKey('Role.id'), nullable=False)
	__table_args__ = (UniqueConstraint('u_id', 'c_id', name='_uid_cid_uc'),)

	def __init__(self, u_id, c_id, r_id):
		self.u_id = u_id
		self.c_id = c_id
		self.r_id = r_id


class Course(db.Model):
	__tablename__ = 'Course'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(255))	

	def __init__(self, name):
		self.name = name


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def initial_db():
	''' 
		create default superuser
		default role : teacher, TA, student 
	'''
	# create default superuser : (username=a, passwd=a)
	data = User.query.filter_by(username='a').first()
	if data is None:
		usr_passwd = generate_password_hash('a')
		default_admin = User(username='a', password=usr_passwd)
		default_admin.set_superuser(True)
		db.session.add(default_admin)
		db.session.commit()


	data = Role.query.filter_by(name='Teacher').first()
	if data is  None:
		teacher = Role(name='Teacher')
		db.session.add(teacher)
		db.session.commit()
	
	data = Role.query.filter_by(name='TA').first()
	if data is None:
		TA = Role(name='TA')
		db.session.add(TA)
		db.session.commit()

	data = Role.query.filter_by(name='Student').first()	
	if data is None:
		student = Role(name='Student')
		db.session.add(student)
		db.session.commit()

	return


def get_user_course_role_list(c_id, r_id):
	result = db.session.query(User.id, User.username)\
					.select_from(UserCourseRole).join(User)\
					.filter(UserCourseRole.c_id==c_id, 
							UserCourseRole.r_id==r_id)\
					.all()

	return result


def get_role_list():
	role_list = db.session.query(Role.id, Role.name).all()	
	role_list = sorted(role_list, key=lambda role: role[0])
	print(role_list)
	print(type(role_list))
	return role_list


def row2dict(row):
	"""Convert query object by sqlalchemy to dictionary object."""
	if not row:
		return None

	d = {}
	for column in row.__table__.columns:
		d[column.name] = getattr(row, column.name)
	return d


@app.route('/', methods=['GET', 'POST'])
def home():
	""" Session control"""
	if session.get('logged_in'):
		return redirect(url_for('hello', username=session['logged_in']))
	else:
		return render_template('index.html')


@app.route('/hello')
@app.route('/hello/<username>')
def hello(username=None):
	if session.get('logged_in') != username:
		return redirect(url_for('home'))
	else:
		return render_template('index.html', username=username)


@app.route('/login/', methods=['GET', 'POST'])
def login():
	"""Login Form"""
	if request.method == 'GET':
		if session.get('logged_in'):
			return redirect(url_for('hello', username=session['logged_in']))
		else:
			return render_template('login.html')
	else:
		name = request.form['username']
		passwd = request.form['password']
		data = User.query.filter_by(username=name).first()
		if data is None:
			return 'User does not exist'

		true_user = check_password_hash(data.password, passwd)
		if true_user:
			session['logged_in'] = name
			return redirect(url_for('hello', username=name))
		else:
			return 'wrong password'


@app.route('/register/', methods=['GET', 'POST'])
def register():
	"""Register Form"""
	if request.method == 'POST':
		name = request.form['username']
		if not name:
			# check if string is empty
			return 'username is empty'

		data = User.query.filter_by(username=name).first()
		if data is not None:
			return 'User exists!'

		usr_passwd = generate_password_hash(request.form['password'])
		new_user = User(username=name, password=usr_passwd)
		db.session.add(new_user)
		db.session.commit()
		#return render_template('login.html')
		return render_template('index.html')

	#return render_template('register.html')
	return render_template('index.html')

@app.route("/logout")
def logout():
	"""Logout Form"""
	if 'logged_in' in session:
		del session['logged_in']

	return redirect(url_for('home'))


@app.route('/user_admin')
def user_admin():
	if not session.get('logged_in'):
		return 'You need to login first'
	
	username = session.get('logged_in')
	user = db.session.query(User).filter_by(username=username).first()
	if user is None:
		return 'something wrong...'

	if not user.is_superuser :
		return 'Permission Deny'

	people = db.session.query(User.id, User.username, User.is_superuser).all() 
	print('people {}'.format(people))

	return render_template('user_admin.html', people = people )


@app.route('/delete_user', methods=['POST'])
def delete_user():
	#TODO check if user is default admin

	u_id = int(request.form['u_id'])	
	if u_id == 1 :
		raise InvalidUsage('Cannot delete default admin', status_code=403)


	user = User.query.filter_by(id=u_id).first()
	print(user.username)
	
	if session['logged_in'] == user.username:
		print('user delete ownself')
		#TODO return http status code 400 Bad Request
		raise InvalidUsage('user delete ownself', status_code=403)


	db.session.delete(user)
	db.session.commit()

	return 'ok'


@app.route('/add_user', methods=['POST'])
def add_user():
	name = request.form['username']
	#check if username exist
	data = User.query.filter_by(username=name).first()
	if data is not None:
		return 'user name exist'

	tmp_passwd = os.urandom(24)	
	usr_passwd = generate_password_hash(tmp_passwd)
	new_user = User(username=name, password=usr_passwd)
	db.session.add(new_user)
	db.session.commit()

	return redirect(url_for('user_admin'))


@app.route('/set_permission', methods=['POST'])
def set_permission():

	u_id = int(request.form['u_id'])
	if u_id ==1:
		raise InvalidUsage('cannot change default admin permission', status_code=403)

	data = User.query.filter_by(id=u_id).first()	
	if data.username == session['logged_in']:
		raise InvalidUsage('cannot change ownself permission', status_code=403)


	print('permission  {}'.format(request.form['permission']))

	if request.form['permission'] == 'Administrator':
		is_superuser = True
	else:
		is_superuser = False


	print('data.id', data.id)
	print('data.name', data.username)
	print('data.is_superuser', data.is_superuser)
	if data.is_superuser == is_superuser:
		print('no effect')
	else:
		data.set_superuser(is_superuser)
		print('data.is_superuser  {}'.format(data.is_superuser))
		db.session.commit()
		print('set superuser')

	#return redirect(url_for('user_admin'))
	return 'ok'


@app.route('/get_user_info', methods=['GET', 'POST'])
def get_user_info():

	return 'ok'


@app.route('/user_info/')
@app.route('/user_info/<u_name>')
def user_info(u_name=None):
	if not session.get('logged_in'):
		return 'You need to login first'

	if u_name is None:
		return 'username is None'

	data = db.session.query(User).filter_by(username=u_name).first()
	if data is None:
		return 'user does not exist'

	print('u_id',data.id)
	u_id = data.id

	course_role_list = db.session.query(
						UserCourseRole.c_id, 
						UserCourseRole.r_id
						).filter_by(u_id=u_id).all()

	print('course_role_list  [(c_id, r_id)]', course_role_list)
	'''
	result = db.session.query(User.id, User.username)\
					.select_from(UserCourseRole).join(User)\
					.filter(UserCourseRole.c_id==c_id, 
							UserCourseRole.r_id==r_id)\
					.all()
	'''
	'''
	result = db.session.query(Course.name)\
				.select_from(UserCourseRole).join(Course)\
				.filter(UserCourseRole.c_id==Course.id,
						UserCourseRole.u_id==u_id
						)\
				.all()
	'''
	result = db.session.query(Course.id, Course.name, Role.name)\
				.select_from(UserCourseRole).join(Course)\
				.filter(UserCourseRole.c_id==Course.id,
						UserCourseRole.u_id==u_id,
						UserCourseRole.r_id==Role.id
						)\
				.all()

	print('result',result)


	return render_template('user_info.html', course_role_list=result)	


@app.route('/course_admin/')
@app.route('/course_admin/<view>')
def course_admin(view=None):
	if not session.get('logged_in'):
		return 'You need to login first'

	course_list = []
	data = db.session.query(User).filter_by(username=session['logged_in']).first()
	u_id = data.id
	permission = data.is_superuser
	
	if not permission:
		view = 'User'

	if view in (None, 'Administrator'):
		view='Administrator'
		course_list = db.session.query(Course.id, Course.name).all()	
		course_list = sorted(course_list, key=lambda course: course[0])
		print(course_list)

	elif view == 'User':

		course_list = db.session.query(Course.id, Course.name, Role.name)\
					.select_from(UserCourseRole).join(Course)\
					.filter(UserCourseRole.c_id==Course.id,
							UserCourseRole.u_id==u_id,
							UserCourseRole.r_id==Role.id
							)\
					.all()



	print(course_list)
	print('view', view)


	return render_template('course_admin.html', course_list=course_list, view=view, permission=permission)


@app.route('/add_course', methods=['POST'])
def add_course():
	name = request.form['course_name']
	#check if course name exist
	
	data = Course.query.filter_by(name=name).first()
	if data is not None:
		return 'course name exist'
	
	new_course = Course(name=name)
	db.session.add(new_course)
	db.session.commit()
	print('new course id: {}'.format(new_course.id))
	print('json.dumps: {}'.format(
		json.dumps({'c_id': new_course.id})
	))

	return json.dumps({'c_id': new_course.id})


@app.route('/rename_course', methods=['POST'])
def rename_course():
	c_id = int(request.form['c_id'])
	instance = Course.query.filter_by(id=c_id).first()
	

	return


@app.route('/delete_course', methods=['POST'])
def delete_course():
	c_id = int(request.form['c_id'])	
	instance = Course.query.filter_by(id=c_id).first()
	print('delete course: {}'.format(instance.name))

	db.session.delete(instance)
	db.session.commit()

	return 'ok'


@app.route('/course_info/', methods=['GET'])
@app.route('/course_info/<c_id>', methods=['GET'])
def course_info(c_id=None):
	if not session.get('logged_in'):
		return 'You need to login first'
	
	if c_id is None:
		return	'Please select course'

	data = Course.query.filter_by(id = c_id).first()
	print('/course_info')
	print('course id {}  name {}'.format(data.id, data.name))
	c_name = data.name

	# teacher	r_id = 1
	# TA		r_id = 2
	# student	r_id = 3
	teacher_list = get_user_course_role_list(c_id, 1)
	TA_list = get_user_course_role_list(c_id, 2)
	student_list = get_user_course_role_list(c_id, 3)
	print('teacher_list',teacher_list)
	# print(type(teacher_list))
	print('TA_list', TA_list)
	print('student_list', student_list)

	return render_template('course_info.html',
							c_name=c_name,
							c_id=c_id,
							teacher_list=teacher_list,
							TA_list=TA_list,
							student_list=student_list
							)


@app.route('/remove_user_from_course', methods=['POST'])
def remove_user_from_course():
	
	u_id = request.form['u_id']
	c_id = request.form['c_id']
	print('u_id', u_id)
	print('c_id', c_id)

	data = db.session.query(UserCourseRole).filter(UserCourseRole.u_id==u_id, UserCourseRole.c_id==c_id).first()
	print(type(data))
	
	if data is not None:
		db.session.delete(data)
		db.session.commit()
	
	return 'ok'


@app.route('/set_role', methods=['POST'])
def set_role():
	'''set UserCourseRole'''

	u_name = request.form['username']
	r_id = int(request.form['r_id'])
	c_id = int(request.form['c_id'])

	data = User.query.filter_by(username=u_name).first()
	if data is None:
		return 'no such user'
	else:
		u_id = data.id
	
	print('u_id',u_id)
	print('c_id',c_id)
	print('r_id',r_id)

	print('UserCourseRole')
	print('(c_id, u_id, r_id)')
	print(db.session.query(UserCourseRole.c_id, UserCourseRole.u_id, UserCourseRole.r_id).all())

	data = db.session.query(UserCourseRole)\
			.filter(UserCourseRole.u_id==u_id, UserCourseRole.c_id==c_id).first()


	if not data:
		print('( u_id, c_id )  record does not exist yet')
		instance = UserCourseRole(u_id=u_id, c_id=c_id, r_id=r_id)
		db.session.add(instance)
		db.session.commit()
	else:
		print('data.u_id', data.u_id)
		print('data.c_id', data.c_id)
		print('data.r_id', data.r_id, type(data.r_id))
		print('r_id',r_id, type(r_id))
		print('( u_id, c_id ) record already exist! Need to modify record')
		if data.r_id != r_id:
			data.r_id = r_id
			db.session.commit()		
		else:
			print('(u_id, c_id, r_id) record already exist! No need to modify')

	return 'ok'


@app.route('/role_admin')
def role_admin():
	if not session.get('logged_in'):
		return 'You need to login first'

	role_list = get_role_list()
	return render_template('role_admin.html', role_list=role_list)


@app.route('/add_role', methods=['POST'])
def add_role():
	name = request.form['role_name']
	#check if role name exist
	
	data = Role.query.filter_by(name=name).first()
	if data is not None:
		return 'role name exist'

	new_role = Role(name=name)
	db.session.add(new_role)
	db.session.commit()
	print('new role id: {}'.format(new_role.id))
	print('json.dumps: {}'.format(
		json.dumps({'r_id': new_role.id})
	))

	return json.dumps({'r_id': new_role.id})



@app.route('/delete_role', methods=['POST'])
def delete_role():
	r_id = int(request.form['r_id'])	
	
	if r_id==1 or r_id==2 or r_id==3 :
		#TODO : set http status code 
		return 'cannot delete default role'
	

	instance = Role.query.filter_by(id=r_id).first()
	print('delete role: {}'.format(instance.name))

	db.session.delete(instance)
	db.session.commit()

	return 'ok'


@app.route('/test')
def test():

	tmp = 'haha'
	tmp2 = 'banana'

	return render_template('test.html', tmp=tmp, tmp2=tmp2)


@app.after_request
def add_header(r):
	"""
	Add headers to both force latest IE rendering engine or Chrome Frame,
	and also to cache the rendered page for 10 minutes.
	"""
	# clear browser cache
	r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
	r.headers["Pragma"] = "no-cache"
	r.headers["Expires"] = "0"
	r.headers['Cache-Control'] = 'public, max-age=0'
	return r


app.secret_key = os.urandom(24)

if __name__ == '__main__':
	app.debug = True
	db.create_all()
	initial_db()
	# set default role : teacher, TA, student
	# create default superuser : a 
	app.secret_key = "123"
	app.run(host='127.0.0.1')
	

