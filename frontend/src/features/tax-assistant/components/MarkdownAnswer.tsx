import Markdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Answers are written by the LLM in Markdown. Rendering rules:
// - Raw HTML is never rendered (react-markdown escapes it by default): the text comes from a model that read
//   untrusted documents, so it must not be able to inject markup or scripts.
// - Links are shown as plain text. The model is told never to invent URLs, and verified links appear only in
//   the source cards, which come from the database.
// - Images are dropped.
const components: Components = {
  a: ({ children }) => <span className="md-link-text">{children}</span>,
  img: () => null,
  table: ({ children }) => <div className="md-table"><table>{children}</table></div>,
  h1: ({ children }) => <h4>{children}</h4>,
  h2: ({ children }) => <h4>{children}</h4>,
  h3: ({ children }) => <h5>{children}</h5>,
}

export function MarkdownAnswer({ text }: { text: string }) {
  return <div className="message-content markdown">
    <Markdown remarkPlugins={[remarkGfm]} components={components} skipHtml>{text}</Markdown>
  </div>
}
