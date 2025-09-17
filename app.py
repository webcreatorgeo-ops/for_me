import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session,jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import random
from openpyxl import Workbook
from flask import send_file
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog_users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
UPLOAD_FOLDER = 'static/carousel'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')



# DB ინიციალიზაცია

db = SQLAlchemy(app)

CAROUSEL_FOLDER = 'static/carousel'


# ========= მოდელები =========
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    zip_code = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    subtitle = db.Column(db.String(200))  # ეს აუცილებელია, რადგან შენ HTML-ით აგზავნი subtitle-ს
    description = db.Column(db.Text)
    ticket = db.Column(db.String(100))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class RestoreRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    surname = db.Column(db.String(50))
    student_class = db.Column(db.String(10))
    age = db.Column(db.Integer)
    homeroom_teacher = db.Column(db.String(100))
    subject = db.Column(db.String(100))
    subject_teacher = db.Column(db.String(100))
    confirmed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sender = db.Column(db.String(20), nullable=False)  # "user" ან "admin"
    reply = db.Column(db.Text, nullable=True)  # ადმინის პასუხი
    read_by_admin = db.Column(db.Boolean, default=False)  # ახალი ველი
    answered = db.Column(db.Boolean, default=False)  # პასუხი დადებულია თუ არა
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')


# ადმინის ავტორიზაციის დეკორატორი
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            flash("გთხოვთ გაიარეთ ავტორიზაცია", "warning")
            return redirect(url_for("login"))
        user = User.query.get(user_id)
        if not user or not user.is_admin:
            flash("თქვენ არ გაქვთ წვდომა ამ გვერდზე", "danger")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated_function

# Routes

@app.route('/admin/reply_restore/<int:reg_id>', methods=['POST'])
@admin_required
def reply_restore(reg_id):
    reply_text = request.form.get('reply_text')
    registration = RestoreRegistration.query.get_or_404(reg_id)
    registration.reply = reply_text
    db.session.commit()
    flash("კომენტარი დაემატა", "success")
    return redirect(url_for('restore_list'))

@app.route('/admin/delete_restore/<int:reg_id>', methods=['POST'])
@admin_required
def delete_restore(reg_id):
    registration = RestoreRegistration.query.get_or_404(reg_id)
    db.session.delete(registration)
    db.session.commit()
    flash("რეგისტრაცია წაიშალა", "info")
    return redirect(url_for('restore_list'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# კონფიგურაცია ერთხელ
app.config["CAROUSEL_FOLDER"] = os.path.join("static", "carousel")

@app.route("/admin/carousel", methods=["GET", "POST"])
@admin_required
def admin_carousel():
    # ფოლდერის შექმნა, თუ არ არსებობს
    os.makedirs(app.config["CAROUSEL_FOLDER"], exist_ok=True)

    if request.method == "POST":
        if "image" not in request.files:
            flash("ფაილი არ აირჩიე!", "danger")
            return redirect(request.url)

        file = request.files["image"]
        if file.filename == "":
            flash("ფაილის სახელი ცარიელია!", "danger")
            return redirect(request.url)

        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["CAROUSEL_FOLDER"], filename)
            file.save(file_path)
            flash("სურათი წარმატებით აიტვირთა!", "success")
            return redirect(url_for("admin_carousel"))

    # მხოლოდ კაროუსელის ფოლდერში არსებული სურათები
    images = os.listdir(app.config["CAROUSEL_FOLDER"])
    return render_template("admin_carousel.html", images=images)


@app.route("/admin/carousel/upload", methods=["POST"])
@admin_required
def upload_image():
    if "file" not in request.files:
        flash("ფაილი არ არის არჩეული", "danger")
        return redirect(url_for("admin_carousel"))

    file = request.files["file"]
    if file.filename == "":
        flash("ფაილის სახელი ცარიელია", "danger")
        return redirect(url_for("admin_carousel"))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config["CAROUSEL_FOLDER"], filename))
        flash("სლაიდი წარმატებით დაემატა!", "success")
    else:
        flash("ფაილის ფორმატი არასწორია!", "danger")

    return redirect(url_for("admin_carousel"))


