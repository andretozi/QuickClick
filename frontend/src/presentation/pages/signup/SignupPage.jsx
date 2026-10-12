import AuthLayout from '@/presentation/components/AuthLayout/AuthLayout.jsx';
import BrandPanel from '@/presentation/components/BrandPanel/BrandPanel.jsx';
import SignupForm from './components/SignupForm/SignupForm.jsx';
import { SIGNUP_PANEL } from '@/domain/content/authContent.js';

/** Tela de cadastro: o mesmo padrão do login, com o painel da marca e o formulário. */
export default function SignupPage() {
  return (
    <AuthLayout panel={<BrandPanel content={SIGNUP_PANEL} />}>
      <SignupForm />
    </AuthLayout>
  );
}
