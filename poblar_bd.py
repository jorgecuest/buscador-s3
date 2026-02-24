import os
import boto3
from dotenv import load_dotenv
from datetime import datetime, timezone
from app import app, db, Documento

load_dotenv()

def populate_from_s3():
    aws_profile = os.environ.get('AWS_PROFILE_NAME')
    s3_bucket = os.environ.get('AWS_S3_BUCKET')

    print(f"Iniciando conexión a S3 para el bucket: {s3_bucket}")
    
    # Configuración de credenciales
    if aws_profile and aws_profile != 'TU_PERFIL_AWS':
        print(f"Usando el perfil de AWS: {aws_profile}")
        session = boto3.Session(profile_name=aws_profile)
    else:
        print("Usando las credenciales por defecto de tu sistema para AWS.")
        session = boto3.Session()

    s3 = session.client('s3')
    
    try:
        count = 0
        total_count = 0
        
        with app.app_context():
            db.create_all() # Garantiza que la tabla exista
            
            # Buscar el registro más reciente insertado en la BD
            ultimo_doc = db.session.query(Documento).order_by(Documento.fecha_agregado.desc()).first()
            ultima_fecha = ultimo_doc.fecha_agregado.replace(tzinfo=timezone.utc) if ultimo_doc else None

            if ultima_fecha:
                print(f"Buscando archivos en S3 subidos DESPUÉS del: {ultima_fecha.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print("La base de datos está vacía. Se buscarán TODOS los archivos del bucket.")

            # Usamos un paginador por si el bucket tiene miles de archivos
            paginator = s3.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=s3_bucket)

        count = 0
        total_count = 0
        with app.app_context():
            db.create_all() # Garantiza que la tabla exista
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        s3_key = obj['Key']
                        
                        # Extraemos solo el nombre del archivo (ignorando las carpetas previas)
                        # Ej: 'clientes/juan/poliza.pdf' -> 'poliza.pdf'
                        nombre = s3_key.split('/')[-1] if '/' in s3_key else s3_key
                        
                        # Ignorar aquellos que son solo carpetas
                        if not nombre:
                            continue
                            
                        # Si ya teníamos una fecha anterior registrada, validamos SÍ el archivo de AWS es estrictamente más nuevo
                        if ultima_fecha and 'LastModified' in obj:
                            if obj['LastModified'] <= ultima_fecha:
                                continue # Ignorar archivo porque es muy viejo y ya sabíamos que existe

                        # Verificamos si ese S3 Key ya existe (candado final por si subieron archivos al mismo tiempo)
                        existe = db.session.query(Documento).filter_by(s3_key=s3_key).first()
                        if not existe:
                            nuevo_doc = Documento(nombre=nombre, s3_key=s3_key)
                            db.session.add(nuevo_doc)
                            count += 1
                            total_count += 1
                            
                            # Hacer commit cada 500 registros para no saturar la memoria
                            # y para que los datos sean visibles en la base de datos de inmediato.
                            if count >= 500:
                                db.session.commit()
                                print(f"Lote insertado. Total procesado: {total_count} documentos...")
                                count = 0
            
            # Commit final de los restantes
            if count > 0:
                db.session.commit()
            print(f"¡Éxito! Se agregaron en total {total_count} documentos nuevos a tu base de datos PostgreSQL.")

    except Exception as e:
        print(f"Ocurrió un error leyendo el bucket de AWS o escribiendo en la BD:\n{e}")

if __name__ == '__main__':
    populate_from_s3()
