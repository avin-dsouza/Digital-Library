from flask import Flask, render_template, request, redirect, send_from_directory, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)

# Config
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  # Needed for flash messages
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create uploads folder if not exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Init DB
db = SQLAlchemy(app)

# Model
class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    subject = db.Column(db.String(100))
    category = db.Column(db.String(100))
    filename = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(10))

# Create DB tables
with app.app_context():
    db.create_all()

# Check allowed file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Home page
@app.route('/')
def index():
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

# Upload page
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        title = request.form['title']
        subject = request.form['subject']
        category = request.form['category']
        file = request.files['file']

        if not title or not subject or not category:
            flash('All fields are required!', 'danger')
            return redirect('/upload')

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            file_size = os.path.getsize(filepath)
            file_type = filename.rsplit('.', 1)[1].lower()

            new_note = Note(
                title=title,
                subject=subject,
                category=category,
                filename=filename,
                file_size=file_size,
                file_type=file_type
            )
            db.session.add(new_note)
            db.session.commit()

            flash('File successfully uploaded!', 'success')
            return redirect('/')

        else:
            flash('File type not allowed. Only PDF, DOCX, PPT, JPG/PNG allowed.', 'danger')
            return redirect('/upload')

    return render_template('upload.html')

# Download
@app.route('/uploads/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Delete
@app.route('/delete/<int:note_id>', methods=['POST'])
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], note.filename)

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        
        db.session.delete(note)
        db.session.commit()
        flash('Note deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting file: {e}', 'danger')

    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
