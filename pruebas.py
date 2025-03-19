import os
import openai
import getpass
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from llama_index.core import (
    VectorStoreIndex, 
    StorageContext, 
    load_index_from_storage,
    ServiceContext,
)
from llama_index.llms.openai import OpenAI
from llama_index.legacy.tools import QueryEngineTool, ToolMetadata
from llama_index.legacy.query_engine import SubQuestionQueryEngine
from llama_index.legacy.agent import OpenAIAgent
from llama_index.legacy.callbacks import CallbackManager, LlamaDebugHandler

# ====== 🔐 Configuración de OpenAI ======
BASE_DIR = Path(__file__).resolve().parent
dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path)
openai.api_key = os.environ["OPENAI_API_KEY"]

# ====== 🛠 Habilitar trazas de depuración ======
llama_debug = LlamaDebugHandler(print_trace_on_end=True)
callback_manager = CallbackManager([llama_debug])


if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = getpass.getpass("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")


from langchain_openai import OpenAI

llm = OpenAI(model_name="gpt-3.5-turbo-instruct")
llm.invoke("Hola, como estas?")

# ====== 🔥 Configurar el modelo de lenguaje ======
llm = OpenAI(model_name="gpt-3.5-turbo", temperature=0)
llm = OpenAI(model_name="gpt-3.5-turbo-instruct")
service_context = ServiceContext.from_defaults()

llm.invoke("Hola, como estas?")


llama_debug = LlamaDebugHandler(print_trace_on_end=True)

callback_manager = CallbackManager([llama_debug])

service_context = ServiceContext.from_defaults(
    callback_manager=callback_manager, llm=llm
)

# ====== 📥 Cargar el índice desde almacenamiento persistente ======
STORE_DIR = './vector_storage_sl'

if os.path.exists(STORE_DIR):
    storage_context = StorageContext.from_defaults(persist_dir=STORE_DIR)
    index = load_index_from_storage(storage_context)
else:
    raise FileNotFoundError("¡No se encontró el índice! Asegúrate de que está indexado correctamente.")

# ====== 🔎 Configurar el Query Engine ======
query_engine_tool = QueryEngineTool(
    query_engine=index.as_query_engine(),
    metadata=ToolMetadata(
        name="database_query_engine",
        description="Útil para responder preguntas sobre la base de datos indexada."
    )
)

query_engine = SubQuestionQueryEngine.from_defaults(
    query_engine_tools=[query_engine_tool],
    service_context=service_context,
    verbose=True,
    use_async=True
)

# ====== 🧠 Crear el Agente con Tools ======
tools = [query_engine_tool]
agent = OpenAIAgent.from_tools(tools, verbose=True)

# ====== 🗣 Loop de Chat ======
while True:
    text_input = input("User: ")
    if text_input.lower() == "exit":
        break
    response = agent.chat(text_input)
    print(f"Agent: {response}")
    print("====================================")
