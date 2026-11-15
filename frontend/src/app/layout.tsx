import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CogniVault — Evidence-First Adaptive Learning",
  description: "Study from your own course material with a tutor that cites every answer, verified practice questions, and a learner model that adapts.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 antialiased selection:bg-indigo-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
