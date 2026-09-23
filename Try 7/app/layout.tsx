import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] });
const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] });

export const metadata: Metadata = {
  title: { default: 'RCA Fieldwork · Try 7', template: '%s · RCA Fieldwork Try 7' },
  description: 'Evidence-backed, specialist-led root-cause investigation across independent model tracks.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={geistSans.variable + ' ' + geistMono.variable}>{children}</body>
    </html>
  );
}
