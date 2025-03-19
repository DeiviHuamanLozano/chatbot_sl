from db import start_engine_azure
import pandas as pd
engine = start_engine_azure()


#query_tb_slis_alerta = """
#        SELECT *
#        FROM prod.tb_slis_alerta
#        ORDER BY alert_date DESC;
#        """
#tb_slis_alerta = pd.read_sql_query(query_tb_slis_alerta, engine)

#query_tb_slis_alerta_detalle = """
#        SELECT *
#        FROM prod.tb_slis_alerta_detalle
#        """
#tb_slis_alerta_detalle = pd.read_sql_query(query_tb_slis_alerta_detalle, engine)  


##### CREACION DE DICCIONARIO #####
"""
tb_slis_alerta.columns.tolist()

diccionario_columnas_1 = {}

for col in tb_slis_alerta.columns:
    diccionario_columnas_1[col] = ''

diccionario_columnas_2 = {}

for col in tb_slis_alerta_detalle.columns:
    diccionario_columnas_2[col] = ''

print(diccionario_columnas_1)
"""
#dict_alerta = {
#    "id_alerta": "Columna: id_alerta. Descripción: Identificador de la alerta",
#    "alert_text": "Columna: alert_text. Descripción: Transcripción de la alerta",
#    "alert_date": "Columna: alert_date. Descripción: Fecha y hora de alerta",
#    "alert_path": "Columna: alert_path. Descripción: Ruta de la grabación de la alerta en GCP",
#    "is_relevant": "Columna: is_relevant. Descripción: Es etiquetado como alerta verdadera",
#    "risk_level": "Columna: risk_level. Descripción: Nivel de riesgo (bajo, medio y alto)",
#    "is_sent_to_tag": "Columna: is_sent_to_tag. Descripción: Alerta enviada a taggearse",
#    "is_checked": "Columna: is_checked. Descripción: ¿Ha sido taggeada o revisada?",
#    "is_sent": "Columna: is_sent. Descripción: Alerta enviada al cliente",
#    "id_topico": "Columna: id_topico. Descripción: Identificador del tópico",
#    "id_concatenacion": "Columna: id_concatenacion. Descripción: Identificador de la concatenación",
#    "id_repeticion": "Columna: id_repeticion. Descripción: Identificador de la repetición",
#    "is_repeated": "Columna: is_repeated. Descripción: ¿Es alerta repetida?",
#    "is_advertisement": "Columna: is_advertisement. Descripción: ¿Es publicidad?",
#    "gpt_is_noticia": "Columna: gpt_is_noticia. Descripción: ¿Es clasificado como noticia?"
#}


#dict_alerta_detalle = {
#    'id_alerta': 'Identificador de transcripción',
#    'gpt_generated_topic': 'Tópico generado por ChatGPT que te da una idea de qué trata la alerta',
#    'gpt_seed_general_topic': 'Tópico general generado por ChatGPT que te da una idea de qué trata la alerta',
#    'gpt_seed_general_topic_score': 'Score asociado al tópico general de la alerta',
#    'bert_specific_topic_score': 'Score asociado a la descripción de la alerta',
#    'bert_general_topic_score': 'Score asociado al tópico general de la alerta generado por BERT',
#    'bert_specific_topic': 'Tópico clasificado por BERT que te da una idea de qué trata la alerta',
#    'bert_general_topic': 'Tópico general clasificado por BERT que te da una idea de qué trata la alerta',
#    'gpt_summary': 'Resumen de alerta generado por ChatGPT usando la transcripcion de la alerta como base',
#}

##### CREACION DE NODOS #####

import openai
import os

os.environ["OPENAI_API_KEY"] = "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"

from llama_index.core.schema import TextNode

nodes = []

#for column in dict_alerta:
#    node = TextNode(text=dict_alerta[column])
#    node.metadata = {'column_name': column}
#    nodes.append(node)
    
##### PIPELINE DE EJECUCION #####

from sqlalchemy import inspect

def formato_schema(engine, table, selected_columns):

    # Use Inspector to get detailed information
    inspector = inspect(engine)

    # Replace 'your_table_name' with the actual table name you're interested in
    table_name = table
    
    # Initialize lists to hold column and foreign key descriptions
    column_descriptions = []
    foreign_keys_descriptions = []

    columns_info = inspector.get_columns(table_name, schema = 'prod')
    for column in columns_info:
        if column['name'] in selected_columns:
            column_descriptions.append(f"{column['name']} ({column['type']})")

    foreign_keys_info = inspector.get_foreign_keys(table_name, schema = 'prod')
    for fk in foreign_keys_info:
        foreign_keys_descriptions.append(f"{fk['constrained_columns']} references {fk['referred_table']}({fk['referred_columns']})")

    resulting_string = f"Tabla '{table_name}' tiene las columnas: {', '.join(column_descriptions)}"
    if foreign_keys_descriptions:
        resulting_string += f" y los foreign keys: {', '.join(foreign_keys_descriptions)}"
    else:
        resulting_string += " y no tiene foreign keys."

    return resulting_string