@app.route("/admin/carousel/delete/<filename>", methods=["POST"])
@admin_required
def delete_image(filename):
    file_path = os.path.join(app.config["CAROUSEL_FOLDER"], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        flash("სურათი წაიშალა!", "success")
    else:
        flash("ფაილი ვერ მოიძებნა!", "danger")
    return redirect(url_for("admin_carousel"))


@app.route('/restore_list')
@admin_required
def restore_list():
    registrations = RestoreRegistration.query.order_by(RestoreRegistration.created_at.desc()).all()
    return render_template('restore_list.html', registrations=registrations)

@app.route('/point')
def pointt():
    return render_template('online.html',)

@app.route('/restore_registration', methods=['GET', 'POST'])
def restore_registration():
    if request.method == 'POST':
        name = request.form.get('name')
        surname = request.form.get('surname')
        student_class = request.form.get('student_class')
        age = request.form.get('age')
        homeroom_teacher = request.form.get('homeroom_teacher')
        subject = request.form.get('subject')
        subject_teacher = request.form.get('subject_teacher')
        confirmed = request.form.get('confirmed') == 'on'

        if not confirmed:
            flash("გთხოვთ დაეთანხმოთ პირობებს", "danger")
            return redirect(url_for('restore_registration'))

        registration = RestoreRegistration(
            name=name,
            surname=surname,
            student_class=student_class,
            age=age,
            homeroom_teacher=homeroom_teacher,
            subject=subject,
            subject_teacher=subject_teacher,
            confirmed=confirmed
        )
        db.session.add(registration)
        db.session.commit()

        flash("განაცხადი წარმატებით გაიგზავნა", "success")
        return redirect(url_for('home'))

    return render_template('restore_form.html')



@app.route('/')
def home():
    # პოსტები
    posts = Post.query.order_by(Post.created_at.desc()).all()

    # თუ საქაღალდე არ არსებობს, შევქმნათ
    if not os.path.exists(CAROUSEL_FOLDER):
        os.makedirs(CAROUSEL_FOLDER)

    # მხოლოდ სურათების სია
    images = [
        img for img in os.listdir(CAROUSEL_FOLDER)
        if img.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))
    ]
    global page_views
    page_views += 1  # ყოველი refresh-ზე ერთი ემატება
    return render_template("home_page.html", posts=posts, images=images,views=page_views)


@app.route('/event')
def event():
    events = Event.query.all()
    return render_template('infov.html', events=events)

@app.route('/register_pirveli')
def pirveli():
    return render_template('register_pirveli.html')

@app.route('/lesse')
def lese():
    return render_template('lesse.html')


@app.route('/event/add', methods=['GET', 'POST'])
def add_event():
    if request.method == 'POST':
        title = request.form['title']
        subtitle = request.form.get('subtitle')  # დაამატე ეს
        description = request.form['description']
        ticket = request.form['ticket']

        new_event = Event(
            title=title,
            subtitle=subtitle,
            description=description,
            ticket=ticket
        )
        db.session.add(new_event)
        db.session.commit()
        return redirect(url_for('event'))

    return render_template('add_event.html')

