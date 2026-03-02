"""
Testes abrangentes para o ICDAS Educacional.
Rodar com: python -m pytest tests.py -v
"""
import json
import os
import sqlite3

import pytest

# Configura ambiente ANTES de importar o app
os.environ["FLASK_DEBUG"] = "0"
os.environ["SECRET_KEY"] = "test-secret-key-only-for-testing"


@pytest.fixture(autouse=True)
def _setup_db(tmp_path, monkeypatch):
    """Cada teste usa um banco temporário isolado."""
    db_path = str(tmp_path / "test_icdas.db")
    monkeypatch.setenv("DB_PATH", db_path)
    # Re-importar para usar o novo DB_PATH não funciona  
    # em vez disso, configuramos diretamente no módulo
    import app as app_module
    app_module.DB_PATH = db_path
    app_module.init_db()
    yield db_path


@pytest.fixture
def client():
    import app as app_module
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"
    with app_module.app.test_client() as c:
        yield c


@pytest.fixture
def app_module():
    import app as app_module
    return app_module


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
        assert "Classificação" in resp.data.decode("utf-8")

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

    def test_quiz_post_resposta_correta(self, client, app_module):
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        img = imagens[0]
        resp = client.post("/quiz", data={
            "imagem_id": str(img["id"]),
            "resposta": str(img["icdas_code"]),
        }, follow_redirects=True)
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
        resp = client.post("/quiz", data={
            "imagem_id": str(img["id"]),
            "resposta": str(resposta_errada),
        }, follow_redirects=True)
        html = resp.data.decode("utf-8")
        assert "Incorreto" in html
        assert "✗" in html

    def test_quiz_mesma_imagem_apos_resposta(self, client, app_module):
        """Bug crítico corrigido: imagem não deve mudar após POST."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        img = imagens[0]
        resp = client.post("/quiz", data={
            "imagem_id": str(img["id"]),
            "resposta": str(img["icdas_code"]),
        }, follow_redirects=True)
        html = resp.data.decode("utf-8")
        # A imagem original deve estar presente (URL-encoded por url_for)
        assert img["nome"] in html

    def test_quiz_placar_sessao(self, client, app_module):
        """Placar deve incrementar durante a sessão."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        img = imagens[0]
        # Primeira resposta
        client.post("/quiz", data={
            "imagem_id": str(img["id"]),
            "resposta": str(img["icdas_code"]),
        })
        # Segunda resposta (errada)
        resposta_errada = (img["icdas_code"] + 1) % 7
        resp = client.post("/quiz", data={
            "imagem_id": str(img["id"]),
            "resposta": str(resposta_errada),
        }, follow_redirects=True)
        html = resp.data.decode("utf-8")
        # Deve mostrar 1/2
        assert "1 / 2" in html

    def test_quiz_botao_proxima_imagem(self, client, app_module):
        """Após feedback, GET /quiz deve mostrar nova pergunta."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        img = imagens[0]
        # Responde (follow_redirects consome a página de feedback via GET)
        client.post("/quiz", data={
            "imagem_id": str(img["id"]),
            "resposta": str(img["icdas_code"]),
        }, follow_redirects=True)
        # Clica "Próxima imagem" (GET) — feedback já consumido,
        # mostra nova questão
        resp = client.get("/quiz")
        html = resp.data.decode("utf-8")
        assert "Verificar Resposta" in html  # Deve mostrar form de novo
        assert "respondido" not in html or "Correto" not in html


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
        resp = client.post("/quiz", data={
            "imagem_id": str(imagens[0]["id"]),
        })
        assert resp.status_code == 200

    def test_quiz_post_resposta_negativa(self, client, app_module):
        """Resposta -1 deve ser tratada como inválida."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        resp = client.post("/quiz", data={
            "imagem_id": str(imagens[0]["id"]),
            "resposta": "-1",
        })
        html = resp.data.decode("utf-8")
        assert resp.status_code == 200
        # Não deve ter incrementado o placar
        assert "Selecione" in html or "0 / 0" in html

    def test_quiz_post_resposta_fora_do_range(self, client, app_module):
        """Resposta > 6 deve ser tratada como inválida."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        resp = client.post("/quiz", data={
            "imagem_id": str(imagens[0]["id"]),
            "resposta": "99",
        })
        html = resp.data.decode("utf-8")
        assert resp.status_code == 200
        # Should show the form again with validation message, not the feedback
        assert "Selecione" in html or "Verificar Resposta" in html
        # Score should NOT have been incremented
        assert "0 / 0" in html

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
        for _ in range(len(imagens)):
            resp = client.get("/quiz")
            html = resp.data.decode("utf-8")
            # Extrair imagem_id do formulário
            import re
            match = re.search(r'name="imagem_id"\s+value="(\d+)"', html)
            if not match:
                # Pode ter completado todas
                break
            img_id = int(match.group(1))
            assert img_id not in vistas, f"Imagem {img_id} repetida!"
            vistas.add(img_id)
            # Responde para avançar
            img = next(i for i in imagens if i["id"] == img_id)
            client.post("/quiz", data={
                "imagem_id": str(img_id),
                "resposta": str(img["icdas_code"]),
            }, follow_redirects=True)
        assert len(vistas) == len(imagens)

    def test_sequencial_completo_mostra_parabens(self, client, app_module):
        """Quando todas as imagens foram vistas, mostra tela de conclusão."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        client.post("/quiz/modo", data={"modo": "sequencial"})
        for _ in range(len(imagens)):
            resp = client.get("/quiz")
            html = resp.data.decode("utf-8")
            import re
            match = re.search(r'name="imagem_id"\s+value="(\d+)"', html)
            if not match:
                break
            img_id = int(match.group(1))
            img = next(i for i in imagens if i["id"] == img_id)
            client.post("/quiz", data={
                "imagem_id": str(img_id),
                "resposta": str(img["icdas_code"]),
            }, follow_redirects=True)
        # Agora, GET /quiz deve mostrar conclusão
        resp = client.get("/quiz")
        html = resp.data.decode("utf-8")
        assert "Parabéns" in html or "completou" in html


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
        client.post("/quiz", data={
            "imagem_id": str(img["id"]),
            "resposta": str(img["icdas_code"]),
        })
        # Finaliza
        resp = client.post("/quiz/finalizar")
        assert resp.status_code == 302
        # Verifica no banco
        db = sqlite3.connect(app_module.DB_PATH)
        rows = db.execute("SELECT * FROM scores").fetchall()
        db.close()
        assert len(rows) == 1
        assert rows[0][2] == 1  # total
        assert rows[0][3] == 1  # acertos

    def test_finalizar_sessao_vazia_nao_salva(self, client, app_module):
        """Se total == 0, não deve criar registro."""
        client.post("/quiz/finalizar")
        db = sqlite3.connect(app_module.DB_PATH)
        rows = db.execute("SELECT * FROM scores").fetchall()
        db.close()
        assert len(rows) == 0

    def test_resetar_limpa_placar(self, client, app_module):
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        img = imagens[0]
        client.post("/quiz", data={
            "imagem_id": str(img["id"]),
            "resposta": str(img["icdas_code"]),
        })
        # Reseta
        client.post("/quiz/resetar")
        # Verifica placar zerado
        resp = client.get("/quiz")
        html = resp.data.decode("utf-8")
        assert "0 / 0" in html

    def test_scores_mostra_historico(self, client, app_module):
        """Após finalizar, /scores deve listar a sessão."""
        imagens = app_module.get_imagens()
        if not imagens:
            pytest.skip("Sem imagens")
        img = imagens[0]
        client.post("/quiz", data={
            "imagem_id": str(img["id"]),
            "resposta": str(img["icdas_code"]),
        })
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
        assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
        assert "strict-origin" in resp.headers.get("Referrer-Policy", "")
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp
        assert "https://cdn.jsdelivr.net" in csp
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
        with open("descricoes.json", encoding="utf-8") as f:
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
        assert "imagem-item" in html

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
        db = app_module.get_db()
        try:
            db.execute(
                "INSERT INTO scores (data, total, acertos) VALUES (?, ?, ?)",
                ("2026-03-02 10:00", 10, 7),
            )
            db.commit()
            rows = db.execute("SELECT * FROM scores").fetchall()
            assert len(rows) == 1
            assert rows[0]["total"] == 10
            assert rows[0]["acertos"] == 7
        finally:
            db.close()


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
            resp = client.post("/quiz", data={
                "imagem_id": str(img["id"]),
                "resposta": str(resposta),
            }, follow_redirects=True)
            assert resp.status_code == 200
            # Deve manter a mesma imagem (bug fix verificação)
            assert img["nome"] in resp.data.decode("utf-8")

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
            client.post("/quiz", data={
                "imagem_id": str(img["id"]),
                "resposta": str(img["icdas_code"]),
            })
            client.post("/quiz/finalizar")

        resp = client.get("/scores")
        html = resp.data.decode("utf-8")
        # Deve ter 3 registros (contamos as linhas da tabela)
        assert html.count("100%") >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
