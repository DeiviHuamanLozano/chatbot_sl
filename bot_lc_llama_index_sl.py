import os
import getpass
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from sqlalchemy import create_engine, inspect
import pandas as pd
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core import SQLDatabase
from llama_index.llms.openai import OpenAI
from prompt_templates import DEFAULT_RESPONSE_SYNTHESIS_PROMPT_TMPL, DEFAULT_TEXT_TO_SQL_TMPL

if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = getpass.getpass("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")


from langchain_openai import OpenAI

llm = OpenAI(model_name="gpt-3.5-turbo-instruct")
llm.invoke("Hola, como estas?")

memory = ConversationBufferMemory()

# Creación del LLMChain
prompt_template = PromptTemplate(template="You are a helpful assistant. {question}", input_variables=["question"])
llm_chain = LLMChain(llm=llm, memory=memory, prompt=prompt_template)


# Configuración del índice
STORE_DIR = './vector_storage_sl'
if os.path.exists(STORE_DIR):
    storage_context = StorageContext.from_defaults(persist_dir=STORE_DIR)
    index = load_index_from_storage(storage_context)
else:
    index = VectorStoreIndex(nodes)
    index.storage_context.persist(persist_dir=STORE_DIR)

##### PIPELINE DE EJECUCION #####
from db import start_engine_azure
import pandas as pd
engine = start_engine_azure()
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

    
def query_consulta_sl(consulta, index):
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
    selected_columns = []
    for nodo_context in response_context.source_nodes:
        complete_context = complete_context + nodo_context.text + "\n"
        selected_columns.append(nodo_context.metadata['column_name'])

    print(f'Las columnas seleccionadas son: {selected_columns}')
    print(f'El contexto enviado es el siguiente \n{complete_context}')

    # llm = OpenAI(temperature=0.1, model="gpt-3.5-turbo")
    sql_database = SQLDatabase(engine, include_tables=["tb_slis_alerta"], schema = 'prod')

    text_to_sql_promt = PromptTemplate(DEFAULT_TEXT_TO_SQL_TMPL)
    response_synthesis_prompt = PromptTemplate(DEFAULT_RESPONSE_SYNTHESIS_PROMPT_TMPL)

    # Definiendo los parámetros que serán usandos en el prompt
    schema = formato_schema(engine, 'tb_slis_alerta', selected_columns)
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
    
    sql_query_str = parse_response_to_sql(response_str)
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
    
    return print(f'Respuesta: {response_str}')
    

















llm = OpenAI(model="gpt-4", api_key="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")
prompt_template = PromptTemplate(template="You are a helpful assistant. {question}", input_variables=["question"])

# Creación de una cadena para manejar la lógica del chatbot
llm_chain = LLMChain(prompt=prompt_template, llm=llm)

def process_query(user_input):

    sql_query = llm_chain.run(user_input)
    
    return sql_query

user_input = "¿Cuántas alertas se etiquetaron como verdaderas el 18 de febrero?"
response = process_query(user_input)