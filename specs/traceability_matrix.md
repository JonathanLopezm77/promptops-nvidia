# Matriz de trazabilidad — REQ-AUT-03 → SPEC-AUT-03

> Generada por `python -m sdd.trazabilidad` (especificación v1.0.1, huella `78f967ade537`). No editar a mano.

Estado de la cadena: **CONFORME**

Cadena: NEC-AUT-01 → REQ-AUT-03 → AC → SPEC-AUT-03 → ARCH → CODE → TEST

## Criterio de aceptación → prueba

| REQ | AC | Reglas | SPEC | ARCH | Código | Pruebas |
|---|---|---|---|---|---|---|
| REQ-AUT-03 | AC-AUT-03-01 | RB-1, RB-2, RB-3 | SPEC-AUT-03 | ARCH-01, ARCH-02, ARCH-03 | `src/auth_lockout/procesador.py`, `src/auth_lockout/repositorio.py`, `src/auth_lockout/politica.py` | test_conformidad_spec.py::test_ac01_el_intento_M_dentro_de_la_ventana_bloquea_durante_B<br>test_req_aut_03_generadas.py::test_01_quinto_fallo_bloquea_cuenta |
| REQ-AUT-03 | AC-AUT-03-02 | RB-4 | SPEC-AUT-03 | ARCH-01 | `src/auth_lockout/procesador.py` | test_conformidad_spec.py::test_ac02_durante_el_bloqueo_se_rechaza_la_contrasena_correcta<br>test_req_aut_03_generadas.py::test_02_contrasena_correcta_no_desbloquea |
| REQ-AUT-03 | AC-AUT-03-03 | RB-6 | SPEC-AUT-03 | ARCH-01, ARCH-03 | `src/auth_lockout/procesador.py`, `src/auth_lockout/politica.py` | test_conformidad_spec.py::test_ac03_al_cumplirse_B_exactos_el_ingreso_es_exitoso_y_el_contador_vuelve_a_0<br>test_req_aut_03_generadas.py::test_03_bloqueo_expira_exactamente_a_los_15_minutos<br>test_req_aut_03_generadas.py::test_04_login_exitoso_despues_de_expirar_bloqueo |
| REQ-AUT-03 | AC-AUT-03-04 | RB-5 | SPEC-AUT-03 | ARCH-01 | `src/auth_lockout/procesador.py` | test_conformidad_spec.py::test_ac04_un_exito_con_M_menos_1_fallos_reinicia_el_contador<br>test_req_aut_03_generadas.py::test_05_exito_reinicia_contador |
| REQ-AUT-03 | AC-AUT-03-05 | RB-2 | SPEC-AUT-03 | ARCH-01, ARCH-03 | `src/auth_lockout/procesador.py`, `src/auth_lockout/politica.py` | test_conformidad_spec.py::test_ac05_un_fallo_de_hace_mas_de_V_sale_de_la_ventana<br>test_conformidad_spec.py::test_ac05_un_fallo_de_exactamente_V_todavia_cuenta<br>test_req_aut_03_generadas.py::test_06_intento_fuera_de_ventana_se_descarta |
| REQ-AUT-03 | AC-AUT-03-06 | RB-7 | SPEC-AUT-03 | ARCH-01, ARCH-02 | `src/auth_lockout/procesador.py`, `src/auth_lockout/repositorio.py` | test_conformidad_spec.py::test_ac06_las_cuentas_son_independientes<br>test_req_aut_03_generadas.py::test_08_bloqueo_no_afecta_a_otras_cuentas |
| REQ-AUT-03 | AC-AUT-03-07 | RB-4, RB-8 | SPEC-AUT-03 | ARCH-01 | `src/auth_lockout/procesador.py` | test_conformidad_spec.py::test_ac07_los_intentos_durante_el_bloqueo_no_lo_modifican<br>test_req_aut_03_generadas.py::test_09_intentos_durante_bloqueo_no_modifican_nada |

## ARCH → código

| ARCH | Módulo | Declara `Implements:` |
|---|---|---|
| ARCH-01 | `src/auth_lockout/procesador.py` | sí |
| ARCH-02 | `src/auth_lockout/repositorio.py` | sí |
| ARCH-03 | `src/auth_lockout/politica.py` | sí |

Reglas sin criterio de aceptación: ninguna.
