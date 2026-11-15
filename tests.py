"""
Testes abrangentes para o ICDAS Educacional.
Rodar com: python -m pytest tests.py -v
"""
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import pytest

# Configura ambiente ANTES de importar o app
os.environ["FLASK_DEBUG"] = "0"
os.environ["SECRET_KEY"] = "test-secret-key-only-for-testing"
os.environ["ADMIN_PASSWORD"] = "test-admin"


@pytest.fixture(autouse=True)
def _setup_db(tmp_path, monkeypatch):
    """Cada teste usa um banco temporário isolado."""
    db_path = str(tmp_path / "test_icdas.db")
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # Re-importar para usar o novo DB_PATH não funciona; o módulo expõe a
    # seleção de backend justamente para testes/standalone poderem alternar DB.
    import app as app_module
    app_module.DB_PATH = db_path
    app_module.DATABASE_URL = ""
    app_module.init_db()
    yield db_path


@pytest.fixture
def client():
    import app as app_module
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    app_module.app.config["RATELIMIT_ENABLED"] = False
    app_module.limiter.reset()
    with app_module.app.test_client() as c:
        with c.session_transaction() as sess:
            sess["quiz_nome"] = "Aluno Teste"
        yield c


@pytest.fixture
def csrf_client():
    """Cliente com CSRF habilitado — simula browser real ou ataque sem token."""
    import app as app_module
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret-csrf"
    app_module.app.config["WTF_CSRF_ENABLED"] = True
    app_module.app.config["WTF_CSRF_TIME_LIMIT"] = 3600
    app_module.app.config["RATELIMIT_ENABLED"] = False
    app_module.limiter.reset()
    with app_module.app.test_client() as c:
        with c.session_transaction() as sess:
            sess["quiz_nome"] = "Aluno Teste"
        yield c


@pytest.fixture
def rate_client():
    """Cliente com rate limiting habilitado — testa throttling real."""
    import app as app_module
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret-rate"
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    app_module.app.config["RATELIMIT_ENABLED"] = True
    app_module.limiter.reset()
    with app_module.app.test_client() as c:
        with c.session_transaction() as sess:
            sess["quiz_nome"] = "Aluno Teste"
        yield c


@pytest.fixture
def app_module():
    import app as app_module
    return app_module


def _prepare_quiz_answer(client, app_module, image):
    """Simula uma questão que foi realmente exibida antes do POST."""
    client.get("/quiz")
    with client.session_transaction() as sess:
        attempt_id = sess.get("attempt_id")
        assert attempt_id
        sess["quiz_atual"] = image["id"]
        fila = sess.get("quiz_fila")
        if isinstance(fila, list):
            sess["quiz_fila"] = [iid for iid in fila if iid != image["id"]]
    return {"attempt_id": str(attempt_id), "imagem_id": str(image["id"])}


def _payload_from_rendered_quiz(html):
    import re
    attempt = re.search(r'name="attempt_id"\s+value="(\d+)"', html)
    image = re.search(r'name="imagem_id"\s+value="(\d+)"', html)
    assert attempt and image, "formulário ativo do quiz não encontrado"
    return {"attempt_id": attempt.group(1), "imagem_id": image.group(1)}


# ============================================================
# TESTES DE ROTA — STATUS CODE E CONTEÚDO BÁSICO
# ============================================================

