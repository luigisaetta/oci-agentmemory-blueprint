import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Agent Memory Console",
  description: "Oracle Agent Memory example console",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
