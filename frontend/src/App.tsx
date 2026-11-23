import {useMemo, useState, type CSSProperties} from 'react';
import {useTranslation} from 'react-i18next';
import {useLocation, useNavigate} from 'react-router-dom';
import {AppHeader} from './shared/components/AppHeader';
import {AppSidebar} from './shared/components/AppSidebar';
import {AppRouter} from './router/AppRouter';
import {createApiClient} from './shared/api/client';
import {useChat} from './features/tax-assistant/hooks/useChat';
import {useConversations} from './features/tax-assistant/hooks/useConversations';
import {AuthPage} from './shared/auth/pages/AuthPage';
import {useSidebarWidth} from './shared/hooks/useSidebarWidth';
import {useAuth} from './shared/auth/AuthProvider';

export default function App() {
  const {i18n, t} = useTranslation();
  const auth = useAuth();
  const request = useMemo(() => createApiClient(), []);
  const navigate = useNavigate();
  const {pathname} = useLocation();
  const history = useConversations(request, auth.user?.id || '');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const sidebar = useSidebarWidth();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [error, setError] = useState('');

  const chat = useChat({
    request,
    conversationId: history.activeId,
    setConversationId: history.setActiveId,
    messages: history.messages,
    setMessages: history.setMessages,
    refreshConversations: history.refresh,
    onError: setError,
  });

  function newConversation() {
    history.startNew();
    setError('');
    navigate('/');
    setMobileNavOpen(false);
  }

  async function renameConversation(id: string, title: string) {
    try {
      await history.rename(id, title);
      return true;
    } catch (renameError) {
      setError((renameError as Error).message);
      return false;
    }
  }

  async function deleteConversation(id: string) {
    try {
      await history.remove(id);
      return true;
    } catch (deleteError) {
      setError((deleteError as Error).message);
      return false;
    }
  }

  async function selectConversation(id: string) {
    try {
      await history.open(id);
      navigate('/');
      setMobileNavOpen(false);
      setError('');
    } catch (loadError) {
      setError((loadError as Error).message);
    }
  }

  async function sendQuestion(question: string) {
    setError('');
    await chat.sendQuestion(question, i18n.resolvedLanguage === 'id' ? 'id' : 'en');
  }

  async function signOut() {
    try { await auth.signOut(); }
    catch { /* Clear local account state even if the server is temporarily unavailable. */ }
    finally { history.startNew(); }
  }

  if (auth.loading) return <main className="auth-screen"><p className="auth-loading">{t('auth.checkingSession')}</p></main>;
  if (!auth.user) return <AuthPage />;

  return (
    <div className={`app-shell ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`} style={{'--sidebar-width': `${sidebar.width}px`} as CSSProperties}>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <AppSidebar
        activeConversation={history.activeId}
        conversations={history.conversations}
        user={auth.user}
        mobileOpen={mobileNavOpen}
        onNewChat={newConversation}
        onOpenConversation={selectConversation}
        onRenameConversation={renameConversation}
        onDeleteConversation={deleteConversation}
        onSignOut={() => void signOut()}
        width={sidebar.width}
        onResize={sidebar.resize}
        onResizeEnd={sidebar.save}
        onCloseMobile={() => setMobileNavOpen(false)}
      />
      {/* The chat fills the screen: only the messages scroll, the composer stays at the bottom. */}
      <main id="main-content" className={`main-area ${pathname === '/' ? 'chat-layout' : ''}`}>
        <AppHeader
          onToggleSidebar={() => setSidebarCollapsed((value) => !value)}
          onOpenMobile={() => setMobileNavOpen(true)}
        />
        <AppRouter
          request={request}
          messages={history.messages}
          busy={chat.busy}
          error={error}
          feedback={chat.feedback}
          setError={setError}
          onSend={sendQuestion}
          onFeedback={chat.submitFeedback}
        />
      </main>
    </div>
  );
}