class TestRotasBasicas:
    """Verifica que todas as rotas retornam 200 e conteúdo esperado."""

    def test_home_status(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_home_conteudo(self, client):
        resp = client.get("/")
        assert "ICDAS" in resp.data.decode("utf-8")
        assert "A escala" in resp.data.decode("utf-8")

    def test_galeria_status(self, client):
        resp = client.get("/galeria")
        assert resp.status_code == 200

    def test_galeria_conteudo(self, client):
        resp = client.get("/galeria")
        html = resp.data.decode("utf-8")
        assert "Galeria" in html
        # Deve ter botões de filtro ICDAS 0–6
        for i in range(7):
            assert f"ICDAS {i}" in html

    def test_explorador_tratamento_isolado_do_quiz(self, client):
        resp = client.get("/arvore-de-tratamento")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "Árvore de tratamento" in html
        assert "Em revisão" in html
        assert "arvore_modelo.js" in html
        assert "arvore_tratamento.js" in html
        assert "arvore_tratamento.css" in html
        assert "data-treatment-tree" in html
        assert 'data-tree-lines' in html
        assert html.count("data-tree-content") == 1
        assert 'data-tree-variant' not in html
        assert "Não constitui indicação de tratamento" in html

    def test_arvore_svg_esquematico_e_tamanhos_responsivos(self, client):
        """Corte único, sem opções ou CSS legados dos spikes descartados."""
        js = client.get("/static/js/arvore_tratamento.js")
        css = client.get("/static/css/arvore_tratamento.css")
        assert js.status_code == css.status_code == 200
        javascript = js.get_data(as_text=True)
        stylesheet = css.get_data(as_text=True)
        assert "radiographicCut" in javascript
        assert "CUT_PATHS" in javascript
        assert "RX_EXTENT_PATHS" in javascript
        assert "OCCLUSAL_EXTENT_PATHS" in javascript
        assert "tree-rx-radiolucency" in javascript
        assert '"0 0 118 84"' in javascript
        assert "tree-rx-diagram" in stylesheet
        assert "tree-rx-layer" not in stylesheet
        assert "tree-rx-switch" not in stylesheet
        assert "diagramStyle" not in javascript
        assert "data-diagram-switch" not in javascript
        assert "tree-rx-diagram--layers" not in stylesheet
        assert "border-radius: 50%" in stylesheet  # números ICDAS circulares
        assert "tree-choices--code" in stylesheet

    def test_home_distingue_classificacao_de_tratamento(self, client):
        html = client.get("/").data.decode("utf-8")
        assert "Sete códigos, um critério" in html
        assert "Árvore de tratamento" in html or "árvore" in html
        assert 'id="arvore-de-tratamento"' in html
        assert html.count("data-treatment-tree") == 1
        assert html.count("data-tree-content") == 1
        assert "arvore_modelo.js" in html and "arvore_tratamento.js" in html
        assert "arvore_tratamento.css" in html
        assert 'href="/#arvore-de-tratamento"' in html
        assert 'href="/arvore-de-tratamento"' in html
        assert "data-decision-guide" not in html
        assert "tree-step" not in html

    def test_arvore_sem_numeracao_de_etapas_e_sem_assistente_legado(self, client):
        javascript = client.get("/static/js/arvore_tratamento.js").get_data(as_text=True)
        landing = client.get("/static/js/redesign.js").get_data(as_text=True)
        stylesheet = client.get("/static/css/arvore_tratamento.css").get_data(as_text=True)
        assert 'class="tree-step"' not in javascript
        assert "tree-step" not in javascript
        assert ".tree-step" not in stylesheet
        assert "data-decision-guide" not in landing
        assert "100cqw" in stylesheet  # círculos dimensionados pela largura da árvore

    def test_quiz_status(self, client):
        resp = client.get("/quiz")
        assert resp.status_code == 200

    def test_quiz_conteudo(self, client):
        resp = client.get("/quiz")
        html = resp.data.decode("utf-8")
        assert "Quiz" in html

    def test_scores_status(self, client):
        resp = client.get("/scores")
        assert resp.status_code == 200

    def test_scores_conteudo_vazio(self, client):
        resp = client.get("/scores")
        html = resp.data.decode("utf-8")
        assert "Nenhuma sessão" in html or "Histórico" in html

    def test_sobre_status(self, client):
        resp = client.get("/sobre")
        assert resp.status_code == 200

    def test_sobre_conteudo(self, client):
        resp = client.get("/sobre")
        html = resp.data.decode("utf-8")
        assert "UFJF" in html
        assert "Alan" in html

    def test_404(self, client):
        resp = client.get("/pagina-inexistente")
        assert resp.status_code == 404
        html = resp.data.decode("utf-8")
        assert "404" in html

    def test_favicon(self, client):
        resp = client.get("/static/favicon.svg")
        assert resp.status_code == 200


# ============================================================
# TESTES DE QUIZ — FLUXO PRINCIPAL
# ============================================================

class TestQuizFluxo:
    """Testa o fluxo completo do quiz: GET → POST → feedback → próxima."""

    def test_quiz_get_mostra_imagem(self, client):
        resp = client.get("/quiz")
        html = resp.data.decode("utf-8")
        # Deve ter um formulário com radio buttons ou mensagem de sem imagem
        assert "imagem_id" in html or "Nenhuma imagem" in html

    def test_quiz_mostra_progresso_da_tentativa(self, client, app_module):
        total = min(app_module.QUIZ_QUESTIONS_PER_ATTEMPT, len(app_module.get_imagens()))
        resp = client.get("/quiz")
        html = resp.data.decode("utf-8")
        assert f'max="{total}" value="0"' in html
        assert 'class="quiz-native-progress sr-only"' in html
        assert f'max="{total}"' in html
        assert "Fotografia clínica para classificação ICDAS" in html
        assert "alt=\"Imagem clínica ICDAS" not in html

    def test_quiz_post_resposta_correta(self, client, app_module):
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        img = imagens[0]
        payload = _prepare_quiz_answer(client, app_module, img)
        payload["resposta"] = str(img["icdas_code"])
        resp = client.post("/quiz", data=payload, follow_redirects=True)
        html = resp.data.decode("utf-8")
        assert "Correto" in html
        assert "✓" in html
        # Deve mostrar a descrição clínica
        desc = app_module.DESCRICOES.get(str(img["icdas_code"]))
        if desc:
            assert desc["titulo"] in html

    def test_quiz_post_resposta_incorreta(self, client, app_module):
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        img = imagens[0]
        resposta_errada = (img["icdas_code"] + 1) % 7
        payload = _prepare_quiz_answer(client, app_module, img)
        payload["resposta"] = str(resposta_errada)
        resp = client.post("/quiz", data=payload, follow_redirects=True)
        html = resp.data.decode("utf-8")
        assert "Incorreto" in html
        assert 'class="feedback-icon">×' in html
        assert '<span>Você marcou <strong>ICDAS' in html

    def test_quiz_mesma_imagem_apos_resposta(self, client, app_module):
        """Bug crítico corrigido: imagem não deve mudar após POST."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        img = imagens[0]
        payload = _prepare_quiz_answer(client, app_module, img)
        payload["resposta"] = str(img["icdas_code"])
        resp = client.post("/quiz", data=payload, follow_redirects=True)
        html = resp.data.decode("utf-8")
        # A imagem original deve estar presente pela URL do asset, sem depender do alt.
        assert quote(img["nome"]) in html

    def test_quiz_placar_sessao(self, client, app_module):
        """Placar deve incrementar com duas imagens distintas."""
        imagens = app_module.get_imagens()
        if len(imagens) < 2:
            pytest.skip("Precisa de pelo menos 2 imagens")
        primeira, segunda = imagens[:2]
        payload = _prepare_quiz_answer(client, app_module, primeira)
        payload["resposta"] = str(primeira["icdas_code"])
        client.post("/quiz", data=payload)
        resposta_errada = (segunda["icdas_code"] + 1) % 7
        payload = _prepare_quiz_answer(client, app_module, segunda)
        payload["resposta"] = str(resposta_errada)
        resp = client.post("/quiz", data=payload, follow_redirects=True)
        html = resp.data.decode("utf-8")
        with client.session_transaction() as sess:
            assert sess["score_acertos"] == 1
            assert sess["score_total"] == 2

    def test_quiz_botao_proxima_imagem(self, client, app_module):
        """Após feedback, GET /quiz deve mostrar nova pergunta."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        img = imagens[0]
        # Responde (follow_redirects consome a página de feedback via GET)
        payload = _prepare_quiz_answer(client, app_module, img)
        payload["resposta"] = str(img["icdas_code"])
        client.post("/quiz", data=payload, follow_redirects=True)
        # Clica "Próxima imagem" (GET) — feedback já consumido,
        # mostra nova questão
        resp = client.get("/quiz")
        html = resp.data.decode("utf-8")
        assert 'id="quiz-answer-form"' in html and 'class="go quiz-submit"' in html
        assert "respondido" not in html or "Correto" not in html


class TestQuizIdentificacao:
    """Testa a identificação do aluno antes do quiz."""

    def test_quiz_pede_nome_antes_de_mostrar_imagem(self, client):
        with client.session_transaction() as sess:
            sess.pop("quiz_nome", None)
        resp = client.get("/quiz")
        html = resp.data.decode("utf-8")
        assert resp.status_code == 200
        assert "Seu nome" in html
        assert 'id="quiz-nome"' in html
        assert "identificador técnico" not in html
        assert "imagem_id" not in html

    def test_iniciar_quiz_grava_nome_na_sessao(self, client):
        with client.session_transaction() as sess:
            sess.pop("quiz_nome", None)
        resp = client.post(
            "/quiz/iniciar",
            data={"nome": "Maria Silva"},
            follow_redirects=True,
        )
        html = resp.data.decode("utf-8")
        assert resp.status_code == 200
        with client.session_transaction() as sess:
            assert sess["quiz_nome"] == "Maria Silva"
        assert 'id="quiz-answer-form"' in html or "Nenhuma imagem" in html

    def test_quiz_nao_prefill_nome_por_ip_compartilhado(self, client, app_module):
        ip_hash = app_module._hash_ip("127.0.0.1")
        db = sqlite3.connect(app_module.DB_PATH)
        try:
            db.execute(
                """
                INSERT INTO scores (data, total, acertos, nome, ip, ip_hash)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("2026-06-27 10:00", 3, 2, "João Souza", "127.0.0.0", ip_hash),
            )
            db.commit()
        finally:
            db.close()
        with client.session_transaction() as sess:
            sess.pop("quiz_nome", None)
        resp = client.get("/quiz")
        html = resp.data.decode("utf-8")
        assert 'value="João Souza"' not in html
        assert 'placeholder="Seu nome"' in html


# ============================================================
# TESTES DE QUIZ — EDGE CASES
# ============================================================

class TestQuizEdgeCases:
    """Testa inputs inválidos e cenários extremos."""

    def test_quiz_post_imagem_id_invalido(self, client):
        """ID inválido não deve crashar — deve redirecionar."""
        resp = client.post("/quiz", data={
            "imagem_id": "999999",
            "resposta": "3",
        })
        assert resp.status_code in (200, 302)

    def test_quiz_post_imagem_id_nao_numerico(self, client):
        """imagem_id não numérico não deve crashar."""
        resp = client.post("/quiz", data={
            "imagem_id": "abc",
            "resposta": "3",
        })
        assert resp.status_code in (200, 302)

    def test_quiz_post_resposta_vazia(self, client, app_module):
        """Resposta não enviada — deve pedir de novo."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        payload = _prepare_quiz_answer(client, app_module, imagens[0])
        resp = client.post("/quiz", data=payload)
        assert resp.status_code == 200

    def test_quiz_post_resposta_negativa(self, client, app_module):
        """Resposta -1 deve ser tratada como inválida."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        payload = _prepare_quiz_answer(client, app_module, imagens[0])
        payload["resposta"] = "-1"
        resp = client.post("/quiz", data=payload)
        html = resp.data.decode("utf-8")
        assert resp.status_code == 200
        # Não deve ter incrementado o placar
        assert "Selecione" in html
        with client.session_transaction() as sess:
            assert sess["score_total"] == 0

    def test_quiz_post_resposta_fora_do_range(self, client, app_module):
        """Resposta > 6 deve ser tratada como inválida."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        payload = _prepare_quiz_answer(client, app_module, imagens[0])
        payload["resposta"] = "99"
        resp = client.post("/quiz", data=payload)
        html = resp.data.decode("utf-8")
        assert resp.status_code == 200
        # Should show the form again with validation message, not the feedback
        assert "Selecione" in html and 'id="quiz-answer-form"' in html
        # Score should NOT have been incremented
        with client.session_transaction() as sess:
            assert sess["score_total"] == 0

    def test_quiz_post_form_completamente_vazio(self, client):
        """POST sem nenhum dado não deve crashar."""
        resp = client.post("/quiz", data={})
        assert resp.status_code in (200, 302)


# ============================================================
# TESTES DE MODO SEQUENCIAL
# ============================================================

class TestModoSequencial:
    """Testa o modo sequencial do quiz."""

    def test_ativar_modo_sequencial(self, client):
        resp = client.post("/quiz/modo", data={"modo": "sequencial"})
        assert resp.status_code == 302  # Redireciona para /quiz

    def test_desativar_modo_sequencial(self, client):
        client.post("/quiz/modo", data={"modo": "sequencial"})
        resp = client.post("/quiz/modo", data={"modo": "aleatorio"})
        assert resp.status_code == 302

    def test_sequencial_nao_repete_imagens(self, client, app_module):
        """No modo sequencial, imagens não devem se repetir."""
        imagens = app_module.get_imagens()
        if len(imagens) < 2:
            pytest.skip("Precisa de pelo menos 2 imagens")
        # Ativar modo sequencial
        client.post("/quiz/modo", data={"modo": "sequencial"})
        vistas = set()
        esperado = min(app_module.QUIZ_QUESTIONS_PER_ATTEMPT, len(imagens))
        for _ in range(esperado):
            resp = client.get("/quiz")
            html = resp.data.decode("utf-8")
            try:
                payload = _payload_from_rendered_quiz(html)
            except AssertionError:
                break
            img_id = int(payload["imagem_id"])
            assert img_id not in vistas, f"Imagem {img_id} repetida!"
            vistas.add(img_id)
            # Responde para avançar
            img = next(i for i in imagens if i["id"] == img_id)
            payload["resposta"] = str(img["icdas_code"])
            client.post("/quiz", data=payload, follow_redirects=True)
        assert len(vistas) == esperado

    def test_sequencial_completo_mostra_parabens(self, client, app_module):
        """Quando todas as imagens foram vistas, mostra tela de conclusão."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        client.post("/quiz/modo", data={"modo": "sequencial"})
        esperado = min(app_module.QUIZ_QUESTIONS_PER_ATTEMPT, len(imagens))
        for _ in range(esperado):
            resp = client.get("/quiz")
            html = resp.data.decode("utf-8")
            try:
                payload = _payload_from_rendered_quiz(html)
            except AssertionError:
                break
            img_id = int(payload["imagem_id"])
            img = next(i for i in imagens if i["id"] == img_id)
            payload["resposta"] = str(img["icdas_code"])
            client.post("/quiz", data=payload, follow_redirects=True)
        # Agora, GET /quiz deve mostrar conclusão
        resp = client.get("/quiz")
        html = resp.data.decode("utf-8")
        assert "Resultado de" in html and "Nenhum erro." in html


class TestAmostraDaTentativa:
    """Cada tentativa usa uma amostra fixa de até 10 imagens do acervo."""

    def test_tentativa_com_acervo_maior_usa_exatamente_10_imagens(self, client, app_module):
        imagens = app_module.get_imagens()
        assert len(imagens) > app_module.QUIZ_QUESTIONS_PER_ATTEMPT

        resp = client.get("/quiz")
        assert resp.status_code == 200
        with client.session_transaction() as sess:
            atual = sess.get("quiz_atual")
            fila = sess.get("quiz_fila")
            assert sess.get("quiz_total") == app_module.QUIZ_QUESTIONS_PER_ATTEMPT
            assert isinstance(fila, list)
            selecionadas = ([atual] if atual is not None else []) + fila

        assert len(selecionadas) == app_module.QUIZ_QUESTIONS_PER_ATTEMPT
        assert len(set(selecionadas)) == len(selecionadas)
        assert set(selecionadas) <= {img["id"] for img in imagens}
        assert 'max="10" value="0"' in resp.data.decode("utf-8") and '1/10' in resp.data.decode("utf-8")

    def test_amostra_nao_repete_e_respeita_limite(self, app_module):
        imagens = [{"id": i, "icdas_code": i % 7} for i in range(30)]
        fila = app_module._new_quiz_queue(imagens, modo="aleatorio")
        assert len(fila) == app_module.QUIZ_QUESTIONS_PER_ATTEMPT
        assert len(set(fila)) == len(fila)
        assert set(fila) <= {img["id"] for img in imagens}

    def test_acervo_menor_que_10_usa_todas_sem_repetir(self, app_module):
        imagens = [{"id": i, "icdas_code": i % 7} for i in range(6)]
        fila = app_module._new_quiz_queue(imagens, modo="aleatorio")
        assert len(fila) == 6
        assert set(fila) == set(range(6))

    def test_sequencial_tambem_sorteia_10_antes_de_ordenar(self, app_module, monkeypatch):
        imagens = [{"id": i, "icdas_code": (29 - i) % 7} for i in range(30)]
        escolhidas = imagens[3:13]
        monkeypatch.setattr(app_module.random, "sample", lambda population, k: escolhidas[:k])
        fila = app_module._new_quiz_queue(imagens, modo="sequencial")
        assert set(fila) == {img["id"] for img in escolhidas}
        codigo = {img["id"]: img["icdas_code"] for img in imagens}
        assert [codigo[i] for i in fila] == sorted(codigo[i] for i in fila)

    def test_sessao_legada_com_fila_grande_e_capada_em_10(self, client, app_module):
        imagens = app_module.get_imagens()
        client.get("/quiz")
        ids = [img["id"] for img in imagens]
        with client.session_transaction() as sess:
            sess["score_total"] = 3
            sess["score_acertos"] = 2
            sess["quiz_atual"] = ids[0]
            sess["quiz_fila"] = ids[1:]
            sess.pop("quiz_total", None)
            sess.pop("quiz_used_ids", None)

        resp = client.get("/quiz")
        assert resp.status_code == 200
        with client.session_transaction() as sess:
            assert sess["quiz_total"] == app_module.QUIZ_QUESTIONS_PER_ATTEMPT
            assert len(sess["quiz_fila"]) == 6
            assert sess["score_total"] + 1 + len(sess["quiz_fila"]) == 10

    def test_fila_corrompida_reinicia_tentativa_com_10(self, client, app_module):
        client.get("/quiz")
        with client.session_transaction() as sess:
            old_attempt = sess["attempt_id"]
            sess["score_total"] = 2
            sess["score_acertos"] = 1
            sess["quiz_fila"] = "corrompida"

        resp = client.get("/quiz")
        assert resp.status_code == 200
        with client.session_transaction() as sess:
            assert sess["attempt_id"] != old_attempt
            assert sess["score_total"] == 0
            assert sess["quiz_total"] == app_module.QUIZ_QUESTIONS_PER_ATTEMPT
            assert len(sess["quiz_fila"]) == 9

        db = sqlite3.connect(app_module.DB_PATH)
        old_status = db.execute("SELECT status FROM attempts WHERE id = ?", (old_attempt,)).fetchone()[0]
        db.close()
        assert old_status == "reset"

    def test_fila_perdida_apos_respostas_reinicia_sem_repetir_estado(self, client, app_module):
        imagens = app_module.get_imagens()
        img = imagens[0]
        payload = _prepare_quiz_answer(client, app_module, img)
        payload["resposta"] = str(img["icdas_code"])
        client.post("/quiz", data=payload)
        with client.session_transaction() as sess:
            old_attempt = sess["attempt_id"]
            sess["quiz_fila"] = None

        resp = client.get("/quiz")
        assert resp.status_code == 200
        with client.session_transaction() as sess:
            assert sess["attempt_id"] != old_attempt
            assert sess["score_total"] == 0
            assert sess["quiz_total"] == app_module.QUIZ_QUESTIONS_PER_ATTEMPT
            assert len(sess["quiz_fila"]) == 9

    def test_quiz_total_corrompido_nao_vaza_para_progresso(self, client, app_module):
        with client.session_transaction() as sess:
            sess["quiz_total"] = 9999
            sess["quiz_fila"] = None
        resp = client.get("/quiz")
        html = resp.data.decode("utf-8")
        assert 'max="10" value="0"' in html and '1/10' in html
        assert 'max="10"' in html

    def test_modo_aleatorio_conclui_exatamente_em_10_respostas(self, client, app_module):
        imagens = app_module.get_imagens()
        vistas = set()
        for _ in range(app_module.QUIZ_QUESTIONS_PER_ATTEMPT):
            resp = client.get("/quiz")
            payload = _payload_from_rendered_quiz(resp.data.decode("utf-8"))
            img_id = int(payload["imagem_id"])
            assert img_id not in vistas
            vistas.add(img_id)
            img = next(i for i in imagens if i["id"] == img_id)
            payload["resposta"] = str(img["icdas_code"])
            client.post("/quiz", data=payload, follow_redirects=True)

        resp = client.get("/quiz")
        assert "Resultado de" in resp.data.decode("utf-8")
        db = sqlite3.connect(app_module.DB_PATH)
        status, total = db.execute(
            "SELECT status, total FROM attempts ORDER BY id DESC LIMIT 1"
        ).fetchone()
        answers = db.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
        db.close()
        assert (status, total, answers) == ("completed", 10, 10)


# ============================================================
# TESTES DE PLACAR E PERSISTÊNCIA
# ============================================================

class TestPlacarPersistencia:
    """Testa finalizar sessão, resetar e scores."""

    def test_finalizar_sessao_salva_no_banco(self, client, app_module):
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        img = imagens[0]
        # Responde uma pergunta
        payload = _prepare_quiz_answer(client, app_module, img)
        payload["resposta"] = str(img["icdas_code"])
        client.post("/quiz", data=payload)
        # Finaliza
        resp = client.post("/quiz/finalizar")
        assert resp.status_code == 302
        # Verifica o modelo atual: tentativa + resposta individual.
        db = sqlite3.connect(app_module.DB_PATH)
        attempts = db.execute(
            "SELECT status, total, acertos FROM attempts ORDER BY id DESC LIMIT 1"
        ).fetchone()
        answers = db.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
        db.close()
        assert attempts == ("completed", 1, 1)
        assert answers == 1

    def test_finalizar_sessao_vazia_nao_salva(self, client, app_module):
        """Se total == 0, não deve criar registro."""
        client.post("/quiz/finalizar")
        db = sqlite3.connect(app_module.DB_PATH)
        rows = db.execute("SELECT * FROM attempts").fetchall()
        db.close()
        assert len(rows) == 0

    def test_resetar_limpa_placar(self, client, app_module):
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        img = imagens[0]
        payload = _prepare_quiz_answer(client, app_module, img)
        payload["resposta"] = str(img["icdas_code"])
        client.post("/quiz", data=payload)
        # Reseta
        client.post("/quiz/resetar")
        # Verifica placar zerado
        resp = client.get("/quiz")
        html = resp.data.decode("utf-8")
        with client.session_transaction() as sess:
            assert sess["score_total"] == 0

    def test_scores_mostra_historico(self, client, app_module):
        """Após finalizar, /scores deve listar a sessão."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        img = imagens[0]
        payload = _prepare_quiz_answer(client, app_module, img)
        payload["resposta"] = str(img["icdas_code"])
        client.post("/quiz", data=payload)
        client.post("/quiz/finalizar")
        resp = client.get("/scores")
        html = resp.data.decode("utf-8")
        assert "100%" in html  # 1 acerto em 1 tentativa

    def test_scores_vazio(self, client):
        resp = client.get("/scores")
        html = resp.data.decode("utf-8")
        assert "Nenhuma sessão" in html


# ============================================================
# TESTES DE SEGURANÇA
# ============================================================

class TestSeguranca:
    """Verifica headers de segurança e configurações."""

    def test_security_headers(self, client):
        resp = client.get("/")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert "strict-origin" in resp.headers.get("Referrer-Policy", "")
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp
        assert "style-src 'self'" in csp
        assert "https://cdn.jsdelivr.net" not in csp
        assert "script-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        pp = resp.headers.get("Permissions-Policy", "")
        assert "camera=()" in pp
        assert "microphone=()" in pp

    def test_finalizar_rejeita_get(self, client):
        """quiz_finalizar deve recusar GET com 405."""
        resp = client.get("/quiz/finalizar")
        assert resp.status_code == 405

    def test_resetar_rejeita_get(self, client):
        """quiz_resetar deve recusar GET com 405."""
        resp = client.get("/quiz/resetar")
        assert resp.status_code == 405

    def test_debug_desligado_por_padrao(self, app_module):
        assert not app_module.app.debug

    def test_secret_key_configurada(self, app_module):
        assert app_module.app.secret_key is not None
        assert len(app_module.app.secret_key) > 0

    def test_host_nao_confiavel_rejeitado_em_producao(self, client):
        resp = client.get("/", headers={"Host": "evil.example"})
        assert resp.status_code == 400

    def test_client_ip_prefere_header_cloudflare_valido(self, app_module):
        with app_module.app.test_request_context(
            "/",
            headers={"CF-Connecting-IP": "203.0.113.9"},
            environ_base={"REMOTE_ADDR": "172.31.252.1"},
        ):
            assert app_module._client_ip() == "203.0.113.9"

    def test_client_ip_ignora_header_cloudflare_invalido(self, app_module):
        with app_module.app.test_request_context(
            "/",
            headers={"CF-Connecting-IP": "nao-e-ip"},
            environ_base={"REMOTE_ADDR": "172.31.252.1"},
        ):
            assert app_module._client_ip() == "172.31.252.1"

    def test_init_db_remove_ip_legado(self, app_module):
        db = sqlite3.connect(app_module.DB_PATH)
        try:
            db.execute(
                """
                INSERT INTO scores (data, total, acertos, nome, ip, ip_hash)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("2026-09-05 12:00", 1, 1, "Teste", "203.0.113.0", "hash"),
            )
            db.commit()
        finally:
            db.close()
        app_module.init_db()
        db = sqlite3.connect(app_module.DB_PATH)
        try:
            assert db.execute("SELECT ip FROM scores ORDER BY id DESC LIMIT 1").fetchone()[0] == ""
        finally:
            db.close()


# ============================================================
# TESTES DE HELPERS E DADOS
# ============================================================

class TestHelpers:
    """Testa funções auxiliares e carregamento de dados."""

    def test_get_imagens_retorna_lista(self, app_module):
        imagens = app_module.get_imagens()
        assert isinstance(imagens, list)

    def test_get_imagens_tem_campos_obrigatorios(self, app_module):
        imagens = app_module.get_imagens()
        for img in imagens:
            assert "id" in img
            assert "nome" in img
            assert "caminho" in img
            assert "icdas_code" in img
            assert isinstance(img["icdas_code"], int)
            assert 0 <= img["icdas_code"] <= 6

    def test_get_imagens_ids_unicos(self, app_module):
        imagens = app_module.get_imagens()
        ids = [img["id"] for img in imagens]
        assert len(ids) == len(set(ids)), "IDs devem ser únicos"

    def test_image_id_e_estavel(self, app_module):
        caminho = "imagens/ICDAS 3a.webp"
        assert app_module._stable_image_id(caminho) == app_module._stable_image_id(caminho)
        assert app_module._stable_image_id(caminho) != app_module._stable_image_id("imagens/ICDAS 3b.webp")

    def test_acervo_cobre_todos_os_codigos(self, app_module):
        codigos = {img["icdas_code"] for img in app_module.get_imagens()}
        assert codigos == set(range(7))

    def test_lote_drive_foi_importado_completo(self, app_module):
        nomes = {img["nome"] for img in app_module.get_imagens()}
        esperados = {
            "ICDAS 0a", "ICDAS 0b", "ICDAS 0c", "ICDAS 1a",
            "ICDAS 2a", "ICDAS 2b", "ICDAS 2c",
            "ICDAS 3a", "ICDAS 3b", "ICDAS 3c", "ICDAS 3d", "ICDAS 3e",
            "ICDAS 4a", "ICDAS 4b", "ICDAS 4c", "ICDAS 5a", "ICDAS 5b",
        }
        assert esperados <= nomes

    def test_destaques_home_representam_0_a_6(self, app_module):
        destaques = app_module._imagens_destaque_home(app_module.get_imagens())
        assert [img["icdas_code"] for img in destaques] == list(range(7))

    def test_embaralhamento_balanceado_preserva_e_intercala(self, app_module):
        imagens = [
            {"id": 1, "icdas_code": 0},
            {"id": 2, "icdas_code": 0},
            {"id": 3, "icdas_code": 0},
            {"id": 4, "icdas_code": 1},
            {"id": 5, "icdas_code": 1},
            {"id": 6, "icdas_code": 1},
        ]
        fila = app_module._balanced_random_ids(imagens)
        assert len(fila) == len(set(fila)) == 6
        assert set(fila) == {1, 2, 3, 4, 5, 6}
        codigo_por_id = {img["id"]: img["icdas_code"] for img in imagens}
        assert all(
            codigo_por_id[atual] != codigo_por_id[proximo]
            for atual, proximo in zip(fila, fila[1:])
        )

    def test_descricoes_completas(self, app_module):
        """descricoes.json deve ter entradas para ICDAS 0-6."""
        for i in range(7):
            desc = app_module.DESCRICOES.get(str(i))
            assert desc is not None, f"Falta descrição para ICDAS {i}"
            assert "titulo" in desc
            assert "descricao_curta" in desc
            assert "descricao_clinica" in desc
            assert len(desc["titulo"]) > 0
            assert len(desc["descricao_clinica"]) > 10

    def test_safe_int_validos(self, app_module):
        assert app_module._safe_int("5") == 5
        assert app_module._safe_int("0") == 0
        assert app_module._safe_int("-1") == -1

    def test_safe_int_invalidos(self, app_module):
        assert app_module._safe_int(None) == -1
        assert app_module._safe_int("abc") == -1
        assert app_module._safe_int("") == -1
        assert app_module._safe_int(None, 0) == 0

    def test_imagens_excluem_logo(self, app_module):
        """Logo UFJF não deve aparecer como imagem ICDAS."""
        imagens = app_module.get_imagens()
        for img in imagens:
            assert "logo-ufjf-gv" not in img["nome"]
            assert "logo-ufjf-gv" not in img["caminho"]

    def test_descricoes_json_valido(self):
        """Arquivo descricoes.json deve ser JSON válido."""
        from pathlib import Path
        with open(Path(__file__).parent / "descricoes.json", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)
        assert len(data) >= 7


# ============================================================
# TESTES DE GALERIA
# ============================================================

class TestGaleria:
    """Testa funcionalidades da galeria."""

    def test_galeria_mostra_imagens(self, client, app_module):
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        resp = client.get("/galeria")
        html = resp.data.decode("utf-8")
        # Deve ter pelo menos uma imagem
        assert 'data-gallery-card' in html

    def test_galeria_filtros_presentes(self, client):
        resp = client.get("/galeria")
        html = resp.data.decode("utf-8")
        assert "filtrar" in html.lower() or "Todos" in html

    def test_galeria_descricoes_presentes(self, client, app_module):
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        resp = client.get("/galeria")
        html = resp.data.decode("utf-8")
        # Pelo menos uma descrição deve aparecer
        for img in imagens[:3]:
            desc = app_module.DESCRICOES.get(str(img["icdas_code"]))
            if desc:
                assert desc["titulo"] in html
                break


# ============================================================
# TESTES DE BANCO DE DADOS
# ============================================================

class TestBancoDados:
    """Testa integridade do SQLite."""

    def test_init_db_cria_tabela(self, app_module):
        db = sqlite3.connect(app_module.DB_PATH)
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='scores'"
        )
        assert cursor.fetchone() is not None
        db.close()

    def test_init_db_idempotente(self, app_module):
        """Chamar init_db duas vezes não deve dar erro."""
        app_module.init_db()
        app_module.init_db()

    def test_inserir_score(self, app_module):
        from database import recent_scores, save_score

        save_score(
            data="2026-03-02 10:00",
            total=10,
            acertos=7,
            nome="Teste",
            ip_hash="hash",
            **app_module._db_options(),
        )
        rows = recent_scores(**app_module._db_options())
        assert len(rows) == 1
        assert rows[0].total == 10
        assert rows[0].acertos == 7


# ============================================================
# TESTE DE FLUXO COMPLETO (integração)
# ============================================================

class TestFluxoCompleto:
    """Simula um usuário real usando o sistema inteiro."""

    def test_usuario_completo(self, client, app_module):
        """Simula: visita home → galeria → quiz (3 perguntas) → finaliza → vê scores."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")

        # 1. Visita a home
        resp = client.get("/")
        assert resp.status_code == 200
        assert "ICDAS" in resp.data.decode("utf-8")

        # 2. Visita a galeria
        resp = client.get("/galeria")
        assert resp.status_code == 200

        # 3. Visita sobre
        resp = client.get("/sobre")
        assert resp.status_code == 200

        # 4. Começa quiz
        resp = client.get("/quiz")
        assert resp.status_code == 200

        # 5. Responde 3 perguntas (acerta 2, erra 1)
        acertos_esperados = 0
        for i in range(3):
            img = imagens[i % len(imagens)]
            if i < 2:  # acerta as 2 primeiras
                resposta = img["icdas_code"]
                acertos_esperados += 1
            else:  # erra a terceira
                resposta = (img["icdas_code"] + 1) % 7
            payload = _prepare_quiz_answer(client, app_module, img)
            payload["resposta"] = str(resposta)
            resp = client.post("/quiz", data=payload, follow_redirects=True)
            assert resp.status_code == 200
            # Deve manter a mesma imagem (bug fix verificação), sem depender do alt.
            assert quote(img["nome"]) in resp.data.decode("utf-8")

        # 6. Finaliza sessão
        resp = client.post("/quiz/finalizar", follow_redirects=True)
        assert resp.status_code == 200

        # 7. Verifica scores
        resp = client.get("/scores")
        html = resp.data.decode("utf-8")
        assert "67%" in html  # 2 de 3

    def test_multiplas_sessoes(self, client, app_module):
        """Simula múltiplas sessões de quiz."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")

        for sessao_num in range(3):
            img = imagens[0]
            payload = _prepare_quiz_answer(client, app_module, img)
            payload["resposta"] = str(img["icdas_code"])
            client.post("/quiz", data=payload)
            client.post("/quiz/finalizar")

        resp = client.get("/scores")
        html = resp.data.decode("utf-8")
        # Deve ter 3 registros (contamos as linhas da tabela)
        assert html.count("100%") >= 3


# ============================================================
# TESTES DE ATAQUES MALICIOSOS
# ============================================================

class TestCSRF:
    """Verifica que requisições POST sem token CSRF válido são rejeitadas."""

    def test_quiz_post_sem_token_retorna_400(self, csrf_client):
        """POST em /quiz sem csrf_token → 400 Bad Request."""
        resp = csrf_client.post("/quiz", data={
            "imagem_id": "0",
            "resposta": "0",
        })
        assert resp.status_code == 400

    def test_finalizar_sem_token_retorna_400(self, csrf_client):
        """POST em /quiz/finalizar sem csrf_token → 400."""
        resp = csrf_client.post("/quiz/finalizar", data={})
        assert resp.status_code == 400

    def test_resetar_sem_token_retorna_400(self, csrf_client):
        """POST em /quiz/resetar sem csrf_token → 400."""
        resp = csrf_client.post("/quiz/resetar", data={})
        assert resp.status_code == 400

    def test_modo_sem_token_retorna_400(self, csrf_client):
        """POST em /quiz/modo sem csrf_token → 400."""
        resp = csrf_client.post("/quiz/modo", data={"modo": "sequencial"})
        assert resp.status_code == 400

    def test_token_invalido_retorna_400(self, csrf_client):
        """POST com token forjado → 400."""
        resp = csrf_client.post("/quiz", data={
            "imagem_id": "0",
            "resposta": "0",
            "csrf_token": "token-inventado-por-atacante",
        })
        assert resp.status_code == 400

    def test_token_vazio_retorna_400(self, csrf_client):
        """POST com csrf_token vazio → 400."""
        resp = csrf_client.post("/quiz/finalizar", data={
            "csrf_token": "",
        })
        assert resp.status_code == 400

    def test_get_nao_exige_csrf(self, csrf_client):
        """GET nunca exige CSRF — deve retornar 200."""
        resp = csrf_client.get("/quiz")
        assert resp.status_code == 200

    def test_get_galeria_nao_exige_csrf(self, csrf_client):
        """GET /galeria nunca exige CSRF."""
        resp = csrf_client.get("/galeria")
        assert resp.status_code == 200


class TestSQLInjection:
    """Garante que inputs com SQL injection não causam erro ou vazamento."""

    SQL_PAYLOADS = [
        "1 OR 1=1",
        "1; DROP TABLE scores; --",
        "' OR '1'='1",
        "1 UNION SELECT * FROM scores --",
        "1'; DELETE FROM scores WHERE '1'='1",
        "999999999999999999",
        "0x41424344",
        "../../../etc/passwd",
    ]

    def test_imagem_id_sql_injection_nao_crasha(self, client):
        """Qualquer payload SQL em imagem_id → no máximo 200/302, nunca 500."""
        for payload in self.SQL_PAYLOADS:
            resp = client.post("/quiz", data={
                "imagem_id": payload,
                "resposta": "3",
            })
            assert resp.status_code in (200, 302), (
                f"Payload '{payload}' causou status {resp.status_code}"
            )

    def test_resposta_sql_injection_nao_crasha(self, client, app_module):
        """Payload SQL em 'resposta' → nunca 500, nunca altera o banco."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        img = imagens[0]
        before = sqlite3.connect(
            app_module.DB_PATH
        ).execute("SELECT COUNT(*) FROM scores").fetchone()[0]
        for payload in self.SQL_PAYLOADS[:4]:
            resp = client.post("/quiz", data={
                "imagem_id": str(img["id"]),
                "resposta": payload,
            })
            assert resp.status_code in (200, 302), (
                f"Resposta '{payload}' causou {resp.status_code}"
            )
        after = sqlite3.connect(
            app_module.DB_PATH
        ).execute("SELECT COUNT(*) FROM scores").fetchone()[0]
        # Inputs inválidos não devem salvar nada no banco
        assert after == before

    def test_modo_sql_injection_ignorado(self, client):
        """Valor inválido em 'modo' → tratado como 'aleatorio', nunca 500."""
        for payload in ["' OR 1=1 --", "sequencial; DROP TABLE scores", ""]:
            resp = client.post("/quiz/modo", data={"modo": payload})
            assert resp.status_code in (200, 302)

    def test_banco_integro_apos_ataques(self, client, app_module):
        """Tabela 'scores' deve existir e estar intacta após tentativas."""
        for payload in self.SQL_PAYLOADS:
            client.post("/quiz", data={"imagem_id": payload, "resposta": "0"})
        db = sqlite3.connect(app_module.DB_PATH)
        cursor = db.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='scores'"
        )
        assert cursor.fetchone() is not None, "Tabela scores foi destruída!"
        db.close()


class TestXSS:
    """Verifica que entradas maliciosas não são renderizadas como HTML."""

    XSS_PAYLOADS = [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert(1)>",
        "javascript:alert(1)",
        "<svg onload=alert(1)>",
        "';alert('xss');//",
        "<SCRIPT SRC=http://evil.com/xss.js></SCRIPT>",
        '"><script>alert(document.cookie)</script>',
        "<body onload=alert('xss')>",
    ]

    def test_modo_xss_nao_refletido(self, client):
        """Payload XSS em 'modo' não aparece não-escapado na resposta."""
        for payload in self.XSS_PAYLOADS:
            resp = client.post(
                "/quiz/modo", data={"modo": payload},
                follow_redirects=True,
            )
            html = resp.data.decode("utf-8", errors="replace")
            # O payload literalmente não deve estar no HTML sem escaping
            assert "<script>" not in html.lower() or \
                "&lt;script&gt;" in html.lower() or \
                payload not in html, (
                f"Payload XSS refletido sem escape: {payload[:30]}"
            )
            assert "onerror=" not in html or payload not in html

    def test_imagem_id_xss_nao_refletido(self, client):
        """Payload XSS em imagem_id não é renderizado como HTML."""
        for payload in self.XSS_PAYLOADS[:3]:
            resp = client.post("/quiz", data={
                "imagem_id": payload,
                "resposta": "3",
            }, follow_redirects=True)
            html = resp.data.decode("utf-8", errors="replace")
            # Se o payload aparecer, deve estar escapado pelo Jinja2
            if payload in html:
                assert "&lt;" in html or "&#" in html, (
                    f"Payload XSS não escapado: {payload[:30]}"
                )

    def test_csp_bloqueia_scripts_inline(self, client):
        """Content-Security-Policy proíbe scripts inline (sem 'unsafe-inline')."""
        resp = client.get("/")
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "script-src 'self'" in csp
        assert "unsafe-inline" not in csp
        assert "unsafe-eval" not in csp

    def test_csp_frame_ancestors_none(self, client):
        """CSP frame-ancestors 'none' bloqueia clickjacking."""
        resp = client.get("/")
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "frame-ancestors 'none'" in csp

    def test_x_frame_options_presente(self, client):
        """X-Frame-Options bloqueia embedding em iframe."""
        resp = client.get("/")
        xfo = resp.headers.get("X-Frame-Options", "")
        assert xfo in ("DENY", "SAMEORIGIN")


class TestPathTraversal:
    """Testa tentativas de acessar arquivos fora da pasta static."""

    PATH_TRAVERSAL_URLS = [
        "/static/../app.py",
        "/static/../.env",
        "/static/../../etc/passwd",
        "/static/../requirements.txt",
        "/static/%2e%2e/app.py",
        "/static/%2e%2e%2f.env",
        "/static/..%2fapp.py",
        "/static/css/../../../app.py",
    ]

    def test_path_traversal_bloqueado(self, client):
        """Tentativas de path traversal devem retornar 404, nunca conteúdo."""
        for url in self.PATH_TRAVERSAL_URLS:
            resp = client.get(url)
            assert resp.status_code in (400, 404), (
                f"Path traversal '{url}' retornou {resp.status_code}"
            )
            # Conteúdo de app.py nunca deve aparecer na resposta
            body = resp.data.decode("utf-8", errors="replace")
            assert "import flask" not in body.lower(), (
                f"Conteúdo de app.py vazou via '{url}'"
            )
            assert "secret_key" not in body.lower(), (
                f"Segredos vazaram via '{url}'"
            )

    def test_rotas_sensiveis_nao_expostas(self, client):
        """Arquivos de configuração não devem ser acessíveis por URL."""
        arquivos_sensiveis = [
            "/.env",
            "/requirements.txt",
            "/app.py",
            "/tests.py",
            "/icdas.db",
        ]
        for url in arquivos_sensiveis:
            resp = client.get(url)
            # O Flask não serve esses arquivos — devem retornar 404
            assert resp.status_code == 404, (
                f"Arquivo sensível '{url}' acessível via HTTP "
                f"(status {resp.status_code})"
            )

    def test_static_db_nao_acessivel(self, client):
        """Banco de dados não deve ser servido nem por /static/."""
        resp = client.get("/static/icdas.db")
        assert resp.status_code == 404


class TestManipulacaoDeSessao:
    """Verifica que manipulação de dados de sessão não compromete o sistema."""

    def test_score_negativo_na_sessao_corrigido(self, client, app_module):
        """score_acertos negativo na sessão → quiz_finalizar não salva negativo."""
        with client.session_transaction() as sess:
            sess["score_acertos"] = -999
            sess["score_total"] = 5

        resp = client.post("/quiz/finalizar")
        assert resp.status_code in (200, 302)

        db = sqlite3.connect(app_module.DB_PATH)
        rows = db.execute("SELECT acertos, total FROM scores").fetchall()
        db.close()
        # Se salvou, acertos deve ser >= 0
        for row in rows:
            assert row[0] >= 0, "acertos negativos foram salvos no banco!"

    def test_acertos_maior_que_total_corrigido(self, client, app_module):
        """acertos > total na sessão → corrigido para total (min(acertos, total))."""
        with client.session_transaction() as sess:
            sess["score_acertos"] = 9999
            sess["score_total"] = 5

        client.post("/quiz/finalizar")

        db = sqlite3.connect(app_module.DB_PATH)
        rows = db.execute("SELECT acertos, total FROM scores").fetchall()
        db.close()
        if rows:
            assert rows[0][0] <= rows[0][1], (
                f"acertos ({rows[0][0]}) > total ({rows[0][1]}) no banco!"
            )

    def test_sessao_com_quiz_fila_corrompida(self, client):
        """quiz_fila corrompida na sessão não deve causar 500."""
        with client.session_transaction() as sess:
            sess["quiz_fila"] = "string-invalida"
        resp = client.get("/quiz")
        assert resp.status_code in (200, 302, 500)
        # Não deve ser 500 de forma não tratada — mas se for, é um crash
        assert resp.status_code != 500, "Sessão corrompida causou 500!"

    def test_sessao_com_quiz_atual_invalido(self, client):
        """quiz_atual inválido na sessão não deve travar (deve pegar nova img)."""
        with client.session_transaction() as sess:
            sess["quiz_atual"] = 99999  # ID que não existe
        resp = client.get("/quiz")
        assert resp.status_code == 200

    def test_sessao_com_score_total_zero_nao_salva(self, client, app_module):
        """total=0 na sessão → finalizar não deve criar registro no banco."""
        with client.session_transaction() as sess:
            sess["score_acertos"] = 0
            sess["score_total"] = 0

        client.post("/quiz/finalizar")

        db = sqlite3.connect(app_module.DB_PATH)
        rows = db.execute("SELECT * FROM scores").fetchall()
        db.close()
        assert len(rows) == 0, "Sessão vazia foi salva indevidamente!"

    def test_sessao_com_feedback_corrompido(self, client):
        """quiz_feedback corrompido na sessão não deve causar 500."""
        with client.session_transaction() as sess:
            sess["quiz_feedback"] = {
                "imagem_id": 99999,
                "correto": "nao-um-bool",
                "mensagem": None,
                "descricao_key": "DROP TABLE",
                "quiz_completo": "true",
            }
        resp = client.get("/quiz")
        assert resp.status_code in (200, 302)


class TestRateLimiting:
    """Verifica que o rate limiting bloqueia requisições excessivas."""

    def test_quiz_post_rate_limit(self, rate_client, app_module):
        """61 POSTs em /quiz disparam 429."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        img = imagens[0]
        last_status = None
        for i in range(62):
            resp = rate_client.post("/quiz", data={
                "imagem_id": str(img["id"]),
                "resposta": str(img["icdas_code"]),
            })
            last_status = resp.status_code
            if resp.status_code == 429:
                break
        assert last_status == 429, (
            "Rate limiting não ativou após 62 POSTs em /quiz"
        )

    def test_429_tem_template_customizado(self, rate_client, app_module):
        """Resposta 429 usa o template 429.html personalizado."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        img = imagens[0]
        for _ in range(62):
            resp = rate_client.post("/quiz", data={
                "imagem_id": str(img["id"]),
                "resposta": "0",
            })
            if resp.status_code == 429:
                html = resp.data.decode("utf-8")
                assert "429" in html
                assert "requisi" in html.lower()  # "requisições"
                break
        else:
            pytest.skip("Rate limit não atingido")

    def test_scores_rate_limit(self, rate_client):
        """31 GETs em /scores disparam 429."""
        last_status = None
        for i in range(32):
            resp = rate_client.get("/scores")
            last_status = resp.status_code
            if resp.status_code == 429:
                break
        assert last_status == 429, (
            "Rate limiting não ativou em /scores"
        )

    def test_finalizar_rate_limit(self, rate_client):
        """11 POSTs em /quiz/finalizar disparam 429."""
        last_status = None
        for _ in range(12):
            resp = rate_client.post("/quiz/finalizar", data={})
            last_status = resp.status_code
            if resp.status_code == 429:
                break
        assert last_status == 429, (
            "Rate limiting não ativou em /quiz/finalizar"
        )

    def test_rate_limit_nao_afeta_gets_normais(self, rate_client):
        """GET em / não tem rate limit agressivo (default 200/min é suficiente)."""
        for _ in range(20):
            resp = rate_client.get("/")
            assert resp.status_code == 200


class TestMetodosHTTP:
    """Verifica rejeição de métodos HTTP não permitidos."""

    def test_finalizar_rejeita_get(self, client):
        assert client.get("/quiz/finalizar").status_code == 405

    def test_finalizar_rejeita_put(self, client):
        assert client.put("/quiz/finalizar").status_code == 405

    def test_finalizar_rejeita_delete(self, client):
        assert client.delete("/quiz/finalizar").status_code == 405

    def test_finalizar_rejeita_patch(self, client):
        assert client.patch("/quiz/finalizar").status_code == 405

    def test_resetar_rejeita_get(self, client):
        assert client.get("/quiz/resetar").status_code == 405

    def test_resetar_rejeita_delete(self, client):
        assert client.delete("/quiz/resetar").status_code == 405

    def test_modo_rejeita_get(self, client):
        assert client.get("/quiz/modo").status_code == 405

    def test_modo_rejeita_delete(self, client):
        assert client.delete("/quiz/modo").status_code == 405

    def test_home_rejeita_post(self, client):
        assert client.post("/").status_code == 405

    def test_galeria_rejeita_post(self, client):
        assert client.post("/galeria").status_code == 405

    def test_sobre_rejeita_post(self, client):
        assert client.post("/sobre").status_code == 405

    def test_scores_rejeita_post(self, client):
        assert client.post("/scores").status_code == 405


class TestHeadersSeguranca:
    """Verifica presença e valores corretos de todos os headers de segurança."""

    def _check_all_headers(self, headers):
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert "strict-origin" in headers.get("Referrer-Policy", "")
        assert "camera=()" in headers.get("Permissions-Policy", "")
        assert "microphone=()" in headers.get("Permissions-Policy", "")
        assert headers.get("X-Permitted-Cross-Domain-Policies") == "none"
        assert headers.get("Cross-Origin-Opener-Policy") == "same-origin"
        assert headers.get("Cross-Origin-Resource-Policy") == "same-origin"
        csp = headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "form-action 'self'" in csp
        assert "base-uri 'self'" in csp

    def test_headers_em_home(self, client):
        self._check_all_headers(client.get("/").headers)

    def test_headers_em_galeria(self, client):
        self._check_all_headers(client.get("/galeria").headers)

    def test_headers_em_quiz(self, client):
        self._check_all_headers(client.get("/quiz").headers)

    def test_headers_em_scores(self, client):
        self._check_all_headers(client.get("/scores").headers)

    def test_headers_em_sobre(self, client):
        self._check_all_headers(client.get("/sobre").headers)

    def test_headers_em_404(self, client):
        self._check_all_headers(client.get("/pagina-inexistente").headers)

    def test_cache_control_no_store_em_dinamicas(self, client):
        """Rotas dinâmicas não devem ser cacheadas."""
        for url in ["/", "/galeria", "/quiz", "/scores", "/sobre"]:
            resp = client.get(url)
            cc = resp.headers.get("Cache-Control", "")
            assert "no-store" in cc, (
                f"Rota '{url}' tem Cache-Control incorreto: {cc!r}"
            )

    def test_cache_control_imutavel_em_static(self, client):
        """Assets estáticos devem ter cache longo e imutável."""
        resp = client.get("/static/css/app.css")
        cc = resp.headers.get("Cache-Control", "")
        # O arquivo pode não existir em CI, mas se retornar 200, verifica cache
        if resp.status_code == 200:
            assert "max-age=31536000" in cc
            assert "immutable" in cc

    def test_csp_sem_unsafe_inline_em_scripts(self, client):
        """CSP não permite scripts inline."""
        csp = client.get("/").headers.get("Content-Security-Policy", "")
        assert "unsafe-inline" not in csp
        assert "unsafe-eval" not in csp

    def test_css_local_versionado(self, client):
        """HTML deve usar CSS local com cache-busting."""
        html = client.get("/").data.decode("utf-8")
        assert "/static/css/app.css?v=" in html
        assert "/static/css/tailwind.css?v=" not in html
        assert "/static/css/custom.css?v=" not in html
        assert "/static/css/ui.css?v=" not in html
        assert "https://cdn.jsdelivr.net" not in html


class TestPayloadsExtremos:
    """Testa comportamento com entradas de tamanho ou formato extremos."""

    def test_payload_gigante_nao_crasha(self, client):
        """POST com body muito grande não deve causar 500."""
        payload_grande = "A" * 100_000
        resp = client.post("/quiz", data={
            "imagem_id": payload_grande,
            "resposta": payload_grande,
        })
        assert resp.status_code in (200, 302, 400, 413), (
            f"Payload gigante causou status inesperado: {resp.status_code}"
        )

    def test_muitos_campos_no_form_nao_crasha(self, client, app_module):
        """Formulário com centenas de campos não deve causar 500."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        data = {"imagem_id": str(imagens[0]["id"]), "resposta": "0"}
        data.update({f"campo_extra_{i}": f"valor_{i}" for i in range(200)})
        resp = client.post("/quiz", data=data)
        assert resp.status_code in (200, 302)

    def test_unicode_malformado_nao_crasha(self, client):
        """Caracteres Unicode especiais em imagem_id não causam 500."""
        payloads_unicode = [
            "\u0000",        # null byte
            "\uffff",        # reservado
            "𝕴𝕮𝕯𝕬𝕾",      # surrogate-range
            "\u202e",        # bidi override
            "א" * 1000,     # CJK/arabic repetido
        ]
        for payload in payloads_unicode:
            resp = client.post("/quiz", data={
                "imagem_id": payload,
                "resposta": "0",
            })
            assert resp.status_code in (200, 302, 400), (
                f"Unicode '{payload[:10]}' causou {resp.status_code}"
            )

    def test_url_extremamente_longa_retorna_404(self, client):
        """URL excessivamente longa retorna 404 ou 414, nunca 500."""
        url_longa = "/" + "a" * 8000
        resp = client.get(url_longa)
        assert resp.status_code in (400, 404, 414)

    def test_metodo_com_body_nulo(self, client):
        """POST sem corpo (content-length 0) não deve causar 500."""
        resp = client.post("/quiz", data=None,
                           content_type="application/x-www-form-urlencoded")
        assert resp.status_code in (200, 302, 400)

    def test_content_type_errado_nao_crasha(self, client):
        """POST com Content-Type JSON (não form) não deve causar 500."""
        import json as _json
        resp = client.post(
            "/quiz",
            data=_json.dumps({"imagem_id": "0", "resposta": "0"}),
            content_type="application/json",
        )
        assert resp.status_code in (200, 302, 400)


class TestRobotsERobotsAbuse:
    """Testa robots.txt e resistência a scraping/enumeração."""

    def test_robots_txt_acessivel(self, client):
        """GET /robots.txt retorna 200 com content-type text."""
        resp = client.get("/robots.txt")
        assert resp.status_code == 200
        assert "text/" in resp.content_type

    def test_robots_txt_permite_crawl_para_ler_noindex(self, client):
        """O Google precisa acessar as URLs para encontrar o noindex."""
        resp = client.get("/robots.txt")
        body = resp.data.decode("utf-8")
        assert "User-agent: *" in body
        assert "Allow: /" in body
        assert "Disallow:" not in body

    @pytest.mark.parametrize("path", ["/", "/quiz", "/scores", "/dashboard", "/static/robots.txt"])
    def test_noindex_em_paginas_e_recursos(self, client, path):
        resp = client.get(path)
        assert resp.headers["X-Robots-Tag"] == "noindex"

    def test_enumeracao_rotas_retorna_404(self, client):
        """Rotas inexistentes devem retornar 404, não 200 nem 500."""
        rotas_inexistentes = [
            "/admin", "/login", "/logout", "/api", "/config",
            "/debug", "/env", "/secret", "/backup", "/dump",
            "/quiz/delete", "/scores/delete", "/static/../secret",
        ]
        for rota in rotas_inexistentes:
            resp = client.get(rota)
            assert resp.status_code in (400, 404), (
                f"Rota '{rota}' retornou {resp.status_code} "
                f"(deveria ser 404!)"
            )

    def test_404_usa_template_customizado(self, client):
        """Página 404 usa template amigável, não stack trace."""
        resp = client.get("/rota-que-nao-existe")
        assert resp.status_code == 404
        html = resp.data.decode("utf-8")
        assert "404" in html
        # Não deve expor stack trace ou nomes de arquivo interno
        assert "Traceback" not in html
        assert "app.py" not in html


class TestModeloAcademico:
    """Cobertura do novo modelo de tentativas, respostas e dashboard."""

    def test_quiz_registra_resposta_individual_e_versao(self, client, app_module):
        imagens = app_module.get_imagens()
        img = imagens[0]
        payload = _prepare_quiz_answer(client, app_module, img)
        payload["resposta"] = str(img["icdas_code"])
        client.post("/quiz", data=payload)
        db = sqlite3.connect(app_module.DB_PATH)
        attempt = db.execute(
            "SELECT quiz_version, total, acertos FROM attempts ORDER BY id DESC LIMIT 1"
        ).fetchone()
        answer = db.execute(
            "SELECT image_key, correct_code, answered_code, correct, response_time_ms "
            "FROM answers ORDER BY id DESC LIMIT 1"
        ).fetchone()
        db.close()
        assert attempt[0].startswith("quiz-")
        assert attempt[1:] == (1, 1)
        assert answer[0] == img["caminho"]
        assert answer[1:4] == (img["icdas_code"], img["icdas_code"], 1)
        assert answer[4] is None or answer[4] >= 0

    def test_post_repetido_da_mesma_imagem_e_idempotente(self, client, app_module):
        img = app_module.get_imagens()[0]
        payload = _prepare_quiz_answer(client, app_module, img)
        payload["resposta"] = str(img["icdas_code"])
        client.post("/quiz", data=payload)
        client.post("/quiz", data=payload)
        db = sqlite3.connect(app_module.DB_PATH)
        count = db.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
        total = db.execute("SELECT total FROM attempts ORDER BY id DESC LIMIT 1").fetchone()[0]
        db.close()
        assert count == 1
        assert total == 1

    def test_reset_preserva_tentativa_anterior(self, client, app_module):
        img = app_module.get_imagens()[0]
        payload = _prepare_quiz_answer(client, app_module, img)
        payload["resposta"] = str(img["icdas_code"])
        client.post("/quiz", data=payload)
        client.post("/quiz/resetar")
        db = sqlite3.connect(app_module.DB_PATH)
        rows = db.execute("SELECT status, total FROM attempts ORDER BY id").fetchall()
        db.close()
        assert rows[0] == ("reset", 1)
        assert rows[-1][0] == "active"

    def test_troca_modo_preserva_tentativa_anterior(self, client, app_module):
        client.get("/quiz")
        client.post("/quiz/modo", data={"modo": "sequencial"})
        db = sqlite3.connect(app_module.DB_PATH)
        rows = db.execute("SELECT status, mode FROM attempts ORDER BY id").fetchall()
        db.close()
        assert rows[0][0] == "mode_change"
        assert rows[-1] == ("active", "sequencial")

    def test_duas_pessoas_mesmo_dispositivo_ficam_separadas(self, client, app_module):
        with client.session_transaction() as sess:
            sess.clear()
        client.post("/quiz/iniciar", data={"nome": "João"})
        client.post("/quiz/trocar-aluno")
        client.post("/quiz/iniciar", data={"nome": "Maria"})
        db = sqlite3.connect(app_module.DB_PATH)
        names = [row[0] for row in db.execute("SELECT name FROM participants ORDER BY id")]
        hashes = [row[0] for row in db.execute("SELECT ip_hash FROM attempts ORDER BY id")]
        db.close()
        assert names == ["João", "Maria"]
        assert len(set(hashes)) == 1
        assert hashes[0]

    def test_trocar_aluno_limpa_identidade_da_sessao(self, client):
        client.post("/quiz/trocar-aluno")
        resp = client.get("/quiz")
        html = resp.data.decode("utf-8")
        assert "Seu nome" in html

    def test_quiz_version_e_deterministica(self, app_module):
        assert app_module._quiz_version() == app_module._quiz_version()
        assert app_module._quiz_version().startswith("quiz-")

    def test_dashboard_exige_login(self, client):
        resp = client.get("/dashboard")
        assert resp.status_code == 302
        assert "/dashboard/login" in resp.headers["Location"]

    def test_dashboard_rejeita_senha_invalida(self, client):
        resp = client.post("/dashboard/login", data={"password": "errada"})
        assert resp.status_code == 401

    def test_dashboard_login_e_export(self, client, app_module):
        img = app_module.get_imagens()[0]
        payload = _prepare_quiz_answer(client, app_module, img)
        payload["resposta"] = str(img["icdas_code"])
        client.post("/quiz", data=payload)
        client.post("/quiz/finalizar")
        resp = client.post("/dashboard/login", data={"password": "test-admin"})
        assert resp.status_code == 302
        dashboard = client.get("/dashboard")
        assert dashboard.status_code == 200
        html = dashboard.data.decode("utf-8")
        assert "Dashboard do professor" in html
        assert "Matriz de confusão" in html
        export = client.get("/dashboard/export.csv")
        assert export.status_code == 200
        assert "text/csv" in export.content_type
        assert "quiz_version" in export.data.decode("utf-8").splitlines()[0]

    def test_form_ativo_carrega_attempt_id(self, client):
        html = client.get("/quiz").data.decode("utf-8")
        payload = _payload_from_rendered_quiz(html)
        assert int(payload["attempt_id"]) > 0

    def test_post_sem_attempt_id_nao_registra(self, client, app_module):
        img = app_module.get_imagens()[0]
        _prepare_quiz_answer(client, app_module, img)
        resp = client.post("/quiz", data={
            "imagem_id": str(img["id"]),
            "resposta": str(img["icdas_code"]),
        })
        assert resp.status_code == 302
        db = sqlite3.connect(app_module.DB_PATH)
        assert db.execute("SELECT COUNT(*) FROM answers").fetchone()[0] == 0
        db.close()

    def test_post_de_outra_imagem_nao_registra(self, client, app_module):
        imagens = app_module.get_imagens()
        if len(imagens) < 2:
            pytest.skip("Precisa de duas imagens")
        payload = _prepare_quiz_answer(client, app_module, imagens[0])
        payload["imagem_id"] = str(imagens[1]["id"])
        payload["resposta"] = str(imagens[1]["icdas_code"])
        resp = client.post("/quiz", data=payload)
        assert resp.status_code == 302
        db = sqlite3.connect(app_module.DB_PATH)
        assert db.execute("SELECT COUNT(*) FROM answers").fetchone()[0] == 0
        db.close()

    def test_post_stale_apos_reset_nao_entra_na_nova_tentativa(self, client, app_module):
        img = app_module.get_imagens()[0]
        stale = _prepare_quiz_answer(client, app_module, img)
        stale["resposta"] = str(img["icdas_code"])
        old_attempt = int(stale["attempt_id"])
        client.post("/quiz/resetar")
        with client.session_transaction() as sess:
            new_attempt = sess["attempt_id"]
        assert new_attempt != old_attempt
        resp = client.post("/quiz", data=stale)
        assert resp.status_code == 302
        db = sqlite3.connect(app_module.DB_PATH)
        rows = db.execute("SELECT id, total FROM attempts ORDER BY id").fetchall()
        answers = db.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
        db.close()
        assert answers == 0
        assert dict(rows)[new_attempt] == 0

    def test_finalizar_vazio_vira_empty(self, client, app_module):
        with client.session_transaction() as sess:
            sess.clear()
        client.post("/quiz/iniciar", data={"nome": "Sem resposta"})
        client.post("/quiz/finalizar")
        db = sqlite3.connect(app_module.DB_PATH)
        row = db.execute("SELECT status, total FROM attempts ORDER BY id DESC LIMIT 1").fetchone()
        db.close()
        assert row == ("empty", 0)

    def test_nome_remove_controles_e_nul(self, client, app_module):
        with client.session_transaction() as sess:
            sess.clear()
        resp = client.post("/quiz/iniciar", data={"nome": "  João\x00\u202e  Silva\n "})
        assert resp.status_code == 302
        db = sqlite3.connect(app_module.DB_PATH)
        name = db.execute("SELECT name FROM participants ORDER BY id DESC LIMIT 1").fetchone()[0]
        db.close()
        assert name == "João Silva"

    def test_nome_apenas_controles_e_rejeitado(self, client):
        with client.session_transaction() as sess:
            sess.clear()
        resp = client.post("/quiz/iniciar", data={"nome": "\x00\u202e\n\t"})
        assert resp.status_code == 400

    def test_csv_neutraliza_formula_em_nome(self, client, app_module):
        with client.session_transaction() as sess:
            sess.clear()
        client.post("/quiz/iniciar", data={"nome": '=HYPERLINK("https://invalid")'})
        img = app_module.get_imagens()[0]
        payload = _prepare_quiz_answer(client, app_module, img)
        payload["resposta"] = str(img["icdas_code"])
        client.post("/quiz", data=payload)
        client.post("/quiz/finalizar")
        client.post("/dashboard/login", data={"password": "test-admin"})
        text = client.get("/dashboard/export.csv").data.decode("utf-8")
        assert "'=HYPERLINK" in text
        assert "\n=HYPERLINK" not in text

    def test_tentativa_stale_expira_no_dashboard(self, client, app_module):
        client.get("/quiz")
        old = (datetime.now(timezone.utc) - timedelta(minutes=61)).isoformat()
        db = sqlite3.connect(app_module.DB_PATH)
        db.execute("UPDATE attempts SET started_at = ? WHERE status = 'active'", (old,))
        db.commit()
        db.close()
        app_module.analytics_snapshot(**app_module._db_options())
        db = sqlite3.connect(app_module.DB_PATH)
        status = db.execute("SELECT status FROM attempts ORDER BY id DESC LIMIT 1").fetchone()[0]
        db.close()
        assert status == "expired"

    def test_anonimo_legado_nao_vira_pessoa_no_ranking(self, app_module):
        from database import create_participant, end_attempt, record_answer, scoreboard_snapshot, start_attempt
        participant = create_participant("Anônimo", **app_module._db_options())
        attempt = start_attempt(
            participant_id=participant.id,
            mode="legacy",
            quiz_version="legacy-score-v1",
            ip_hash="",
            **app_module._db_options(),
        )
        record_answer(
            attempt_id=attempt.id,
            image_key="legacy/test",
            correct_code=0,
            answered_code=0,
            response_time_ms=None,
            question_order=1,
            **app_module._db_options(),
        )
        end_attempt(attempt.id, "completed", **app_module._db_options())
        snapshot = scoreboard_snapshot(**app_module._db_options())
        assert all(item["nome"] != "Anônimo" for item in snapshot["ranking"])

    def test_cookie_com_participant_id_stale_se_recupera(self, client, app_module):
        client.get("/quiz")
        with client.session_transaction() as sess:
            stale_participant = sess["participant_id"]
            stale_attempt = sess["attempt_id"]
            nome = sess["quiz_nome"]
        db = sqlite3.connect(app_module.DB_PATH)
        db.execute("DELETE FROM answers WHERE attempt_id = ?", (stale_attempt,))
        db.execute("DELETE FROM attempts WHERE id = ?", (stale_attempt,))
        db.execute("DELETE FROM participants WHERE id = ?", (stale_participant,))
        db.commit()
        db.close()
        resp = client.get("/quiz")
        assert resp.status_code == 200
        assert 'id="quiz-answer-form"' in resp.data.decode("utf-8")
        with client.session_transaction() as sess:
            assert sess["quiz_nome"] == nome
            recovered_participant = sess["participant_id"]
            recovered_attempt = sess["attempt_id"]
        db = sqlite3.connect(app_module.DB_PATH)
        participant_name = db.execute(
            "SELECT name FROM participants WHERE id = ?", (recovered_participant,)
        ).fetchone()[0]
        attempt_participant = db.execute(
            "SELECT participant_id FROM attempts WHERE id = ?", (recovered_attempt,)
        ).fetchone()[0]
        db.close()
        assert participant_name == nome
        assert attempt_participant == recovered_participant


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

# ---------------------------------------------------------------------------
# ICDASQuiz 2026 redesign: functional and access-control regression gates.
# ---------------------------------------------------------------------------

class TestRedesign2026:
    def test_modern_web_assets_sao_unicos_e_bundle_esta_atual(self, client):
        """Avoid duplicate font downloads and stale generated CSS."""
        from hashlib import sha256
        from pathlib import Path
        from runpy import run_path

        root = Path(__file__).resolve().parent
        font = root / 'static/fonts/onest-cb4d777c.woff2'
        assert sha256(font.read_bytes()).hexdigest().startswith('cb4d777c')
        css = (root / 'static/css/app.css').read_text()
        assert "../fonts/onest-cb4d777c.woff2" in css
        html = client.get('/').get_data(as_text=True)
        assert html.count('fonts/onest-cb4d777c.woff2') == 1
        assert html.count('css/app.css?v=') == 1
        assert html.count('rel="stylesheet"') == 2  # app + treatment tree
        assert 'fonts/onest.woff2' not in html
        build = run_path(str(root / 'tools/build_web_css.py'), run_name='_css_test')['build']
        assert css == build()

    def test_nativo_dialog_e_progresso_acessivel(self, client):
        html = client.get('/quiz').get_data(as_text=True)
        assert '<progress class="quiz-native-progress sr-only" max="10" value="0"' in html
        assert 'class="quiz-segments" aria-hidden="true"' in html
        assert 'commandfor="quiz-viewer" command="show-modal"' in html
        assert '<dialog id="quiz-viewer" class="photo-viewer"' in html
        assert 'closedby="any"' in html
        gallery = client.get('/galeria').get_data(as_text=True)
        assert '<dialog class="gallery-lightbox"' in gallery
        assert 'closedby="any"' in gallery
        home = client.get('/').get_data(as_text=True)
        assert 'class="skip-link" href="#main"' in home
        assert 'role="region" data-mini-quiz' in home

    def test_dashboard_filtra_pelo_periodo_sem_carregar_todo_historico(self, app_module):
        from database import (
            Attempt, create_participant, record_answer, session_scope,
            start_attempt, utcnow,
        )

        options = app_module._db_options()
        def add_case(name, age_days, image_key):
            person = create_participant(name, **options)
            attempt = start_attempt(
                participant_id=person.id, mode='aleatorio',
                quiz_version='performance-test', ip_hash='0' * 64,
                **options,
            )
            record_answer(
                attempt_id=attempt.id, image_key=image_key,
                correct_code=0, answered_code=0, response_time_ms=4000,
                question_order=1, **options,
            )
            with session_scope(**options) as db:
                row = db.get(Attempt, attempt.id)
                row.started_at = utcnow() - timedelta(days=age_days)
                db.commit()

        add_case('Atual', 0, 'imagens/atual.webp')
        add_case('Antigo', 70, 'imagens/antigo.webp')
        last30 = app_module.dashboard_redesign_snapshot(period='30', **options)
        last90 = app_module.dashboard_redesign_snapshot(period='90', **options)
        alltime = app_module.dashboard_redesign_snapshot(period='tudo', **options)
        assert last30['summary'][1]['value'] == 1
        assert last30['codes'][0]['n'] == 1
        assert last90['summary'][1]['value'] == 2
        assert last90['codes'][0]['n'] == 2
        assert alltime['summary'][1]['value'] == 2

    def test_galeria_modal_fechado_eh_oculto_no_css(self, client):
        stylesheet = client.get('/static/css/app.css').get_data(as_text=True)
        assert '.gallery-lightbox:not([open]){display:none!important}' in stylesheet
        assert '.gallery-lightbox[open]{display:flex' in stylesheet
        assert '.hero-deck-back{pointer-events:none;z-index:0' in stylesheet

    def test_todas_as_telas_renderizam_e_assets_sao_locais(self, client):
        routes = ("/", "/quiz", "/galeria", "/scores", "/sobre", "/arvore-de-tratamento", "/dashboard/login")
        for route in routes:
            response = client.get(route)
            assert response.status_code == 200, (route, response.status_code)
            html = response.get_data(as_text=True)
            assert 'onest-cb4d777c.woff2' in html
            assert 'app.css?v=' in html
            assert 'https://fonts.googleapis.com' not in html
            assert 'X-Robots-Tag' in response.headers
            assert response.headers['X-Robots-Tag'] == 'noindex'
            assert "style-src 'self'" in response.headers['Content-Security-Policy']
        for file in ('css/app.css', 'fonts/onest-cb4d777c.woff2', 'js/redesign.js'):
            assert client.get('/static/' + file).status_code == 200, file

    def test_quiz_que_ainda_nao_foi_respondido_nao_revela_gabarito(self, client, app_module):
        response = client.get('/quiz')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'id="quiz-answer-form"' in html
        assert 'name="resposta"' in html
        assert 'name="attempt_id"' in html
        assert 'name="imagem_id"' in html
        assert 'max="10" value="0"' in html
        assert 'quiz-feedback-card' not in html
        for desc in app_module.DESCRICOES.values():
            assert desc['descricao_clinica'] not in html

    def test_revisao_de_resultado_eh_autorizada_por_participante(self, client, app_module):
        images = app_module.get_imagens()
        for _ in range(10):
            response = client.get('/quiz')
            form = _payload_from_rendered_quiz(response.get_data(as_text=True))
            photo = next(p for p in images if p['id'] == int(form['imagem_id']))
            form['resposta'] = str(photo['icdas_code'])
            response = client.post('/quiz', data=form, follow_redirects=True)
            assert response.status_code == 200
        result = client.get('/quiz')
        html = result.get_data(as_text=True)
        assert 'quiz-thumbnails' in html
        assert html.count('data-review-index=') == 10
        assert 'Nenhum erro.' in html
        with client.session_transaction() as sess:
            participant_id = sess['participant_id']
            attempt_id = sess['last_completed_attempt_id']
        correct = app_module.attempt_review_snapshot(
            attempt_id=attempt_id, participant_id=participant_id, **app_module._db_options())
        assert correct is not None
        assert len(correct['answers']) == 10
        assert all(item['correct'] for item in correct['answers'])
        assert app_module.attempt_review_snapshot(
            attempt_id=attempt_id, participant_id=participant_id + 1000,
            **app_module._db_options()) is None
        client.post('/quiz/trocar-aluno')
        html = client.get('/quiz').get_data(as_text=True)
        assert 'quiz-thumbnails' not in html
        assert 'Seu nome' in html

    def test_dashboard_periodo_e_valores_vem_do_banco(self, client, app_module):
        image = app_module.get_imagens()[0]
        form = _prepare_quiz_answer(client, app_module, image)
        form['resposta'] = str((image['icdas_code'] + 1) % 7)
        client.post('/quiz', data=form, follow_redirects=True)
        client.post('/quiz/finalizar')
        report = app_module.dashboard_redesign_snapshot(
            period='30', **app_module._db_options())
        assert report['summary'][1]['value'] == 1
        assert report['completed'] == 1
        assert report['codes'][image['icdas_code']]['n'] == 1
        assert report['codes'][image['icdas_code']]['pct'] == 0
        assert report['confusion'][image['icdas_code']][(image['icdas_code'] + 1) % 7] == 1
        assert sum(sum(row) for row in report['confusion']) == 1
        assert report['students'][0]['name'] == 'Aluno Teste'
        assert sum(n for _, n in report['statuses']) == 1
        assert client.get('/dashboard').status_code == 302
        assert client.post('/dashboard/login', data={'password': 'test-admin'}).status_code == 302
        for value in ('30','90','tudo'):
            r = client.get(f'/dashboard?periodo={value}')
            assert r.status_code == 200
            html = r.get_data(as_text=True)
            assert 'Matriz de confusão' in html
            assert 'Tentativas recentes' in html
            assert f'href="/dashboard?periodo={value}" aria-current="true"' in html
            assert 'IP técnico' in html
        assert 'href="/dashboard?periodo=30" aria-current="true"' in client.get(
            '/dashboard?periodo=invalid').get_data(as_text=True)

    def test_galeria_filtro_abre_categoria_via_url(self, client):
        response = client.get('/galeria?codigo=4')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'data-gallery-filter="4"' in html
        assert 'data-gallery-card' in html
        assert 'gallery-lightbox' in html
        assert 'galeria.js' in html

class TestHandoffFinish2026:
    """Regression gates for approved visual details and progressive mobile zoom."""

    def test_landing_exemplos_abrem_dialog_por_codigo(self, client, app_module):
        html = client.get('/').get_data(as_text=True)
        assert html.count('data-scale-open="') == 7
        assert html.count('data-scale-photo ') == len(app_module.get_imagens())
        assert 'id="scale-lightbox"' in html
        assert 'closedby="any"' in html
        assert 'data-scale-prev' in html and 'data-scale-next' in html
        assert 'data-pinch-zoom' in html
        assert 'js/scale.js' in html and 'js/image-zoom.js' in html
        assert 'href="/galeria?codigo=0"' in html
        assert 'data-treatment-tree' in html

    def test_arvore_guia_visual_e_breadcrumbs_sem_nova_regra(self, client):
        for route in ('/', '/arvore-de-tratamento'):
            html = client.get(route).get_data(as_text=True)
            assert 'data-tree-cut-extent' in html
            assert 'data-tree-cut-readout' in html
            assert 'data-tree-crumbs' in html
            assert 'Representação de corte transversal de um dente' in html
            assert 'em revisão clínica' in html
        controller = client.get('/static/js/arvore_tratamento.js').get_data(as_text=True)
        for required in ('showCut(', 'updateGuide(', 'data-crumb-field', 'pointerover', 'focusin'):
            assert required in controller
        assert 'Meyer-Lueckel & Paris, 2016' in controller

    def test_zoom_e_motion_pref_progressive(self, client):
        css = client.get('/static/css/app.css').get_data(as_text=True)
        assert '@keyframes hero-word-in' in css
        assert '@keyframes hero-blob-float' in css
        assert 'prefers-reduced-motion:reduce' in css
        assert 'data-pinch-zoom' in client.get('/galeria').get_data(as_text=True)
        assert 'js/image-zoom.js' in client.get('/galeria').get_data(as_text=True)
        quiz = client.get('/quiz').get_data(as_text=True)
        assert 'data-pinch-zoom' in quiz
        assert 'js/image-zoom.js' in quiz
        js = client.get('/static/js/image-zoom.js').get_data(as_text=True)
        assert 'pointermove' in js
        assert 'Math.hypot' in js
        assert 'wheel' in js
        assert 'pinch-ready' in js

class TestMicrointeractionPolish20261115:
    """Contract tests for the handoff's answer-feedback and touch states."""

    def test_miniquiz_expoe_badge_legivel_e_placar(self, client):
        html = client.get('/').get_data(as_text=True)
        assert 'data-mini-quiz' in html
        assert 'data-demo-result-badge hidden aria-hidden="true"' in html
        assert 'data-demo-score' in html
        assert 'aria-live="polite" aria-atomic="true" data-demo-hint' in html
        assert html.count('data-demo-code="') >= 9  # 2 public photos + 7 keys
        assert html.count('class="quiz-code k" data-demo-code') == 7
        assert 'hero-deck-back' in html and 'hero-deck-back back2' in html

    def test_miniquiz_corretas_erradas_e_avanco_protegidos(self, client):
        js = client.get('/static/js/redesign.js').get_data(as_text=True)
        # Select only the code buttons; photo data attributes also contain a code.
        assert ".demo-codes button[data-demo-code]" in js
        assert "const isAnswer = item.dataset.demoCode === correct" in js
        assert "item.classList.toggle('is-correct', isAnswer)" in js
        assert "item.classList.toggle('is-wrong', isChoice && !isRight)" in js
        assert "item.classList.toggle('is-dim', !isAnswer && !isChoice)" in js
        assert "current >= cards.length || checking" in js
        assert "lock?.querySelector('.go')?.focus" in js

    def test_geometria_animacao_e_navegacao_movel(self, client):
        css = client.get('/static/css/app.css').get_data(as_text=True)
        assert '.quiz-codes:not(.demo-codes){padding:11px 8px 5px' in css
        assert 'icdas-answer-pop' in css and 'icdas-answer-shake' in css
        assert 'icdas-feedback-enter' in css and 'icdas-badge-enter' in css
        assert 'prefers-reduced-motion:no-preference' in css
        assert '.polish-reveal' in css
        assert '.site-header .site-nav a.nav-anchor{display:none}' in css
        assert '.site-header .site-nav a:first-child{display:none}' in css
        assert '.site-header .site-nav a{display:inline-flex;align-items:center;min-height:44px}' in css

    def test_feedback_longo_e_acessivel_em_celulares_pequenos(self, client):
        """A long ICDAS explanation must scroll, not be clipped or unreachable."""
        html = client.get('/quiz').get_data(as_text=True)
        assert 'class="quiz-response-scroll" tabindex="0"' in html
        assert 'aria-label="Opções de classificação ICDAS"' in html
        css = client.get('/static/css/app.css').get_data(as_text=True)
        assert '.quiz-workspace.has-feedback .quiz-response-scroll{scrollbar-width:thin' in css
        assert 'min-height:44px' in css

    def test_acoes_contextuais_e_alvos_da_arvore(self, client):
        quiz_js = client.get('/static/js/quiz.js').get_data(as_text=True)
        assert "button.classList.toggle('is-ready', Boolean(active))" in quiz_js
        css = client.get('/static/css/app.css').get_data(as_text=True)
        assert 'icdas-cta-ready' in css
        tree = client.get('/static/css/arvore_tratamento.css').get_data(as_text=True)
        assert '.tree-choices--code .tree-option{--code-diameter:44px}' in tree
