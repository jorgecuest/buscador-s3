import os
import boto3
from dotenv import load_dotenv
from datetime import datetime, timezone
from app import app, db, Documento

load_dotenv()

def populate_from_s3():
    """
    Escanea el bucket de S3 e indexa los archivos nuevos en la base de datos PostgreSQL.
    Solo procesa archivos que han sido agregados o modificados después de la última
    sincronización exitosa (indexación diferencial).
    """
    aws_profile = os.environ.get('AWS_PROFILE_NAME')
    s3_bucket = os.environ.get('AWS_S3_BUCKET')

    print(f"Iniciando conexión a S3 para el bucket: {s3_bucket}")
    
    # Configuración de credenciales de AWS
    if aws_profile and aws_profile not in ['TU_PERFIL_AWS', '']:
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
            db.create_all() # Garantiza que la tabla de documentos exista
            
            # Obtiene la fecha del archivo más reciente que ya tenemos en la base de datos
            ultimo_doc = db.session.query(Documento).order_by(Documento.fecha_agregado.desc()).first()
            ultima_fecha = ultimo_doc.fecha_agregado.replace(tzinfo=timezone.utc) if ultimo_doc else None

            if ultima_fecha:
                print(f"Buscando archivos en S3 subidos DESPUÉS del: {ultima_fecha.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print("La base de datos está vacía. Se buscarán TODOS los archivos del bucket.")

            # Paginador de Boto3 para manejar buckets con gran cantidad de objetos eficientemente
            paginator = s3.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=s3_bucket)

            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        s3_key = obj['Key']
                        
                        # Extraemos el nombre del archivo (Key) ignorando la estructura de carpetas
                        nombre = s3_key.split('/')[-1] if '/' in s3_key else s3_key
                        
                        # Ignorar si es un prefijo (carpeta vacía en S3)
                        if not nombre:
                            continue
                            
                        # Lógica de Sincronización Diferencial:
                        # Si el archivo en S3 es anterior o igual a nuestra última sincronización, lo saltamos
                        if ultima_fecha and 'LastModified' in obj:
                            if obj['LastModified'] <= ultima_fecha:
                                continue 

                        # Verificamos si la ruta (Key) ya existe para evitar duplicados exactos
                        existe = db.session.query(Documento).filter_by(s3_key=s3_key).first()
                        if not existe:
                            nuevo_doc = Documento(nombre=nombre, s3_key=s3_key)
                            db.session.add(nuevo_doc)
                            count += 1
                            total_count += 1
                            
                            # Realiza un commit cada 500 registros para optimizar el rendimiento y la memoria
                            if count >= 500:
                                db.session.commit()
                                print(f"Lote insertado. Total procesado: {total_count} documentos...")
                                count = 0
            
            # Commit de los registros finales que no completaron un lote de 500
            if count > 0:
                db.session.commit()
            print(f"¡Éxito! Se agregaron en total {total_count} documentos nuevos a tu base de datos.")

    except Exception as e:
        print(f"Ocurrió un error leyendo el bucket de AWS o escribiendo en la BD:\n{e}")

if __name__ == '__main__':
    # Punto de entrada para ejecución manual o mediante tareas programadas (Crontab)
    populate_from_s3()