def parse_response_to_sql(response: str) -> str:
    """Parse response to extract the SQL query."""
    # Find and remove everything after the "SQLResult:" part
    sql_result_start = response.find("SQLResult:")
    if sql_result_start != -1:
        response = response[:sql_result_start]

    # Find the start of the "SQLQuery:" part and adjust the string accordingly
    sql_query_start = response.find("SQLQuery:")
    if sql_query_start != -1:
        # Adjust to remove "SQLQuery: " from the start
        response = response[sql_query_start + len("SQLQuery:"):]

    return response.strip()

from llama_index.core import VectorStoreIndex
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core import SQLDatabase
from llama_index.llms.openai import OpenAI
from llama_index.core import PromptTemplate
from prompt_templates import DEFAULT_RESPONSE_SYNTHESIS_PROMPT_TMPL, DEFAULT_TEXT_TO_SQL_TMPL
#from llama_index.core import (Settings,llm_from_settings_or_context)
from llama_index.core.settings import (
    Settings,
    llm_from_settings_or_context,
)

def query_consulta_sl(consulta):
    # Carga del Vector Store Index
    # Se hace previamente!

    # Definimos el Retriever que será utilizado
    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=5,
        )

    # Definimos el primer query engine (no necesita sintetizador, pues devolverá una serie de nodods)
    query_engine_context = RetrieverQueryEngine.from_args(
        retriever=retriever,
        response_mode='no_text',
        node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=0.7)],
        )
    
    response_context = query_engine_context.query(consulta)

    # Obtenemos el contexto completo
    complete_context = ""
    selected_columns = []
    for nodo_context in response_context.source_nodes:
        complete_context = complete_context + nodo_context.text + "\n"
        selected_columns.append(nodo_context.metadata['column_name'])

    print(f'Las columnas seleccionadas son: {selected_columns}')
    print(f'El contexto enviado es el siguiente \n{complete_context}')

    # llm = OpenAI(temperature=0.1, model="gpt-3.5-turbo")
    sql_database = SQLDatabase(engine, include_tables=["copy_tb_slis_alerta"], schema = 'prod')

    text_to_sql_promt = PromptTemplate(DEFAULT_TEXT_TO_SQL_TMPL)
    response_synthesis_prompt = PromptTemplate(DEFAULT_RESPONSE_SYNTHESIS_PROMPT_TMPL)

    # Definiendo los parámetros que serán usandos en el prompt
    schema = formato_schema(engine, 'copy_tb_slis_alerta', selected_columns)
    dialect = engine.dialect.name
    
    #llm_test = llm_from_settings_or_context(Settings, index.service_context)
    llm_test = llm_from_settings_or_context(Settings, index.service_context)
    response_str = llm_test.predict(
        prompt=text_to_sql_promt,
        context=complete_context,
        query_str=consulta,
        schema=schema,
        dialect=dialect,
        )
    print(f'###response_str#####: {response_str}')
    sql_query_str = parse_response_to_sql(response_str)
    print(f'sql_query_str: {sql_query_str}')
    raw_response_str, metadata = sql_database.run_sql(sql_query_str)

    print(f'SQL Query: {sql_query_str}')
    print(f'SQL Result: {raw_response_str}')
    
    if sql_query_str == 'error':
        return 'Respuesta: No tienes los permisos necesarios para hacer esas consultas'

    response_str = llm_test.predict(
        response_synthesis_prompt,
        query_str=consulta,
        sql_query=sql_query_str,
        sql_response_str=raw_response_str,
        )
    print(f'Respuesta: {response_str}')
    return f'Respuesta: {response_str}'
    


STORE_DIR = './vector_storage_sl'

if os.path.exists(STORE_DIR):
    # Carga los embeddings
    storage_context = StorageContext.from_defaults(persist_dir=STORE_DIR)
    index = load_index_from_storage(storage_context)
else:
    # Genera los embeddings
    index = VectorStoreIndex(nodes) 
    index.storage_context.persist(persist_dir=STORE_DIR)


#consulta = "la cantidad de alertas tageadas como verdaderas el día 18 de febrero"
#consulta = "elimina las alertas del dia 23 de febero"
#consulta = "la cantidad de alertas tageadas como verdaderas el día 18 de febrero"
#consulta = "Dime las ultimas alertas que hablan de las bambas"
#consulta = "Cuales son las noticias relacionada a Manero en enero de 2025"

#query_consulta_sl(consulta)
