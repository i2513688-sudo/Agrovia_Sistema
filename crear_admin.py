from werkzeug.security import generate_password_hash
from db import query, execute

correo = input("Correo del administrador: ").strip()
password = input("Contraseña: ").strip()
dni = input("DNI: ").strip()
nombres = input("Nombres: ").strip()
apellido = input("Apellido paterno: ").strip()

exists = query("SELECT id_usuario FROM usuarios WHERE correo=%s OR numero_documento=%s", (correo,dni), one=True)
if exists:
    print("Ya existe un usuario con ese correo o documento.")
    raise SystemExit

uid = execute("""
INSERT INTO usuarios
(codigo_usuario,tipo_documento,numero_documento,nombres,apellido_paterno,telefono,correo,password_hash,estado,origen_registro)
VALUES (%s,'DNI',%s,%s,%s,'000000000',%s,%s,'ACTIVO','WEB')
""", ("USR-"+dni, dni, nombres, apellido, correo, generate_password_hash(password)))

execute("INSERT INTO usuarios_roles(id_usuario,id_rol,estado) VALUES(%s,2,'ACTIVO')", (uid,))
print("Administrador creado. Ya puedes iniciar sesión.")
