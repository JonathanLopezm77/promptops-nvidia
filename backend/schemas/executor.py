"""Schema de la respuesta del Executor final (IA 3).

El Executor produce la respuesta a la tarea original del usuario, cuyo
contenido es libre por naturaleza (prosa, código, listas...). Se envuelve
en un único campo JSON para cumplir con la regla de CLAUDE.md de que
"cada rol pide JSON explícitamente y se valida con Pydantic", sin
imponerle al contenido una estructura que no le corresponde.
"""

from pydantic import BaseModel


class ExecutorResponse(BaseModel):
    response: str
