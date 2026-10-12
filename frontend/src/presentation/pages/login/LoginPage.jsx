import AuthLayout from '@/presentation/components/AuthLayout/AuthLayout.jsx';
import BrandPanel from '@/presentation/components/BrandPanel/BrandPanel.jsx';
import LoginForm from './components/LoginForm/LoginForm.jsx';
import { BRAND_PANEL } from '@/domain/content/loginContent.js';

/** Tela de login: painel da marca de um lado e o formulário do outro. */
export default function LoginPage() {
  return (
    <AuthLayout panel={<BrandPanel content={BRAND_PANEL} />}>
      <LoginForm />
    </AuthLayout>
  );
}
