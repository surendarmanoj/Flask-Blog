from crypt import methods
import email
from turtle import title
from flask import render_template,url_for, flash, redirect, request, abort
from flaskblog.forms import (RegistrationForm, LoginForm,
                                UpdateForm, PostFrom, 
                                ResetPasswordForm,ResetRequestForm)
from flaskblog.models import User, Post
from flaskblog import app, db, bcrypt
from flask_login import login_user, current_user, logout_user, login_required
import secrets
import os
from PIL import Image
import csv
import smtplib
from email.mime.text import MIMEText


@app.route("/")
def home():
    page = request.args.get('page',1,type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(per_page=5, page=page)
    return render_template('index.html', posts=posts)

@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page',1,type=int)
    user = User.query.filter_by(username=username)\
        .first_or_404()
    posts = Post.query.filter_by(author=user)\
        .order_by(Post.date_posted.desc())\
        .paginate(per_page=5, page=page)
    return render_template('user_post.html', posts=posts, user=user)


@app.route("/about")
def about():
    return render_template('about.html')

@app.route("/register", methods=['POST','GET'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user1 = User(username=form.username.data, email=form.email.data, password=hashed_pw)
        db.session.add(user1)
        db.session.commit()
        flash("Your Accouint has been created Successfully.. Now You can Login!!!","success")
        return redirect(url_for('login'))
    return render_template('register.html',title
    ="Register", form=form)


@app.route("/login", methods=['POST','GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password,form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('login unsuccessful.. Please check your Credentials','danger')
    return render_template('login.html',title
    ="Login", form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path,'static/profile_pics',picture_fn)

    op_size = (125,125)
    i = Image.open(form_picture)
    i.thumbnail(op_size)


    i.save(picture_path)
    return picture_fn

@app.route('/account', methods=['POST','GET'])
@login_required
def account():
    form = UpdateForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash("Your Deatils have been updated!!",'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file, form=form)


@app.route("/post/new", methods=['GET','POST'])
@login_required
def new_post():
    form = PostFrom()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content = form.content.data, author = current_user)
        db.session.add(post)
        db.session.commit()
        flash("Your Post has been successfully Created !!",'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title="Create Post", form=form, legend = "New Post")

@app.route("/post/csv", methods=['GET','POST'])
@login_required
def new_post_csv():
    with open('flaskblog/post.csv','r') as f:
        post_csv = csv.DictReader(f)
        for i in post_csv:
            post = Post(title=i['title'],content="static",author=current_user)
            db.session.add(post)
            db.session.commit()
            
        return "hi"

@app.route('/post/<int:post_id>')
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title,post=post )

@app.route('/post/<int:post_id>/update', methods=['GET','POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostFrom()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your Post has been Updated!!!','success')
        return redirect(url_for('post', post_id=post.id))
    form.title.data = post.title
    form.content.data = post.content
    return render_template('create_post.html', title="Update Post", form=form, legend='Update Post')

@app.route('/post/<int:post_id>/delete', methods=['POST','GET'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your Post has been Deleted!!!','success')
    return redirect(url_for('home'))

def send_reset_email(user):
    token = user.get_reset_token()
    form = ResetRequestForm()

    with open("./flaskblog/static/password.txt" , 'r') as f:
        password = f.read()
        f.close()
    
    msge1 = list({url_for("reset_token", token=token, _external=True)})
    msge = msge1[0]
    msg = MIMEText(msge)

    me = "surendarmanoj85@gmail.com"
    you = form.email.data
    msg['Subject'] = "Password Reset Email for the flask blog account"
    msg['From'] = me
    msg['To'] = you

    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login(me, password)
    s.send_message(msg)
    s.quit()


@app.route('/reset_password', methods=['POST','GET'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = ResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email = form.email.data).first()
        send_reset_email(user)
        flash('Password Reset Has been sent to Your Registered Email address.','success')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)

@app.route('/reset_password/<token>', methods=['POST','GET'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash(' This is an invalid token or it might have expired!!!','warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_pw = bcrypt.generate_password_hash(form.password.data)
        user.password = hashed_pw
        db.session.commit()
        flash('Your Password Has been reseted successfully!!!','success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)