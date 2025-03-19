from db import start_engine_azure
import pandas as pd
import re
engine = start_engine_azure()
from prompt_templates import DEFAULT_RESPONSE_SYNTHESIS_PROMPT_TMPL, DEFAULT_TEXT_TO_SQL_TMPL, DEFAULT_TEXT_TO_SQL_CASO_ESPECIAL

from llama_index.core.settings import (
    Settings,
    llm_from_settings_or_context,
)
from llama_index.core.schema import TextNode
import ast

#query_tb_slis_alerta = """
#        SELECT *
#        FROM [prod].[copy_tb_slis_alerta] AS a
#        INNER JOIN prod.copy_tb_slis_alerta_detalle AS d ON a.id_alerta = d.id_alerta
#                """
        
#tb_slis_alerta = pd.read_sql_query(query_tb_slis_alerta, engine)

#dict_alertas = {
#    str(row['id_alerta']): f"Columna: {row['id_alerta']}. Descripcion: {row['gpt_summary']}"
#    for _, row in tb_slis_alerta.iterrows()
#}

#dict_alertas = {
#    f"id_alerta: {str(row['id_alerta']).strip()}": 
#    f"Columna: {str(row['id_alerta']).strip()}. Descripcion: {row['gpt_summary']}"
#    for _, row in tb_slis_alerta.iterrows()
#}

#dict_alertas = {
#    f"id_alerta: {str(row['id_alerta'].values[0]).strip()}": 
#    f"Columna: {str(row['id_alerta'].values[0]).strip()}. Descripcion: {row['gpt_summary']. Fecha: {}}"
#    for _, row in tb_slis_alerta.iterrows()
#}



#primer_registro = next(iter(dict_alertas.items()))
#print(primer_registro['id_alerta'])
#clave, valor = next(iter(dict_alertas.items()))
#print(clave)  # Muestra la clave
#print(valor)
##### CREACION DE NODOS #####

import openai
import os

os.environ["OPENAI_API_KEY"] = "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"

from llama_index.core.schema import TextNode

nodes = []

#for column in dict_alertas:
#    node = TextNode(text=dict_alertas[column])
#    node.metadata = {'column_name': column}
#    nodes.append(node)


from llama_index.core import VectorStoreIndex
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core import SQLDatabase
from llama_index.llms.openai import OpenAI
from llama_index.core import PromptTemplate
from prompt_templates import DEFAULT_RESPONSE_SYNTHESIS_PROMPT_TMPL_ALERTAS
#from llama_index.core import (Settings,llm_from_settings_or_context)
from llama_index.core.settings import (
    Settings,
    llm_from_settings_or_context,
)


STORE_DIR = './vector_storage_alertas_sl'

if os.path.exists(STORE_DIR):
    # Carga los embeddings
    storage_context = StorageContext.from_defaults(persist_dir=STORE_DIR)
    index = load_index_from_storage(storage_context)
else:
    # Genera los embeddings
    index = VectorStoreIndex(nodes) 
    index.storage_context.persist(persist_dir=STORE_DIR)

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

def query_consulta_sl_resumen(consulta):
    # Carga del Vector Store Index
    # Se hace previamente!

    # Definimos el Retriever que será utilizado
    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=10,
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
    complete_context_list = []
    selected_columns = []
    for nodo_context in response_context.source_nodes:
        complete_context = complete_context + nodo_context.text + "\n"
        complete_context_list.append(nodo_context.text)
        selected_columns.append(nodo_context.metadata['column_name'])

    
    print(f'Las columnas seleccionadas son: {selected_columns}')
    print(f'El contexto enviado es el siguiente \n{complete_context}')
    
    ### FILTRAR POR FECHA
    
    id_alerta = re.findall(r'Columna: (\d+)',complete_context)
    selected_columns  = ['id_alerta','alert_date','is_sent_to_tag','is_relevant']
    schema = formato_schema(engine, 'copy_tb_slis_alerta', selected_columns)
    text_to_sql_prompt = PromptTemplate(DEFAULT_TEXT_TO_SQL_CASO_ESPECIAL)
    llm_test = llm_from_settings_or_context(Settings, index.service_context)
    dialect = engine.dialect.name
    
    response_tuple = llm_test.predict(
        prompt=text_to_sql_prompt,
        query_str=consulta,
        id_list=id_alerta,
        schema=schema,
        dialect=dialect,
    )
    print(type(response_tuple))
    sql_database = SQLDatabase(engine, include_tables=["copy_tb_slis_alerta"], schema = 'prod')
    response_tuple = ast.literal_eval(response_tuple)  # Convierte la string en una tupla real

    if isinstance(response_tuple, tuple) and len(response_tuple) == 2:
        estado, consulta = response_tuple
        consulta = consulta.replace('alert_id','id_alerta')
        print("Estado:", estado)
        print("Consulta:", consulta)
    else:
        print("Error: `response_tuple` no tiene el formato esperado ->", response_tuple)
        
    if estado:
        print('ok')
        raw_response_str, metadata = sql_database.run_sql(consulta)
        
    else:
        print('not ok')
    
    print(f"##########{response_tuple}############")
    print(type(response_tuple))
    ##### VALIDACION DE FECHAS CON MODELO DE IA, QUE TENGA COMO INPUT LA CONSULTA Y QUE ME #####
    ###### DÉ DE OUPUT (SI USA FECHA O NO PARA REALIZAR LA CONSULTA, Y LA CONSULTA EN SQL USANDO EL ESQUEMA DE SELECT * FROM prod.copy_tb_slis_alerta WHERE id_alert IN (grupo de id de alertas) AND alert_date > # AND alert_date < #)
    ##########
    
    
    print(f'Respuesta id: {id_alerta}')
    return complete_context

