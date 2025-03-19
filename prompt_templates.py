from datetime import datetime

fecha_hora_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
DEFAULT_TEXT_TO_SQL_TMPL = (
    "Dada una pregunta de entrada, genera únicamente una consulta {dialect} "
    "sintácticamente correcta para visualizar datos. No puedes modificar, insertar, eliminar "
    "ni actualizar información en la base de datos. Solo puedes formular consultas SELECT. "

    "Reglas para generar la consulta:\n"
    "- Nunca utilices UPDATE, DELETE, INSERT, DROP o ALTER.\n"
    "- No uses SELECT *: selecciona solo las columnas necesarias según la pregunta.\n"
    "- Usa TOP 5 en lugar de LIMIT para limitar los resultados.\n"
    "- Considera una alerta como válida solo si `is_relevant = 1`.\n"
    "- Para buscar en transcripciones, filtra en `alert_text`.\n"
    "- No filtres por `risk_level` a menos que se especifique en la pregunta.\n\n"

    "Reglas para fechas:\n"
    "- El formato de fecha es dd/mm/yyyy.\n"
    "- Si la consulta es para un día específico, usa:\n"
    "- Cuando se filtre por fecha, ten en cuenta que se usa la hora y minutos "
    " Por lo que se debe usar el filtro de esta forma: alert_date BETWEEN 'YYYY-MM-DD 00:00:00' AND 'YYYY-MM-DD 23:59:59'.\n"
    "- Para intervalos de días, el rango debe ir desde '00:00:00' del primer día hasta '00:00:00' del siguiente.\n"
    f"- Ten en cuenta que hoy es {fecha_hora_actual}.\n\n"

    "Errores y restricciones:\n"
    "- Si la consulta solicitada no es un SELECT, devuelve:\n"
    "  `SQLQuery: 'error', SQLResult: [], Respuesta: 'No tiene permisos para esta consulta'`.\n\n"

    "Se requiere que uses el siguiente formato, cada uno ocupando una línea:\n\n"
    "Consulta: Aquí la pregunta\n"
    "SQLQuery: Consulta SQL para ejecutar\n"
    "SQLResult: Resultado de la SQLQuery\n"
    "Respuesta: Respuesta final aquí\n\n"
    "Además, tomá en consideración el siguiente contexto al momento de seleccionar las columnas "
    "que serán relevantes para la consulta. \n"
    "=====================\n"
    "Contexto: {context}\n"
    "=====================\n"
    "A continuación se detalla el esquema de la tabla.\n"
    "{schema}\n\n"
    "Consulta: {query_str}\n"
    "Respuesta: "

)

DEFAULT_TEXT_TO_SQL_CASO_ESPECIAL = (
    "Dada una consulta SQL y una lista de IDs, determina si la consulta involucra un filtro por fecha de alerta "
    "y genera una consulta {dialect} ajustada según los IDs proporcionados.\n\n"

    "Reglas para la validación:\n"
    "- Si la consulta tiene un filtro en `alert_date`, devuelve `True` en la primera posición de la tupla.\n"
    "- Si la consulta no tiene filtro de fecha, devuelve `False`.\n"
    "- En la segunda posición de la tupla, devuelve la consulta SQL ajustada.\n\n"

    "Reglas para modificar la consulta:\n"
    "- Filtra por los IDs dados en `alert_id` usando `WHERE alert_id IN (...)`.\n"
    "- Si ya existe un filtro de fecha en `alert_date`, mantenlo en la consulta ajustada.\n"
    "- Si no hay filtro de fecha pero la pregunta lo requiere, agrégalo con `alert_date BETWEEN 'YYYY-MM-DD 00:00:00' AND 'YYYY-MM-DD 23:59:59'`.\n"
    "- Considera una alerta como válida solo si `is_relevant = 1`.\n\n"
    "- Considera que 'id_alerta' es el identificador de alertas. No uses 'alert_id'"
    "- Busca en la tabla copy_tb_slis_alerta"
    "Formato de salida esperado:\n"
    "Tupla: (Bool, SQLQuery)\n\n"

    "Consulta SQL original:\n"
    "{query_str}\n\n"
    "Lista de IDs:\n"
    "{id_list}\n\n"
    "Respuesta: "
)

DEFAULT_RESPONSE_SYNTHESIS_PROMPT_TMPL = (
    "Dada una pregunta de entrada, sintetiza una respuesta a partir de los resultados de la consulta.\n"
    "Consulta: {query_str}\n"
    "SQL: {sql_query}\n"
    "Respuesta SQL: {sql_response_str}\n"
    "Respuesta: "
)

DEFAULT_RESPONSE_SYNTHESIS_PROMPT_TMPL_ALERTAS = (
    "Dada una pregunta de entrada, sintetiza una respuesta a partir de los resultados de la consulta.\n"
    "Resume los 5 registros más importantes como máximo, basándote únicamente en los detalles proporcionados. No añadas información que no esté explícitamente mencionada en los registros. Evita especulaciones y asegúrate de que la respuesta sea factual y directamente relacionada con la consulta.\n"
    "Consulta: {query_str}\n"
    "Respuesta: "
)