import os
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, Enum
from azure.storage.blob import BlobServiceClient
from werkzeug.utils import secure_filename

# Flask and SQLAlchemy Configuration
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@localhost/documentdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = '/path/to/temp/uploads'
db = SQLAlchemy(app)

# Enum for Upload Status
class UploadStatus(str, Enum):
    UPLOADED = 'uploaded'
    TRANSFER = 'transfer'
    PROCESSED = 'processed'

# Metadata Model
class DocumentMetadata(db.Model):
    __tablename__ = 'document_metadata'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    author = Column(String)
    type_file = Column(String, nullable=False)
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_modification = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(Enum(UploadStatus), default=UploadStatus.UPLOADED)
    file_path = Column(String)
    blob_url = Column(String)

# Azure Blob Storage Configuration
AZURE_STORAGE_CONNECTION_STRING = 'your_azure_storage_connection_string'
AZURE_CONTAINER_NAME = 'documents'

def get_blob_service_client():
    return BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

def extract_file_metadata(file):
    """
    Extract metadata from uploaded file
    """
    return {
        'name': secure_filename(file.filename),
        'type_file': file.mimetype,
        'author': request.form.get('author', 'Unknown')
    }

@app.route('/upload', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Extract Metadata
    metadata = extract_file_metadata(file)
    
    # Save file locally
    filename = secure_filename(file.filename)
    local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(local_path)

    # Create DB Entry
    doc_metadata = DocumentMetadata(
        name=metadata['name'],
        author=metadata['author'],
        type_file=metadata['type_file'],
        file_path=local_path,
        status=UploadStatus.UPLOADED
    )
    
    try:
        db.session.add(doc_metadata)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

    return jsonify({
        'message': 'File uploaded successfully',
        'document_id': doc_metadata.id
    }), 201

@app.route('/transfer/<int:document_id>', methods=['POST'])
def transfer_to_blob_storage(document_id):
    # Retrieve document metadata
    doc = DocumentMetadata.query.get_or_404(document_id)
    
    if doc.status != UploadStatus.UPLOADED:
        return jsonify({'error': 'Invalid document status'}), 400

    try:
        # Upload to Azure Blob Storage
        blob_service_client = get_blob_service_client()
        container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)
        
        blob_name = f"{uuid.uuid4()}_{doc.name}"
        blob_client = container_client.upload_blob(
            os.path.join(doc.file_path), 
            blob_name
        )

        # Update metadata
        doc.status = UploadStatus.TRANSFER
        doc.blob_url = blob_client.url
        db.session.commit()

        return jsonify({
            'message': 'File transferred to blob storage',
            'blob_url': doc.blob_url
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/process/<int:document_id>', methods=['POST'])
def process_document(document_id):
    # Retrieve document metadata
    doc = DocumentMetadata.query.get_or_404(document_id)
    
    if doc.status != UploadStatus.TRANSFER:
        return jsonify({'error': 'Invalid document status'}), 400

    try:
        # Mark as processed (in a real scenario, you'd add processing logic)
        doc.status = UploadStatus.PROCESSED
        db.session.commit()

        return jsonify({
            'message': 'Document processed successfully',
            'document_id': doc.id
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Initialize DB
@app.before_first_request
def create_tables():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)

# Requirements (requirements.txt):
# flask
# flask-sqlalchemy
# psycopg2-binary
# azure-storage-blob
# werkzeug