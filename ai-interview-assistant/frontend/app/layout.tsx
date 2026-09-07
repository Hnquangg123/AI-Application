import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("host") ?? "localhost:3000";
  const protocol = requestHeaders.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  const origin = `${protocol}://${host}`;
  const socialImage = `${origin}/og.png`;

  return {
    metadataBase: new URL(origin),
    title: "MockMate — AI Interview Practice",
    description: "A friendly AI interview coach for realistic, adaptive practice sessions.",
    openGraph: {
      title: "MockMate — AI Interview Practice",
      description: "Practice. Reflect. Grow.",
      type: "website",
      images: [{ url: socialImage, width: 1733, height: 909, alt: "MockMate AI interview practice" }],
    },
    twitter: {
      card: "summary_large_image",
      title: "MockMate — AI Interview Practice",
      description: "Practice. Reflect. Grow.",
      images: [socialImage],
    },
  };
}

const themeInitScript = `
  try {
    const saved = localStorage.getItem("mockmate.theme");
    const theme = saved === "light" || saved === "dark"
      ? saved
      : matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    document.documentElement.dataset.theme = theme;
  } catch {
    document.documentElement.dataset.theme = "light";
  }
`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
