# SPEC-AUT-03 — Especificación (contrato del desarrollo)

> Generado por `python -m sdd.render` desde `specs/specification.json` (huella `78f967ade537`). No editar a mano: se cambia la especificación y se regenera.

- **Versión:** 1.0.1 · **Estado:** aprobada
- **Trazabilidad:** NEC-AUT-01 → REQ-AUT-03 → SPEC-AUT-03
- **Alcance:** Solo el inicio de sesión de clientes registrados (D-09).

## Descripción

Bloqueo temporal de cuenta de cliente registrado tras 5 intentos fallidos consecutivos de inicio de sesión dentro de una ventana de 10 minutos. El bloqueo dura 15 minutos, durante los cuales se rechaza todo intento de inicio de sesión de esa cuenta. Un inicio de sesión exitoso reinicia el contador de intentos fallidos a 0. Al expirar el bloqueo, el cliente puede autenticarse normalmente con su contraseña correcta.

## Parámetros de la política

| Parámetro | Valor | Significado |
|---|---|---|
| max_intentos_fallidos | 5 | intentos fallidos consecutivos que bloquean |
| ventana_minutos | 10 | periodo en que deben ocurrir |
| bloqueo_minutos | 15 | duración del bloqueo |

## Entradas

| Nombre | Tipo | Validaciones |
|---|---|---|
| identificador_cuenta | string (RFC 5322, correo electrónico del cliente registrado) | formato de email válido; debe corresponder a una cuenta registrada en el sistema |
| contrasena | string | no vacía; comparación contra el hash almacenado de la cuenta |
| timestamp_intento | string (ISO 8601, YYYY-MM-DDTHH:MM:SSZ) | fecha-hora válida generada por el servidor en el momento del intento; no modificable por el cliente |

## Salidas

| Nombre | Tipo |
|---|---|
| resultado_autenticacion | enum (EXITOSO \| CREDENCIALES_INVALIDAS \| CUENTA_BLOQUEADA) |
| cuenta_bloqueada_hasta | string (ISO 8601, YYYY-MM-DDTHH:MM:SSZ) \| null |
| contador_intentos_fallidos | integer (rango 0-5; mientras la cuenta está bloqueada vale max_intentos_fallidos: D-10) |
| mensaje | string (mensaje informativo para el cliente) |

## Reglas de negocio

| ID | Regla | Origen |
|---|---|---|
| RB-1 | El sistema registra cada intento fallido de inicio de sesión con su timestamp (ISO 8601) asociado a la cuenta del cliente. | fase de especificación (Kimi K3, paso 2_especificacion) |
| RB-2 | Solo se consideran los intentos fallidos ocurridos dentro de una ventana deslizante de 10 minutos respecto al intento actual; los intentos fuera de esa ventana no cuentan. | fase de especificación (Kimi K3, paso 2_especificacion) |
| RB-3 | Al alcanzarse el quinto intento fallido consecutivo dentro de la ventana de 10 minutos, la cuenta queda bloqueada durante 15 minutos a partir del momento del quinto intento. | fase de especificación (Kimi K3, paso 2_especificacion) |
| RB-4 | Mientras la cuenta esté bloqueada, el sistema rechaza todo intento de inicio de sesión de esa cuenta, incluidos los intentos con contraseña correcta, devolviendo CUENTA_BLOQUEADA. | fase de especificación (Kimi K3, paso 2_especificacion) |
| RB-5 | Un inicio de sesión exitoso (cuenta no bloqueada y credenciales válidas) reinicia el contador de intentos fallidos a 0. | fase de especificación (Kimi K3, paso 2_especificacion) |
| RB-6 | Transcurridos 15 minutos o más desde el inicio del bloqueo, el bloqueo expira automáticamente y el cliente puede autenticarse con su contraseña correcta; el contador de intentos fallidos se reinicia a 0. | fase de especificación (Kimi K3, paso 2_especificacion) |
| RB-7 | El contador de intentos fallidos es por cuenta, independiente del dispositivo o dirección IP de origen. | fase de especificación (Kimi K3, paso 2_especificacion) |
| RB-8 | Los intentos de inicio de sesión que ocurren mientras la cuenta está bloqueada se rechazan sin modificar el bloqueo: no lo extienden ni cuentan como intentos fallidos para un bloqueo posterior. | revisión humana (decisión D-08) |

## Criterios de aceptación