@app.route('/event/delete/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)  # თუ არ არსებობს, გამოიტანს 404-ს
    db.session.delete(event)
    db.session.commit()
    return redirect(url_for('event'))





@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        surname = request.form.get('surname')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        state = request.form.get('state')
        city = request.form.get('city')

        #  1. reCAPTCHA შემოწმება
        #recaptcha_response = request.form.get('g-recaptcha-response')
        #secret_key = 'შეიყვანე_შენი_secret_key_აქ'  # შეავსე შენი reCAPTCHA საიდუმლო გასაღებით
        #verify_url = 'https://www.google.com/recaptcha/api/siteverify'

       # response = requests.post(verify_url, data={
            #'secret': secret_key,
           # 'response': recaptcha_response
       # })
        #result = response.json()

        #if not result.get('success'):
           # flash('გთხოვთ დაადასტურეთ, რომ არ ხართ რობოტი.', 'danger')
           # return render_template('register form.html')

        #  2. უკვე რეგისტრირებული ელფოსტა
        if User.query.filter_by(email=email).first():
            flash("ელფოსტა უკვე რეგისტრირებულია", "danger")
            return render_template('register form.html')

        #  3. პაროლების შედარება
        if password != confirm_password:
            flash("პაროლები არ ემთხვევა", "danger")
            return render_template('register form.html')

        hashed_password = generate_password_hash(password)

        #  4. კოდის გენერაცია
        verification_code = random.randint(100001, 999999)
        print(verification_code)

        #  5. სესიაში რეგისტრაციის მონაცემები
        session['verification_code'] = verification_code
        session['registration_data'] = {
            'name': name,
            'surname': surname,
            'email': email,
            'username': email if email else f"{name}_{surname}",  # fallback
            'password_hash': hashed_password,
            'state': state,
            'city': city
        }

        #  6. ელფოსტის გაგზავნა
        subject = "ვერიფიკაციის კოდი"
        body = f"თქვენი ვერიფიკაციის კოდია: {verification_code}"
        sender_email = "shota.cholokava17@gmail.com"
        password_smtp = "vgdc lvtc iozy jwni"

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, password_smtp)
                server.sendmail(sender_email, email, msg.as_string())
            flash("ვერიფიკაციის კოდი გაიგზავნა ელფოსტაზე", "success")
            return redirect(url_for('verify1'))
        except Exception as e:
            flash(f"შეცდომა გაგზავნისას: {e}", "danger")
            return render_template('register form.html')

    return render_template('register form.html')


@app.route('/verify1')
def verify1():
    return render_template('verify.html')




@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    #Message.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    flash("მომხმარებელი წაიშალა", "info")
    return redirect(url_for('users'))




@app.route('/verify', methods=['POST'])
def verify():
    code = request.form.get('code')
    try:
        if int(code) == session.get('verification_code'):
            user_data = session.get('registration_data')
            if user_data:
                new_user = User(
                    name=user_data['name'],
                    surname=user_data['surname'],
                    email=user_data['email'],
                    password_hash=user_data['password_hash'],
                    state=user_data['state'],
                    city=user_data['city']
                )
                db.session.add(new_user)
                db.session.commit()

                session.pop('registration_data', None)
                session.pop('verification_code', None)

                flash("ვერიფიკაცია წარმატებით დასრულდა. რეგისტრაცია დასრულდა!", "success")
                return redirect(url_for('login'))
            else:
                flash("მონაცემები არ მოიძებნა", "danger")
        else:
            flash("არასწორი ვერიფიკაციის კოდი", "danger")
    except ValueError:
        flash("კოდი უნდა იყოს რიცხვი", "danger")

    return render_template('verify.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.name
            session['state'] = user.state
            session['is_admin'] = user.is_admin

            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home_page'))
        else:
            flash("არასწორი ელფოსტა ან პაროლი", "danger")
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()

        if user:
            new_password = str(random.randint(100000, 999999))
            hashed_password = generate_password_hash(new_password)
            user.password_hash = hashed_password
            db.session.commit()

            subject = "ახალი პაროლი"
            body = f"თქვენი ახალი პაროლია: {new_password}"
            sender_email = "shota.cholokava17@gmail.com"
            password_smtp = "vgdc lvtc iozy jwni"

            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            try:
                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls()
                    server.login(sender_email, password_smtp)
                    server.sendmail(sender_email, email, msg.as_string())
                flash("ახალი პაროლი გაიგზავნა ელფოსტაზე", "success")
            except Exception as e:
                flash(f"შეცდომა გაგზავნისას: {e}", "danger")
        else:
            flash("ელფოსტა არ არის რეგისტრირებული", "danger")

    return render_template('forgot.html')

@app.route('/developer')
def developer():
    return render_template('developer_page.html')

@app.route("/game")
def game():
    return render_template("game.html")


page_views = 9000

@app.route('/form1')
def home_page():
    posts = Post.query.order_by(Post.created_at.desc()).all()

    # თუ საქაღალდე არ არსებობს, შევქმნათ
    if not os.path.exists(CAROUSEL_FOLDER):
        os.makedirs(CAROUSEL_FOLDER)

    # მხოლოდ სურათების სია
    images = [
        img for img in os.listdir(CAROUSEL_FOLDER)
        if img.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))
    ]
    global page_views
    page_views += 1  # ყოველი refresh-ზე ერთი ემატება
    return render_template("home_page.html", posts=posts, images=images, views=page_views)


