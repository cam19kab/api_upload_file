from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Configure the database URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@localhost/dbname'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    file_extension = db.Column(db.String(10), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False)
    date_modified = db.Column(db.DateTime, nullable=False)
    size = db.Column(db.Integer, nullable=False)

@app.route('/files', methods=['POST'])
def upload_file():
    file = request.files['file']
    filename = file.filename
    extension = os.path.splitext(filename)[1].lower()
    
    if extension not in ['.docx', '.xlsx', '.pdf', '.ppt']:
        return jsonify({'error': 'Unsupported file format'}), 400
    
    new_file = File(
        filename=filename,
        file_extension=extension,
        author=request.form.get('author'),
        date_created=datetime.now(),
        date_modified=datetime.now(),
        size=file.content_length
    )
    db.session.add(new_file)
    db.session.commit()
    
    return jsonify({'message': 'File uploaded successfully'}), 200

@app.route('/files/<int:id>', methods=['GET'])
def get_file(id):
    file = File.query.get_or_404(id)
    return send_file(file.filename, mimetype='application/octet-stream')

if __name__ == '__main__':
    app.run(debug=True)
