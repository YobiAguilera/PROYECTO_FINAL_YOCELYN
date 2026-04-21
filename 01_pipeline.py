import sqlite3
import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime
import random
import os
import time

# Rango de fechas del negocio
FECHA_INICIO = datetime(2025, 12, 1)
FECHA_FIN    = datetime(2026, 4, 30)

print("Iniciando Pipeline de Datos..")
start_time = time.time()

# Configuración
DB_NAME = "novatech.db"
NUM_SUCURSALES = 8
NUM_EMPLEADOS = 100
NUM_PRODUCTOS = 50
NUM_CLIENTES = 500
NUM_VENTAS = 15000
NUM_GASTOS = 3000

fake = Faker('es_MX')
Faker.seed(42)
np.random.seed(42)
random.seed(42)

# PRIMERA PARTE: EXTRACCION Y GENERACIÓN DE DATOS (ficticios)
print("\nGenerando datos sintéticos...")

#Sucursales
ciudades = ["Ciudad de México", "Monterrey", "Guadalajara", "Culiacán", "Tijuana", "Puebla", "Querétaro", "Mérida"]
sucursales = pd.DataFrame({
    'id': range(1, NUM_SUCURSALES + 1),
    'nombre': [f"NovaTech {c}" for c in ciudades],
    'ciudad': ciudades,
    'estado': ["CDMX", "Nuevo León", "Jalisco", "Sinaloa", "Baja California", "Puebla", "Querétaro", "Yucatán"],
    'region': ["Centro", "Norte", "Occidente", "Norte", "Norte", "Centro", "Centro", "Sur"]
})

#empleados
puestos = ["Vendedor", "Gerente", "Cajero", "Almacenista", "Soporte Técnico"]
prob_puestos = [0.5, 0.1, 0.15, 0.15, 0.1]
empleados = pd.DataFrame({
    'id': range(1, NUM_EMPLEADOS + 1),
    'nombre': [fake.name() for _ in range(NUM_EMPLEADOS)],
    'puesto': np.random.choice(puestos, NUM_EMPLEADOS, p=prob_puestos),
    'sucursal_id': np.random.randint(1, NUM_SUCURSALES + 1, NUM_EMPLEADOS),
    'fecha_ingreso': [fake.date_between(start_date='-5y', end_date=FECHA_FIN).isoformat() for _ in range(NUM_EMPLEADOS)],
    'salario': np.random.normal(15000, 3000, NUM_EMPLEADOS).round(2)
})
#Salarios de gerentes (ajuste, ganan el doble)
empleados.loc[empleados['puesto'] == 'Gerente', 'salario'] *= 2

#Productos
categorias = ["Laptops", "Smartphones", "Periféricos", "Monitores", "Redes", "Almacenamiento"]
productos = pd.DataFrame({
    'id': range(1, NUM_PRODUCTOS + 1),
    'nombre': [f"{fake.word().capitalize()} {fake.word().capitalize()} {random.choice(['Pro', 'Max', 'Lite', 'Plus', ''])}" for _ in range(NUM_PRODUCTOS)],
    'categoria': np.random.choice(categorias, NUM_PRODUCTOS),
    'costo': np.random.uniform(500, 15000, NUM_PRODUCTOS).round(2)
})
# Margen de ganancia
productos['precio_unitario'] = (productos['costo'] * np.random.uniform(1.3, 1.8, NUM_PRODUCTOS)).round(2)

#Clientes
clientes = pd.DataFrame({
    'id': range(1, NUM_CLIENTES + 1),
    'nombre': [fake.company() if random.random() > 0.7 else fake.name() for _ in range(NUM_CLIENTES)],
    'email': [fake.email() for _ in range(NUM_CLIENTES)],
    'ciudad': [fake.city() for _ in range(NUM_CLIENTES)],
    'tipo_cliente': np.random.choice(['Menudeo', 'Mayoreo'], NUM_CLIENTES, p=[0.8, 0.2])
})

#Ventas
fechas_ventas = [fake.date_time_between(start_date=FECHA_INICIO, end_date=FECHA_FIN) for _ in range(NUM_VENTAS)]
fechas_ventas.sort() # orden cronologico

empleados_vendedores = empleados[empleados['puesto'] == 'Vendedor']['id'].tolist()
productos_lista = productos['id'].tolist()
clientes_lista = clientes['id'].tolist()

ventas = pd.DataFrame({
    'id': range(1, NUM_VENTAS + 1),
    'fecha': [dt.strftime('%Y-%m-%d %H:%M:%S') for dt in fechas_ventas],
    'producto_id': np.random.choice(productos_lista, NUM_VENTAS),
    'empleado_id': np.random.choice(empleados_vendedores, NUM_VENTAS),
    'cliente_id': np.random.choice(clientes_lista, NUM_VENTAS),
    'cantidad': np.random.choice([1, 2, 3, 5, 10], NUM_VENTAS, p=[0.6, 0.2, 0.1, 0.05, 0.05]),
    'tipo_pago': np.random.choice(['Tarjeta', 'Efectivo', 'Transferencia'], NUM_VENTAS, p=[0.6, 0.2, 0.2])
})