@app.route('/archevani')
def foa():
    return render_template('data.html')

@app.route('/saskolo')
def saskologo():
    return render_template('saskolo.html')

comments = []
comment_counter = 1
@app.route('/forum', methods=['GET', 'POST'])
def forum():
    global comment_counter

    success = False
    if request.method == 'POST':
        username = request.form['username']
        text = request.form['comment']
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        comments.append({
            'id': comment_counter,
            'username': username,
            'text': text,
            'timestamp': timestamp,
            'reply': None
        })
        comment_counter += 1
        success = True

    is_admin = session.get('is_admin', False)
    return render_template('forum.html', comments=comments, success=success, is_admin=is_admin)


@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    if not session.get('is_admin'):
        return "Unauthorized", 403
    global comments
    comments = [c for c in comments if c['id'] != comment_id]
    return redirect(url_for('forum'))


@app.route('/reply_comment/<int:comment_id>', methods=['POST'])
def reply_comment(comment_id):
    if not session.get('is_admin'):
        return "Unauthorized", 403
    reply_text = request.form.get('reply_text')
    for comment in comments:
        if comment['id'] == comment_id:
            comment['reply'] = reply_text
            break
    return redirect(url_for('forum'))


@app.route('/logout')
def logout():
    session.clear()
    flash("შედი ან დარეგისტრირდი რათა ისარგებლო ყველა ფუნქციით", "info")
    return redirect(url_for('login'))



@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user_id = session.get('user_id')
    if not user_id:
        flash("გთხოვთ გაიარეთ ავტორიზაცია", "warning")
        return redirect(url_for('login', next=request.path))

    user = User.query.get(user_id)
    if not user:
        flash("მომხმარებელი ვერ მოიძებნა", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name')
        surname = request.form.get('surname')
        state = request.form.get('state')
        city = request.form.get('city')
        zip_code = request.form.get('zip_code')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not state:
            flash("გთხოვ, აირჩიე რეგიონი", "danger")
            return redirect(url_for('profile'))

        if new_password:
            if new_password != confirm_password:
                flash("პაროლები არ ემთხვევა", "danger")
                return redirect(url_for('profile'))
            user.password_hash = generate_password_hash(new_password)

        admin_code = request.form.get('admin_code')
        if admin_code == 'mindori1232':
            session['is_admin'] = True
            user.is_admin = True
            flash("თქვენ გახდით ადმინისტრატორი!", "success")

        user.name = name
        user.surname = surname
        user.state = state
        user.city = city
        user.zip_code = zip_code

        db.session.commit()
        session['state'] = user.state

        flash("პროფილი წარმატებით განახლდა", "success")
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)


@app.route('/manage_posts', methods=['GET', 'POST'])
def manage_posts():
    if not session.get('is_admin'):
        return redirect(url_for('home'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        image = request.files.get('image')
        image_url = ''
        if image and image.filename:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)
            image_url = f"/static/uploads/{filename}"

        new_post = Post(title=title, content=content, image_url=image_url)
        db.session.add(new_post)
        db.session.commit()
        flash('პოსტი წარმატებით აიტვირთა!')
        return redirect(url_for('manage_posts'))

    return render_template('manage_posts.html')


@app.route("/post")
def post_list():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("post_list.html", posts=posts)

@app.route("/post/<int:post_id>")
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template("post_detail.html", post=post)



@app.route('/post/edit/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    if not session.get('is_admin'):
        flash("⛔ მხოლოდ ადმინს აქვს წვდომა.")
        return redirect(url_for('post_list'))

    post = Post.query.get_or_404(post_id)

    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']

        image = request.files.get('image')
        if image and image.filename:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)
            post.image_url = f"/static/uploads/{filename}"

        try:
            db.session.commit()
            flash("✅ პოსტი წარმატებით განახლდა.")
        except Exception as e:
            db.session.rollback()
            flash(f"❌ შეცდომა: {e}")

        return redirect(url_for('post_list'))

    return render_template('edit_post.html', post=post)

@app.route('/post/delete/<int:post_id>')
def delete_post(post_id):
    if not session.get('is_admin'):
        flash("⛔ მხოლოდ ადმინს აქვს წვდომა.")
        return redirect(url_for('post_list'))

    post = db.session.merge(Post.query.get_or_404(post_id))  # სწორი სესიაში დაბრუნება
    db.session.delete(post)
    db.session.commit()
    flash('🗑️ პოსტი წაიშალა.')
    return redirect(url_for('post_list'))


@app.route('/create_survey')
@admin_required
def create_survey():
    return render_template('create_survey.html')


@app.route('/admin/')
@admin_required
def admin():
    return render_template('admin_dashboard.html')

@app.route('/users', endpoint='users')
@admin_required
def users_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('users_list.html', users=users)
##################

# მომხმარებლის ჩატი
@app.route('/chat')
def chat():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for("login"))

    return render_template('chat.html', user=user)


