from langchain.tools import Tool
from bot_sl_consultas_texto import query_consulta_sl_resumen
from bot_sl_llamaindex import query_consulta_sl
from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.callbacks import StdOutCallbackHandler

tools = [
    Tool(name="Buscar en la base de datos", func=query_consulta_sl, description="Busqueda en cantidad de alertas en intervalo de fechas en la base de datos"),
    Tool(name="Buscar en alertas", func=query_consulta_sl_resumen, description="Busqueda de temas especificos dentro "),
]

# Configura la memoria de conversación para almacenar el historial de chat
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Inicializa el modelo de lenguaje de OpenAI
llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", model_kwargs={"language": "es"})

# Inicializa el agente con herramientas y modelo de lenguaje
agent_executor = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
    memory=memory,
    verbose=True  # Activar el modo verbose para mayor detalle en logs
)

handler = StdOutCallbackHandler()


user_query = "Dime las ultimas alertas que hablan de las bambas"

response = agent_executor.run(user_query)

print("Agent response:", response)