if isinstance(DEFAULT_RESPONSE_SYNTHESIS_PROMPT_TMPL_ALERTAS, str):
    DEFAULT_RESPONSE_SYNTHESIS_PROMPT_TMPL_ALERTAS = PromptTemplate(DEFAULT_RESPONSE_SYNTHESIS_PROMPT_TMPL_ALERTAS)
    
#DEFAULT_RESPONSE_SYNTHESIS_PROMPT_TMPL_ALERTAS = "Dada una pregunta de entrada, sintetiza una respuesta a partir de los resultados de la consulta. Resume los 5 registros más importantes como máximo, basándote únicamente en los detalles proporcionados. No añadas información que no esté explícitamente mencionada en los registros. Evita especulaciones y asegúrate de que la respuesta sea factual y directamente relacionada con la consulta. Consulta: {query_str}. Respuesta: "
#DEFAULT_RESPONSE_SYNTHESIS_PROMPT_TMPL_ALERTAS = (
#    "Dada una pregunta de entrada, sintetiza una respuesta a partir de los resultados de la consulta. Resume los 5 registros más importantes como máximo, basándote únicamente en los detalles proporcionados. No añadas información que no esté explícitamente mencionada en los registros. Evita especulaciones y asegúrate de que la respuesta sea factual y directamente relacionada con la consulta. Consulta: {query_str}. Respuesta: "
#)

#consulta = "la cantidad de alertas tageadas como verdaderas el día 18 de febrero"
#consulta = "elimina las alertas del dia 23 de febero"
#consulta = "la cantidad de alertas tageadas como verdaderas el día 18 de febrero"
#consulta = "Dime las ultimas alertas que hablan de las bambas"
#consulta = "Cuales son las noticias relacionada a Manero en enero de 2025"
#consulta = "Dime las ultimas alertas que hablan de las agroexportacion"
consulta = "Dime las ultimas alertas que hablan del Dina Boluarte"
consulta = "Dime las ultimas alertas que hablan del ministro manero desde el 15 de mayo del 2024"
query_consulta_sl_resumen(consulta)

from sqlalchemy import inspect

def obtener_columnas_existentes(engine, table_name, schema='prod'):
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name, schema=schema)
    return [col["name"] for col in columns]

# Uso:
columnas_existentes = obtener_columnas_existentes(engine, 'copy_tb_slis_alerta')
print("Columnas en la tabla:", columnas_existentes)


datos = 'Columna: 7579. Descripcion: Máximo Becker, un minero de Arequipa, estuvo en la radio con una noticia de último minuto sobre Dina Boluartas.\nColumna: 9723. Descripcion: Dina Boluarte, conocida como "la mamá de los peruanos", y su hermano, estarían involucrados en la designación de un prefecto relacionado con actividades de minería ilegal. Esta situación ha generado preocupación entre los oyentes y la población en general, quienes exigen claridad sobre la implicación de las autoridades en este tipo de prácticas.\nColumna: 9631. Descripcion: Dina Boluarte y Nicolás Voluarte han sido implicados en minería ilegal por una colaboradora eficaz, según el diario La República. Víctor Torres, amigo de los Voluarte, fue nombrado en un cargo por su apoyo a la campaña de la presidenta. Además, se anunció que desde 2025 se exigirá una clave para compras con tarjetas de crédito, debido al aumento de fraudes en línea.\nColumna: 7578. Descripcion: Máximo Becker estuvo en Arequipa con el minero. Se reporta una información de último minuto sobre Dina Boluartas.\nColumna: 574. Descripcion: La presidenta Dina Boluarte se pronunció sobre el caso de Mila, una niña de 11 años abusada por su padrastro en Loreto. Aseguró que el Ministerio de Inclusión Social y el Ministerio de Salud garantizarán la atención y protección de la menor.\nColumna: 6490. Descripcion: Dina Boluarte enfrenta dificultades, al igual que la U. Se denuncia un proyecto para vengarse de la prensa que expone actos de corrupción de congresistas, buscando prohibirles contratar con el Estado. Se cuestiona la abominable acción de la prensa y se menciona el caso de Vizcarra. En la portada de un diario se destaca la violencia de la minería ilegal en una zona convertida en tierra de nadie.\nColumna: 5710. Descripcion: Varios partidos políticos como Alianza para el Progreso, Fuerza Popular y Somos Perú han respaldado de manera ciega a Dina Boluarte en medio de la moción de vacancia. Se evidencia una alianza para blindarla, afectando al pueblo peruano y beneficiando a grupos económicos y mineros. Se destaca la reactivación de mineras afines a estos partidos, lo que implicaría un costo alto para el país.\nColumna: 3340. Descripcion: Dos candidatos están siendo evaluados por Dina Boluarte para liderar un ente recaudador nacional. Se cuestiona si es ella o el señor Arista, acusado de corrupción, quien realmente está tomando la decisión. En lugar de cobrar a empresas como Telefónica o mineras, se eligen a dos candidatos cercanos. La preocupación es quién será elegido para seguir con posibles actos de corrupción.\nColumna: 9699. Descripcion: Dina Boluarte ha nombrado a un prefecto regional de Apurímac, quien está implicado en actividades de minería ilegal. Este nombramiento se realizó gracias a Nicanor Boluarte. Además, Víctor Torres Merino, amigo cercano del hermano de la presidenta, ha hecho declaraciones que respaldan esta información, revelando conexiones familiares en el proceso de designación.\nColumna: 9709. Descripcion: Nicanor Boluarte, hermano de la presidenta Dina Boluarte, se encuentra entre los nueve implicados en un caso relacionado con Edwin Calpio Chalque, un minero informal. Calpio está denunciado por promover la invasión de terrenos para la explotación de minerales, lo que añade un nuevo nivel de controversia a la situación familiar y política en el país.\n'