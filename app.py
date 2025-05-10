from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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

# Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        flash('Please login to view notes.', 'warning')
        return redirect(url_for('login'))

    query = Note.query
    search_subject = request.args.get('subject')
    file_type = request.args.get('file_type')
    category = request.args.get('category')
    sort_by = request.args.get('sort_by')

    if search_subject:
        query = query.filter(Note.subject.ilike(f"%{search_subject}%"))
    if file_type:
        query = query.filter_by(file_type=file_type)
    if category:
        query = query.filter(Note.category.ilike(f"%{category}%"))
    if sort_by == 'title_asc':
        query = query.order_by(Note.title.asc())
    elif sort_by == 'title_desc':
        query = query.order_by(Note.title.desc())
    elif sort_by == 'size_asc':
        query = query.order_by(Note.file_size.asc())
    elif sort_by == 'size_desc':
        query = query.order_by(Note.file_size.desc())
    elif sort_by == 'date_asc':
        query = query.order_by(Note.uploaded_at.asc())
    elif sort_by == 'date_desc':
        query = query.order_by(Note.uploaded_at.desc())

    notes = query.all()
    return render_template('index.html', notes=notes)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        flash('You must be logged in to upload.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        subject = request.form['subject']
        category = request.form['category']
        file = request.files['file']

        if not title or not subject or not category or not file:
            flash('All fields are required!', 'danger')
            return redirect(url_for('upload'))

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            file_size = os.path.getsize(filepath)
            file_type = filename.rsplit('.', 1)[1].lower()

            note = Note(
                title=title,
                subject=subject,
                category=category,
                filename=filename,
                file_size=file_size,
                file_type=file_type
            )
            db.session.add(note)
            db.session.commit()

            flash('File uploaded successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid file type.', 'danger')

    return render_template('upload.html')

@app.route('/uploads/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/delete/<int:note_id>', methods=['POST'])
def delete_note(note_id):
    if 'user_id' not in session:
        flash('Login required.', 'warning')
        return redirect(url_for('login'))

    note = Note.query.get_or_404(note_id)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], note.filename)

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        db.session.delete(note)
        db.session.commit()
        flash('Note deleted.', 'success')
    except Exception as e:
        flash(f'Error deleting: {e}', 'danger')

    return redirect(url_for('index'))

# Authentication
@app.route('/login', methods=['GET', 'POST'])
def login():
    username = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials.', 'danger')

    return render_template('login.html', username=username)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm']

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
        else:
            hashed = generate_password_hash(password)
            new_user = User(username=username, password=hashed)
            db.session.add(new_user)
            db.session.commit()
            flash('Registered successfully! Please log in.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

# Run
if __name__ == '__main__':
    app.run(debug=True)
