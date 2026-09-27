"""Tests de las funciones de scripts/prompts_sdlc.py que deciden qué se
publica como evidencia del punto 4: si fallaran, el catálogo podría
mostrar como "aprobada" una versión que nadie aprobó."""

from scripts.prompts_sdlc import (
    FASES,
    DIR_INICIALES,
    iteracion_aprobada,
    linea_base,
    marcadores,
    mejor_score,
)


def _it(n, source, score, decisiones=()):
    return {
        "iteration_number": n, "source": source, "output_prompt": f"v{n}",
        "audits": [{"parse_ok": True, "total_score": score}] if score is not None else [],
        "human_decisions": [{"decision": d, "feedback": None} for d in decisiones],
    }


def test_marcadores_detecta_las_variables_de_la_plantilla():
    texto = "Usa {{REQUISITOS_APROBADOS}} y {{ RESTRICCIONES_TECNICAS }}; ignora {llaves simples}."
    assert marcadores(texto) == {"REQUISITOS_APROBADOS", "RESTRICCIONES_TECNICAS"}


def test_solo_cuenta_como_aprobada_la_iteracion_con_decision_approve():
    run = {"iterations": [_it(1, "original", 30), _it(2, "optimizer", 70, ["iterate"]), _it(3, "optimizer", 85)]}
    assert iteracion_aprobada(run) is None  # nadie aprobó todavía

    run["iterations"][2]["human_decisions"] = [{"decision": "approve", "feedback": None}]
    assert iteracion_aprobada(run)["iteration_number"] == 3


def test_la_linea_base_no_cuenta_para_el_mejor_score():
    run = {"iterations": [_it(1, "original", 95), _it(2, "optimizer", 60), _it(3, "optimizer", 80)]}
    assert linea_base(run)["iteration_number"] == 1
    assert mejor_score(run) == 80


def test_modelo_de_marca_como_deducido_lo_que_no_se_registro():
    from scripts.prompts_sdlc import modelo_de

    run = {"optimizer_model": "moonshotai/kimi-k3"}
    assert modelo_de({"source": "optimizer", "model": "nvidia/nemotron"}, run) == "nvidia/nemotron"
    assert "deducido" in modelo_de({"source": "optimizer", "model": None}, run)
    assert modelo_de({"source": "original", "model": None}, run) == "—"


def test_los_siete_prompts_iniciales_existen_y_declaran_sus_variables():
    assert [f["n"] for f in FASES] == [1, 2, 3, 4, 5, 6, 7]
    for fase in FASES:
        texto = (DIR_INICIALES / f"{fase['n']}_{fase['clave']}.txt").read_text(encoding="utf-8")
        # Cada plantilla tiene al menos una variable, más allá de la nota "{{...}}".
        assert marcadores(texto), fase["clave"]
