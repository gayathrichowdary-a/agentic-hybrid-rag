import "./globals.css";

export const metadata = { title: "Agentic Hybrid RAG", description: "Ask questions across your own documents." };

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
