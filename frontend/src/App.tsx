import {useMemo, useRef, useState} from 'react';
import {useTranslation} from 'react-i18next';
import {useNavigate} from 'react-router-dom';
import {AppHeader} from './shared/components/AppHeader';
import {AppSidebar} from './shared/components/AppSidebar';
import {SettingsModal} from './shared/components/SettingsModal';
import {AppRouter} from './router/AppRouter';
import {createApiClient} from './shared/api/client';
import {useChat} from './features/tax-assistant/hooks/useChat';
import {useConversations} from './features/tax-assistant/hooks/useConversations';

export default function App() {
  const {t, i18n} = useTranslation();
  const [token, setToken] = useState(() => localStorage.getItem('taxora-token') || '');
  const tokenRef = useRef(token);
  tokenRef.current = token;
  const request = useMemo(() => createApiClient(() => tokenRef.current), []);
  const navigate = useNavigate();
  const history = useConversations(request, token);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
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

  async function sendQuestion(question: string, period: string, taxpayer: string) {
    if (!token) {
      setSettingsOpen(true);
      setError(t('errors.missingToken'));
      return;
    }
    setError('');
    await chat.sendQuestion(question, period, taxpayer, i18n.resolvedLanguage === 'id' ? 'id' : 'en');
  }

  function saveToken(value: string) {
    localStorage.setItem('taxora-token', value);
    tokenRef.current = value;
    setToken(value);
    setSettingsOpen(false);
    setError('');
  }

  function disconnect() {
    localStorage.removeItem('taxora-token');
    tokenRef.current = '';
    setToken('');
    setSettingsOpen(false);
    history.startNew();
  }

  return (
    <div className={`app-shell ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <AppSidebar
        activeConversation={history.activeId}
        conversations={history.conversations}
        token={token}
        mobileOpen={mobileNavOpen}
        onNewChat={newConversation}
        onOpenConversation={selectConversation}
        onOpenSettings={() => setSettingsOpen(true)}
        onCloseMobile={() => setMobileNavOpen(false)}
      />
      <main id="main-content" className="main-area">
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
      <SettingsModal
        open={settingsOpen}
        token={token}
        onClose={() => setSettingsOpen(false)}
        onSave={saveToken}
        onDisconnect={disconnect}
      />
    </div>
  );
}
