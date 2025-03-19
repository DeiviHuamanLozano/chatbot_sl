from config import *
from sqlalchemy import create_engine, Engine, text
import urllib
from datetime import datetime, timedelta
import pandas as pd
import json
import openai

def start_engine_azure() -> Engine:
    conn_str = f'Driver={MSSQL_DRIVER};Server=tcp:{MSSQL_SERVER},1433;Database={MSSQL_DATABASE};Uid={MSSQL_USER};Pwd={MSSQL_PASSWORD};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'
    conn_str = conn_str.replace('"', "")
    # print(conn_str)
    params = urllib.parse.quote_plus(conn_str)
    conn_str = 'mssql+pyodbc:///?odbc_connect={}'.format(params)
    return create_engine(conn_str)


def retrieve_today_earliest_alert():
    # Calculate yesterday's date
    today = datetime.now() - pd.Timedelta(days=7)
    formatted_date = today.strftime('%Y-%m-%d')
    print(formatted_date)
    # Set up database connection
    engine = start_engine_azure()
    with engine.connect() as conn:
        # Define SQL query using parameterized input for dates
        query = text("""
            SELECT TOP 1 * 
            FROM [prod].[tb_slis_alerta] as a
            INNER JOIN [prod].[tb_slis_alerta_detalle] as r ON a.id_alerta = r.id_alerta
            INNER JOIN [prod].[tp_slis_audio_transcripcion] as t ON t.id_concatenacion = a.id_concatenacion
            INNER JOIN [prod].[tb_slis_empresa_actividad_economica_source] as eae ON eae.id_source = t.id_source
            INNER JOIN [prod].[tb_slis_empresa] as e ON e.id_company = eae.id_company
            WHERE a.alert_date > :date AND a.is_sent_to_tag = 1 AND a.is_checked != 1
            ORDER BY a.[alert_date]
        """)
        # Execute the query with a parameter
        df = pd.read_sql(query, conn, params={'date': formatted_date})

    return df


def retrieve_count_earliest_alert(day_inicial):
    # day_datetime = datetime.strptime(day_inicial, "%Y-%m-%d")
    #day_final_datetime = datetime.strptime(day_final, "%Y-%m-%d")
    #next_day = day_final_datetime + timedelta(days=1)
    #WHERE [alert_date] = '{day_datetime.strftime("%Y-%m-%d")}
    engine = start_engine_azure()
    with engine.connect() as conn:
        #today = datetime.now().date() - pd.Timedelta(days=1)
    
        query = f"""
        SELECT [alert_date]
        FROM [prod].[tb_slis_alerta]
        AND [is_sent_to_tag] = 0 
        AND [is_checked] != 1
        ORDER BY [id_alerta] DESC
        """
        
        query = """
        SELECT *
        FROM [prod].[tb_slis_alerta]
            WHERE [alert_date] = :alert_date
        AND is_relevant = 1
        AND [is_checked] != 1
        ORDER BY [id_alerta] DESC
        """
        
        #result = pd.read_sql(query, conn)
        df = pd.read_sql_query(query, engine, params={'alert_date': day_inicial})
    return len(df)

#retrieve_count_earliest_alert('2025-02-18')

def retrieve_count_especific_day(day):
    day_datetime = datetime.strptime(day, "%Y-%m-%d")
    next_day = day_datetime + timedelta(days=1)
    engine = start_engine_azure()
    with engine.connect() as conn:
        query = f"""
        SELECT [alert_date]
        FROM [prod].[tb_slis_alert]
        WHERE [alert_date] >= '{day_datetime.strftime("%Y-%m-%d")}'
        AND [alert_date] < '{next_day.strftime("%Y-%m-%d")}'
        AND [is_sent_to_tag] = 1
        AND [is_checked] != 1
        """
        result = pd.read_sql(query, conn)
    
    return len(result)


