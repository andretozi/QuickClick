import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.infrastructure.banco.models import User, MarketplaceToken, AiUsage, VendedorModel, ContaVinculadaModel
from backend.infrastructure.database import Base, get_db


class TestDatabaseModels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        cls.Session = sessionmaker(bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.session = self.Session()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def test_tabelas_criadas(self):
        table_names = Base.metadata.tables.keys()
        self.assertIn("users", table_names)
        self.assertIn("marketplace_tokens", table_names)
        self.assertIn("ai_usage", table_names)
        self.assertIn("vendedores", table_names)
        self.assertIn("contas_vinculadas", table_names)

    def test_criar_e_consultar_usuario(self):
        user = User(
            email="vendedor@quickclick.com",
            password_hash="hash_secreto_123",
        )
        self.session.add(user)
        self.session.commit()

        consultado = self.session.query(User).filter_by(email="vendedor@quickclick.com").first()
        self.assertIsNotNone(consultado)
        self.assertEqual(consultado.email, "vendedor@quickclick.com")
        self.assertEqual(consultado.password_hash, "hash_secreto_123")

    def test_marketplace_token_vinculado_a_usuario(self):
        user = User(email="seller@quickclick.com", password_hash="hash_seller")
        self.session.add(user)
        self.session.commit()

        token = MarketplaceToken(
            user_id=user.id,
            access_token="access_token_ml_123",
            refresh_token="refresh_token_ml_456",
        )
        self.session.add(token)
        self.session.commit()

        token_consultado = self.session.query(MarketplaceToken).filter_by(user_id=user.id).first()
        self.assertIsNotNone(token_consultado)
        self.assertEqual(token_consultado.access_token, "access_token_ml_123")
        self.assertEqual(token_consultado.refresh_token, "refresh_token_ml_456")

    def test_ai_usage_creditos_padrao(self):
        user = User(email="ai_user@quickclick.com", password_hash="hash_ai")
        self.session.add(user)
        self.session.commit()

        usage = AiUsage(user_id=user.id)
        self.session.add(usage)
        self.session.commit()

        usage_consultado = self.session.query(AiUsage).filter_by(user_id=user.id).first()
        self.assertIsNotNone(usage_consultado)
        self.assertEqual(usage_consultado.credits_left, 3)

    def test_vendedor_e_conta_vinculada(self):
        vendedor = VendedorModel(id=1, nome="Loja Demo", plano="gratis")
        self.session.add(vendedor)
        self.session.commit()

        conta = ContaVinculadaModel(
            vendedor_id=vendedor.id,
            marketplace="mercado-livre",
            conectada_em="2026-10-15T12:00:00",
            access_token="tok_123",
            refresh_token="ref_456",
            token_expira_em="2026-10-15T18:00:00",
        )
        self.session.add(conta)
        self.session.commit()

        v_cons = self.session.query(VendedorModel).filter_by(id=1).first()
        c_cons = self.session.query(ContaVinculadaModel).filter_by(vendedor_id=1).first()
        self.assertIsNotNone(v_cons)
        self.assertIsNotNone(c_cons)
        self.assertEqual(c_cons.marketplace, "mercado-livre")

    def test_get_db_generator(self):
        generator = get_db()
        db = next(generator)
        self.assertIsNotNone(db)
        try:
            next(generator)
        except StopIteration:
            pass
        finally:
            generator.close()


if __name__ == "__main__":
    unittest.main()