# მესიჯის გაგზავნა (მომხმარებელი)
@app.route('/send_message', methods=['POST'])
def send_message():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "unauthorized"}), 401

    message_text = request.form.get('message')
    if message_text:
        new_message = ChatMessage(user_id=user_id, sender="user", message=message_text)
        db.session.add(new_message)
        db.session.commit()
    return jsonify({"success": True})


# მესიჯის გაგზავნა (ადმინი)
@app.route('/admin/send/<int:user_id>', methods=['POST'])
def admin_send(user_id):
    user = User.query.get_or_404(user_id)
    message_text = request.form.get('message')
    if message_text:
        new_message = ChatMessage(user_id=user.id, sender="admin", message=message_text)
        db.session.add(new_message)
        db.session.commit()
    return jsonify({"success": True})


# მესიჯების წამოღება (ორივე მხარისთვის)
@app.route('/get_messages/<int:user_id>')
def get_messages(user_id):
    messages = ChatMessage.query.filter_by(user_id=user_id).order_by(ChatMessage.created_at.asc()).all()
    data = [
        {
            "id": m.id,
            "sender": m.sender,
            "message": m.message,
            "time": m.created_at.strftime("%H:%M %d-%m")
        }
        for m in messages
    ]
    return jsonify(data)


from sqlalchemy import func, desc

@app.route('/adminchat')
def admin_dashboard():
    # ყველა მომხმარებლის ბოლო მესიჯი
    subquery = (
        db.session.query(
            ChatMessage.user_id,
            func.max(ChatMessage.created_at).label("last_time")
        )
        .group_by(ChatMessage.user_id)
        .subquery()
    )

    last_messages = (
        db.session.query(ChatMessage)
        .join(subquery, (ChatMessage.user_id == subquery.c.user_id) &
                      (ChatMessage.created_at == subquery.c.last_time))
        .order_by(desc(ChatMessage.created_at))
        .all()
    )

    # ახლა თითოეული msg შეიძლება იყოს user ან admin, შესაბამისად განვსაზღვრავთ სტილს
    return render_template("admin_ajax.html", last_messages=last_messages)



# კონკრეტული მომხმარებელთან ჩატი (ადმინი)
@app.route('/adminchat')
def admin_dashboarda():
    from sqlalchemy import func

    # მომხმარებლების ბოლო მესიჯი
    subquery = (
        db.session.query(
            ChatMessage.user_id,
            func.max(ChatMessage.created_at).label("last_time")
        ).group_by(ChatMessage.user_id).subquery()
    )

    last_messages = (
        db.session.query(ChatMessage)
        .join(subquery, (ChatMessage.user_id == subquery.c.user_id) & (ChatMessage.created_at == subquery.c.last_time))
        .order_by(ChatMessage.created_at.desc())
        .all()
    )

    return render_template("admin_ajax.html", last_messages=last_messages)


