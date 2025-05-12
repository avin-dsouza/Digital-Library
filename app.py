from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png'}

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(10))

with app.app_context():
    db.create_all()

# Helpers
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required():
    return 'user_id' in session

# Routes
@app.route('/')
def index():
    if not login_required():
        return redirect(url_for('login'))

    query = Note.query

    # Filters
    subject = request.args.get('subject')
    file_type = request.args.get('file_type')
    category = request.args.get('category')
    sort_by = request.args.get('sort_by')

    if subject:
        query = query.filter(Note.subject.ilike(f"%{subject}%"))
    if file_type:
        query = query.filter_by(file_type=file_type)
    if category:
        query = query.filter(Note.category.ilike(f"%{category}%"))

    # Sorting
    sort_options = {
        'title_asc': Note.title.asc(),
        'title_desc': Note.title.desc(),
        'size_asc': Note.file_size.asc(),
        'size_desc': Note.file_size.desc(),
        'date_asc': Note.uploaded_at.asc(),
        'date_desc': Note.uploaded_at.desc()
    }
    if sort_by in sort_options:
        query = query.order_by(sort_options[sort_by])

    notes = query.all()
    return render_template('index.html', notes=notes)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if not login_required():
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        subject = request.form['subject']
        category = request.form['category']
        file = request.files['file']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)

            note = Note(
                title=title,
                subject=subject,
                category=category,
                filename=filename,
                file_size=os.path.getsize(path),
                file_type=filename.rsplit('.', 1)[1].lower()
            )
            db.session.add(note)
            db.session.commit()
            return redirect(url_for('index'))

    return render_template('upload.html')

@app.route('/uploads/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/delete/<int:note_id>', methods=['POST'])
def delete_note(note_id):
    if not login_required():
        return redirect(url_for('login'))

    note = Note.query.get_or_404(note_id)
    path = os.path.join(app.config['UPLOAD_FOLDER'], note.filename)

    if os.path.exists(path):
        os.remove(path)

    db.session.delete(note)
    db.session.commit()
    return redirect(url_for('index'))

# Auth Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
        return redirect(url_for('login'))  # Silent fail

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if User.query.filter_by(username=request.form['username']).first():
            return redirect(url_for('register'))  # Username exists

        user = User(
            username=request.form['username'],
            password=generate_password_hash(request.form['password'])
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
