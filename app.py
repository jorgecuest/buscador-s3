import boto3
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
db_user = os.environ.get('DB_USER', 'root')
db_password = os.environ.get('DB_PASSWORD', '38Dc2783n8n')
db_host = os.environ.get('DB_HOST', '10.11.4.15')
db_port = os.environ.get('DB_PORT', '5432')
db_name = os.environ.get('DB_NAME', 'seguros')

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 
    f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
)
db = SQLAlchemy(app)

# Modelo de la DB
class Documento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), index=True)
    s3_key = db.Column(db.String(500), unique=True)
    fecha_agregado = db.Column(db.DateTime, default=datetime.utcnow, index=True)

# Ruta principal
@app.route('/')
def home():
    return render_template('index.html')

# API de búsqueda en la DB
@app.route('/api/buscar')
def buscar():
    q = request.args.get('q', '')
    # Busca en la DB, no en S3. Por eso es veloz.
    resultados = Documento.query.filter(Documento.nombre.contains(q)).limit(20).all()
    return jsonify([{'id': r.id, 'nombre': r.nombre} for r in resultados])

# API para generar el enlace de S3
@app.route('/api/ver/<int:doc_id>')
def ver(doc_id):
    doc = db.session.get(Documento, doc_id)
    aws_profile = os.environ.get('AWS_PROFILE_NAME', 'TU_PERFIL_AWS')
    s3_bucket = os.environ.get('AWS_S3_BUCKET', 'app-insurance-buck')
    
    # Intenta usar el perfil, si está vacío o no configurado usa las credenciales por defecto de AWS
    if aws_profile and aws_profile != 'TU_PERFIL_AWS':
        session = boto3.Session(profile_name=aws_profile)
    else:
        session = boto3.Session()
        
    s3 = session.client('s3')
    
    url = s3.generate_presigned_url('get_object',
        Params={'Bucket': s3_bucket, 'Key': doc.s3_key},
        ExpiresIn=600)
    return jsonify({'url': url})

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Crea el archivo seguros.db automáticamente
    app.run(host='0.0.0.0', debug=True)