@app.route('/admin/chat/<int:user_id>')
def admin_chat(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('admin_chat.html', user=user)
############################################


@app.route('/manage_teachers', methods=['GET', 'POST'])
def manage_teachers():
    if not session.get('is_admin'):
        return redirect(url_for('teachers_list'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        image = request.files.get('image')
        image_url = ''
        if image and image.filename:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)
            # სწორად შევინახოთ ბმული, რომ HTML-ში გამოჩნდეს
            image_url = f"/static/uploads/{filename}"

        new_teacher = Teacher(title=title, content=content, image_url=image_url)
        db.session.add(new_teacher)
        db.session.commit()
        flash('👨‍🏫 მასწავლებელი წარმატებით დაემატა!')
        return redirect(url_for('manage_teachers'))

    teachers = Teacher.query.order_by(Teacher.created_at.desc()).all()
    return render_template('manage_teachers.html', teachers=teachers)

# უბრალო გვერდი მასწავლებლების სიის სანახავად
@app.route('/teachers')
def teachers_list():
    teachers = Teacher.query.order_by(Teacher.created_at.desc()).all()
    return render_template('post_teachers.html', teachers=teachers)




# ==================== ერთის ნახვა ====================
@app.route("/teachers/<int:teacher_id>")
def view_teacher(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    return render_template("teacher_view.html", teacher=teacher)


# ==================== რედაქტირება (ADMIN) ====================
@app.route('/teachers/edit/<int:teacher_id>', methods=['GET', 'POST'])
def edit_teacher(teacher_id):
    if not session.get('is_admin'):
        flash("⛔ მხოლოდ ადმინს აქვს წვდომა.")
        return redirect(url_for('teachers_list'))

    teacher = Teacher.query.get_or_404(teacher_id)

    if request.method == 'POST':
        teacher.title = request.form['title']
        teacher.content = request.form['content']

        image = request.files.get('image')
        if image and image.filename:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)
            teacher.image_url = f"/static/uploads/{filename}"

        try:
            db.session.commit()
            flash("✅ ჩანაწერი განახლდა.")
        except Exception as e:
            db.session.rollback()
            flash(f"❌ შეცდომა: {e}")

        return redirect(url_for('teachers_list'))

    return render_template('teachers_edit.html', teacher=teacher)


# ==================== წაშლა (ADMIN) ====================
@app.route('/teachers/delete/<int:teacher_id>')
def delete_teacher(teacher_id):
    if not session.get('is_admin'):
        flash("⛔ მხოლოდ ადმინს აქვს წვდომა.")
        return redirect(url_for('teachers_list'))

    teacher = db.session.merge(Teacher.query.get_or_404(teacher_id))
    db.session.delete(teacher)
    db.session.commit()
    flash('🗑️ ჩანაწერი წაიშალა.')
    return redirect(url_for('teachers_list'))

#################################################


@app.route('/download_restore')
def download_restore():
    registrations = RestoreRegistration.query.all()  # შენი მოდელი

    wb = Workbook()
    ws = wb.active
    ws.title = "Registrations"

    # სათაურები
    headers = ["სახელი", "გვარი", "კლასი", "ასაკი", "დამრიგებელი", "საგანი", "მასწავლებელი", "დადასტ.", "რეგისტრაციის დრო"]
    ws.append(headers)

    # მონაცემები
    for r in registrations:
        ws.append([
            r.name,
            r.surname,
            r.student_class,
            r.age,
            r.homeroom_teacher,
            r.subject,
            r.subject_teacher,
            "✔️" if r.confirmed else "❌",
            r.created_at.strftime("%Y-%m-%d %H:%M")
        ])

    # ფაილის შექმნა მეხსიერებაში
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(output, as_attachment=True, download_name="აღდგენაზე რეგისტრირებულები.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
######################################

@app.route('/download_user')
def download_user():
    users = User.query.all()  # შენს User მოდელს მოარგე

    # Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Users"

    # Header row
    ws.append(["სახელი", "გვარი", "ელ-ფოსტა", "რეგიონი", "ქალაქი", "ადმინი"])

    # მონაცემები
    for u in users:
        ws.append([
            u.name,
            u.surname,
            u.email,
            u.state,
            u.city,
            "✔️" if u.is_admin else "❌"
        ])

    # ჩაწერა მეხსიერებაში (ფაილში ჩაწერის გარეშე)
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="მომხმარებლები.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

##############################################

@app.route('/post/search', methods=['GET', 'POST'])
def search_posts():
    query = request.form.get('search', '').strip()  # ძებნის ტექსტი
    if query:
        posts = Post.query.filter(
            (Post.title.ilike(f"%{query}%")) |
            (Post.content.ilike(f"%{query}%"))
        ).order_by(Post.created_at.desc()).all()
    else:
        posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('post_list.html', posts=posts, search_query=query)



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)