| ID | Criterio | Verifica |
|---|---|---|
| AC-AUT-03-01 | **Dado** un cliente registrado con 4 intentos fallidos consecutivos en los últimos 10 minutos, **cuando** falla el quinto intento de inicio de sesión, **entonces** la cuenta queda bloqueada durante 15 minutos y el sistema devuelve CUENTA_BLOQUEADA con la fecha-hora de fin de bloqueo en formato ISO 8601. | RB-1, RB-2, RB-3 |
| AC-AUT-03-02 | **Dado** una cuenta bloqueada, **cuando** el cliente intenta iniciar sesión con su contraseña correcta antes de que transcurran los 15 minutos de bloqueo, **entonces** el sistema rechaza el inicio de sesión y devuelve CUENTA_BLOQUEADA. | RB-4 |
| AC-AUT-03-03 | **Dado** una cuenta cuyo bloqueo se inició hace 15 minutos o más, **cuando** el cliente ingresa su contraseña correcta, **entonces** el inicio de sesión es exitoso y el contador de intentos fallidos queda en 0. | RB-6 |
| AC-AUT-03-04 | **Dado** un cliente con 4 intentos fallidos consecutivos dentro de la ventana de 10 minutos, **cuando** inicia sesión correctamente, **entonces** el contador de intentos fallidos vuelve a 0 y la cuenta no se bloquea. | RB-5 |
| AC-AUT-03-05 | **Dado** un cliente con 4 intentos fallidos donde el más antiguo ocurrió hace más de 10 minutos, **cuando** falla un nuevo intento, **entonces** el intento antiguo se descarta de la ventana, el contador efectivo es menor a 5 y la cuenta no se bloquea. | RB-2 |
| AC-AUT-03-06 | **Dado** la cuenta A bloqueada por 5 intentos fallidos consecutivos, **cuando** el cliente de la cuenta B inicia sesión con su contraseña correcta, **entonces** el inicio de sesión de la cuenta B es exitoso y los intentos de la cuenta A no afectan a la cuenta B. | RB-7 |
| AC-AUT-03-07 | **Dado** una cuenta bloqueada hace 5 minutos, **cuando** el cliente falla otro intento de inicio de sesión, **entonces** el sistema devuelve CUENTA_BLOQUEADA, la fecha-hora de fin de bloqueo no cambia y, al expirar el bloqueo, el contador de intentos fallidos está en 0. | RB-4, RB-8 |

## Decisiones de la revisión (supuestos resueltos)

| ID | Tema | Decisión | Fundamento |
|---|---|---|---|
| D-01 | Identificador de la cuenta | Se acepta: la cuenta se identifica con el correo del cliente registrado. El componente lo trata como un identificador opaco no vacío; validar el formato del correo es responsabilidad del backend de inicio de sesión. | R4: el módulo no gestiona credenciales ni sesiones. |
| D-02 | Tipo de ventana y su límite | Se acepta la ventana deslizante. Límite: un intento fallido ocurrido exactamente 10 minutos antes todavía cuenta; solo se descartan los ocurridos hace MÁS de 10 minutos. | El requisito dice 'dentro de un periodo de 10 minutos' y AC-AUT-03-05 descarta solo los de 'hace más de 10 minutos'. |
| D-03 | Inicio y fin del bloqueo | Se acepta: el bloqueo empieza en el instante del quinto intento fallido y termina exactamente 15 minutos después; en ese instante ya se permite iniciar sesión. | Criterio 2 del requisito: 'bloqueada hace 15 minutos o más ... el inicio de sesión es exitoso'. |
| D-04 | Significado de 'consecutivos' | Se acepta: un inicio de sesión exitoso interrumpe la racha y reinicia el contador a 0. | Criterio 3 del requisito. |
| D-05 | Contador al expirar el bloqueo | Se acepta: al expirar el bloqueo el contador queda en 0 (el cliente vuelve a tener 5 intentos). | Un bloqueo cumplido cierra la racha que lo provocó; si no se reiniciara, un único fallo posterior volvería a bloquear la cuenta, lo que contradice la necesidad NEC-AUT-01 (no castigar de más al cliente legítimo). |
| D-06 | Alcance del contador | Se acepta: el contador y el bloqueo son por cuenta, sin importar dispositivo o IP. Se agrega el criterio AC-AUT-03-06 porque RB-7 no tenía ninguno. | El requisito habla de 'la cuenta de un cliente'. |
| D-07 | Origen del tiempo | Se acepta: el instante lo genera el servidor en UTC y se recibe como parámetro; un instante sin zona horaria se rechaza. | R2: el módulo nunca lee el reloj del sistema. |
| D-08 | Intentos durante el bloqueo | Los intentos durante el bloqueo se rechazan y no modifican nada: no extienden el bloqueo ni cuentan para uno posterior (RB-8, AC-AUT-03-07). | El requisito fija el bloqueo en 'durante 15 minutos'; extenderlo lo contradiría. Hueco no mencionado por el modelo: detectado en la revisión. |
| D-09 | Alcance del bloqueo | El bloqueo afecta solo al inicio de sesión, no a otras operaciones. | Pregunta del motor de requisitos en la validación (paso 1); el texto del requisito ya lo responde: 'rechaza todo inicio de sesión'. |
| D-10 | Contador durante el bloqueo | Mientras la cuenta está bloqueada, la salida contador_intentos_fallidos vale max_intentos_fallidos (los intentos que provocaron el bloqueo); los intentos durante el bloqueo no lo incrementan (RB-8). | Hallazgo OBS-01 del reporte de defectos de la fase de Testing (paso 5_pruebas): la especificación v1.0.0 no definía este valor; solo el contrato de arquitectura (C-07). Se lleva a la fuente de verdad. |

## Alertas

| Tipo | Descripción | Tratamiento |
|---|---|---|
| legal | El registro de intentos fallidos de inicio de sesión con timestamps asociados a cuentas de clientes constituye tratamiento de datos personales (registros de actividad/seguridad), potencialmente sujeto a normativas de protección de datos (ej. RGPD/GDPR, LFPDPPP u otras leyes locales aplicables), que exigen base jurídica, minimización, plazos de retención definidos e información al titular. En Colombia aplica la Ley 1581 de 2012 (protección de datos personales). | Revisar con el responsable de protección de datos la base jurídica (interés legítimo en seguridad), definir y documentar el periodo de retención de los registros de intentos fallidos, e incluir este tratamiento en el aviso de privacidad de la tienda en línea. Minimización ya incluida en el diseño: solo se conservan los intentos dentro de la ventana y el fin del bloqueo vigente. El plazo de retención queda como pendiente del equipo con el responsable de datos. |