# Vincular sucursal del empleado a la venta
sucursales_empleados = empleados.set_index('id')['sucursal_id'].to_dict()
ventas['sucursal_id'] = ventas['empleado_id'].map(sucursales_empleados)

# Calcular totales
precios_productos = productos.set_index('id')['precio_unitario'].to_dict()
ventas['precio_unitario'] = ventas['producto_id'].map(precios_productos)

# Descuentos para ventas al por mayor (tipo de cliente con 15% de dcto)
tipos_clientes = clientes.set_index('id')['tipo_cliente'].to_dict()
ventas['tipo_cliente'] = ventas['cliente_id'].map(tipos_clientes)
ventas['descuento'] = np.where(ventas['tipo_cliente'] == 'Mayoreo', 0.15, 0.0)

ventas['total'] = (ventas['cantidad'] * ventas['precio_unitario'] * (1 - ventas['descuento'])).round(2)
ventas = ventas.drop(columns=['precio_unitario', 'tipo_cliente', 'descuento'])

#Cobranza (en relación a ventas)
# Asumimos que el 80% está pagado al 100%, 15% tiene pagos parciales, 5% no ha pagado
estados_cobranza = np.random.choice(['Pagado', 'Parcial', 'Pendiente'], NUM_VENTAS, p=[0.8, 0.15, 0.05])
montos_pagados = []
saldos = []

for i, estado in enumerate(estados_cobranza):
    total_venta = ventas.iloc[i]['total']
    if estado == 'Pagado':
        montos_pagados.append(total_venta)
        saldos.append(0.0)
    elif estado == 'Parcial':
        pagado = round(total_venta * random.uniform(0.1, 0.9), 2)
        montos_pagados.append(pagado)
        saldos.append(round(total_venta - pagado, 2))
    else:
        montos_pagados.append(0.0)
        saldos.append(total_venta)

cobranza = pd.DataFrame({
    'id': range(1, NUM_VENTAS + 1),
    'venta_id': ventas['id'],
    'fecha_ultimo_pago': ventas['fecha'], 
    'monto_pagado': montos_pagados,
    'saldo_pendiente': saldos,
    'estatus': estados_cobranza
})

#Gastos
categorias_gastos = ["Servicios", "Nómina", "Mantenimiento", "Papelería", "Marketing", "Logística"]
gastos = pd.DataFrame({
    'id': range(1, NUM_GASTOS + 1),
    'fecha': [fake.date_time_between(start_date=FECHA_INICIO, end_date=FECHA_FIN).strftime('%Y-%m-%d') for _ in range(NUM_GASTOS)],
    'sucursal_id': np.random.randint(1, NUM_SUCURSALES + 1, NUM_GASTOS),
    'categoria': np.random.choice(categorias_gastos, NUM_GASTOS),
    'monto': np.random.uniform(500, 20000, NUM_GASTOS).round(2),
    'descripcion': [fake.sentence() for _ in range(NUM_GASTOS)]
})

#Inventario
#se cruzan todas las sucursales con todos los productos
inventario_data = []
inv_id = 1
for suc_id in range(1, NUM_SUCURSALES + 1):
    for prod_id in range(1, NUM_PRODUCTOS + 1):
        inventario_data.append({
            'id': inv_id,
            'sucursal_id': suc_id,
            'producto_id': prod_id,
            'stock': random.randint(0, 100),
            'fecha_actualizacion': fake.date_time_between(start_date=datetime(2026, 4, 20), end_date=FECHA_FIN).strftime('%Y-%m-%d %H:%M:%S')
        })
        inv_id += 1
inventario = pd.DataFrame(inventario_data)


# PARTES 2 Y 3: ETL Y CARGA EN SQLITE 
print("Transformando y cargando en SQLite...")
if os.path.exists(DB_NAME):
    os.remove(DB_NAME)

conn = sqlite3.connect(DB_NAME)

# Guardar dataFrames a SQLite
sucursales.to_sql('sucursales', conn, index=False)
empleados.to_sql('empleados', conn, index=False)
productos.to_sql('productos', conn, index=False)
clientes.to_sql('clientes', conn, index=False)
ventas.to_sql('ventas', conn, index=False)
cobranza.to_sql('cobranza', conn, index=False)
gastos.to_sql('gastos', conn, index=False)
inventario.to_sql('inventario', conn, index=False)

# para mejorar el rendimiento de las consultas creamos indices
cursor = conn.cursor()
cursor.execute("CREATE INDEX idx_ventas_fecha ON ventas(fecha)")
cursor.execute("CREATE INDEX idx_ventas_sucursal ON ventas(sucursal_id)")
cursor.execute("CREATE INDEX idx_ventas_producto ON ventas(producto_id)")
cursor.execute("CREATE INDEX idx_cobranza_estatus ON cobranza(estatus)")
conn.commit()

# Verificaciones
tablas = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
print(f"\n Pipeline completado exitosamente en {time.time() - start_time:.2f} segundos.")
print("Tablas creadas y registros insertados:")
for t in tablas:
    tabla = t[0]
    count = cursor.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
    print(f"  - {tabla}: {count:,} registros")

conn.close()
print(f"\n Base de datos guardada como: {DB_NAME}")
