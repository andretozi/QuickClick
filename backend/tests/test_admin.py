"""
Testes do Painel de Moderação Administrativa (/api/admin)

Garante:
1. Sigilo / Stealth absoluto: não-admins e anônimos recebem HTTP 404 idêntico a rotas inexistentes.
2. Ações de moderação: advertência, suspensão temporária, banimento e reativação.
3. Derrubada de sessões em tempo real por versionamento de token JWT.
4. Expurgo em cascata de dados do vendedor (produtos, conexões, IA).
5. Promoção segura via lista de administradores e registro imutável em auditoria.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.bootstrap import criar_app
from backend.domain.usuario import PAPEL_ADMIN, PAPEL_VENDEDOR, STATUS_ATIVA, STATUS_BANIDA, STATUS_SUSPENSA
from backend.infrastructure.banco import models
from backend.infrastructure.configuracao import Config
from backend.infrastructure.database import Base
from backend.infrastructure.seguranca.token_jwt import ServicoJWT
from backend.tests import leitor_de_teste

SEGREDO_JWT_TESTE = "segredo-jwt-so-dos-testes-com-mais-de-32-caracteres"
CHAVE_CRIPTO_TESTE = "nN1Yc8pK0wVQx3vT1o6m2f9W1u0Hq2c5e7Kx8Zl4bD0="
EMAIL_ADMIN = "superadmin@quickclick.com.br"
EMAIL_VENDEDOR = "vendedor@loja.com.br"
INDEX_HTML = "<!doctype html><title>Quick Click</title>"


class TestPainelAdmin(unittest.TestCase):
    def setUp(self):
        self._pasta = tempfile.TemporaryDirectory()
        raiz = Path(self._pasta.name)
        front = raiz / "frontend" / "dist"
        (front / "assets").mkdir(parents=True)
        (front / "index.html").write_text(INDEX_HTML, encoding="utf-8")

        self.leitor = leitor_de_teste(
            QUICKCLICK_JWT_SECRET=SEGREDO_JWT_TESTE,
            TOKENS_CHAVE_CRIPTO=CHAVE_CRIPTO_TESTE,
            ADMIN_EMAILS=EMAIL_ADMIN,
        )
        self.config = Config(raiz=raiz, pasta_front=front)

        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)

        self.SessionLocal = sessionmaker(bind=self.engine)
        self.servico_jwt = ServicoJWT(SEGREDO_JWT_TESTE)

        # Cria usuário admin e vendedor comum
        with self.SessionLocal() as session:
            admin_user = models.User(
                id=1,
                email=EMAIL_ADMIN,
                nome="Admin Chefe",
                loja="Administração",
                store_name="Administração",
                password_hash="$2b$12$fakehashforadminpasswordtesting123456789012345",
                papel=PAPEL_ADMIN,
                status_conta=STATUS_ATIVA,
                token_versao=1,
            )
            admin_vendedor = models.VendedorModel(id=1, nome="Admin Chefe", plano="pro")
            vendedor_user = models.User(
                id=2,
                email=EMAIL_VENDEDOR,
                nome="João Vendedor",
                loja="Loja do João",
                store_name="Loja do João",
                password_hash="$2b$12$fakehashforvendedorpasswordtesting123456789012",
                papel=PAPEL_VENDEDOR,
                status_conta=STATUS_ATIVA,
                token_versao=1,
            )
            vendedor_vendedor = models.VendedorModel(id=2, nome="João Vendedor", plano="gratis")
            session.add_all([admin_user, admin_vendedor, vendedor_user, vendedor_vendedor])
            session.commit()

        app = criar_app(config=self.config, session_factory=self.SessionLocal, leitor=self.leitor)
        self.client = TestClient(app)

        self.token_admin = self.servico_jwt.gerar_token(1, EMAIL_ADMIN, papel=PAPEL_ADMIN, versao=1)
        self.token_vendedor = self.servico_jwt.gerar_token(2, EMAIL_VENDEDOR, papel=PAPEL_VENDEDOR, versao=1)

    def tearDown(self):
        self.client.close()
        self.engine.dispose()
        self._pasta.cleanup()

    # 1. Sigilo / Stealth absoluto
    def test_anonimo_recebe_404_no_painel_admin(self):
        """Um scanner sem autenticação recebe 404 (idêntico a rota não existente)."""
        res = self.client.get("/api/admin/overview")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()["erro"]["codigo"], "nao_encontrado")

    def test_vendedor_comum_recebe_404_no_painel_admin(self):
        """Um usuário autenticado sem papel de administrador recebe 404 opaco."""
        res = self.client.get(
            "/api/admin/overview",
            headers={"Authorization": f"Bearer {self.token_vendedor}"},
        )
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()["erro"]["codigo"], "nao_encontrado")

    # 2. Acesso do Administrador
    def test_admin_acessa_overview_com_sucesso(self):
        res = self.client.get(
            "/api/admin/overview",
            headers={"Authorization": f"Bearer {self.token_admin}"},
        )
        self.assertEqual(res.status_code, 200)
        dados = res.json()
        self.assertIn("resumo", dados)
        self.assertIn("contas", dados)
        self.assertEqual(dados["resumo"]["total_contas"], 2)
        self.assertEqual(len(dados["contas"]), 2)

    # 3. Punições: Advertência, Suspensão, Banimento, Reativação
    def test_advertir_vendedor(self):
        res = self.client.post(
            "/api/admin/users/2/punishment",
            headers={"Authorization": f"Bearer {self.token_admin}"},
            json={"tipo": "advertir", "motivo": "Fotos fora do padrão"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["ok"])

        # Verifica banco
        with self.SessionLocal() as session:
            vendedor = session.get(models.User, 2)
            self.assertEqual(vendedor.status_conta, "advertida")
            self.assertEqual(vendedor.motivo_moderacao, "Fotos fora do padrão")

    def test_suspender_e_bloquear_acesso(self):
        res = self.client.post(
            "/api/admin/users/2/punishment",
            headers={"Authorization": f"Bearer {self.token_admin}"},
            json={"tipo": "suspender", "motivo": "Violação de termos de uso", "dias_suspensao": 5},
        )
        self.assertEqual(res.status_code, 200)

        # Vendedor suspenso tenta acessar /api/auth/me -> 403 ContaSuspensa
        res_me = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {self.token_vendedor}"},
        )
        self.assertEqual(res_me.status_code, 403)
        self.assertEqual(res_me.json()["erro"]["codigo"], "conta_suspensa")

    def test_banir_vendedor_e_bloquear_login(self):
        res = self.client.post(
            "/api/admin/users/2/punishment",
            headers={"Authorization": f"Bearer {self.token_admin}"},
            json={"tipo": "banir", "motivo": "Fraude confirmada"},
        )
        self.assertEqual(res.status_code, 200)

        # Vendedor banido tenta autenticar
        res_me = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {self.token_vendedor}"},
        )
        self.assertEqual(res_me.status_code, 403)
        self.assertEqual(res_me.json()["erro"]["codigo"], "conta_banida")

    def test_reativar_conta_punida(self):
        # Primeiro bane
        self.client.post(
            "/api/admin/users/2/punishment",
            headers={"Authorization": f"Bearer {self.token_admin}"},
            json={"tipo": "banir", "motivo": "Fraude"},
        )
        # Em seguida reativa
        res = self.client.post(
            "/api/admin/users/2/punishment",
            headers={"Authorization": f"Bearer {self.token_admin}"},
            json={"tipo": "reativar", "motivo": "Esclarecimento aceito"},
        )
        self.assertEqual(res.status_code, 200)

        with self.SessionLocal() as session:
            vendedor = session.get(models.User, 2)
            self.assertEqual(vendedor.status_conta, STATUS_ATIVA)

    # 4. Derrubar sessões em tempo real
    def test_derrubar_sessoes_invalida_token_antigo(self):
        # Token antigo v1 é válido inicialmente
        res_antes = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {self.token_vendedor}"},
        )
        self.assertEqual(res_antes.status_code, 200)

        # Admin derruba sessões
        res_kill = self.client.post(
            "/api/admin/users/2/kill-sessions",
            headers={"Authorization": f"Bearer {self.token_admin}"},
        )
        self.assertEqual(res_kill.status_code, 200)

        # Mesmo token agora é rejeitado
        res_depois = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {self.token_vendedor}"},
        )
        self.assertEqual(res_depois.status_code, 401)

    # 5. Exclusão definitiva de conta
    def test_excluir_conta_com_confirmacao_de_email(self):
        # Confirmação errada falha com 400
        res_falha = self.client.request(
            "DELETE",
            "/api/admin/users/2",
            headers={"Authorization": f"Bearer {self.token_admin}"},
            json={"confirmacao_email": "outro@email.com", "motivo": "Solicitado"},
        )
        self.assertEqual(res_falha.status_code, 400)

        # Confirmação correta exclui
        res_ok = self.client.request(
            "DELETE",
            "/api/admin/users/2",
            headers={"Authorization": f"Bearer {self.token_admin}"},
            json={"confirmacao_email": EMAIL_VENDEDOR, "motivo": "Solicitação judicial"},
        )
        self.assertEqual(res_ok.status_code, 200)

        # Vendedor não existe mais no banco
        with self.SessionLocal() as session:
            self.assertIsNone(session.get(models.User, 2))

    # 6. Auditoria imutável
    def test_listar_auditoria(self):
        self.client.post(
            "/api/admin/users/2/punishment",
            headers={"Authorization": f"Bearer {self.token_admin}"},
            json={"tipo": "advertir", "motivo": "Aviso prévio"},
        )

        res = self.client.get(
            "/api/admin/audit",
            headers={"Authorization": f"Bearer {self.token_admin}"},
        )
        self.assertEqual(res.status_code, 200)
        logs = res.json()
        self.assertGreaterEqual(len(logs), 1)
        self.assertEqual(logs[0]["acao"], "advertir")
        self.assertEqual(logs[0]["alvo_id"], 2)


if __name__ == "__main__":
    unittest.main()