def update_alert_values(alert_id, update_dict):
    update_dict = json.loads(update_dict)
    
    engine = start_engine_azure()
    
    tp_value = 0 if update_dict.get("classification") == "falso positivo" else 1
    
    nivel_riesgo = update_dict.get("risk_level")
    if isinstance(nivel_riesgo, str):
        nivel_riesgo = f"{nivel_riesgo}"  

    checked = 1  
    
    query = text("""
        UPDATE [prod].[tb_slis_alerta]
        SET is_sent = :tp_value,
            is_relevant = :tp_value,
            risk_level = :nivel_riesgo, 
            is_checked = :checked
        WHERE id_alerta = :alert_id
    """)
    
    with engine.connect() as conn:
        conn.execute(query, {
            'tp_value': tp_value,
            'nivel_riesgo': nivel_riesgo,
            'checked': checked,
            'alert_id': alert_id
        })
        conn.commit()
        print(f"Alerta con ID {alert_id} actualizada correctamente.")
#dict = {'classification':'falso positivo','risk_level':'bajo'}
#import json
#'{"classification":"falso positivo","risk_level":"bajo"}'
#update_alert_values(166, '{"classification":"falso positivo","risk_level":"bajo"}')
def get_source_alias(source_id: int):
    engine = start_engine_azure()

    with engine.connect() as conn:
        df = pd.read_sql(f"SELECT TOP 1 * FROM [prod].[tb_slis_source] WHERE [id_source] = {source_id}", conn)
        assert len(df) == 1, "Source error, there are more than one source with the same id"

    row_dict = df.iloc[0].to_dict()

    return row_dict['original_name']


def get_clients_from_topic(tema: str) -> list:
    query_clientes = (
        f"SELECT * FROM [prod].[tb_clients] "
        f"WHERE [tema] = '{tema}' OR [tema] = 'all' AND [status] = 1"
    )
    (
        f'''
        SELECT *
        FROM [prod].[tb_slis_cliente] AS c
        INNER JOIN [prod].[tb_slis_empresa] AS e ON c.id_company = e.id_company
        WHERE e.status = 1 AND c.status = 1 AND e.name = 'AGAP';

        '''
    )
    
    with start_engine_azure().begin() as conn:
        df_clientes = pd.read_sql(query_clientes, conn)
    
    print(f"CLIENTES ENCONTRADOS PARA EL TEMA {tema}: {df_clientes['nombre'].to_list()}")

    return df_clientes["telefono"].tolist()

def get_clientes_aa():
    query = (
        """
        select phone_number
        from [prod].[tb_slis_cliente]
        where id_company = 1 and status = 1
        """
    )
    with start_engine_azure().begin() as conn:
        df_clientes_aa = pd.read_sql(query,conn)
    
    return df_clientes_aa["phone_number"].tolist()

def get_clientes_alerta(id_source_alerta):
    query = (
        f"""
        SELECT c.phone_number
        FROM [prod].[tb_slis_empresa_actividad_economica_source] as ae
        INNER JOIN [prod].tb_slis_cliente AS c ON c.id_company = ae.id_company
        where ae.id_source = {id_source_alerta} AND c.status = 1
        """
    )
    with start_engine_azure().begin() as conn:
        df_clientes_aa = pd.read_sql(query,conn)
    
    return df_clientes_aa["phone_number"].tolist()

def search_keyword_alert(keyword):
    query = (
        f"""
        SELECT TOP 5 *, COUNT(*) OVER() AS Total_Alerts
        FROM [prod].[tb_slis_alerta] AS a
        INNER JOIN [prod].[tb_slis_alerta_detalle] AS d ON a.id_alerta = d.id_alerta
        WHERE d.gpt_summary LIKE '%{keyword}%' 
        ORDER BY a.is_relevant DESC
        """
    )
    with start_engine_azure().begin() as conn:
        df_alertas = pd.read_sql(query, conn)
    
    # Genera el reporte usando ChatGPT
    report = generate_report_with_openai(df_alertas, keyword)
    return report

def generate_report_with_openai(df, keyword):
    message_body = (
        f"Genera un reporte sobre las 5 primeras alertas relacionadas con la palabra clave '{keyword}'. "
        f"En total, hay {df.iloc[0]['Total_Alerts']} alertas relacionadas con este término. "
        "Los detalles de las primeras 5 alertas son los siguientes:"
    )
    # Aquí añades una descripción detallada de cada alerta si es necesario
    for index, row in df.iterrows():
        message_body += f"\nAlerta {index + 1}: {row['gpt_summary']} - Riesgo: {row['risk_level']}"

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "Por favor, detalla el siguiente informe de alertas."},
                  {"role": "user", "content": message_body}]
    )
    return response.choices[0].message.content

#search_keyword_alert('agua')