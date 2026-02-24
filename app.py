import boto3
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Configuración de la aplicación Flask y la base de datos PostgreSQL
app = Flask(__name__)
db_user = os.environ.get('DB_USER', 'root')
db_password = os.environ.get('DB_PASSWORD', '38Dc2783n8n')
db_host = os.environ.get('DB_HOST', '10.11.4.15')
db_port = os.environ.get('DB_PORT', '5432')
db_name = os.environ.get('DB_NAME', 'seguros')

# URI de conexión a la base de datos (prioriza DATABASE_URL si existe)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 
    f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
)
db = SQLAlchemy(app)

# Modelo que representa la tabla de documentos en la base de datos
class Documento(db.Model):
    """
    Representa un archivo almacenado en AWS S3 con su referencia en la DB.
    """
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), index=True)        # Nombre legible del archivo
    s3_key = db.Column(db.String(500), unique=True)        # Ruta única dentro del bucket de S3
    fecha_agregado = db.Column(db.DateTime, default=datetime.utcnow, index=True) # Fecha de indexación

# Ruta principal que sirve la interfaz web (Frontend)
@app.route('/')
def home():
    """Renderiza la página principal de búsqueda."""
    return render_template('index.html')

# API de búsqueda que consulta la base de datos PostgreSQL
@app.route('/api/buscar')
def buscar():
    """Busca documentos por nombre en la base de datos local."""
    q = request.args.get('q', '')
    # La búsqueda se hace en la DB (indexada) para mayor velocidad, no directamente en S3.
    resultados = db.session.query(Documento).filter(Documento.nombre.contains(q)).limit(20).all()
    return jsonify([{'id': r.id, 'nombre': r.nombre} for r in resultados])

# API para obtener una URL temporal (presignada) de AWS S3
@app.route('/api/ver/<int:doc_id>')
def ver(doc_id):
    """Genera un enlace temporal de descarga/visualización para un archivo en S3."""
    doc = db.session.get(Documento, doc_id)
    
    aws_profile = os.environ.get('AWS_PROFILE_NAME', 'TU_PERFIL_AWS')
    s3_bucket = os.environ.get('AWS_S3_BUCKET', 'app-insurance-buck')

    # Configuración de la sesión de AWS (Boto3)
    try:
        if aws_profile and aws_profile not in ['TU_PERFIL_AWS', '']:
            session = boto3.Session(profile_name=aws_profile)
        else:
            session = boto3.Session()
        s3 = session.client('s3')
    except Exception as e:
        print(f"Error configurando sesión de AWS: {e}")
        return jsonify({'error': 'Configuración de AWS inválida'}), 500
    
    # Genera la URL de acceso que expira en 600 segundos (10 minutos)
    url = s3.generate_presigned_url('get_object',
        Params={'Bucket': s3_bucket, 'Key': doc.s3_key},
        ExpiresIn=600)
    return jsonify({'url': url})

if __name__ == '__main__':
    # Asegura que la base de datos y las tablas se creen al iniciar
    with app.app_context():
        db.create_all() 
    # Inicia el servidor Flask en modo debug permitiendo conexiones externas
    app.run(host='0.0.0.0', debug=True)