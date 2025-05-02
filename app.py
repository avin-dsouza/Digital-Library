from flask import Flask, render_template, request, redirect, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

# Config
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    category = db.Column(db.String(100))  # <-- new field
    filename = db.Column(db.String(100))

# Create DB tables
with app.app_context():
    db.create_all()

# Check allowed file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Home page
@app.route('/')
def index():
    notes = Note.query.all()
    return render_template('index.html', notes=notes)

# Upload page
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        title = request.form['title']
        subject = request.form['subject']
        category = request.form['category']
        file = request.files['file']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Save to database
            new_note = Note(title=title, subject=subject, category=category, filename=filename)
            db.session.add(new_note)
            db.session.commit()

            return redirect('/')
        else:
            return "File type not allowed. Only PDF, DOCX, PPT, JPG/PNG allowed.", 400

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

    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(note)
    db.session.commit()

    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
